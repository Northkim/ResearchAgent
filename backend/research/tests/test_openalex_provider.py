from __future__ import annotations

import asyncio
import json
from functools import wraps
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from backend.research.adapters import (
    HttpxOpenAlexTransport,
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexHttpResponse,
    OpenAlexPaperSearchProvider,
)
from backend.research.contracts import (
    ProviderBudget,
    ProviderFailureCategory,
    ProviderReservation,
    ResearchQuery,
)
from backend.research.ports import ProviderError, ProviderRequestContext
from backend.persistence.adapters import InMemoryUnitOfWork
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService
from backend.research.skills import search_papers
from backend.skill_system.exceptions import SkillExecutionFailure
from backend.skill_system.models import SkillCapabilities, SkillExecutionContext

NOW = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)


def async_test(function):
    @wraps(function)
    def run(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))

    return run


class SyntheticTransport:
    def __init__(self, responses: list[OpenAlexHttpResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, path, *, params, timeout_seconds, headers):
        del timeout_seconds, headers
        self.calls.append((path, dict(params)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _response(value: Any, status: int = 200, **headers: str) -> OpenAlexHttpResponse:
    return OpenAlexHttpResponse(
        status_code=status,
        body=json.dumps(value).encode(),
        headers=headers,
    )


def _rate(remaining: str = "1", search_cost: str = "0.001") -> OpenAlexHttpResponse:
    return _response(
        {
            "rate_limit": {
                "daily_remaining_usd": remaining,
                "prepaid_remaining_usd": "0",
                "endpoint_costs_usd": {"search": search_cost},
            }
        }
    )


def _work(
    identifier: str = "W123",
    *,
    title: str = "A Unicode α Study",
    doi: str | None = "https://doi.org/10.1234/example",
    abstract: dict[str, list[int]] | None = None,
    authorships: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/{identifier}",
        "doi": doi,
        "display_name": title,
        "authorships": authorships
        if authorships is not None
        else [
            {
                "author": {
                    "id": "https://openalex.org/A42",
                    "display_name": "Zoë Researcher",
                    "orcid": "https://orcid.org/0000-0000-0000-0042",
                }
            }
        ],
        "abstract_inverted_index": abstract
        if abstract is not None
        else {"Synthetic": [0], "abstract": [1], "evidence": [2]},
        "publication_year": 2025,
        "publication_date": "2025-01-01",
        "primary_location": {"source": {"display_name": "Synthetic Test Journal"}},
        "language": "en",
        "type": "article",
        "updated_date": "2026-01-01T00:00:00",
    }


def _works(items: list[Any], *, count: int | None = None) -> OpenAlexHttpResponse:
    return _response(
        {
            "meta": {
                "count": len(items) if count is None else count,
                "per_page": len(items),
                "next_cursor": None,
                "cost_usd": 0.001,
            },
            "results": items,
        },
        **{"x-request-id": "synthetic-request-id"},
    )


def _context() -> ProviderRequestContext:
    return ProviderRequestContext(
        operation_id="operation-1",
        idempotency_key="idempotency-1",
        request_fingerprint="sha256:" + "1" * 64,
        deadline=NOW + timedelta(seconds=90),
    )


def _provider(
    transport: SyntheticTransport,
    *,
    sleeper=None,
    api_key: str | None = None,
    clock=lambda: NOW,
) -> OpenAlexPaperSearchProvider:
    return OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key=api_key),
        transport=transport,
        clock=clock,
        sleeper=sleeper,
    )


def test_request_identity_escapes_user_text_and_contains_plan_fingerprint() -> None:
    provider = _provider(SyntheticTransport([]))
    identity = provider.request_identity(
        ResearchQuery(topic='agent "instructions" \\ evidence', max_results=3),
        limit=3,
    )
    assert identity["exact_query"] == (
        '"agent" AND "\\"instructions\\"" AND "\\\\" AND "evidence"'
    )
    assert identity["search_plan_fingerprint"].startswith("sha256:")
    assert "api_key" not in identity


def test_request_identity_rejects_more_than_five_selected_results_pre_call() -> None:
    provider = _provider(SyntheticTransport([]))
    with pytest.raises(ProviderError) as caught:
        provider.request_identity(
            ResearchQuery(topic="bounded selection", max_results=6),
            limit=6,
        )
    assert caught.value.category is ProviderFailureCategory.INVALID_QUERY


@async_test
async def test_http_transport_does_not_retain_credential_bearing_exception(
    monkeypatch,
) -> None:
    canary = "synthetic-secret-canary"

    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, path, *, params):
            request = httpx.Request(
                "GET",
                f"https://api.openalex.org{path}",
                params=params,
            )
            raise httpx.ConnectError("synthetic network failure", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: FailingClient())
    transport = HttpxOpenAlexTransport("https://api.openalex.org")

    with pytest.raises(ProviderError) as caught:
        await transport.get(
            "/works",
            params={"api_key": canary, "search": "safe query"},
            timeout_seconds=15,
            headers={"accept": "application/json"},
        )

    assert caught.value.category is ProviderFailureCategory.PROVIDER_UNAVAILABLE
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert canary not in str(caught.value)
    assert canary not in repr(caught.value.safe_details)


@async_test
async def test_maps_complete_openalex_record_and_search_evidence() -> None:
    transport = SyntheticTransport([_rate(), _works([_work()])])
    result = await _provider(transport, api_key="not-a-real-key").search(
        ResearchQuery(topic="evidence synthesis", max_results=1),
        limit=1,
        context=_context(),
    )

    paper = result.papers[0]
    assert paper.provider_id == "W123"
    assert paper.title == "A Unicode α Study"
    assert paper.authors[0].name == "Zoë Researcher"
    assert paper.abstract == "Synthetic abstract evidence"
    assert paper.doi == "10.1234/example"
    assert paper.source_url == "https://openalex.org/W123"
    assert paper.source_provider == "openalex@1.0.0"
    assert "identity_unverified_discovery_only" in paper.metadata_limitations
    assert result.search_plan is not None
    assert result.search_execution.provider_reported_cost_usd == "0.001"
    assert result.search_statistics.records_normalized == 1
    assert result.usage.request_count == 2
    assert result.usage.estimated_cost_minor_units == 0
    assert result.search_plan.fingerprint == result.search_execution.search_plan_fingerprint
    assert transport.calls[1][1]["api_key"] == "not-a-real-key"
    assert "api_key" not in json.dumps(result.search_execution.to_dict())


@async_test
async def test_missing_optional_fields_are_explicit_not_fabricated() -> None:
    work = _work(doi=None, abstract={})
    work["authorships"] = []
    work["primary_location"] = None
    work["publication_year"] = "invalid"
    result = await _provider(SyntheticTransport([_rate(), _works([work])])).search(
        ResearchQuery(topic="metadata missingness", max_results=1),
        limit=1,
        context=_context(),
    )

    paper = result.papers[0]
    assert paper.abstract is None
    assert paper.doi is None
    assert paper.authors == ()
    assert paper.publication_venue is None
    assert paper.publication_year is None
    assert {
        "abstract_missing",
        "doi_missing",
        "authors_missing",
        "venue_missing",
        "publication_year_missing_or_invalid",
    }.issubset(paper.metadata_limitations)


@async_test
async def test_exact_doi_and_openalex_id_deduplicate_but_title_year_is_advisory() -> None:
    first = _work("W1", doi="10.1234/same", title="Shared Title")
    same_doi = _work("W2", doi="10.1234/same", title="Other")
    same_id = _work("W1", doi="10.1234/other", title="Other 2")
    advisory = _work("W3", doi=None, title="Shared Title")
    result = await _provider(
        SyntheticTransport([_rate(), _works([first, same_doi, same_id, advisory])])
    ).search(
        ResearchQuery(topic="identity policy", max_results=4),
        limit=4,
        context=_context(),
    )

    assert [paper.provider_id for paper in result.papers] == ["W1", "W3"]
    assert result.search_statistics.duplicate_doi_count == 1
    assert result.search_statistics.duplicate_provider_id_count == 1
    assert result.search_statistics.advisory_title_year_clusters == 1


@async_test
async def test_malformed_records_are_rejected_with_explicit_statistics() -> None:
    result = await _provider(
        SyntheticTransport(
            [_rate(), _works([{"id": "bad"}, "not-an-object"], count=2)]
        )
    ).search(
        ResearchQuery(topic="schema safety", max_results=2),
        limit=2,
        context=_context(),
    )

    assert result.papers == ()
    assert result.complete is True
    assert result.search_statistics.records_rejected == 2
    assert result.search_statistics.records_normalized == 0


@async_test
async def test_incomplete_bounded_page_fails_closed() -> None:
    with pytest.raises(ProviderError) as caught:
        await _provider(
            SyntheticTransport([_rate(), _works([_work()], count=100)])
        ).search(
            ResearchQuery(topic="incomplete page", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE
    assert caught.value.safe_details["failure_point"] == "incomplete_page"
    assert caught.value.safe_details["request_count"] == 2


@async_test
async def test_top_level_contract_drift_fails_closed() -> None:
    with pytest.raises(ProviderError) as caught:
        await _provider(SyntheticTransport([_rate(), _response({"meta": {}})])).search(
            ResearchQuery(topic="contract drift", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE


@async_test
async def test_rate_limit_retries_with_bounded_backoff() -> None:
    delays: list[float] = []

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    transport = SyntheticTransport(
        [_rate(), _response({}, status=429, **{"retry-after": "2"}), _works([_work()])]
    )
    result = await _provider(transport, sleeper=sleeper).search(
        ResearchQuery(topic="retry behavior", max_results=1),
        limit=1,
        context=_context(),
    )
    assert result.usage.request_count == 3
    assert result.usage.retry_count == 1
    assert delays == [2.0]


@async_test
@pytest.mark.parametrize(
    ("status", "category"),
    [
        (401, ProviderFailureCategory.PROVIDER_AUTHENTICATION),
        (400, ProviderFailureCategory.INVALID_QUERY),
    ],
)
async def test_non_retryable_http_failures_are_normalized(
    status: int,
    category: ProviderFailureCategory,
) -> None:
    with pytest.raises(ProviderError) as caught:
        await _provider(
            SyntheticTransport([_rate(), _response({"secret": "redacted"}, status=status)])
        ).search(
            ResearchQuery(topic="normalized failures", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is category
    assert "secret" not in str(caught.value.safe_details)


@async_test
async def test_official_403_rate_limit_contract_is_bounded_and_retryable() -> None:
    responses = [_rate(), *[_response({}, status=403) for _ in range(3)]]
    with pytest.raises(ProviderError) as caught:
        await _provider(
            SyntheticTransport(responses),
            sleeper=lambda _: None,
        ).search(
            ResearchQuery(topic="rate policy", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.PROVIDER_RATE_LIMIT
    assert caught.value.retryable is True
    assert caught.value.safe_details["request_count"] == 4
    assert caught.value.safe_details["retry_count"] == 2


@async_test
async def test_free_credit_preflight_blocks_before_search() -> None:
    transport = SyntheticTransport([_rate(remaining="0", search_cost="0.001")])
    with pytest.raises(ProviderError) as caught:
        await _provider(transport).search(
            ResearchQuery(topic="budget safety", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.BUDGET_EXCEEDED
    assert [path for path, _ in transport.calls] == ["/rate-limit"]


@async_test
async def test_malformed_json_is_rejected_without_raw_content_diagnostic() -> None:
    transport = SyntheticTransport(
        [_rate(), OpenAlexHttpResponse(status_code=200, body=b"{not-json")]
    )
    with pytest.raises(ProviderError) as caught:
        await _provider(transport).search(
            ResearchQuery(topic="json safety", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE
    assert "not-json" not in str(caught.value.safe_details)


@async_test
async def test_transport_timeout_retries_twice_then_reports_actual_usage() -> None:
    timeout = lambda: ProviderError(
        ProviderFailureCategory.PROVIDER_TIMEOUT,
        "synthetic timeout",
        retryable=True,
        safe_details={"failure_point": "http_transport"},
    )
    transport = SyntheticTransport([_rate(), timeout(), timeout(), timeout()])
    with pytest.raises(ProviderError) as caught:
        await _provider(transport, sleeper=lambda _: None).search(
            ResearchQuery(topic="timeout policy", max_results=1),
            limit=1,
            context=_context(),
        )
    assert caught.value.category is ProviderFailureCategory.PROVIDER_TIMEOUT
    assert caught.value.safe_details["request_count"] == 4
    assert caught.value.safe_details["retry_count"] == 2
    assert len(transport.calls) == 4


@async_test
async def test_live_skill_reserves_settles_emits_evidence_and_replay_does_not_call(
    tmp_path,
) -> None:
    transport = SyntheticTransport([_rate(), _works([_work()])])
    provider = _provider(transport, clock=lambda: datetime.now(UTC))
    uow = InMemoryUnitOfWork()
    context = SkillExecutionContext(
        project_id="openalex-project",
        workflow_run_id="openalex-run",
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        step_id="search_papers",
        step_run_id="search-step-run",
        attempt=1,
        capabilities=SkillCapabilities(
            paper_search=provider,
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
            provider_execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        ),
    )
    query = ResearchQuery(
        topic="supervised adapter",
        year_from=2020,
        year_to=2026,
        max_results=1,
    )
    output = await search_papers({"query": query.to_dict()}, context)

    assert {
        item.logical_name for item in output.emitted_artifacts
    } == {
        "search_plan.json",
        "search_execution.json",
        "search_statistics.json",
    }
    operation = uow.provider_operations.list_for_run(
        "openalex-project",
        "openalex-run",
    )[0]
    assert operation.is_live_provider is True
    assert operation.reservation.request_count == 4
    assert operation.actual_usage.request_count == 2
    assert operation.actual_usage.estimated_cost_minor_units == 0
    assert operation.status.value == "SUCCEEDED"
    assert operation.settlement_state.value == "SETTLED"
    assert len(transport.calls) == 2

    with pytest.raises(SkillExecutionFailure) as caught:
        await search_papers({"query": query.to_dict()}, context)
    assert caught.value.code == "PROVIDER_REPLAY_REQUIRES_PERSISTED_OUTPUT"
    assert len(transport.calls) == 2


@async_test
async def test_live_skill_failure_settles_actual_attempts(tmp_path) -> None:
    timeout = lambda: ProviderError(
        ProviderFailureCategory.PROVIDER_TIMEOUT,
        "synthetic timeout",
        retryable=True,
        safe_details={"failure_point": "http_transport"},
    )
    transport = SyntheticTransport([_rate(), timeout(), timeout(), timeout()])
    provider = _provider(
        transport,
        sleeper=lambda _: None,
        clock=lambda: datetime.now(UTC),
    )
    uow = InMemoryUnitOfWork()
    context = SkillExecutionContext(
        project_id="openalex-failure-project",
        workflow_run_id="openalex-failure-run",
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        step_id="search_papers",
        step_run_id="search-step-run",
        attempt=1,
        capabilities=SkillCapabilities(
            paper_search=provider,
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
            provider_execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        ),
    )
    query = ResearchQuery(
        topic="failure settlement",
        year_from=2020,
        year_to=2026,
        max_results=3,
    )
    with pytest.raises(ProviderError):
        await search_papers({"query": query.to_dict()}, context)
    operation = uow.provider_operations.list_for_run(
        "openalex-failure-project",
        "openalex-failure-run",
    )[0]
    assert operation.status.value == "FAILED"
    assert operation.settlement_state.value == "SETTLED"
    assert operation.failure_category is ProviderFailureCategory.PROVIDER_TIMEOUT
    assert operation.actual_usage.request_count == 4
    assert operation.retry_count == 2


@async_test
async def test_live_skill_budget_fails_before_any_provider_call(tmp_path) -> None:
    transport = SyntheticTransport([])
    provider = _provider(transport, clock=lambda: datetime.now(UTC))
    uow = InMemoryUnitOfWork()
    policy = ProviderExecutionPolicy(
        budget=ProviderBudget(
            max_provider_requests=3,
            max_llm_calls=0,
            max_input_tokens=0,
            max_output_tokens=0,
            max_cost_minor_units=0,
            live_provider_enabled=True,
        ),
        live_provider_names=frozenset({"openalex"}),
        reservations={"openalex": ProviderReservation(request_count=4)},
    )
    context = SkillExecutionContext(
        project_id="openalex-budget-project",
        workflow_run_id="openalex-budget-run",
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        step_id="search_papers",
        step_run_id="search-step-run",
        attempt=1,
        capabilities=SkillCapabilities(
            paper_search=provider,
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
            provider_execution_policy=policy,
        ),
    )
    query = ResearchQuery(
        topic="budget fail closed",
        year_from=2020,
        year_to=2026,
        max_results=3,
    )
    with pytest.raises(SkillExecutionFailure) as caught:
        await search_papers({"query": query.to_dict()}, context)
    assert caught.value.code == "BUDGET_EXCEEDED"
    assert caught.value.details["dimension"] == "provider_requests"
    assert transport.calls == []
    assert uow.provider_operations.list_for_run(
        "openalex-budget-project",
        "openalex-budget-run",
    ) == ()
