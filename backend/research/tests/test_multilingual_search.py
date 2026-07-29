from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from backend.persistence.adapters import InMemoryUnitOfWork
from backend.research.adapters import (
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexPaperSearchProvider,
)
from backend.research.contracts import (
    FieldRejectionDiagnostic,
    PaperAuthor,
    PaperRecord,
    ProviderBudget,
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderReservation,
    ProviderUsage,
    QueryVariant,
    QueryVariantType,
    ResearchQuery,
    SearchDiagnosticCode,
    SearchExecution,
    SearchPlan,
    SearchStatistics,
    SettlementState,
    canonical_hash,
)
from backend.research.evaluation.candidate_pool import EvaluationGenerationError
from backend.research.evaluation.contracts import EvaluationCompletionState
from backend.research.evaluation.multilingual import (
    MultilingualCandidatePoolGenerator,
    load_multilingual_plan,
)
from backend.research.evaluation.topics import load_topic_set
from backend.research.ports import (
    PaperSearchProvider,
    PaperSearchResult,
    ProviderError,
    ProviderIdentity,
)
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService

NOW = datetime(2026, 7, 29, 8, 0, tzinfo=UTC)
PLAN_PATH = "evaluation/topics/openalex_chinese_multilingual_v1.json"


def _topic():
    return next(
        item
        for item in load_topic_set("evaluation/topics/openalex_v1.json").topics
        if item.topic_id == "nonenglish-chinese-digital-humanities"
    )


def _paper(
    provider_id: str,
    doi: str | None,
    *,
    title: str,
    year: int = 2025,
    language: str | None = "zh",
) -> PaperRecord:
    return PaperRecord(
        paper_id=PaperRecord.internal_id(
            provider="openalex",
            provider_id=provider_id,
            doi=doi,
        ),
        provider_id=provider_id,
        title=title,
        authors=(PaperAuthor(name="Synthetic Author"),),
        abstract="Synthetic abstract content for a network-free test.",
        publication_year=year,
        publication_venue="Synthetic Venue",
        source_provider="openalex@test",
        source_url=f"https://openalex.org/{provider_id}",
        doi=doi,
        retrieved_at=NOW,
        raw_metadata_hash=canonical_hash(
            {"provider_id": provider_id, "doi": doi, "title": title}
        ),
        language=language,
    )


class EvidenceProvider(PaperSearchProvider):
    IDENTITY = ProviderIdentity(
        provider="openalex",
        adapter_version="test",
        model_or_endpoint="synthetic-evidence",
    )

    def __init__(self, results, failures=()):
        self.results = results
        self.failures = set(failures)
        self.calls: list[str] = []

    @property
    def identity(self):
        return self.IDENTITY

    def request_identity(self, query: ResearchQuery, *, limit: int):
        del limit
        exact = " AND ".join(f'"{item}"' for item in query.topic.split())
        return {"exact_query": exact, "query_hash": query.query_hash}

    async def search(self, query, *, limit, context):
        del limit
        self.calls.append(query.topic)
        if query.topic in self.failures:
            raise ProviderError(
                ProviderFailureCategory.PROVIDER_UNAVAILABLE,
                "synthetic variant failure",
                retryable=False,
                safe_details={"request_count": 1, "latency_ms": 1},
            )
        papers = tuple(self.results.get(query.topic, ()))
        fingerprint = canonical_hash(
            {"query": query.to_dict(), "operation": context.operation_id}
        )
        usage = ProviderUsage(
            provider="openalex",
            model_or_endpoint="synthetic-evidence",
            operation_kind=ProviderOperationKind.SEARCH,
            request_count=1,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=1,
        )
        return PaperSearchResult(
            papers=papers,
            usage=usage,
            request_fingerprint=context.request_fingerprint,
            retrieved_at=NOW,
            search_plan=SearchPlan(
                topic=query.topic,
                research_question=None,
                keywords=(),
                exact_query=self.request_identity(query, limit=1)["exact_query"],
                year_from=query.year_from,
                year_to=query.year_to,
                language_policy=query.language,
                document_type_policy="synthetic",
                inclusion_criteria=("synthetic",),
                exclusion_criteria=("synthetic",),
                maximum_results=20,
                pagination_policy={"maximum_pages": 1},
                sort_policy="synthetic",
                provider="openalex",
                adapter_version="test",
                api_contract_snapshot="synthetic",
                planned_at=NOW,
            ),
            search_execution=SearchExecution(
                search_plan_fingerprint=fingerprint,
                provider="openalex",
                adapter_version="test",
                endpoint="synthetic",
                requested_fields=("metadata",),
                request_count=1,
                retry_count=0,
                complete=True,
                cursor_pages=1,
                retrieved_at=NOW,
                provider_reported_cost_usd="0",
            ),
            search_statistics=SearchStatistics(
                search_plan_fingerprint=fingerprint,
                provider_reported_count=len(papers),
                records_received=len(papers),
                records_normalized=len(papers),
                records_rejected=0,
                duplicate_doi_count=0,
                duplicate_provider_id_count=0,
                advisory_title_year_clusters=0,
                missing_abstract_count=0,
                incomplete=False,
            ),
        )


def _policy() -> ProviderExecutionPolicy:
    return ProviderExecutionPolicy(
        budget=ProviderBudget(
            max_provider_requests=4,
            max_llm_calls=0,
            max_input_tokens=0,
            max_output_tokens=0,
            max_cost_minor_units=0,
            max_runtime_seconds=30,
            live_provider_enabled=True,
        ),
        live_provider_names=frozenset({"openalex"}),
        reservations={"openalex": ProviderReservation(request_count=1)},
        operation_timeout_seconds=30,
    )


def _generator(tmp_path, provider):
    unit = InMemoryUnitOfWork()
    service = ProviderOperationService(
        unit.provider_operations,
        commit_callback=unit.commit,
    )
    return (
        MultilingualCandidatePoolGenerator(
            provider=provider,
            provider_operations=service,
            execution_policy=_policy(),
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
            clock=lambda: NOW,
        ),
        service,
    )


def test_query_variant_and_plan_are_immutable_and_hash_stable() -> None:
    first = load_multilingual_plan(PLAN_PATH)
    second = load_multilingual_plan(PLAN_PATH)
    assert first.plan_checksum == second.plan_checksum
    assert [item.checksum for item in first.query_variants] == [
        item.checksum for item in second.query_variants
    ]
    with pytest.raises(FrozenInstanceError):
        first.query_variants[0].source_query = "changed"
    with pytest.raises(TypeError):
        first.coverage_warning_policy["low_result_count"] = 1
    with pytest.raises(ValueError):
        QueryVariant(
            variant_id="bad",
            source_query="bad",
            source_language="en",
            variant_language="en",
            variant_type="NOT_A_TYPE",
            exact_provider_query='"bad"',
            generated_by="test",
            generation_method="test",
            generation_version="v1",
            owner_approved=True,
            created_at=NOW,
        )


def test_plan_rejects_duplicate_ids_queries_and_invalid_budget() -> None:
    plan = load_multilingual_plan(PLAN_PATH)
    first = plan.query_variants[0]
    duplicate_id = replace(
        plan.query_variants[1],
        variant_id=first.variant_id,
        checksum="",
    )
    with pytest.raises(ValueError, match="IDs must be unique"):
        replace(
            plan,
            query_variants=(first, duplicate_id),
            total_request_limit=2,
            plan_checksum="",
        )
    duplicate_query = replace(
        plan.query_variants[1],
        exact_provider_query=first.exact_provider_query,
        checksum="",
    )
    with pytest.raises(ValueError, match="queries must be unique"):
        replace(
            plan,
            query_variants=(first, duplicate_query),
            total_request_limit=2,
            plan_checksum="",
        )
    with pytest.raises(ValueError, match="at least one request"):
        replace(plan, total_request_limit=3, plan_checksum="")


def test_unapproved_variant_is_rejected_before_provider_call(tmp_path) -> None:
    plan = load_multilingual_plan(PLAN_PATH)
    unapproved = replace(plan.query_variants[0], owner_approved=False, checksum="")
    unsafe = replace(
        plan,
        query_variants=(unapproved,),
        total_request_limit=1,
        plan_checksum="",
    )
    provider = EvidenceProvider({})
    generator, _ = _generator(tmp_path, provider)
    with pytest.raises(EvaluationGenerationError, match="owner-approved"):
        asyncio.run(
            generator.generate(
                evaluation_id="unapproved",
                topic=_topic(),
                plan=unsafe,
                topic_set_version="1.0.0",
            )
        )
    assert provider.calls == []


def test_execution_merge_provenance_operations_and_replay(tmp_path) -> None:
    plan = load_multilingual_plan(PLAN_PATH)
    values = [item.source_query for item in plan.query_variants]
    shared = _paper("W1", "10.1234/shared", title="Shared work")
    provider = EvidenceProvider(
        {
            values[0]: (
                shared,
                _paper("W2", "10.1234/title-a", title="Advisory title"),
            ),
            values[1]: (
                shared,
                _paper("W3", "10.1234/title-b", title="Advisory title"),
            ),
            values[2]: (_paper("W4", "10.1234/english", title="English result", language="en"),),
            values[3]: (),
        }
    )
    generator, service = _generator(tmp_path, provider)
    first = asyncio.run(
        generator.generate(
            evaluation_id="multilingual-network-free",
            topic=_topic(),
            plan=plan,
            topic_set_version="1.0.0",
        )
    )
    assert provider.calls == values
    assert len(first.candidates) == 4
    shared_candidate = next(item for item in first.candidates if item.openalex_id == "W1")
    assert shared_candidate.first_seen_variant_id == "zh-original-v1"
    assert shared_candidate.all_matched_variant_ids == (
        "zh-original-v1",
        "zh-manual-synonym-v1",
    )
    operations = service.list_for_run(
        project_id="evaluation:multilingual-network-free",
        workflow_run_id="evaluation:multilingual-network-free",
    )
    assert len(operations) == 4
    assert all(item.status is ProviderOperationStatus.SUCCEEDED for item in operations)
    assert all(item.settlement_state is SettlementState.SETTLED for item in operations)
    assert {
        item.logical_name for item in first.artifacts
    }.issuperset(
        {
            "multilingual_search_plan.json",
            "query_variant_execution.json",
            "multilingual_search_statistics.json",
            "deterministic_merge_report.json",
            "coverage_diagnostics.json",
            "merged_candidates.json",
        }
    )
    second = asyncio.run(
        generator.generate(
            evaluation_id="multilingual-network-free",
            topic=_topic(),
            plan=plan,
            topic_set_version="1.0.0",
        )
    )
    assert second.resumed is True
    assert provider.calls == values
    retained = "\n".join(
        path.read_text(errors="ignore")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert '"results":[' not in retained
    assert '"relevance_label":"' not in retained


def test_partial_and_total_variant_failures_settle_operations(tmp_path) -> None:
    plan = load_multilingual_plan(PLAN_PATH)
    values = [item.source_query for item in plan.query_variants]
    partial_provider = EvidenceProvider(
        {values[0]: (_paper("W1", "10.1234/one", title="One"),)},
        failures=values[1:],
    )
    partial, partial_service = _generator(tmp_path / "partial", partial_provider)
    result = asyncio.run(
        partial.generate(
            evaluation_id="partial",
            topic=_topic(),
            plan=plan,
            topic_set_version="1.0.0",
        )
    )
    assert len(result.candidates) == 1
    assert any(
        item.code is SearchDiagnosticCode.PARTIAL_VARIANT_FAILURE
        for item in result.diagnostics
    )
    assert partial_service.repository.list_unsettled(
        project_id="evaluation:partial"
    ) == ()

    total_provider = EvidenceProvider({}, failures=values)
    total, total_service = _generator(tmp_path / "total", total_provider)
    empty = asyncio.run(
        total.generate(
            evaluation_id="total",
            topic=_topic(),
            plan=plan,
            topic_set_version="1.0.0",
        )
    )
    assert empty.candidates == ()
    assert any(item.blocking for item in empty.diagnostics)
    assert empty.evaluation_run.completion_state is EvaluationCompletionState.FAILED
    assert total_service.repository.list_unsettled(project_id="evaluation:total") == ()


def test_exact_identity_conflicts_stay_separate_and_title_year_is_advisory(
    tmp_path,
) -> None:
    plan = load_multilingual_plan(PLAN_PATH)
    values = [item.source_query for item in plan.query_variants]
    provider = EvidenceProvider(
        {
            values[0]: (
                _paper("W10", "10.1234/conflict", title="Same title"),
                _paper("W20", "10.1234/doi-a", title="ID conflict"),
            ),
            values[1]: (
                _paper("W11", "10.1234/conflict", title="Same title"),
                _paper("W20", "10.1234/doi-b", title="ID conflict"),
            ),
        }
    )
    generator, _ = _generator(tmp_path, provider)
    result = asyncio.run(
        generator.generate(
            evaluation_id="conflicts",
            topic=_topic(),
            plan=plan,
            topic_set_version="1.0.0",
        )
    )
    assert {item.openalex_id for item in result.candidates}.issuperset(
        {"W10", "W11", "W20"}
    )
    assert any(
        item.code is SearchDiagnosticCode.IDENTITY_CONFLICT
        for item in result.diagnostics
    )
    assert any(
        item.code is SearchDiagnosticCode.ADVISORY_TITLE_YEAR_CLUSTER
        for item in result.diagnostics
    )


def test_safe_rejection_diagnostics_include_length_limit_hash_and_bounded_preview() -> None:
    provider = OpenAlexPaperSearchProvider(OpenAlexConfiguration())
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "x" * 501,
                "authorships": [],
                "abstract_inverted_index": {"safe": [0]},
                "doi": None,
                "publication_year": 2025,
                "primary_location": None,
                "language": "zh",
            }
        ]
    }
    papers, mapping = provider._map_results(payload, retrieved_at=NOW)
    assert papers == ()
    diagnostic = mapping["rejection_diagnostics"][0]
    assert diagnostic.category is SearchDiagnosticCode.FIELD_LENGTH_REJECTED
    assert diagnostic.field_name == "title"
    assert diagnostic.measured_normalized_length == 501
    assert diagnostic.configured_limit == 500
    assert diagnostic.value_sha256.startswith("sha256:")
    assert diagnostic.preview_length <= 80
    assert "x" * 501 not in repr(diagnostic)


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("safe\x00unsafe", SearchDiagnosticCode.CONTROL_CHARACTER_REJECTED),
        ("\ud800", SearchDiagnosticCode.INVALID_UNICODE),
    ],
)
def test_control_and_invalid_unicode_are_typed(value, code) -> None:
    provider = OpenAlexPaperSearchProvider(OpenAlexConfiguration())
    with pytest.raises(ValueError) as caught:
        provider._clean_optional(value, field_name="title", maximum=500)
    assert caught.value.diagnostic.category is code
    assert "\x00" not in (caught.value.diagnostic.safe_preview or "")


def test_historical_unavailable_diagnostic_does_not_invent_details() -> None:
    diagnostic = FieldRejectionDiagnostic(
        category=SearchDiagnosticCode.FIELD_LENGTH_REJECTED,
        field_name=None,
        measured_normalized_length=None,
        configured_limit=None,
        record_identity=None,
        value_sha256=None,
        safe_preview=None,
        preview_length=0,
        adapter_version="1.0.0",
        validator_version="historical/unknown",
        details_available=False,
        unavailable_reason=(
            "Historical artifact did not record field name, measured length, or limit"
        ),
    )
    assert diagnostic.details_available is False
    assert diagnostic.field_name is None
    assert diagnostic.measured_normalized_length is None
    assert diagnostic.configured_limit is None
