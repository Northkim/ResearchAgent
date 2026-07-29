"""Supervised OpenAlex Works search adapter.

All OpenAlex payloads are untrusted data.  The adapter performs protocol
translation only: it never owns workflow state, ranking, persistence, or
artifact publication.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import httpx

from backend.research.contracts import (
    FieldRejectionDiagnostic,
    PaperAuthor,
    PaperRecord,
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    ResearchQuery,
    SearchExecution,
    SearchPlan,
    SearchStatistics,
    SearchDiagnosticCode,
    canonical_hash,
    normalize_doi,
    sha256_bytes,
)
from backend.research.ports import (
    PaperSearchProvider,
    PaperSearchResult,
    ProviderError,
    ProviderIdentity,
    ProviderRequestContext,
)

_OPENALEX_ID = re.compile(r"^(?:https://openalex\.org/)?(W\d+)$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRET_LIKE = re.compile(
    r"(?i)(?:(?:api[_-]?key|authorization|bearer|token|secret)\s*[:=]\s*\S+"
    r"|sk-[a-z0-9_-]{8,})"
)
_CONTRACT_SNAPSHOT = "openalex-works-api/2026-07-27"
_VALIDATOR_VERSION = "openalex-field-validator/v2"
_SAFE_PREVIEW_LIMIT = 80
_REQUESTED_FIELDS = (
    "id",
    "doi",
    "display_name",
    "authorships",
    "abstract_inverted_index",
    "publication_year",
    "publication_date",
    "primary_location",
    "language",
    "type",
    "updated_date",
)


@dataclass(frozen=True, slots=True)
class OpenAlexConfiguration:
    api_key: str | None = field(default=None, repr=False)
    base_url: str = "https://api.openalex.org"
    timeout_seconds: float = 15.0
    retries_after_initial: int = 2
    max_discovery_requests: int = 3
    max_candidates: int = 20
    max_selected_workflow_results: int = 5
    max_response_bytes: int = 2 * 1024 * 1024
    user_agent: str = "ReAgent/9B-1 (supervised scholarly metadata discovery)"

    def __post_init__(self) -> None:
        if self.base_url != "https://api.openalex.org":
            raise ValueError("OpenAlex base_url must use the approved official endpoint")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 15:
            raise ValueError("OpenAlex timeout_seconds must be in (0, 15]")
        if not 0 <= self.retries_after_initial <= 2:
            raise ValueError("OpenAlex retries_after_initial must be in [0, 2]")
        if not 1 <= self.max_discovery_requests <= 3:
            raise ValueError("OpenAlex max_discovery_requests must be in [1, 3]")
        if not 1 <= self.max_candidates <= 20:
            raise ValueError("OpenAlex max_candidates must be in [1, 20]")
        if not 3 <= self.max_selected_workflow_results <= 5:
            raise ValueError("OpenAlex selected workflow result cap must be in [3, 5]")
        if self.max_response_bytes <= 0:
            raise ValueError("OpenAlex max_response_bytes must be positive")
        if self.api_key is not None and not self.api_key.strip():
            raise ValueError("OpenAlex api_key cannot be blank")


@dataclass(frozen=True, slots=True)
class OpenAlexHttpResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


class _FieldRejection(ValueError):
    def __init__(self, diagnostic: FieldRejectionDiagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic.category.value)


class OpenAlexTransport(Protocol):
    async def get(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        timeout_seconds: float,
        headers: Mapping[str, str],
    ) -> OpenAlexHttpResponse: ...


class HttpxOpenAlexTransport:
    """Small transport wrapper that never exposes credential-bearing URLs."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def get(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        timeout_seconds: float,
        headers: Mapping[str, str],
    ) -> OpenAlexHttpResponse:
        response: httpx.Response | None = None
        failure: ProviderError | None = None
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(timeout_seconds),
                follow_redirects=False,
                headers=dict(headers),
            ) as client:
                response = await client.get(path, params=dict(params))
        except httpx.TimeoutException:
            failure = ProviderError(
                ProviderFailureCategory.PROVIDER_TIMEOUT,
                "OpenAlex request timed out",
                retryable=True,
                safe_details={"failure_point": "http_transport"},
            )
        except httpx.HTTPError:
            failure = ProviderError(
                ProviderFailureCategory.PROVIDER_UNAVAILABLE,
                "OpenAlex network request failed",
                retryable=True,
                safe_details={"failure_point": "http_transport"},
            )
        # Raise only after leaving the HTTP exception handler.  httpx request
        # errors retain their Request object, including query parameters such
        # as api_key; chaining or retaining that exception would make a
        # credential-bearing URL available to traceback/error collectors.
        if failure is not None:
            raise failure
        if response is None:
            raise RuntimeError("OpenAlex transport completed without a response")
        return OpenAlexHttpResponse(
            status_code=response.status_code,
            body=response.content,
            headers={
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower()
                in {
                    "retry-after",
                    "x-ratelimit-limit",
                    "x-ratelimit-remaining",
                    "x-ratelimit-credits-used",
                    "x-ratelimit-reset",
                    "x-request-id",
                }
            },
        )


class OpenAlexPaperSearchProvider(PaperSearchProvider):
    IDENTITY = ProviderIdentity(
        provider="openalex",
        adapter_version="1.0.0",
        model_or_endpoint="GET /works?search=",
    )

    def __init__(
        self,
        configuration: OpenAlexConfiguration,
        *,
        transport: OpenAlexTransport | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], Any] | None = None,
    ) -> None:
        self.configuration = configuration
        self._transport = transport or HttpxOpenAlexTransport(configuration.base_url)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper or asyncio.sleep

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    def request_identity(
        self,
        query: ResearchQuery,
        *,
        limit: int,
    ) -> Mapping[str, Any]:
        self._validate_limit(limit)
        plan = self._search_plan(
            query,
            limit=limit,
            planned_at=datetime(2000, 1, 1, tzinfo=UTC),
        )
        return {
            "query_hash": query.query_hash,
            "search_plan_fingerprint": plan.fingerprint,
            "exact_query": self._exact_query(query),
            "filters": self._filters(query),
            "discovery_limit": self.configuration.max_candidates,
            "selected_paper_limit": limit,
            "cursor": "*",
            "maximum_pages": 1,
            "requested_fields": list(_REQUESTED_FIELDS),
            "provider": self.identity.provider,
            "adapter_version": self.identity.adapter_version,
            "api_contract_snapshot": _CONTRACT_SNAPSHOT,
        }

    async def search(
        self,
        query: ResearchQuery,
        *,
        limit: int,
        context: ProviderRequestContext,
    ) -> PaperSearchResult:
        if context.cancellation_requested:
            raise ProviderError(
                ProviderFailureCategory.CANCELLED,
                "OpenAlex request was cancelled before execution",
                retryable=False,
            )
        self._validate_limit(limit)
        exact_query = self._exact_query(query)
        planned_at = self._now()
        plan = self._search_plan(
            query,
            limit=limit,
            planned_at=planned_at,
        )
        started = time.monotonic()
        requests = 0
        retries = 0
        request_ids: list[str] = []

        # Fail closed before a billable search if free daily credit cannot cover it.
        try:
            rate_response = await self._request(
                "/rate-limit",
                params=self._auth_params({}),
                context=context,
            )
            requests += 1
            request_ids.extend(self._request_ids(rate_response))
            rate_payload = self._decode_json(rate_response, failure_point="rate_limit")
            self._assert_free_credit(rate_payload)
        except ProviderError as error:
            if requests == 0 and error.safe_details.get("failure_point") != (
                "operation_deadline"
            ):
                requests = 1
            raise self._with_failure_usage(error, requests, retries, started) from error

        params = self._auth_params(
            {
                "search": exact_query,
                "filter": self._filters(query),
                "per_page": str(self.configuration.max_candidates),
                "cursor": "*",
                "select": ",".join(_REQUESTED_FIELDS),
            }
        )
        response: OpenAlexHttpResponse | None = None
        for attempt in range(self.configuration.retries_after_initial + 1):
            try:
                response = await self._request("/works", params=params, context=context)
                requests += 1
                request_ids.extend(self._request_ids(response))
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise self._http_error(response)
                if response.status_code >= 400:
                    raise self._http_error(response)
                break
            except ProviderError as error:
                requests += 1 if response is None else 0
                if not error.retryable or attempt >= self.configuration.retries_after_initial:
                    raise self._with_failure_usage(error, requests, retries, started)
                retries += 1
                await self._sleep_before_retry(attempt, response)
                response = None
        if response is None:
            raise AssertionError("OpenAlex retry loop completed without a response")

        try:
            payload = self._decode_json(response, failure_point="works")
            papers, mapping = self._map_results(payload, retrieved_at=self._now())
            meta = payload.get("meta")
            if not isinstance(meta, Mapping):
                raise ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex response is missing meta",
                    retryable=False,
                    safe_details={"failure_point": "response_meta"},
                )
            count = meta.get("count", 0)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex response count is invalid",
                    retryable=False,
                    safe_details={"failure_point": "response_meta"},
                )
            per_page = meta.get("per_page")
            if (
                not isinstance(per_page, int)
                or isinstance(per_page, bool)
                or not 1 <= per_page <= 100
            ):
                raise ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex response per_page is invalid",
                    retryable=False,
                    safe_details={"failure_point": "response_meta"},
                )
            next_cursor = meta.get("next_cursor")
            if next_cursor is not None and not isinstance(next_cursor, str):
                raise ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex response next_cursor is invalid",
                    retryable=False,
                    safe_details={"failure_point": "response_meta"},
                )
            cost = self._decimal_string(meta.get("cost_usd"))
            if cost == "unknown":
                raise ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex response cost_usd is invalid",
                    retryable=False,
                    safe_details={"failure_point": "response_meta"},
                )
        except ProviderError as error:
            raise self._with_failure_usage(error, requests, retries, started) from error
        complete = mapping["received"] >= min(self.configuration.max_candidates, count)
        warnings = list(mapping["warnings"])
        if not complete:
            warnings.append("OpenAlex page did not provide the requested candidate count")
            raise self._with_failure_usage(
                ProviderError(
                    ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                    "OpenAlex returned an incomplete bounded discovery page",
                    retryable=False,
                    safe_details={
                        "failure_point": "incomplete_page",
                        "provider_count": count,
                        "records_normalized": len(papers),
                    },
                ),
                requests,
                retries,
                started,
            )
        retrieved_at = self._now()
        usage = ProviderUsage(
            provider=self.identity.provider,
            model_or_endpoint=self.identity.model_or_endpoint,
            operation_kind=ProviderOperationKind.SEARCH,
            request_count=requests,
            input_tokens=0,
            output_tokens=0,
            # Provider credit usage is recorded separately.  This is the
            # project monetary/out-of-pocket budget in whole minor units.
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=max(0, int((time.monotonic() - started) * 1000)),
            retry_count=retries,
            provider_request_ids=tuple(dict.fromkeys(request_ids)),
        )
        execution = SearchExecution(
            search_plan_fingerprint=plan.fingerprint,
            provider=self.identity.provider,
            adapter_version=self.identity.adapter_version,
            endpoint="/works?search=",
            requested_fields=_REQUESTED_FIELDS,
            request_count=requests,
            retry_count=retries,
            complete=complete,
            cursor_pages=1,
            retrieved_at=retrieved_at,
            provider_reported_cost_usd=cost,
            provider_request_ids=usage.provider_request_ids,
            warnings=tuple(warnings),
        )
        statistics = SearchStatistics(
            search_plan_fingerprint=plan.fingerprint,
            provider_reported_count=count,
            records_received=mapping["received"],
            records_normalized=len(papers),
            records_rejected=mapping["rejected"],
            duplicate_doi_count=mapping["duplicate_doi"],
            duplicate_provider_id_count=mapping["duplicate_provider_id"],
            advisory_title_year_clusters=mapping["advisory_clusters"],
            missing_abstract_count=mapping["missing_abstract"],
            incomplete=not complete,
        )
        return PaperSearchResult(
            papers=papers,
            usage=usage,
            request_fingerprint=context.request_fingerprint,
            retrieved_at=retrieved_at,
            complete=complete,
            warnings=tuple(warnings),
            search_plan=plan,
            search_execution=execution,
            search_statistics=statistics,
            rejection_diagnostics=mapping["rejection_diagnostics"],
        )

    def _search_plan(
        self,
        query: ResearchQuery,
        *,
        limit: int,
        planned_at: datetime,
    ) -> SearchPlan:
        return SearchPlan(
            topic=query.topic,
            research_question=None,
            keywords=query.keywords,
            exact_query=self._exact_query(query),
            year_from=query.year_from,
            year_to=query.year_to,
            language_policy=f"{query.language}: advisory metadata; not a hard filter",
            document_type_policy="broad scholarly Works; type is advisory",
            inclusion_criteria=("An abstract is available for abstract-only review.",),
            exclusion_criteria=("No abstract is available.",),
            maximum_results=self.configuration.max_candidates,
            pagination_policy={
                "mode": "cursor",
                "initial_cursor": "*",
                "maximum_pages": 1,
                "per_page": self.configuration.max_candidates,
            },
            sort_policy="OpenAlex default relevance descending; citation count is not a ReAgent quality score",
            provider=self.identity.provider,
            adapter_version=self.identity.adapter_version,
            api_contract_snapshot=_CONTRACT_SNAPSHOT,
            planned_at=planned_at,
        )

    async def _request(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        context: ProviderRequestContext,
    ) -> OpenAlexHttpResponse:
        if context.deadline is not None and self._now() >= context.deadline:
            raise ProviderError(
                ProviderFailureCategory.PROVIDER_TIMEOUT,
                "OpenAlex operation deadline expired",
                retryable=False,
                safe_details={"failure_point": "operation_deadline"},
            )
        response = await self._transport.get(
            path,
            params=params,
            timeout_seconds=self.configuration.timeout_seconds,
            headers={"accept": "application/json", "user-agent": self.configuration.user_agent},
        )
        if len(response.body) > self.configuration.max_response_bytes:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex response exceeded the configured size limit",
                retryable=False,
                safe_details={"failure_point": "response_size"},
            )
        if path == "/rate-limit" and response.status_code >= 400:
            raise self._http_error(response)
        return response

    def _auth_params(self, params: Mapping[str, str]) -> dict[str, str]:
        result = dict(params)
        if self.configuration.api_key is not None:
            result["api_key"] = self.configuration.api_key
        return result

    def _assert_free_credit(self, payload: Mapping[str, Any]) -> None:
        rate = payload.get("rate_limit")
        if not isinstance(rate, Mapping):
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex rate-limit response has an unexpected schema",
                retryable=False,
                safe_details={"failure_point": "rate_limit_schema"},
            )
        try:
            remaining = Decimal(str(rate["daily_remaining_usd"]))
            search_cost = Decimal(str(rate["endpoint_costs_usd"]["search"]))
        except (KeyError, TypeError, InvalidOperation) as error:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex rate-limit response is missing free-credit fields",
                retryable=False,
                safe_details={"failure_point": "rate_limit_schema"},
            ) from error
        if remaining < search_cost:
            raise ProviderError(
                ProviderFailureCategory.BUDGET_EXCEEDED,
                "OpenAlex free daily credit cannot cover the supervised search",
                retryable=False,
                safe_details={
                    "failure_point": "free_credit_preflight",
                    "required_usd": str(search_cost),
                    "remaining_usd": str(remaining),
                },
            )

    def _map_results(
        self,
        payload: Mapping[str, Any],
        *,
        retrieved_at: datetime,
    ) -> tuple[tuple[PaperRecord, ...], dict[str, Any]]:
        results = payload.get("results")
        if not isinstance(results, list):
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex response results must be an array",
                retryable=False,
                safe_details={"failure_point": "results_schema"},
            )
        if len(results) > self.configuration.max_candidates:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex returned more records than the bounded request allowed",
                retryable=False,
                safe_details={"failure_point": "results_count"},
            )
        papers: list[PaperRecord] = []
        warnings: list[str] = []
        rejected = 0
        missing_abstract = 0
        duplicate_doi = 0
        duplicate_provider_id = 0
        doi_seen: set[str] = set()
        provider_seen: set[str] = set()
        title_year: Counter[tuple[str, int | None]] = Counter()
        rejection_diagnostics: list[FieldRejectionDiagnostic] = []
        for index, raw in enumerate(results):
            if not isinstance(raw, Mapping):
                rejected += 1
                warnings.append(f"record[{index}] rejected: not an object")
                continue
            try:
                paper = self._map_work(raw, retrieved_at=retrieved_at)
            except _FieldRejection as error:
                rejected += 1
                rejection_diagnostics.append(error.diagnostic)
                warnings.append(
                    f"record[{index}] rejected: {error.diagnostic.category.value}"
                )
                continue
            except ValueError as error:
                rejected += 1
                warnings.append(f"record[{index}] rejected: {str(error)[:120]}")
                continue
            if paper.doi and paper.doi in doi_seen:
                duplicate_doi += 1
                continue
            if paper.provider_id in provider_seen:
                duplicate_provider_id += 1
                continue
            if paper.doi:
                doi_seen.add(paper.doi)
            provider_seen.add(paper.provider_id)
            if paper.abstract is None:
                missing_abstract += 1
            title_year[(self._normalize_title(paper.title), paper.publication_year)] += 1
            papers.append(paper)
        advisory = sum(1 for count in title_year.values() if count > 1)
        return tuple(papers), {
            "received": len(results),
            "rejected": rejected,
            "duplicate_doi": duplicate_doi,
            "duplicate_provider_id": duplicate_provider_id,
            "advisory_clusters": advisory,
            "missing_abstract": missing_abstract,
            "warnings": tuple(warnings),
            "rejection_diagnostics": tuple(rejection_diagnostics),
        }

    def _map_work(self, raw: Mapping[str, Any], *, retrieved_at: datetime) -> PaperRecord:
        identifier = raw.get("id")
        if not isinstance(identifier, str):
            raise ValueError("missing OpenAlex work ID")
        match = _OPENALEX_ID.fullmatch(identifier.strip())
        if match is None:
            raise ValueError("malformed OpenAlex work ID")
        provider_id = match.group(1)
        title = self._clean_required(
            raw.get("display_name"),
            "title",
            maximum=500,
            record_identity=provider_id,
        )
        limitations: list[str] = ["identity_unverified_discovery_only"]
        authors: list[PaperAuthor] = []
        authorships = raw.get("authorships")
        if isinstance(authorships, list):
            for authorship in authorships[:100]:
                if not isinstance(authorship, Mapping):
                    continue
                author = authorship.get("author")
                if not isinstance(author, Mapping):
                    continue
                name = self._clean_optional(
                    author.get("display_name"),
                    field_name="author.display_name",
                    maximum=300,
                    record_identity=provider_id,
                )
                if not name:
                    continue
                author_id = self._openalex_optional_id(author.get("id"), prefix="A")
                orcid = self._clean_optional(
                    author.get("orcid"),
                    field_name="author.orcid",
                    maximum=50,
                    record_identity=provider_id,
                )
                authors.append(
                    PaperAuthor(
                        name=name,
                        provider_author_id=author_id,
                        orcid=orcid,
                    )
                )
        if not authors:
            limitations.append("authors_missing")
        abstract = self._reconstruct_abstract(
            raw.get("abstract_inverted_index"),
            record_identity=provider_id,
        )
        if abstract is None:
            limitations.append("abstract_missing")
        doi: str | None = None
        raw_doi = raw.get("doi")
        if isinstance(raw_doi, str):
            try:
                doi = normalize_doi(raw_doi)
            except ValueError:
                limitations.append("doi_malformed")
        else:
            limitations.append("doi_missing")
        year = raw.get("publication_year")
        if not isinstance(year, int) or isinstance(year, bool) or not 1000 <= year <= 2100:
            year = None
            limitations.append("publication_year_missing_or_invalid")
        venue: str | None = None
        location = raw.get("primary_location")
        if isinstance(location, Mapping):
            source = location.get("source")
            if isinstance(source, Mapping):
                venue = self._clean_optional(
                    source.get("display_name"),
                    field_name="primary_location.source.display_name",
                    maximum=500,
                    record_identity=provider_id,
                )
        if venue is None:
            limitations.append("venue_missing")
        language = self._clean_optional(
            raw.get("language"),
            field_name="language",
            maximum=20,
            record_identity=provider_id,
        )
        if language is None:
            limitations.append("language_missing")
        return PaperRecord(
            paper_id=PaperRecord.internal_id(
                provider=self.identity.provider,
                provider_id=provider_id,
                doi=doi,
            ),
            provider_id=provider_id,
            title=title,
            authors=tuple(authors),
            abstract=abstract,
            publication_year=year,
            publication_venue=venue,
            source_provider=f"{self.identity.provider}@{self.identity.adapter_version}",
            source_url=f"https://openalex.org/{provider_id}",
            doi=doi,
            retrieved_at=retrieved_at,
            raw_metadata_hash=canonical_hash(raw),
            language=language,
            metadata_limitations=tuple(dict.fromkeys(limitations)),
        )

    def _reconstruct_abstract(
        self,
        value: Any,
        *,
        record_identity: str | None = None,
    ) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("abstract_inverted_index is not an object")
        positions: dict[int, str] = {}
        for token, indexes in value.items():
            clean = self._clean_required(
                token,
                "abstract_inverted_index.token",
                maximum=200,
                record_identity=record_identity,
            )
            if not isinstance(indexes, list):
                raise ValueError("abstract positions are not an array")
            for index in indexes:
                if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                    raise ValueError("abstract position is invalid")
                if index in positions:
                    raise ValueError("abstract positions overlap")
                positions[index] = clean
        if not positions:
            return None
        if max(positions) >= 10_000 or set(positions) != set(range(max(positions) + 1)):
            raise ValueError("abstract positions are incomplete or too large")
        abstract = " ".join(positions[index] for index in range(len(positions)))
        if len(abstract) > 50_000:
            raise _FieldRejection(
                self._field_rejection(
                    category=SearchDiagnosticCode.FIELD_LENGTH_REJECTED,
                    field_name="abstract",
                    normalized_value=abstract,
                    configured_limit=50_000,
                    record_identity=record_identity,
                )
            )
        return abstract

    def _decode_json(
        self,
        response: OpenAlexHttpResponse,
        *,
        failure_point: str,
    ) -> Mapping[str, Any]:
        try:
            value = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex returned malformed JSON",
                retryable=False,
                safe_details={"failure_point": failure_point},
            ) from error
        if not isinstance(value, Mapping):
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "OpenAlex response root must be an object",
                retryable=False,
                safe_details={"failure_point": failure_point},
            )
        return value

    def _http_error(self, response: OpenAlexHttpResponse) -> ProviderError:
        status = response.status_code
        if status == 401:
            category = ProviderFailureCategory.PROVIDER_AUTHENTICATION
        elif status == 403:
            category = ProviderFailureCategory.PROVIDER_RATE_LIMIT
        elif status == 429:
            category = ProviderFailureCategory.PROVIDER_RATE_LIMIT
        elif status >= 500:
            category = ProviderFailureCategory.PROVIDER_UNAVAILABLE
        elif status == 400:
            category = ProviderFailureCategory.INVALID_QUERY
        else:
            category = ProviderFailureCategory.PROVIDER_UNAVAILABLE
        return ProviderError(
            category,
            f"OpenAlex request failed with HTTP {status}",
            retryable=status in {403, 429} or status >= 500,
            safe_details={
                "http_status": status,
                "retry_after_present": "retry-after" in response.headers,
            },
        )

    async def _sleep_before_retry(
        self,
        attempt: int,
        response: OpenAlexHttpResponse | None,
    ) -> None:
        retry_after = None if response is None else response.headers.get("retry-after")
        delay = min(4.0, float(2**attempt))
        if retry_after is not None:
            try:
                delay = min(15.0, max(delay, float(retry_after)))
            except ValueError:
                pass
        result = self._sleeper(delay)
        if hasattr(result, "__await__"):
            await result

    def _with_failure_usage(
        self,
        error: ProviderError,
        requests: int,
        retries: int,
        started: float,
    ) -> ProviderError:
        if isinstance(error.safe_details.get("request_count"), int):
            return error
        return ProviderError(
            error.category,
            str(error),
            retryable=error.retryable,
            safe_details={
                **dict(error.safe_details),
                "request_count": requests,
                "retry_count": retries,
                "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
            },
        )

    def _filters(self, query: ResearchQuery) -> str:
        filters = ["has_abstract:true"]
        if query.year_from is not None:
            filters.append(f"from_publication_date:{query.year_from}-01-01")
        if query.year_to is not None:
            filters.append(f"to_publication_date:{query.year_to}-12-31")
        return ",".join(filters)

    def _validate_limit(self, limit: int) -> None:
        effective_cap = min(
            self.configuration.max_candidates,
            self.configuration.max_selected_workflow_results,
        )
        if not 1 <= limit <= effective_cap:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "Search limit exceeds the supervised selected-paper cap",
                retryable=False,
                safe_details={
                    "maximum_candidates": self.configuration.max_candidates,
                    "maximum_selected_papers": (
                        self.configuration.max_selected_workflow_results
                    ),
                },
            )

    def _exact_query(self, query: ResearchQuery) -> str:
        topic = self._clean_required(query.topic, "query topic", maximum=300)
        # A research topic is a conjunction of terms, not an exact-title phrase.
        # Quoting each term keeps provider syntax supplied by the user in the
        # data boundary while avoiding the live-verified recall collapse caused
        # by quoting the entire multi-word topic.
        values = [*topic.split(), *query.keywords]
        terms = []
        for value in values:
            cleaned = self._clean_required(value, "query term", maximum=300)
            escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"')
            terms.append(f'"{escaped}"')
        exact = " AND ".join(terms)
        if len(exact.encode("utf-8")) > 3000:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "OpenAlex query exceeds the supervised URL-safe limit",
                retryable=False,
            )
        return exact

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("OpenAlex adapter clock must return an aware datetime")
        return value

    @classmethod
    def _clean_required(
        cls,
        value: Any,
        field_name: str,
        *,
        maximum: int,
        record_identity: str | None = None,
    ) -> str:
        cleaned = cls._clean_optional(
            value,
            field_name=field_name,
            maximum=maximum,
            record_identity=record_identity,
        )
        if cleaned is None:
            raise ValueError(f"{field_name} is missing")
        return cleaned

    @classmethod
    def _clean_optional(
        cls,
        value: Any,
        *,
        maximum: int,
        field_name: str = "provider_text",
        record_identity: str | None = None,
    ) -> str | None:
        if not isinstance(value, str):
            return None
        try:
            value.encode("utf-8", errors="strict")
            cleaned = unicodedata.normalize("NFC", value).strip()
        except (UnicodeEncodeError, UnicodeError):
            raise _FieldRejection(
                cls._field_rejection(
                    category=SearchDiagnosticCode.INVALID_UNICODE,
                    field_name=field_name,
                    normalized_value=value,
                    configured_limit=maximum,
                    record_identity=record_identity,
                )
            ) from None
        if not cleaned:
            return None
        if _CONTROL.search(cleaned):
            raise _FieldRejection(
                cls._field_rejection(
                    category=SearchDiagnosticCode.CONTROL_CHARACTER_REJECTED,
                    field_name=field_name,
                    normalized_value=cleaned,
                    configured_limit=maximum,
                    record_identity=record_identity,
                )
            )
        if len(cleaned) > maximum:
            raise _FieldRejection(
                cls._field_rejection(
                    category=SearchDiagnosticCode.FIELD_LENGTH_REJECTED,
                    field_name=field_name,
                    normalized_value=cleaned,
                    configured_limit=maximum,
                    record_identity=record_identity,
                )
            )
        return cleaned

    @classmethod
    def _field_rejection(
        cls,
        *,
        category: SearchDiagnosticCode,
        field_name: str,
        normalized_value: str,
        configured_limit: int,
        record_identity: str | None,
    ) -> FieldRejectionDiagnostic:
        preview = normalized_value.encode("utf-8", errors="replace").decode("utf-8")
        preview = _CONTROL.sub("", preview)
        preview = " ".join(preview.split())
        preview = _SECRET_LIKE.sub("[REDACTED]", preview)[:_SAFE_PREVIEW_LIMIT]
        return FieldRejectionDiagnostic(
            category=category,
            field_name=field_name,
            measured_normalized_length=len(normalized_value),
            configured_limit=configured_limit,
            record_identity=record_identity,
            value_sha256=sha256_bytes(
                normalized_value.encode("utf-8", errors="surrogatepass")
            ),
            safe_preview=preview,
            preview_length=len(preview),
            adapter_version=cls.IDENTITY.adapter_version,
            validator_version=_VALIDATOR_VERSION,
        )

    @staticmethod
    def _normalize_title(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    @staticmethod
    def _openalex_optional_id(value: Any, *, prefix: str) -> str | None:
        if not isinstance(value, str):
            return None
        candidate = value.rsplit("/", 1)[-1]
        return candidate if re.fullmatch(fr"{prefix}\d+", candidate) else None

    @staticmethod
    def _request_ids(response: OpenAlexHttpResponse) -> tuple[str, ...]:
        value = response.headers.get("x-request-id")
        return (value[:200],) if value else ()

    @staticmethod
    def _decimal_string(value: Any) -> str:
        try:
            decimal = Decimal(str(value))
        except InvalidOperation:
            return "unknown"
        if decimal < 0:
            return "unknown"
        return format(decimal, "f")
