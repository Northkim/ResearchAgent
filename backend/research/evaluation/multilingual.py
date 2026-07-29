"""Evaluation-only orchestration for explicit multilingual paper searches."""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from backend.research.contracts import (
    DiagnosticCause,
    MultilingualSearchPlan,
    PaperRecord,
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderUsage,
    QueryVariant,
    ResearchQuery,
    SearchDiagnostic,
    SearchDiagnosticCode,
    SettlementState,
    canonical_hash,
)
from backend.research.contracts._serialization import canonical_json
from backend.research.ports import (
    ArtifactContentStorage,
    PaperSearchProvider,
    ProviderError,
    ProviderRequestContext,
)
from backend.research.services import (
    BudgetExceededError,
    ProviderExecutionPolicy,
    ProviderOperationService,
)

from .candidate_pool import EvaluationArtifact, EvaluationGenerationError
from .contracts import (
    EvaluationCandidate,
    EvaluationCompletionState,
    EvaluationRun,
    EvaluationTopic,
)


@dataclass(frozen=True, slots=True)
class MultilingualCandidatePoolResult:
    evaluation_run: EvaluationRun
    candidates: tuple[EvaluationCandidate, ...]
    diagnostics: tuple[SearchDiagnostic, ...]
    artifacts: tuple[EvaluationArtifact, ...]
    resumed: bool


@dataclass(frozen=True, slots=True)
class _VariantOutcome:
    variant: QueryVariant
    operation_id: str
    papers: tuple[PaperRecord, ...]
    usage: ProviderUsage | None
    execution: Mapping[str, Any]
    statistics: Mapping[str, Any]
    rejection_diagnostics: tuple[Mapping[str, Any], ...]
    failure: Mapping[str, Any] | None


@dataclass(slots=True)
class _MergedPaper:
    paper: PaperRecord
    first_seen_variant_id: str
    matched_variant_ids: list[str]
    query_checksums: list[str]
    operation_ids: list[str]


def load_multilingual_plan(path: str | Path) -> MultilingualSearchPlan:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("Multilingual search-plan file must contain an object")
    query_value = value.get("original_query")
    variants_value = value.get("query_variants")
    if not isinstance(query_value, Mapping) or not isinstance(variants_value, list):
        raise ValueError("Multilingual search plan is missing query contracts")
    query = ResearchQuery(
        topic=str(query_value["topic"]),
        keywords=tuple(str(item) for item in query_value.get("keywords", ())),
        year_from=(
            None if query_value.get("year_from") is None else int(query_value["year_from"])
        ),
        year_to=None if query_value.get("year_to") is None else int(query_value["year_to"]),
        max_results=int(query_value.get("max_results", 20)),
        language=str(query_value.get("language", "und")),
        inclusion_criteria=tuple(
            str(item) for item in query_value.get("inclusion_criteria", ())
        ),
        exclusion_criteria=tuple(
            str(item) for item in query_value.get("exclusion_criteria", ())
        ),
        schema_version=str(query_value.get("schema_version", "research-query/v1")),
    )
    return MultilingualSearchPlan(
        plan_id=str(value["plan_id"]),
        original_query=query,
        original_language=str(value["original_language"]),
        query_variants=tuple(QueryVariant.from_dict(item) for item in variants_value),
        language_filter=(
            None if value.get("language_filter") is None else str(value["language_filter"])
        ),
        merge_policy_version=str(value["merge_policy_version"]),
        deduplication_policy_version=str(value["deduplication_policy_version"]),
        per_variant_request_limit=int(value["per_variant_request_limit"]),
        total_request_limit=int(value["total_request_limit"]),
        candidate_limit=int(value["candidate_limit"]),
        expansion_version=str(value["expansion_version"]),
        coverage_warning_policy=dict(value.get("coverage_warning_policy", {})),
        plan_checksum=str(value.get("plan_checksum", "")),
        schema_version=str(
            value.get("schema_version", "reagent-multilingual-search-plan/v1")
        ),
    )


class MultilingualCandidatePoolGenerator:
    """Run approved variants in order and publish one deterministic candidate pool."""

    def __init__(
        self,
        *,
        provider: PaperSearchProvider,
        provider_operations: ProviderOperationService,
        execution_policy: ProviderExecutionPolicy,
        artifact_storage: ArtifactContentStorage,
        clock: Callable[[], datetime] | None = None,
        include_abstract_preview: bool = False,
    ) -> None:
        self.provider = provider
        self.provider_operations = provider_operations
        self.execution_policy = execution_policy
        self.artifact_storage = artifact_storage
        self.clock = clock or (lambda: datetime.now(UTC))
        self.include_abstract_preview = include_abstract_preview

    async def generate(
        self,
        *,
        evaluation_id: str,
        topic: EvaluationTopic,
        plan: MultilingualSearchPlan,
        topic_set_version: str,
    ) -> MultilingualCandidatePoolResult:
        evaluation_id = self._safe_segment(evaluation_id, "evaluation_id")
        self._validate_plan(topic, plan)
        manifest_key = f"{evaluation_id}/evaluation_manifest.json"
        existing = self._read_json_if_present(manifest_key)
        if existing is not None:
            return self._resume(existing, manifest_key)

        started_at = self._now()
        outcomes: list[_VariantOutcome] = []
        diagnostics: list[SearchDiagnostic] = []
        total_requests = 0
        for variant in plan.query_variants:
            outcome = await self._execute_variant(
                evaluation_id=evaluation_id,
                topic=topic,
                plan=plan,
                variant=variant,
            )
            outcomes.append(outcome)
            if outcome.usage is not None:
                total_requests += outcome.usage.request_count
            if total_requests > plan.total_request_limit:
                diagnostics.append(
                    SearchDiagnostic(
                        code=SearchDiagnosticCode.TOTAL_REQUEST_BUDGET_EXCEEDED,
                        cause=DiagnosticCause.LOCAL_VALIDATION,
                        message="Actual provider requests exceeded the immutable plan limit",
                        blocking=True,
                        variant_id=variant.variant_id,
                        details={
                            "actual_request_count": total_requests,
                            "configured_limit": plan.total_request_limit,
                        },
                    )
                )
                break
            diagnostics.extend(self._variant_diagnostics(outcome, plan))

        succeeded = tuple(item for item in outcomes if item.failure is None)
        failed = tuple(item for item in outcomes if item.failure is not None)
        if failed:
            diagnostics.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.PARTIAL_VARIANT_FAILURE,
                    cause=(
                        DiagnosticCause.UNKNOWN
                        if not succeeded
                        else DiagnosticCause.COMBINED
                    ),
                    message=(
                        "All query variants failed"
                        if not succeeded
                        else "One or more query variants failed; successful variants were retained"
                    ),
                    blocking=not succeeded,
                    details={
                        "failed_variant_ids": [
                            item.variant.variant_id for item in failed
                        ],
                        "successful_variant_ids": [
                            item.variant.variant_id for item in succeeded
                        ],
                    },
                )
            )

        merged, merge_report, merge_diagnostics = self._merge(succeeded)
        diagnostics.extend(merge_diagnostics)
        diagnostics.extend(self._merged_diagnostics(merged, plan))
        excluded_by_limit = merged[plan.candidate_limit :]
        merge_report["candidate_limit_exclusions"] = [
            {
                "paper_id": item.paper.paper_id,
                "reason": "CANDIDATE_LIMIT",
            }
            for item in excluded_by_limit
        ]
        if excluded_by_limit:
            diagnostics.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.CANDIDATE_LIMIT_TRUNCATED,
                    cause=DiagnosticCause.LOCAL_VALIDATION,
                    message="Merged candidates above the immutable cap were explicitly excluded",
                    details={
                        "configured_limit": plan.candidate_limit,
                        "excluded_count": len(excluded_by_limit),
                    },
                )
            )
        candidates = self._candidates(topic, merged, plan)
        completed_at = self._now()

        base = f"{evaluation_id}/topics/{self._safe_segment(topic.topic_id, 'topic_id')}"
        execution_document = {
            "schema_version": "reagent-query-variant-execution/v1",
            "plan_checksum": plan.plan_checksum,
            "executions": [
                {
                    "variant": item.variant.to_dict(),
                    "operation_id": item.operation_id,
                    "provider": self.provider.identity.provider,
                    "adapter_version": self.provider.identity.adapter_version,
                    "execution": dict(item.execution),
                    "statistics": dict(item.statistics),
                    "rejection_diagnostics": list(item.rejection_diagnostics),
                    "failure": item.failure,
                    "raw_provider_response_retained": False,
                }
                for item in outcomes
            ],
        }
        statistics_document = {
            "schema_version": "reagent-multilingual-search-statistics/v1",
            "plan_checksum": plan.plan_checksum,
            "per_variant": [
                {
                    "variant_id": item.variant.variant_id,
                    **dict(item.statistics),
                    "failed": item.failure is not None,
                }
                for item in outcomes
            ],
            "variants_configured": len(plan.query_variants),
            "variants_succeeded": len(succeeded),
            "variants_failed": len(failed),
            "input_normalized_records": sum(len(item.papers) for item in succeeded),
            "merged_candidate_count": len(candidates),
            "exact_merge_count": len(merge_report["exact_merges"]),
            "advisory_cluster_count": len(merge_report["advisory_title_year_clusters"]),
            "total_request_count": total_requests,
        }
        candidate_document = {
            "schema_version": "reagent-multilingual-candidate-pool/v1",
            "topic_id": topic.topic_id,
            "plan_checksum": plan.plan_checksum,
            "candidate_count": len(candidates),
            "candidates": [item.to_dict() for item in candidates],
            "contains_relevance_labels": False,
            "raw_provider_response_retained": False,
        }
        artifacts = [
            self._write_json(
                f"{base}/multilingual_search_plan.json",
                "multilingual_search_plan.json",
                plan.to_dict(),
            ),
            self._write_json(
                f"{base}/query_variant_execution.json",
                "query_variant_execution.json",
                execution_document,
            ),
            self._write_json(
                f"{base}/multilingual_search_statistics.json",
                "multilingual_search_statistics.json",
                statistics_document,
            ),
            self._write_json(
                f"{base}/deterministic_merge_report.json",
                "deterministic_merge_report.json",
                merge_report,
            ),
            self._write_json(
                f"{base}/coverage_diagnostics.json",
                "coverage_diagnostics.json",
                {
                    "schema_version": "reagent-coverage-diagnostics/v1",
                    "plan_checksum": plan.plan_checksum,
                    "diagnostics": [item.to_dict() for item in diagnostics],
                },
            ),
            self._write_json(
                f"{base}/merged_candidates.json",
                "merged_candidates.json",
                candidate_document,
            ),
        ]
        topic_manifest_document = {
            "schema_version": "reagent-multilingual-topic-manifest/v1",
            "topic_id": topic.topic_id,
            "query_fingerprint": plan.plan_checksum,
            "pool_checksum": artifacts[-1].checksum,
            "operation_ids": [item.operation_id for item in outcomes],
            "operation_settled": True,
            "usage": {
                "request_count": total_requests,
                "latency_ms": sum(
                    item.usage.latency_ms
                    for item in outcomes
                    if item.usage is not None
                ),
                "retry_count": sum(
                    item.usage.retry_count
                    for item in outcomes
                    if item.usage is not None
                ),
            },
            "artifacts": [item.to_dict() for item in artifacts],
            "candidates": [item.to_dict() for item in candidates],
        }
        topic_manifest = self._write_json(
            f"{base}/topic_manifest.json",
            "topic_manifest.json",
            topic_manifest_document,
        )
        artifacts.append(topic_manifest)
        self._assert_no_unsettled(evaluation_id)

        provider_usages = tuple(
            item.usage.to_dict() for item in outcomes if item.usage is not None
        )
        run = EvaluationRun(
            evaluation_id=evaluation_id,
            topic_set_version=topic_set_version,
            provider=self.provider.identity.provider,
            adapter_version=self.provider.identity.adapter_version,
            api_contract_snapshot="openalex-works-api/2026-07-27",
            query_fingerprints={topic.topic_id: plan.plan_checksum},
            candidate_pool_checksums={topic.topic_id: artifacts[-2].checksum},
            started_at=started_at,
            completed_at=completed_at,
            request_count=total_requests,
            latency_ms=sum(int(item["latency_ms"]) for item in provider_usages),
            retry_count=sum(int(item["retry_count"]) for item in provider_usages),
            provider_usage=provider_usages,
            completion_state=(
                EvaluationCompletionState.FAILED
                if any(item.blocking for item in diagnostics)
                else EvaluationCompletionState.CANDIDATES_COMPLETE
            ),
        )
        manifest_document = {
            "schema_version": "reagent-multilingual-evaluation-manifest/v1",
            "evaluation_run": run.to_dict(),
            "artifacts": [item.to_dict() for item in artifacts],
            "candidate_count": len(candidates),
            "human_judgments_generated": False,
            "relevance_labels_generated": False,
            "raw_provider_response_retained": False,
            "plan_checksum": plan.plan_checksum,
        }
        manifest = self._write_json(
            manifest_key,
            "evaluation_manifest.json",
            manifest_document,
        )
        artifacts.append(manifest)
        return MultilingualCandidatePoolResult(
            evaluation_run=run,
            candidates=candidates,
            diagnostics=tuple(diagnostics),
            artifacts=tuple(artifacts),
            resumed=False,
        )

    async def _execute_variant(
        self,
        *,
        evaluation_id: str,
        topic: EvaluationTopic,
        plan: MultilingualSearchPlan,
        variant: QueryVariant,
    ) -> _VariantOutcome:
        query = ResearchQuery(
            topic=variant.source_query,
            keywords=(),
            year_from=plan.original_query.year_from,
            year_to=plan.original_query.year_to,
            max_results=min(20, plan.candidate_limit),
            language=variant.variant_language,
            inclusion_criteria=plan.original_query.inclusion_criteria,
            exclusion_criteria=plan.original_query.exclusion_criteria,
        )
        selected_limit = min(5, plan.candidate_limit)
        request_identity = self.provider.request_identity(query, limit=selected_limit)
        actual_exact_query = request_identity.get("exact_query")
        if (
            actual_exact_query is not None
            and actual_exact_query != variant.exact_provider_query
        ):
            raise EvaluationGenerationError(
                f"Variant {variant.variant_id} exact provider query does not match "
                "the injected adapter compiler"
            )
        fingerprint = canonical_hash(
            {
                "plan_checksum": plan.plan_checksum,
                "variant_checksum": variant.checksum,
                "provider_request_identity": request_identity,
            }
        )
        operation = self._operation(
            evaluation_id=evaluation_id,
            topic=topic,
            variant=variant,
            fingerprint=fingerprint,
        )
        reservation = operation.reservation.request_count
        if reservation > plan.per_variant_request_limit:
            raise EvaluationGenerationError(
                f"Variant {variant.variant_id} reservation exceeds its request limit"
            )
        try:
            reserved, replay = self.provider_operations.reserve(
                operation,
                budget=self.execution_policy.budget,
            )
        except BudgetExceededError as error:
            raise EvaluationGenerationError(
                f"Multilingual provider budget exceeded: {error.dimension}"
            ) from error
        if replay:
            raise EvaluationGenerationError(
                "A variant ProviderOperation already exists without the immutable "
                "evaluation manifest; refusing a duplicate provider call"
            )
        self.provider_operations.commit_staged()
        now = self._now()
        self.provider_operations.mark_running(operation.id, at=now)
        self.provider_operations.commit_staged()
        context = ProviderRequestContext(
            operation_id=operation.id,
            idempotency_key=operation.idempotency_key,
            request_fingerprint=fingerprint,
            deadline=now
            + timedelta(seconds=self.execution_policy.operation_timeout_seconds),
        )
        try:
            result = await self.provider.search(
                query,
                limit=selected_limit,
                context=context,
            )
        except ProviderError as error:
            usage = self._failure_usage(error)
            self.provider_operations.settle_failure(
                operation.id,
                category=error.category,
                at=self._now(),
                usage=usage,
                provider_call_started=True,
                diagnostic_metadata={
                    "variant_id": variant.variant_id,
                    "retryable": error.retryable,
                    **self._safe_failure_details(error.safe_details),
                },
            )
            self.provider_operations.commit_staged()
            return _VariantOutcome(
                variant=variant,
                operation_id=operation.id,
                papers=(),
                usage=usage,
                execution={"complete": False},
                statistics={"records_normalized": 0, "records_rejected": 0},
                rejection_diagnostics=(),
                failure={
                    "category": error.category.value,
                    "retryable": error.retryable,
                    "details": self._safe_failure_details(error.safe_details),
                },
            )
        if (
            not result.complete
            or result.search_plan is None
            or result.search_execution is None
            or result.search_statistics is None
        ):
            self.provider_operations.settle_failure(
                operation.id,
                category=ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                at=self._now(),
                usage=result.usage,
                provider_call_started=True,
                diagnostic_metadata={
                    "variant_id": variant.variant_id,
                    "failure_point": "missing_or_incomplete_search_evidence",
                },
            )
            self.provider_operations.commit_staged()
            return _VariantOutcome(
                variant=variant,
                operation_id=operation.id,
                papers=(),
                usage=result.usage,
                execution={"complete": False},
                statistics={"records_normalized": 0, "records_rejected": 0},
                rejection_diagnostics=tuple(
                    item.to_dict() for item in result.rejection_diagnostics
                ),
                failure={
                    "category": ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE.value,
                    "retryable": False,
                    "details": {
                        "failure_point": "missing_or_incomplete_search_evidence"
                    },
                },
            )
        self.provider_operations.settle_success(
            operation.id,
            usage=result.usage,
            at=self._now(),
        )
        self.provider_operations.commit_staged()
        return _VariantOutcome(
            variant=variant,
            operation_id=operation.id,
            papers=result.papers,
            usage=result.usage,
            execution=result.search_execution.to_dict(),
            statistics=result.search_statistics.to_dict(),
            rejection_diagnostics=tuple(
                item.to_dict() for item in result.rejection_diagnostics
            ),
            failure=None,
        )

    def _merge(
        self,
        outcomes: tuple[_VariantOutcome, ...],
    ) -> tuple[tuple[_MergedPaper, ...], dict[str, Any], tuple[SearchDiagnostic, ...]]:
        merged: list[_MergedPaper] = []
        exact_merges: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        diagnostics: list[SearchDiagnostic] = []
        for outcome in outcomes:
            for paper in outcome.papers:
                target: _MergedPaper | None = None
                method: str | None = None
                for existing in merged:
                    doi_match = bool(paper.doi and paper.doi == existing.paper.doi)
                    id_match = paper.provider_id == existing.paper.provider_id
                    if doi_match and paper.provider_id != existing.paper.provider_id:
                        conflicts.append(
                            {
                                "type": "DOI_WITH_CONFLICTING_OPENALEX_ID",
                                "doi": paper.doi,
                                "retained_paper_ids": [
                                    existing.paper.paper_id,
                                    paper.paper_id,
                                ],
                            }
                        )
                        continue
                    if (
                        id_match
                        and paper.doi
                        and existing.paper.doi
                        and paper.doi != existing.paper.doi
                    ):
                        conflicts.append(
                            {
                                "type": "OPENALEX_ID_WITH_CONFLICTING_DOI",
                                "openalex_id": paper.provider_id,
                                "retained_paper_ids": [
                                    existing.paper.paper_id,
                                    paper.paper_id,
                                ],
                            }
                        )
                        continue
                    if doi_match:
                        target = existing
                        method = "EXACT_NORMALIZED_DOI"
                        break
                    if id_match:
                        target = existing
                        method = "EXACT_OPENALEX_ID"
                        break
                if target is None:
                    merged.append(
                        _MergedPaper(
                            paper=paper,
                            first_seen_variant_id=outcome.variant.variant_id,
                            matched_variant_ids=[outcome.variant.variant_id],
                            query_checksums=[
                                canonical_hash(outcome.variant.exact_provider_query)
                            ],
                            operation_ids=[outcome.operation_id],
                        )
                    )
                    continue
                if outcome.variant.variant_id not in target.matched_variant_ids:
                    target.matched_variant_ids.append(outcome.variant.variant_id)
                    target.query_checksums.append(
                        canonical_hash(outcome.variant.exact_provider_query)
                    )
                    target.operation_ids.append(outcome.operation_id)
                exact_merges.append(
                    {
                        "method": method,
                        "retained_paper_id": target.paper.paper_id,
                        "merged_paper_id": paper.paper_id,
                        "variant_id": outcome.variant.variant_id,
                    }
                )
        title_year: dict[tuple[str, int | None], list[str]] = {}
        for item in merged:
            key = (self._normalize_title(item.paper.title), item.paper.publication_year)
            title_year.setdefault(key, []).append(item.paper.paper_id)
        advisory = [
            {
                "normalized_title_hash": canonical_hash(key[0]),
                "publication_year": key[1],
                "paper_ids": sorted(ids),
                "automatic_merge": False,
            }
            for key, ids in sorted(title_year.items())
            if len(ids) > 1
        ]
        if advisory:
            diagnostics.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.ADVISORY_TITLE_YEAR_CLUSTER,
                    cause=DiagnosticCause.METADATA_SHAPE,
                    message="Title/year similarities were retained as advisory clusters",
                    details={"cluster_count": len(advisory), "automatic_merge": False},
                )
            )
        if conflicts:
            diagnostics.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.IDENTITY_CONFLICT,
                    cause=DiagnosticCause.METADATA_SHAPE,
                    message="Conflicting exact identifiers were preserved as separate records",
                    details={"conflict_count": len(conflicts)},
                )
            )
        merged.sort(key=lambda item: (item.paper.paper_id, item.first_seen_variant_id))
        report = {
            "schema_version": "reagent-deterministic-merge-report/v1",
            "policy_order": [
                "EXACT_NORMALIZED_DOI",
                "EXACT_OPENALEX_ID",
                "NORMALIZED_TITLE_YEAR_ADVISORY_ONLY",
                "FUZZY_AUTOMATIC_MERGE_PROHIBITED",
            ],
            "input_record_count": sum(len(item.papers) for item in outcomes),
            "output_record_count": len(merged),
            "exact_merges": exact_merges,
            "identity_conflicts": conflicts,
            "advisory_title_year_clusters": advisory,
            "fuzzy_automatic_merge": False,
            "silent_candidate_loss": False,
        }
        return tuple(merged), report, tuple(diagnostics)

    def _candidates(
        self,
        topic: EvaluationTopic,
        merged: tuple[_MergedPaper, ...],
        plan: MultilingualSearchPlan,
    ) -> tuple[EvaluationCandidate, ...]:
        candidates: list[EvaluationCandidate] = []
        for rank, item in enumerate(merged[: plan.candidate_limit], start=1):
            paper = item.paper
            candidate_id = "candidate:" + canonical_hash(
                {
                    "topic_id": topic.topic_id,
                    "paper_id": paper.paper_id,
                    "plan_checksum": plan.plan_checksum,
                }
            ).removeprefix("sha256:")
            preview = None
            if self.include_abstract_preview and paper.abstract:
                preview = " ".join(paper.abstract.split())[:500]
            candidates.append(
                EvaluationCandidate(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    topic=topic.topic,
                    research_question=topic.research_question,
                    candidate_id=candidate_id,
                    rank=rank,
                    paper_id=paper.paper_id,
                    openalex_id=paper.provider_id,
                    title=paper.title,
                    authors=tuple(author.name for author in paper.authors),
                    year=paper.publication_year,
                    venue=paper.publication_venue,
                    doi=paper.doi,
                    abstract_available=paper.abstract is not None,
                    normalized_metadata_hash=paper.raw_metadata_hash,
                    search_execution_id=plan.plan_checksum,
                    provider=self.provider.identity.provider,
                    adapter_version=self.provider.identity.adapter_version,
                    abstract_preview=preview,
                    first_seen_variant_id=item.first_seen_variant_id,
                    all_matched_variant_ids=tuple(item.matched_variant_ids),
                    matched_query_checksums=tuple(item.query_checksums),
                    provider_operation_ids=tuple(item.operation_ids),
                    source_query_language=plan.original_language,
                    retrieval_timestamp=paper.retrieved_at,
                    original_paper_checksum=paper.canonical_hash(),
                )
            )
        return tuple(candidates)

    def _variant_diagnostics(
        self,
        outcome: _VariantOutcome,
        plan: MultilingualSearchPlan,
    ) -> tuple[SearchDiagnostic, ...]:
        if outcome.failure is not None:
            return ()
        statistics = outcome.statistics
        received = int(statistics.get("records_received", len(outcome.papers)))
        normalized = int(statistics.get("records_normalized", len(outcome.papers)))
        rejected = int(statistics.get("records_rejected", 0))
        low_threshold = int(plan.coverage_warning_policy.get("low_result_count", 5))
        result: list[SearchDiagnostic] = []
        if received == 0:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.ZERO_RESULTS,
                    cause=DiagnosticCause.UNKNOWN,
                    message="Provider returned zero records; cause is not inferred",
                    variant_id=outcome.variant.variant_id,
                )
            )
        elif received < low_threshold:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.LOW_RESULT_COUNT,
                    cause=DiagnosticCause.UNKNOWN,
                    message="Provider result count is below the configured coverage threshold",
                    variant_id=outcome.variant.variant_id,
                    details={"result_count": received, "threshold": low_threshold},
                )
            )
        if normalized == 0:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.NO_NORMALIZED_RESULTS,
                    cause=(
                        DiagnosticCause.LOCAL_VALIDATION
                        if rejected
                        else DiagnosticCause.UNKNOWN
                    ),
                    message="No provider records crossed the normalization boundary",
                    variant_id=outcome.variant.variant_id,
                    details={"records_received": received, "records_rejected": rejected},
                )
            )
        for raw in outcome.rejection_diagnostics:
            code = SearchDiagnosticCode(str(raw["category"]))
            result.append(
                SearchDiagnostic(
                    code=code,
                    cause=DiagnosticCause.LOCAL_VALIDATION,
                    message="A provider field was rejected by an unchanged safety boundary",
                    variant_id=outcome.variant.variant_id,
                    record_identity=(
                        None
                        if raw.get("record_identity") is None
                        else str(raw["record_identity"])
                    ),
                    details=dict(raw),
                )
            )
        limitation_codes = {
            "abstract_missing": SearchDiagnosticCode.MISSING_ABSTRACT,
            "doi_missing": SearchDiagnosticCode.MISSING_DOI,
            "authors_missing": SearchDiagnosticCode.MISSING_AUTHORS,
            "publication_year_missing_or_invalid": SearchDiagnosticCode.MISSING_YEAR,
            "venue_missing": SearchDiagnosticCode.MISSING_VENUE,
            "language_missing": SearchDiagnosticCode.LANGUAGE_FIELD_MISSING,
        }
        for limitation, code in limitation_codes.items():
            count = sum(
                limitation in paper.metadata_limitations for paper in outcome.papers
            )
            if count:
                result.append(
                    SearchDiagnostic(
                        code=code,
                        cause=DiagnosticCause.METADATA_SHAPE,
                        message="Normalized provider metadata contains missing fields",
                        variant_id=outcome.variant.variant_id,
                        details={"record_count": count},
                    )
                )
        declared_languages = {
            paper.language.casefold()
            for paper in outcome.papers
            if paper.language is not None
        }
        expected_language = outcome.variant.variant_language.casefold()
        if (
            declared_languages
            and expected_language not in {"und", "zh-en", "multilingual"}
            and expected_language not in declared_languages
        ):
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.LANGUAGE_MISMATCH,
                    cause=DiagnosticCause.UNKNOWN,
                    message=(
                        "Declared result languages do not include the variant language; "
                        "provider coverage and metadata causes remain ambiguous"
                    ),
                    variant_id=outcome.variant.variant_id,
                    details={
                        "variant_language": outcome.variant.variant_language,
                        "declared_languages": sorted(declared_languages),
                    },
                )
            )
        return tuple(result)

    def _merged_diagnostics(
        self,
        merged: tuple[_MergedPaper, ...],
        plan: MultilingualSearchPlan,
    ) -> tuple[SearchDiagnostic, ...]:
        if not merged:
            return ()
        languages = Counter(
            item.paper.language or "missing"
            for item in merged
        )
        result: list[SearchDiagnostic] = []
        known = {key.casefold() for key in languages if key != "missing"}
        if known and known <= {"en"} and plan.original_language.casefold() not in {"en", "eng"}:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.ONLY_ENGLISH_RESULTS,
                    cause=DiagnosticCause.UNKNOWN,
                    message="All records with declared language metadata are English",
                    details={"language_distribution": dict(sorted(languages.items()))},
                )
            )
        original_codes = {
            part.casefold()
            for part in plan.original_language.replace("_", "-").split("-")
        }
        if known and known <= original_codes:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.ONLY_ORIGINAL_LANGUAGE_RESULTS,
                    cause=DiagnosticCause.UNKNOWN,
                    message="All declared record languages match the original query language",
                    details={"language_distribution": dict(sorted(languages.items()))},
                )
            )
        multi = sum(1 for item in merged if len(item.matched_variant_ids) > 1)
        threshold = float(
            plan.coverage_warning_policy.get("duplicate_concentration_ratio", 0.75)
        )
        if merged and multi / len(merged) >= threshold:
            result.append(
                SearchDiagnostic(
                    code=SearchDiagnosticCode.DUPLICATE_CONCENTRATION,
                    cause=DiagnosticCause.UNKNOWN,
                    message="A high share of candidates matched multiple variants",
                    details={
                        "multi_variant_candidate_count": multi,
                        "candidate_count": len(merged),
                        "configured_ratio": threshold,
                    },
                )
            )
        return tuple(result)

    def _validate_plan(
        self,
        topic: EvaluationTopic,
        plan: MultilingualSearchPlan,
    ) -> None:
        if plan.original_query.topic != topic.topic:
            raise EvaluationGenerationError(
                "Multilingual plan original query does not match the evaluation topic"
            )
        if any(not variant.owner_approved for variant in plan.query_variants):
            raise EvaluationGenerationError(
                "Every executable QueryVariant must be explicitly owner-approved"
            )
        if not any(
            item.variant_type.value == "ORIGINAL" for item in plan.query_variants
        ):
            raise EvaluationGenerationError(
                "Multilingual plan must retain an ORIGINAL query variant"
            )
        reservation = self.execution_policy.reservation_for(
            self.provider.identity.provider
        ).request_count
        if reservation * len(plan.query_variants) > plan.total_request_limit:
            raise EvaluationGenerationError(
                "Provider reservations exceed the plan total request limit"
            )

    def _operation(
        self,
        *,
        evaluation_id: str,
        topic: EvaluationTopic,
        variant: QueryVariant,
        fingerprint: str,
    ) -> ProviderOperation:
        now = self._now()
        idempotency_key = (
            f"live:evaluation:{evaluation_id}:{topic.topic_id}:"
            f"{variant.variant_id}:{fingerprint}"
        )
        operation_id = "provider_op:" + canonical_hash(
            {"project": evaluation_id, "idempotency_key": idempotency_key}
        ).removeprefix("sha256:")
        return ProviderOperation(
            id=operation_id,
            project_id=f"evaluation:{evaluation_id}",
            workflow_run_id=f"evaluation:{evaluation_id}",
            logical_step_id=f"openalex_multilingual:{topic.topic_id}:{variant.variant_id}",
            step_run_id=None,
            provider_category=ProviderCategory.PAPER_SEARCH,
            operation_kind=ProviderOperationKind.SEARCH,
            provider_identity=self.provider.identity.provider,
            adapter_version=self.provider.identity.adapter_version,
            model_or_endpoint=self.provider.identity.model_or_endpoint,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            reservation=self.execution_policy.reservation_for(
                self.provider.identity.provider
            ),
            is_live_provider=(
                self.provider.identity.provider
                in self.execution_policy.live_provider_names
            ),
            created_at=now,
            updated_at=now,
        )

    def _resume(
        self,
        manifest: Mapping[str, Any],
        manifest_key: str,
    ) -> MultilingualCandidatePoolResult:
        artifacts = tuple(
            EvaluationArtifact(
                logical_name=str(item["logical_name"]),
                storage_key=str(item["storage_key"]),
                checksum=str(item["checksum"]),
                size=int(item["size"]),
                media_type=str(item["media_type"]),
            )
            for item in manifest.get("artifacts", ())
        )
        for artifact in artifacts:
            verification = self.artifact_storage.verify(
                artifact.storage_key,
                expected_checksum=artifact.checksum,
                expected_size=artifact.size,
            )
            if not verification.valid:
                raise EvaluationGenerationError(
                    f"Multilingual artifact checksum mismatch: {artifact.logical_name}"
                )
        topic_manifest = next(
            (item for item in artifacts if item.logical_name == "topic_manifest.json"),
            None,
        )
        if topic_manifest is None:
            raise EvaluationGenerationError("Multilingual topic manifest is unavailable")
        topic_value = self._read_json_if_present(topic_manifest.storage_key)
        if topic_value is None:
            raise EvaluationGenerationError("Multilingual topic manifest disappeared")
        for operation_id in topic_value.get("operation_ids", ()):
            operation = self.provider_operations.repository.get(str(operation_id))
            if operation is None or operation.settlement_state is not SettlementState.SETTLED:
                raise EvaluationGenerationError(
                    "Multilingual manifest has an unavailable or unsettled operation"
                )
        candidates = tuple(
            EvaluationCandidate.from_dict(item)
            for item in topic_value.get("candidates", ())
        )
        diagnostic_artifact = next(
            (item for item in artifacts if item.logical_name == "coverage_diagnostics.json"),
            None,
        )
        diagnostics: tuple[SearchDiagnostic, ...] = ()
        if diagnostic_artifact is not None:
            document = self._read_json_if_present(diagnostic_artifact.storage_key) or {}
            diagnostics = tuple(
                SearchDiagnostic(
                    code=SearchDiagnosticCode(str(item["code"])),
                    cause=DiagnosticCause(str(item["cause"])),
                    message=str(item["message"]),
                    blocking=bool(item.get("blocking", False)),
                    variant_id=(
                        None
                        if item.get("variant_id") is None
                        else str(item["variant_id"])
                    ),
                    record_identity=(
                        None
                        if item.get("record_identity") is None
                        else str(item["record_identity"])
                    ),
                    details=dict(item.get("details", {})),
                    schema_version=str(item["schema_version"]),
                )
                for item in document.get("diagnostics", ())
            )
        run_value = manifest["evaluation_run"]
        run = EvaluationRun(
            evaluation_id=str(run_value["evaluation_id"]),
            topic_set_version=str(run_value["topic_set_version"]),
            provider=str(run_value["provider"]),
            adapter_version=str(run_value["adapter_version"]),
            api_contract_snapshot=str(run_value["api_contract_snapshot"]),
            query_fingerprints=dict(run_value["query_fingerprints"]),
            candidate_pool_checksums=dict(run_value["candidate_pool_checksums"]),
            started_at=datetime.fromisoformat(str(run_value["started_at"])),
            completed_at=datetime.fromisoformat(str(run_value["completed_at"])),
            request_count=int(run_value["request_count"]),
            latency_ms=int(run_value["latency_ms"]),
            retry_count=int(run_value["retry_count"]),
            provider_usage=tuple(run_value["provider_usage"]),
            completion_state=EvaluationCompletionState(
                str(run_value["completion_state"])
            ),
            schema_version=str(run_value["schema_version"]),
        )
        from backend.research.contracts import sha256_bytes

        manifest_content = self.artifact_storage.read(manifest_key)
        manifest_artifact = EvaluationArtifact(
            logical_name="evaluation_manifest.json",
            storage_key=manifest_key,
            checksum=sha256_bytes(manifest_content),
            size=len(manifest_content),
            media_type="application/json",
        )
        return MultilingualCandidatePoolResult(
            evaluation_run=run,
            candidates=candidates,
            diagnostics=diagnostics,
            artifacts=(*artifacts, manifest_artifact),
            resumed=True,
        )

    def _write_json(
        self,
        storage_key: str,
        logical_name: str,
        document: Mapping[str, Any],
    ) -> EvaluationArtifact:
        content = canonical_json(document).encode("utf-8")
        stored = self.artifact_storage.write_immutable(
            storage_key,
            content,
            media_type="application/json",
        )
        return EvaluationArtifact(
            logical_name=logical_name,
            storage_key=stored.storage_key,
            checksum=stored.checksum,
            size=stored.size,
            media_type=stored.media_type,
        )

    def _read_json_if_present(self, storage_key: str) -> Mapping[str, Any] | None:
        try:
            content = self.artifact_storage.read(storage_key)
        except FileNotFoundError:
            return None
        value = json.loads(content)
        if not isinstance(value, Mapping):
            raise EvaluationGenerationError("Stored multilingual artifact is invalid")
        return value

    def _assert_no_unsettled(self, evaluation_id: str) -> None:
        if self.provider_operations.repository.list_unsettled(
            project_id=f"evaluation:{evaluation_id}"
        ):
            raise EvaluationGenerationError(
                "Multilingual publication blocked by unsettled ProviderOperations"
            )

    def _failure_usage(self, error: ProviderError) -> ProviderUsage | None:
        request_count = error.safe_details.get("request_count")
        if not isinstance(request_count, int):
            return None
        return ProviderUsage(
            provider=self.provider.identity.provider,
            model_or_endpoint=self.provider.identity.model_or_endpoint,
            operation_kind=ProviderOperationKind.SEARCH,
            request_count=request_count,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=int(error.safe_details.get("latency_ms", 0)),
            retry_count=int(error.safe_details.get("retry_count", 0)),
            failure_category=error.category,
        )

    @staticmethod
    def _safe_failure_details(value: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: item
            for key, item in dict(value).items()
            if key.casefold() not in {"api_key", "authorization", "url", "raw_response"}
        }

    @staticmethod
    def _normalize_title(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        if (
            not value
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
            or not all(character.isalnum() or character in "-_." for character in value)
        ):
            raise EvaluationGenerationError(f"{field_name} is not a safe path segment")
        return value

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise EvaluationGenerationError("Evaluation clock must be timezone-aware")
        return value
