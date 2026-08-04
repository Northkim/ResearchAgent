"""Fixed-origin OpenAlex Works adapter for the experimental R3C Proxy.

The adapter contains transport and normalization only.  Tests inject a scripted
transport; the HTTPX transport is reserved for the separately gated R3C-A run.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from backend.research.contracts import PaperAuthor, PaperRecord, canonical_hash

from .contracts import (
    MAX_RESULT_BYTES,
    MAX_TIMEOUT_SECONDS,
    MICROUSD_PER_USD,
    OPENALEX_ADAPTER_ID,
    OPENALEX_RESERVED_SEARCH_COST_MICROUSD,
    PaperSearchV01Request,
    canonical_json,
    sha256_bytes,
)
from .ports import (
    OpenAlexCredentialSource,
    OpenAlexTransport,
    ProviderHTTPResponse,
    ProxyAdapterError,
    ProxyAdapterInternalError,
    ProxyAdapterResult,
)
from .openalex_diagnostics import (
    FailureStage,
    ObservedKind,
    ValidatorCode,
    observed_kind,
    provider_structural_shape_checksum,
    structural_failure,
)

OPENALEX_API_KEY_ENV = "REAGENT_OPENALEX_API_KEY"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_SELECT_FIELDS = (
    "id",
    "doi",
    "display_name",
    "authorships",
    "abstract_inverted_index",
    "publication_year",
    "primary_location",
    "language",
)
OPENALEX_SELECT = ",".join(OPENALEX_SELECT_FIELDS)
OPENALEX_MAX_RESPONSE_BYTES = 512 * 1024
OPENALEX_ADAPTER_VERSION = "v0.1"

_WORK_ID = re.compile(r"https://openalex\.org/(W[0-9]+)\Z")
_AUTHOR_ID = re.compile(r"https://openalex\.org/(A[0-9]+)\Z")
_SAFE_HEADER_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")


class EnvironmentOpenAlexCredentialSource:
    """Read the sole credential variable only when ``get`` is explicitly called."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = environment

    def get(self) -> str:
        environment = os.environ if self._environment is None else self._environment
        value = environment.get(OPENALEX_API_KEY_ENV)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError("Experimental OpenAlex Proxy requires its server credential")
        return value.strip()


class SafeTransportFailure(RuntimeError):
    """Transport-only failure with no URL, query, credential, or raw body."""

    def __init__(self, *, uncertain: bool, timeout: bool = False) -> None:
        super().__init__("OpenAlex transport failed")
        self.uncertain = uncertain
        self.timeout = timeout


class HTTPXOpenAlexTransport:
    """Fixed-policy live transport; never used by R3C-I tests."""

    def get(
        self,
        *,
        url: str,
        params: tuple[tuple[str, str], ...],
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> ProviderHTTPResponse:
        if url != OPENALEX_WORKS_URL:
            raise ValueError("OpenAlex transport origin/path is not allowlisted")
        if timeout_seconds != MAX_TIMEOUT_SECONDS:
            raise ValueError("OpenAlex transport timeout must be exactly 10 seconds")
        if maximum_response_bytes != OPENALEX_MAX_RESPONSE_BYTES:
            raise ValueError("OpenAlex transport response limit must be exactly 512 KiB")
        timeout = httpx.Timeout(
            timeout_seconds,
            connect=timeout_seconds,
            read=timeout_seconds,
            write=timeout_seconds,
            pool=timeout_seconds,
        )
        request_log_filter = _DropCurrentThreadHTTPXLogs()
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.addFilter(request_log_filter)
        try:
            with httpx.Client(
                verify=True,
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
            ) as client:
                with client.stream("GET", OPENALEX_WORKS_URL, params=params) as response:
                    chunks: list[bytes] = []
                    received = 0
                    for chunk in response.iter_bytes():
                        received += len(chunk)
                        if received > maximum_response_bytes:
                            raise ProxyAdapterError(
                                "PROVIDER_RESPONSE_TOO_LARGE",
                                "Provider response exceeded the approved byte limit",
                                provider_http_calls=1,
                                provider_http_status=response.status_code,
                                structural_failure=structural_failure(
                                    failure_stage=FailureStage.RESPONSE_BYTES,
                                    approved_json_path="/",
                                    observed_kind=ObservedKind.LIMIT_EXCEEDED,
                                    validator_code=ValidatorCode.RESPONSE_BYTES_LIMIT,
                                ),
                            )
                        chunks.append(chunk)
                    return ProviderHTTPResponse(
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        body=b"".join(chunks),
                    )
        except ProxyAdapterError:
            raise
        except httpx.ReadTimeout as error:
            raise SafeTransportFailure(uncertain=True, timeout=True) from None
        except httpx.TimeoutException as error:
            raise SafeTransportFailure(uncertain=False, timeout=True) from None
        except httpx.HTTPError as error:
            raise SafeTransportFailure(uncertain=False) from None
        finally:
            httpx_logger.removeFilter(request_log_filter)


class OpenAlexPaperSearchAdapter:
    adapter_id = OPENALEX_ADAPTER_ID
    adapter_version = OPENALEX_ADAPTER_VERSION

    def __init__(
        self,
        *,
        credential_source: OpenAlexCredentialSource,
        transport: OpenAlexTransport,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.credential_source = credential_source
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(UTC))
        self.invocation_count = 0

    def search(self, request: PaperSearchV01Request) -> ProxyAdapterResult:
        self.invocation_count += 1
        credential = self.credential_source.get()
        if not credential:
            raise ProxyAdapterError(
                "PROVIDER_AUTHENTICATION_FAILED",
                "Provider credential is unavailable",
                provider_http_calls=0,
            )
        params = (
            ("search", request.query),
            ("per_page", str(request.max_results)),
            ("select", OPENALEX_SELECT),
            ("api_key", credential),
        )
        try:
            response = self.transport.get(
                url=OPENALEX_WORKS_URL,
                params=params,
                timeout_seconds=MAX_TIMEOUT_SECONDS,
                maximum_response_bytes=OPENALEX_MAX_RESPONSE_BYTES,
            )
        except ProxyAdapterError:
            raise
        except SafeTransportFailure as error:
            code = (
                "PROVIDER_RECONCILIATION_REQUIRED"
                if error.uncertain
                else ("PROVIDER_TIMEOUT" if error.timeout else "PROVIDER_UNAVAILABLE")
            )
            raise ProxyAdapterError(
                code,
                "Provider transport did not complete safely",
                provider_http_calls=1,
                uncertain=error.uncertain,
            ) from None
        except Exception:
            raise ProxyAdapterError(
                "PROVIDER_UNAVAILABLE",
                "Provider transport did not complete safely",
                provider_http_calls=1,
                structural_failure=structural_failure(
                    failure_stage=FailureStage.UNCLASSIFIED_INTERNAL,
                    approved_json_path="/",
                    observed_kind=ObservedKind.UNKNOWN,
                    validator_code=ValidatorCode.UNCLASSIFIED_INTERNAL,
                ),
            ) from None

        if len(response.body) > OPENALEX_MAX_RESPONSE_BYTES:
            raise ProxyAdapterError(
                "PROVIDER_RESPONSE_TOO_LARGE",
                "Provider response exceeded the approved byte limit",
                provider_http_calls=1,
                provider_http_status=response.status_code,
                structural_failure=structural_failure(
                    failure_stage=FailureStage.RESPONSE_BYTES,
                    approved_json_path="/",
                    observed_kind=ObservedKind.LIMIT_EXCEEDED,
                    validator_code=ValidatorCode.RESPONSE_BYTES_LIMIT,
                ),
            )
        response_checksum = sha256_bytes(response.body)
        self._raise_for_status(response.status_code, response_checksum)
        value = self._decode_json(response.body, response_checksum)
        provider_shape_checksum = provider_structural_shape_checksum(value)
        cost_microusd, headers = self._usage_evidence(
            value,
            response.headers,
            response_checksum,
            provider_shape_checksum,
        )
        if cost_microusd != OPENALEX_RESERVED_SEARCH_COST_MICROUSD:
            raise ProxyAdapterError(
                "PROVIDER_CONTRACT_CHANGED",
                "Provider reported a cost outside the qualified contract",
                provider_http_calls=1,
                provider_http_status=response.status_code,
                provider_response_checksum=response_checksum,
                reported_cost_microusd=cost_microusd,
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta/cost_usd",
                    observed_kind=ObservedKind.INVALID_VALUE,
                    validator_code=ValidatorCode.COST_QUALIFIED_PRICE,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        results = value.get("results")
        if not isinstance(results, list):
            self._invalid_response(
                response_checksum,
                "Provider results were not an array",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.RESULTS_ARRAY,
                    approved_json_path="/results",
                    observed_kind=observed_kind(results, missing="results" not in value),
                    validator_code=ValidatorCode.RESULTS_ARRAY_REQUIRED,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        if len(results) > request.max_results:
            self._invalid_response(
                response_checksum,
                "Provider returned too many results",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.RESULTS_ARRAY,
                    approved_json_path="/results",
                    observed_kind=ObservedKind.LIMIT_EXCEEDED,
                    validator_code=ValidatorCode.RESULT_COUNT_LIMIT,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        retrieved_at = self._now()
        papers: list[PaperRecord] = []
        try:
            for record_index, item in enumerate(results):
                context = _WorkDiagnosticContext(
                    provider_shape_checksum=provider_shape_checksum,
                    record_index=record_index,
                    normalized_records_before_failure=len(papers),
                )
                papers.append(self._paper(item, retrieved_at, context))
        except ProxyAdapterError as error:
            raise ProxyAdapterError(
                error.code,
                str(error),
                provider_http_calls=1,
                provider_http_status=response.status_code,
                provider_response_checksum=response_checksum,
                reported_cost_microusd=cost_microusd,
                structural_failure=error.structural_failure,
            ) from None
        try:
            provider_data = {
                "schema_version": "paper-search-result/v0.1",
                "source_classification": "LIVE_OPENALEX_SCHOLARLY_METADATA",
                "untrusted_provider_data": True,
                "papers": [paper.to_dict() for paper in papers],
            }
            encoded = canonical_json(provider_data).encode("utf-8")
        except Exception:
            raise ProxyAdapterInternalError(
                structural_failure(
                    failure_stage=FailureStage.NORMALIZED_SERIALIZATION,
                    approved_json_path="/normalized_results",
                    observed_kind=ObservedKind.UNKNOWN,
                    validator_code=ValidatorCode.NORMALIZED_CANONICAL_SERIALIZATION,
                    normalized_records_before_failure=len(papers),
                    provider_shape_checksum=provider_shape_checksum,
                )
            ) from None
        if len(encoded) > MAX_RESULT_BYTES:
            raise ProxyAdapterError(
                "PROVIDER_RESPONSE_TOO_LARGE",
                "Normalized Provider result exceeded the approved byte limit",
                provider_http_calls=1,
                provider_http_status=response.status_code,
                provider_response_checksum=response_checksum,
                reported_cost_microusd=cost_microusd,
                structural_failure=structural_failure(
                    failure_stage=FailureStage.RESULT_SIZE,
                    approved_json_path="/normalized_results",
                    observed_kind=ObservedKind.LIMIT_EXCEEDED,
                    validator_code=ValidatorCode.NORMALIZED_RESULT_SIZE,
                    normalized_records_before_failure=len(papers),
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        return ProxyAdapterResult(
            provider_data=provider_data,
            provider_http_calls=1,
            reported_cost_microusd=cost_microusd,
            provider_response_checksum=response_checksum,
            provider_http_status=response.status_code,
            provider_credits_used=headers["provider_credits_used"],
            rate_limit_limit=headers["rate_limit_limit"],
            rate_limit_remaining=headers["rate_limit_remaining"],
            rate_limit_reset=headers["rate_limit_reset"],
            provider_structural_shape_checksum=provider_shape_checksum,
        )

    @staticmethod
    def _raise_for_status(status: int, checksum: str) -> None:
        if 200 <= status < 300:
            return
        if 300 <= status < 400:
            code = "PROVIDER_CONTRACT_CHANGED"
        elif status == 401:
            code = "PROVIDER_AUTHENTICATION_FAILED"
        elif status == 403:
            code = "PROVIDER_AUTHORIZATION_FAILED"
        elif status in {408}:
            code = "PROVIDER_TIMEOUT"
        elif status == 429:
            code = "PROVIDER_RATE_LIMITED"
        elif status in {500, 502, 503, 504}:
            code = "PROVIDER_UNAVAILABLE"
        else:
            code = "PROVIDER_INVALID_RESPONSE"
        raise ProxyAdapterError(
            code,
            "Provider returned a rejected status category",
            provider_http_calls=1,
            provider_http_status=status,
            provider_response_checksum=checksum,
            structural_failure=structural_failure(
                failure_stage=FailureStage.RESPONSE_BYTES,
                approved_json_path="/",
                observed_kind=ObservedKind.INVALID_VALUE,
                validator_code=ValidatorCode.HTTP_STATUS_REJECTED,
            ),
        )

    @staticmethod
    def _decode_json(body: bytes, checksum: str) -> dict[str, Any]:
        try:
            text = body.decode("utf-8", errors="strict")
            value = json.loads(
                text,
                object_pairs_hook=_unique_object,
                parse_float=Decimal,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
            OpenAlexPaperSearchAdapter._invalid_response(
                checksum,
                "Provider response was not strict JSON",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.JSON_ROOT,
                    approved_json_path="/",
                    observed_kind=ObservedKind.INVALID_VALUE,
                    validator_code=ValidatorCode.JSON_DECODE,
                ),
            )
        if not isinstance(value, dict):
            OpenAlexPaperSearchAdapter._invalid_response(
                checksum,
                "Provider response root was not an object",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.JSON_ROOT,
                    approved_json_path="/",
                    observed_kind=observed_kind(value),
                    validator_code=ValidatorCode.JSON_ROOT_OBJECT,
                    provider_value=value,
                ),
            )
        return value

    @staticmethod
    def _usage_evidence(
        value: dict[str, Any],
        headers: Mapping[str, str],
        checksum: str,
        provider_shape_checksum: str,
    ) -> tuple[int, dict[str, Any]]:
        meta = value.get("meta")
        if not isinstance(meta, dict):
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider cost evidence was missing",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta",
                    observed_kind=observed_kind(meta, missing="meta" not in value),
                    validator_code=ValidatorCode.META_OBJECT,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        if "cost_usd" not in meta:
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider cost evidence was missing",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta/cost_usd",
                    observed_kind=ObservedKind.MISSING,
                    validator_code=ValidatorCode.COST_REQUIRED,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        try:
            cost = usd_decimal_to_microusd(meta["cost_usd"])
        except ValueError:
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider cost evidence was invalid",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta/cost_usd",
                    observed_kind=(
                        ObservedKind.NULL
                        if meta["cost_usd"] is None
                        else ObservedKind.INVALID_VALUE
                    ),
                    validator_code=ValidatorCode.COST_EXACT_DECIMAL,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        normalized_headers = {str(key).lower(): str(item).strip() for key, item in headers.items()}
        required = {
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-credits-used",
            "x-ratelimit-reset",
        }
        if not required <= normalized_headers.keys():
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider usage headers were missing",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta",
                    observed_kind=ObservedKind.MISSING,
                    validator_code=ValidatorCode.RATE_HEADERS_REQUIRED,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        try:
            limit = _bounded_integer(normalized_headers["x-ratelimit-limit"])
            remaining = _bounded_integer(normalized_headers["x-ratelimit-remaining"])
            credits = _bounded_decimal_string(normalized_headers["x-ratelimit-credits-used"])
            reset = str(_bounded_integer(normalized_headers["x-ratelimit-reset"], maximum=10**13))
        except ValueError:
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider usage headers were invalid",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta",
                    observed_kind=ObservedKind.INVALID_VALUE,
                    validator_code=ValidatorCode.RATE_HEADERS_BOUNDED,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        if remaining > limit:
            OpenAlexPaperSearchAdapter._contract_changed(
                checksum,
                "Provider usage headers were contradictory",
                structural_failure=structural_failure(
                    failure_stage=FailureStage.COST_USAGE,
                    approved_json_path="/meta",
                    observed_kind=ObservedKind.INVALID_VALUE,
                    validator_code=ValidatorCode.RATE_HEADERS_CONSISTENT,
                    provider_shape_checksum=provider_shape_checksum,
                ),
            )
        return cost, {
            "provider_credits_used": credits,
            "rate_limit_limit": limit,
            "rate_limit_remaining": remaining,
            "rate_limit_reset": reset,
        }

    @staticmethod
    def _paper(
        value: Any,
        retrieved_at: datetime,
        context: _WorkDiagnosticContext,
    ) -> PaperRecord:
        if not isinstance(value, dict):
            raise ProxyAdapterError(
                "PROVIDER_INVALID_RESPONSE",
                "Provider result was not an object",
                provider_http_calls=1,
                structural_failure=_work_failure(
                    context,
                    failure_stage=FailureStage.WORK_NORMALIZATION,
                    approved_json_path="/results/*",
                    observed_kind=observed_kind(value),
                    validator_code=ValidatorCode.WORK_OBJECT_REQUIRED,
                ),
            )
        selected = {field: value.get(field) for field in OPENALEX_SELECT_FIELDS}
        provider_id = _work_id(
            selected["id"],
            context,
            missing="id" not in value,
        )
        title = _safe_text(
            selected["display_name"],
            "display_name",
            maximum=2_000,
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/display_name",
            required_code=ValidatorCode.DISPLAY_NAME_REQUIRED_TEXT,
            length_code=ValidatorCode.DISPLAY_NAME_LENGTH,
            control_code=ValidatorCode.DISPLAY_NAME_CONTROL,
            missing="display_name" not in value,
        )
        authors = _authors(
            selected["authorships"],
            context,
            missing="authorships" not in value,
        )
        abstract = _abstract(selected["abstract_inverted_index"], context)
        year = selected["publication_year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise _invalid_field(
                "publication_year",
                context=context,
                failure_stage=FailureStage.WORK_NORMALIZATION,
                approved_json_path="/results/*/publication_year",
                observed_kind=ObservedKind.WRONG_TYPE,
                validator_code=ValidatorCode.PUBLICATION_YEAR_INTEGER,
            )
        if year is not None and not 1000 <= year <= 3000:
            raise _invalid_field(
                "publication_year",
                context=context,
                failure_stage=FailureStage.WORK_NORMALIZATION,
                approved_json_path="/results/*/publication_year",
                observed_kind=ObservedKind.INVALID_VALUE,
                validator_code=ValidatorCode.PUBLICATION_YEAR_RANGE,
            )
        venue = _venue(selected["primary_location"], context)
        language = selected["language"]
        if language is not None:
            language = _safe_text(
                language,
                "language",
                maximum=32,
                context=context,
                failure_stage=FailureStage.WORK_NORMALIZATION,
                approved_json_path="/results/*/language",
                required_code=ValidatorCode.LANGUAGE_REQUIRED_TEXT,
                length_code=ValidatorCode.LANGUAGE_LENGTH,
                control_code=ValidatorCode.LANGUAGE_CONTROL,
            )
        doi = selected["doi"]
        if doi is not None and not isinstance(doi, str):
            raise _invalid_field(
                "doi",
                context=context,
                failure_stage=FailureStage.WORK_NORMALIZATION,
                approved_json_path="/results/*/doi",
                observed_kind=ObservedKind.WRONG_TYPE,
                validator_code=ValidatorCode.DOI_STRING_OR_NULL,
            )
        try:
            return PaperRecord(
                paper_id=PaperRecord.internal_id(
                    provider=OPENALEX_ADAPTER_ID,
                    provider_id=provider_id,
                    doi=doi,
                ),
                provider_id=provider_id,
                title=title,
                authors=tuple(authors),
                abstract=abstract,
                publication_year=year,
                publication_venue=venue,
                source_provider=OPENALEX_ADAPTER_ID,
                source_url=f"https://openalex.org/{provider_id}",
                doi=doi,
                language=language,
                retrieved_at=retrieved_at,
                raw_metadata_hash=canonical_hash(selected),
                metadata_limitations=(
                    "OpenAlex metadata is untrusted discovery data; relevance is decided locally.",
                ),
            )
        except ValueError:
            raise _invalid_field(
                "paper metadata",
                context=context,
                failure_stage=FailureStage.PAPER_MODEL_VALIDATION,
                approved_json_path="/results/*",
                observed_kind=ObservedKind.MODEL_VALIDATION,
                validator_code=ValidatorCode.PAPER_RECORD_MODEL,
            ) from None

    @staticmethod
    def _invalid_response(
        checksum: str,
        message: str,
        *,
        structural_failure,
    ) -> None:
        raise ProxyAdapterError(
            "PROVIDER_INVALID_RESPONSE",
            message,
            provider_http_calls=1,
            provider_http_status=200,
            provider_response_checksum=checksum,
            structural_failure=structural_failure,
        )

    @staticmethod
    def _contract_changed(
        checksum: str,
        message: str,
        *,
        structural_failure,
    ) -> None:
        raise ProxyAdapterError(
            "PROVIDER_CONTRACT_CHANGED",
            message,
            provider_http_calls=1,
            provider_http_status=200,
            provider_response_checksum=checksum,
            structural_failure=structural_failure,
        )

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("OpenAlex adapter clock must be timezone-aware")
        return value.astimezone(UTC)


def usd_decimal_to_microusd(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("USD cost must be an exact decimal value")
    text = str(value)
    try:
        amount = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("USD cost is malformed") from error
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -6:
        raise ValueError("USD cost is negative, non-finite, or excessively precise")
    microusd = amount * MICROUSD_PER_USD
    integral = microusd.to_integral_value()
    if microusd != integral:
        raise ValueError("USD cost cannot be represented exactly in microusd")
    return int(integral)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class _DropCurrentThreadHTTPXLogs(logging.Filter):
    """Drop HTTPX's credential-bearing request URL log on the calling thread."""

    def __init__(self) -> None:
        super().__init__()
        self.thread_id = threading.get_ident()

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread != self.thread_id


@dataclass(frozen=True, slots=True)
class _WorkDiagnosticContext:
    provider_shape_checksum: str
    record_index: int
    normalized_records_before_failure: int


def _bounded_integer(value: str, *, maximum: int = 10**9) -> int:
    if not value.isdigit():
        raise ValueError("header is not an integer")
    parsed = int(value)
    if not 0 <= parsed <= maximum:
        raise ValueError("header integer is outside the accepted range")
    return parsed


def _bounded_decimal_string(value: str) -> str:
    if len(value) > 64 or not _SAFE_HEADER_NUMBER.fullmatch(value):
        raise ValueError("header decimal is invalid")
    parsed = Decimal(value)
    if not parsed.is_finite() or parsed < 0:
        raise ValueError("header decimal is invalid")
    return format(parsed, "f")


def _work_failure(
    context: _WorkDiagnosticContext,
    *,
    failure_stage: FailureStage,
    approved_json_path: str,
    observed_kind: ObservedKind,
    validator_code: ValidatorCode,
    nested_element_index: int | None = None,
):
    return structural_failure(
        failure_stage=failure_stage,
        approved_json_path=approved_json_path,
        observed_kind=observed_kind,
        validator_code=validator_code,
        normalized_records_before_failure=context.normalized_records_before_failure,
        record_index=context.record_index,
        nested_element_index=nested_element_index,
        provider_shape_checksum=context.provider_shape_checksum,
    )


def _work_id(
    value: Any,
    context: _WorkDiagnosticContext,
    *,
    missing: bool,
) -> str:
    if not isinstance(value, str):
        raise _invalid_field(
            "id",
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/id",
            observed_kind=observed_kind(value, missing=missing),
            validator_code=ValidatorCode.WORK_ID_REQUIRED_STRING,
        )
    match = _WORK_ID.fullmatch(value)
    if match is None:
        raise _invalid_field(
            "id",
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/id",
            observed_kind=ObservedKind.INVALID_VALUE,
            validator_code=ValidatorCode.WORK_ID_FORMAT,
        )
    return match.group(1)


def _safe_text(
    value: Any,
    field: str,
    *,
    maximum: int,
    context: _WorkDiagnosticContext,
    failure_stage: FailureStage,
    approved_json_path: str,
    required_code: ValidatorCode,
    length_code: ValidatorCode,
    control_code: ValidatorCode,
    missing: bool = False,
    nested_element_index: int | None = None,
) -> str:
    if not isinstance(value, str):
        raise _invalid_field(
            field,
            context=context,
            failure_stage=failure_stage,
            approved_json_path=approved_json_path,
            observed_kind=observed_kind(value, missing=missing),
            validator_code=required_code,
            nested_element_index=nested_element_index,
        )
    if not value.strip():
        raise _invalid_field(
            field,
            context=context,
            failure_stage=failure_stage,
            approved_json_path=approved_json_path,
            observed_kind=ObservedKind.EMPTY,
            validator_code=required_code,
            nested_element_index=nested_element_index,
        )
    result = value.strip()
    if len(result) > maximum:
        raise _invalid_field(
            field,
            context=context,
            failure_stage=failure_stage,
            approved_json_path=approved_json_path,
            observed_kind=ObservedKind.LIMIT_EXCEEDED,
            validator_code=length_code,
            nested_element_index=nested_element_index,
        )
    if any(unicodedata.category(character).startswith("C") for character in result):
        raise _invalid_field(
            field,
            context=context,
            failure_stage=failure_stage,
            approved_json_path=approved_json_path,
            observed_kind=ObservedKind.CONTROL_CHARACTER,
            validator_code=control_code,
            nested_element_index=nested_element_index,
        )
    return result


def _authors(
    value: Any,
    context: _WorkDiagnosticContext,
    *,
    missing: bool,
) -> list[PaperAuthor]:
    if not isinstance(value, list):
        raise _invalid_field(
            "authorships",
            context=context,
            failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
            approved_json_path="/results/*/authorships",
            observed_kind=observed_kind(value, missing=missing),
            validator_code=ValidatorCode.AUTHORSHIPS_ARRAY_REQUIRED,
        )
    if len(value) > 100:
        raise _invalid_field(
            "authorships",
            context=context,
            failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
            approved_json_path="/results/*/authorships",
            observed_kind=ObservedKind.LIMIT_EXCEEDED,
            validator_code=ValidatorCode.AUTHORSHIPS_COUNT_LIMIT,
        )
    authors: list[PaperAuthor] = []
    for nested_index, item in enumerate(value):
        if not isinstance(item, dict):
            raise _invalid_field(
                "authorships",
                context=context,
                failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
                approved_json_path="/results/*/authorships/*",
                observed_kind=ObservedKind.WRONG_TYPE,
                validator_code=ValidatorCode.AUTHORSHIP_OBJECT_REQUIRED,
                nested_element_index=nested_index,
            )
        if not isinstance(item.get("author"), dict):
            raise _invalid_field(
                "authorships",
                context=context,
                failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
                approved_json_path="/results/*/authorships/*/author",
                observed_kind=observed_kind(
                    item.get("author"),
                    missing="author" not in item,
                ),
                validator_code=ValidatorCode.AUTHOR_OBJECT_REQUIRED,
                nested_element_index=nested_index,
            )
        author = item["author"]
        name = _safe_text(
            author.get("display_name"),
            "author.display_name",
            maximum=500,
            context=context,
            failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
            approved_json_path="/results/*/authorships/*/author/display_name",
            required_code=ValidatorCode.AUTHOR_DISPLAY_NAME_REQUIRED_TEXT,
            length_code=ValidatorCode.AUTHOR_DISPLAY_NAME_LENGTH,
            control_code=ValidatorCode.AUTHOR_DISPLAY_NAME_CONTROL,
            missing="display_name" not in author,
            nested_element_index=nested_index,
        )
        identifier = author.get("id")
        provider_author_id = None
        if identifier is not None:
            if not isinstance(identifier, str) or (match := _AUTHOR_ID.fullmatch(identifier)) is None:
                raise _invalid_field(
                    "author.id",
                    context=context,
                    failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
                    approved_json_path="/results/*/authorships/*/author/id",
                    observed_kind=(
                        ObservedKind.WRONG_TYPE
                        if not isinstance(identifier, str)
                        else ObservedKind.INVALID_VALUE
                    ),
                    validator_code=ValidatorCode.AUTHOR_ID_FORMAT,
                    nested_element_index=nested_index,
                )
            provider_author_id = match.group(1)
        orcid = author.get("orcid")
        if orcid is not None:
            orcid = _safe_text(
                orcid,
                "author.orcid",
                maximum=64,
                context=context,
                failure_stage=FailureStage.AUTHORSHIP_NORMALIZATION,
                approved_json_path="/results/*/authorships/*/author/orcid",
                required_code=ValidatorCode.AUTHOR_ORCID_REQUIRED_TEXT,
                length_code=ValidatorCode.AUTHOR_ORCID_LENGTH,
                control_code=ValidatorCode.AUTHOR_ORCID_CONTROL,
                nested_element_index=nested_index,
            )
        try:
            authors.append(
                PaperAuthor(
                    name=name,
                    provider_author_id=provider_author_id,
                    orcid=orcid,
                )
            )
        except ValueError:
            raise ProxyAdapterInternalError(
                _work_failure(
                    context,
                    failure_stage=FailureStage.PAPER_MODEL_VALIDATION,
                    approved_json_path="/results/*/authorships/*/author",
                    observed_kind=ObservedKind.MODEL_VALIDATION,
                    validator_code=ValidatorCode.PAPER_AUTHOR_MODEL,
                    nested_element_index=nested_index,
                )
            ) from None
    return authors


def _abstract(value: Any, context: _WorkDiagnosticContext) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _invalid_field(
            "abstract_inverted_index",
            context=context,
            failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
            approved_json_path="/results/*/abstract_inverted_index",
            observed_kind=ObservedKind.WRONG_TYPE,
            validator_code=ValidatorCode.ABSTRACT_OBJECT_OR_NULL,
        )
    if len(value) > 20_000:
        raise _invalid_field(
            "abstract_inverted_index",
            context=context,
            failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
            approved_json_path="/results/*/abstract_inverted_index",
            observed_kind=ObservedKind.LIMIT_EXCEEDED,
            validator_code=ValidatorCode.ABSTRACT_TOKEN_COUNT_LIMIT,
        )
    positions: dict[int, str] = {}
    for token_index, (token, raw_positions) in enumerate(value.items()):
        safe_token = _safe_text(
            token,
            "abstract token",
            maximum=500,
            context=context,
            failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
            approved_json_path="/results/*/abstract_inverted_index",
            required_code=ValidatorCode.ABSTRACT_TOKEN_REQUIRED_TEXT,
            length_code=ValidatorCode.ABSTRACT_TOKEN_LENGTH,
            control_code=ValidatorCode.ABSTRACT_TOKEN_CONTROL,
            nested_element_index=token_index,
        )
        if not isinstance(raw_positions, list):
            raise _invalid_field(
                "abstract positions",
                context=context,
                failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
                approved_json_path="/results/*/abstract_inverted_index",
                observed_kind=ObservedKind.WRONG_TYPE,
                validator_code=ValidatorCode.ABSTRACT_POSITIONS_ARRAY,
                nested_element_index=token_index,
            )
        if len(raw_positions) > 20_000:
            raise _invalid_field(
                "abstract positions",
                context=context,
                failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
                approved_json_path="/results/*/abstract_inverted_index",
                observed_kind=ObservedKind.LIMIT_EXCEEDED,
                validator_code=ValidatorCode.ABSTRACT_POSITIONS_COUNT_LIMIT,
                nested_element_index=token_index,
            )
        for position_index, position in enumerate(raw_positions):
            if isinstance(position, bool) or not isinstance(position, int):
                raise _invalid_field(
                    "abstract position",
                    context=context,
                    failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
                    approved_json_path="/results/*/abstract_inverted_index",
                    observed_kind=ObservedKind.WRONG_TYPE,
                    validator_code=ValidatorCode.ABSTRACT_POSITION_INTEGER,
                    nested_element_index=position_index,
                )
            if not 0 <= position <= 100_000:
                raise _invalid_field(
                    "abstract position",
                    context=context,
                    failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
                    approved_json_path="/results/*/abstract_inverted_index",
                    observed_kind=ObservedKind.INVALID_POSITION,
                    validator_code=ValidatorCode.ABSTRACT_POSITION_RANGE,
                    nested_element_index=position_index,
                )
            if position in positions:
                raise _invalid_field(
                    "abstract position",
                    context=context,
                    failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
                    approved_json_path="/results/*/abstract_inverted_index",
                    observed_kind=ObservedKind.INVALID_POSITION,
                    validator_code=ValidatorCode.ABSTRACT_POSITION_UNIQUE,
                    nested_element_index=position_index,
                )
            positions[position] = safe_token
    if not positions:
        return None
    maximum = max(positions)
    if len(positions) != maximum + 1:
        raise _invalid_field(
            "abstract positions",
            context=context,
            failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
            approved_json_path="/results/*/abstract_inverted_index",
            observed_kind=ObservedKind.INVALID_POSITION,
            validator_code=ValidatorCode.ABSTRACT_POSITIONS_CONTIGUOUS,
        )
    result = " ".join(positions[index] for index in range(maximum + 1))
    if len(result) > MAX_RESULT_BYTES:
        raise _invalid_field(
            "abstract",
            context=context,
            failure_stage=FailureStage.ABSTRACT_RECONSTRUCTION,
            approved_json_path="/results/*/abstract_inverted_index",
            observed_kind=ObservedKind.LIMIT_EXCEEDED,
            validator_code=ValidatorCode.ABSTRACT_RESULT_SIZE,
        )
    return result


def _venue(value: Any, context: _WorkDiagnosticContext) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _invalid_field(
            "primary_location",
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/primary_location",
            observed_kind=ObservedKind.WRONG_TYPE,
            validator_code=ValidatorCode.PRIMARY_LOCATION_OBJECT_OR_NULL,
        )
    source = value.get("source")
    if source is None:
        return None
    if not isinstance(source, dict):
        raise _invalid_field(
            "primary_location.source",
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/primary_location/source",
            observed_kind=ObservedKind.WRONG_TYPE,
            validator_code=ValidatorCode.PRIMARY_SOURCE_OBJECT_OR_NULL,
        )
    display_name = source.get("display_name")
    return (
        None
        if display_name is None
        else _safe_text(
            display_name,
            "venue",
            maximum=1_000,
            context=context,
            failure_stage=FailureStage.WORK_NORMALIZATION,
            approved_json_path="/results/*/primary_location/source/display_name",
            required_code=ValidatorCode.VENUE_REQUIRED_TEXT,
            length_code=ValidatorCode.VENUE_LENGTH,
            control_code=ValidatorCode.VENUE_CONTROL,
        )
    )


def _invalid_field(
    field: str,
    *,
    context: _WorkDiagnosticContext,
    failure_stage: FailureStage,
    approved_json_path: str,
    observed_kind: ObservedKind,
    validator_code: ValidatorCode,
    nested_element_index: int | None = None,
) -> ProxyAdapterError:
    return ProxyAdapterError(
        "PROVIDER_INVALID_RESPONSE",
        f"Provider field {field} was invalid",
        provider_http_calls=1,
        provider_http_status=200,
        structural_failure=_work_failure(
            context,
            failure_stage=failure_stage,
            approved_json_path=approved_json_path,
            observed_kind=observed_kind,
            validator_code=validator_code,
            nested_element_index=nested_element_index,
        ),
    )
