"""Synthetic-only repeated judgment orchestration with durable replay."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import (
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderUsage,
    SettlementState,
    canonical_hash,
)
from backend.research.contracts._serialization import canonical_json
from backend.research.ports import ArtifactContentStorage
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService

from .audit_queue import HumanAuditQueueBuilder
from .contracts import EvaluationCandidate, MetricValue, RelevanceLabel
from .fake_judge import FAKE_MODEL, FAKE_PROVIDER, FakeAutomatedRelevanceJudge
from .judge_port import AutomatedJudgeError, JudgeCallContext, PairwisePreference
from .prompts import JudgePromptRegistry
from .silver_aggregation import JudgmentAggregator
from .silver_contracts import (
    AgreementState,
    AuditQueueState,
    AutomatedJudgment,
    AutomatedJudgmentRequest,
    ConsistencyState,
    EvidenceState,
    HumanAuditReason,
    HumanAuditRequest,
    HumanAuditQueue,
    HumanAuditStatus,
    HumanAuditType,
    JudgmentConsensus,
    JudgmentMode,
    MetadataWarningState,
    PairwiseConsistencyResult,
    PairwiseJudgmentRequest,
    SilverDisposition,
    SilverMetricReport,
    SilverMetricSet,
    SupportingSpan,
)
from .silver_metrics import SilverMetrics
from .synthetic_fixtures import SYNTHETIC_PROVIDER, SyntheticFixtureSet

SYNTHETIC_RUN_SCHEMA = "reagent-synthetic-silver-run/v1"


@dataclass(frozen=True, slots=True)
class SyntheticSilverRun:
    evaluation_id: str
    candidates: tuple[EvaluationCandidate, ...]
    judgments: tuple[AutomatedJudgment, ...]
    pairwise_results: tuple[PairwiseConsistencyResult, ...]
    consensuses: tuple[JudgmentConsensus, ...]
    audit_queue: HumanAuditQueue
    metrics: SilverMetricReport
    provider_operation_count: int
    resumed: bool


class SyntheticSilverOrchestrator:
    def __init__(
        self,
        *,
        judge: FakeAutomatedRelevanceJudge,
        provider_operations: ProviderOperationService,
        execution_policy: ProviderExecutionPolicy,
        artifact_storage: ArtifactContentStorage,
        prompt_registry: JudgePromptRegistry | None = None,
    ) -> None:
        if judge.identity.provider != FAKE_PROVIDER:
            raise ValueError("Phase 9B-2C-2 accepts only the deterministic Fake Judge")
        if execution_policy.live_provider_names:
            raise ValueError("Synthetic judge policy cannot enable live providers")
        self.judge = judge
        self.operations = provider_operations
        self.policy = execution_policy
        self.storage = artifact_storage
        self.prompts = prompt_registry or JudgePromptRegistry()

    def run(
        self,
        *,
        evaluation_id: str,
        fixtures: SyntheticFixtureSet,
    ) -> SyntheticSilverRun:
        self._assert_synthetic(fixtures)
        final_key = f"{evaluation_id}/silver/synthetic_run.json"
        try:
            value = json.loads(self.storage.read(final_key))
        except FileNotFoundError:
            value = None
        if value is not None:
            result = self._result_from_dict(value, fixtures.candidates)
            self._assert_all_settled(evaluation_id)
            return replace(result, resumed=True)

        judgments: list[AutomatedJudgment] = []
        by_candidate: dict[str, list[AutomatedJudgment]] = {
            item.candidate_id: [] for item in fixtures.candidates
        }
        for candidate in fixtures.candidates:
            for run_index, prompt_version in enumerate(
                self.prompts.pointwise_versions, start=1
            ):
                request = self._pointwise_request(
                    evaluation_id=evaluation_id,
                    candidate=candidate,
                    prompt_version=prompt_version,
                    language=fixtures.candidate_languages[candidate.candidate_id],
                )
                judgment = self._execute_pointwise(request, run_index=run_index)
                if judgment is not None:
                    judgments.append(judgment)
                    by_candidate[candidate.candidate_id].append(judgment)

        pairwise_results: list[PairwiseConsistencyResult] = []
        candidate_by_id = {item.candidate_id: item for item in fixtures.candidates}
        for left_id, right_id in fixtures.pairwise_pairs:
            result = self._execute_mirrored_pairwise(
                evaluation_id=evaluation_id,
                left=candidate_by_id[left_id],
                right=candidate_by_id[right_id],
            )
            if result is not None:
                pairwise_results.append(result)
        self._assert_all_settled(evaluation_id)

        aggregator = JudgmentAggregator()
        consensuses = tuple(
            aggregator.aggregate(
                candidate_id=candidate.candidate_id,
                judgments=tuple(by_candidate[candidate.candidate_id]),
                content_language=fixtures.candidate_languages[candidate.candidate_id],
                metadata_warnings=fixtures.metadata_warnings[candidate.candidate_id],
                pairwise_results=tuple(pairwise_results),
            )
            for candidate in fixtures.candidates
        )
        audit_queue = HumanAuditQueueBuilder().build(
            evaluation_id=evaluation_id,
            candidates=fixtures.candidates,
            consensuses=consensuses,
        )
        metrics = SilverMetrics().calculate(
            candidates=fixtures.candidates,
            consensuses=consensuses,
            audit_queue=audit_queue,
        )
        operation_count = len(
            self.operations.list_for_run(
                project_id=self._project_id(evaluation_id),
                workflow_run_id=evaluation_id,
            )
        )
        result = SyntheticSilverRun(
            evaluation_id=evaluation_id,
            candidates=fixtures.candidates,
            judgments=tuple(judgments),
            pairwise_results=tuple(pairwise_results),
            consensuses=consensuses,
            audit_queue=audit_queue,
            metrics=metrics,
            provider_operation_count=operation_count,
            resumed=False,
        )
        self._persist_result(final_key, result, fixtures)
        return result

    def _pointwise_request(
        self,
        *,
        evaluation_id: str,
        candidate: EvaluationCandidate,
        prompt_version: str,
        language: str,
    ) -> AutomatedJudgmentRequest:
        values = {
            "evaluation_id": evaluation_id,
            "topic_id": candidate.topic_id,
            "candidate_id": candidate.candidate_id,
            "topic_description": candidate.topic,
            "research_question": candidate.research_question,
            "inclusion_rubric": (
                "Central contribution directly addresses the topic.",
                "Topic is a substantial and necessary component.",
            ),
            "exclusion_rubric": (
                "Topic is secondary, incidental, absent, or unsupported by available evidence.",
            ),
            "title": candidate.title,
            "bounded_abstract_preview": candidate.abstract_preview,
            "publication_year": candidate.year,
            "venue": candidate.venue,
            "content_scope": "title_and_bounded_abstract_preview_only",
            "candidate_metadata_checksum": candidate.identity_hash,
            "prompt_version": prompt_version,
            "rubric_version": self.prompts.rubric_version,
            "content_language": language,
        }
        self.prompts.validate_input_fields(values)
        return AutomatedJudgmentRequest(**values)

    def _execute_pointwise(
        self,
        request: AutomatedJudgmentRequest,
        *,
        run_index: int,
    ) -> AutomatedJudgment | None:
        key = (
            f"{request.evaluation_id}/silver/judgments/{request.candidate_id}/"
            f"run-{run_index}.json"
        )
        existing = self._read_optional(key)
        if existing is not None:
            return (
                _judgment_from_dict(existing["judgment"])
                if existing["status"] == "SUCCEEDED"
                else None
            )
        request_key = (
            f"{request.evaluation_id}/silver/requests/{request.candidate_id}/"
            f"run-{run_index}.json"
        )
        self._write(request_key, request.to_dict())
        operation = self._reserve_operation(
            evaluation_id=request.evaluation_id,
            logical_step_id=f"pointwise-{run_index}",
            call_id=request.candidate_id,
            request_checksum=request.request_checksum,
        )
        now = datetime.now(UTC)
        running = self.operations.mark_running(operation.id, at=now)
        self.operations.commit_staged()
        try:
            judgment = self.judge.judge(
                request,
                context=JudgeCallContext(
                    run_index=run_index,
                    timeout_seconds=self.policy.operation_timeout_seconds,
                ),
            )
        except AutomatedJudgeError as error:
            self.operations.settle_failure(
                running.id,
                category=error.category,
                at=datetime.now(UTC),
                usage=self._failure_usage(error.category),
                provider_call_started=True,
                diagnostic_metadata={
                    "safe_error_type": type(error).__name__,
                    "synthetic": True,
                },
            )
            self.operations.commit_staged()
            self._write(
                key,
                {
                    "schema_version": "reagent-synthetic-judge-call/v1",
                    "status": "FAILED",
                    "failure_category": error.category.value,
                    "operation_id": operation.id,
                    "judgment": None,
                },
            )
            return None
        if judgment.input_checksum != request.request_checksum:
            raise ValueError("Fake Judge returned a judgment for a different input")
        self.operations.settle_success(
            running.id, usage=judgment.usage, at=datetime.now(UTC)
        )
        self.operations.commit_staged()
        self._write(
            key,
            {
                "schema_version": "reagent-synthetic-judge-call/v1",
                "status": "SUCCEEDED",
                "operation_id": operation.id,
                "judgment": judgment.to_dict(),
            },
        )
        return judgment

    def _execute_mirrored_pairwise(
        self,
        *,
        evaluation_id: str,
        left: EvaluationCandidate,
        right: EvaluationCandidate,
    ) -> PairwiseConsistencyResult | None:
        prompt = self.prompts.get(self.prompts.pairwise_version)
        forward = PairwiseJudgmentRequest(
            evaluation_id=evaluation_id,
            topic_id=left.topic_id,
            left_candidate_id=left.candidate_id,
            right_candidate_id=right.candidate_id,
            left_title=left.title,
            right_title=right.title,
            left_preview=left.abstract_preview,
            right_preview=right.abstract_preview,
            prompt_version=prompt.version,
            prompt_hash=prompt.prompt_hash,
            rubric_version=self.prompts.rubric_version,
        )
        mirrored = PairwiseJudgmentRequest(
            evaluation_id=evaluation_id,
            topic_id=left.topic_id,
            left_candidate_id=right.candidate_id,
            right_candidate_id=left.candidate_id,
            left_title=right.title,
            right_title=left.title,
            left_preview=right.abstract_preview,
            right_preview=left.abstract_preview,
            prompt_version=prompt.version,
            prompt_hash=prompt.prompt_hash,
            rubric_version=self.prompts.rubric_version,
        )
        first = self._execute_pairwise_call(forward, call_suffix="forward", run_index=1)
        second = self._execute_pairwise_call(mirrored, call_suffix="mirrored", run_index=2)
        if first is None or second is None:
            return None
        usage = ProviderUsage(
            provider=FAKE_PROVIDER,
            model_or_endpoint=FAKE_MODEL,
            operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
            request_count=2,
            input_tokens=128,
            output_tokens=48,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=2,
        )
        return PairwiseConsistencyResult(
            left_candidate_id=left.candidate_id,
            right_candidate_id=right.candidate_id,
            preferred_candidate_id=first.preferred_candidate_id,
            mirrored_order_result=second.preferred_candidate_id,
            order_consistent=first.preferred_candidate_id == second.preferred_candidate_id,
            reason=first.reason,
            prompt_version=prompt.version,
            prompt_hash=prompt.prompt_hash,
            usage=usage,
        )

    def _execute_pairwise_call(
        self,
        request: PairwiseJudgmentRequest,
        *,
        call_suffix: str,
        run_index: int,
    ) -> PairwisePreference | None:
        pair_id = f"{request.left_candidate_id}--{request.right_candidate_id}"
        key = (
            f"{request.evaluation_id}/silver/pairwise/{pair_id}-{call_suffix}.json"
        )
        existing = self._read_optional(key)
        if existing is not None:
            if existing["status"] != "SUCCEEDED":
                return None
            return PairwisePreference(
                preferred_candidate_id=str(existing["preferred_candidate_id"]),
                reason=str(existing["reason"]),
                usage=_usage_from_dict(existing["usage"]),
            )
        self._write(
            f"{request.evaluation_id}/silver/pairwise-requests/{pair_id}-{call_suffix}.json",
            request.to_dict(),
        )
        operation = self._reserve_operation(
            evaluation_id=request.evaluation_id,
            logical_step_id="pairwise-mirrored",
            call_id=f"{pair_id}-{call_suffix}",
            request_checksum=request.request_checksum,
        )
        running = self.operations.mark_running(operation.id, at=datetime.now(UTC))
        self.operations.commit_staged()
        try:
            preference = self.judge.compare(
                request,
                context=JudgeCallContext(
                    run_index=run_index,
                    timeout_seconds=self.policy.operation_timeout_seconds,
                ),
            )
        except AutomatedJudgeError as error:
            self.operations.settle_failure(
                running.id,
                category=error.category,
                at=datetime.now(UTC),
                usage=self._failure_usage(error.category),
                provider_call_started=True,
                diagnostic_metadata={"safe_error_type": type(error).__name__, "synthetic": True},
            )
            self.operations.commit_staged()
            self._write(
                key,
                {
                    "status": "FAILED",
                    "failure_category": error.category.value,
                    "operation_id": operation.id,
                },
            )
            return None
        self.operations.settle_success(
            running.id, usage=preference.usage, at=datetime.now(UTC)
        )
        self.operations.commit_staged()
        self._write(
            key,
            {
                "status": "SUCCEEDED",
                "operation_id": operation.id,
                "preferred_candidate_id": preference.preferred_candidate_id,
                "reason": preference.reason,
                "usage": preference.usage.to_dict(),
            },
        )
        return preference

    def _reserve_operation(
        self,
        *,
        evaluation_id: str,
        logical_step_id: str,
        call_id: str,
        request_checksum: str,
    ) -> ProviderOperation:
        identity = self.judge.identity
        operation_id = canonical_hash(
            {
                "evaluation_id": evaluation_id,
                "logical_step_id": logical_step_id,
                "call_id": call_id,
                "request_checksum": request_checksum,
            }
        )
        now = datetime.now(UTC)
        operation = ProviderOperation(
            id=operation_id,
            project_id=self._project_id(evaluation_id),
            workflow_run_id=evaluation_id,
            logical_step_id=logical_step_id,
            step_run_id=None,
            provider_category=ProviderCategory.LLM,
            operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
            provider_identity=identity.provider,
            adapter_version=identity.adapter_version,
            model_or_endpoint=identity.model,
            idempotency_key=operation_id,
            request_fingerprint=request_checksum,
            reservation=self.policy.reservation_for(identity.provider),
            is_live_provider=False,
            created_at=now,
            updated_at=now,
        )
        reserved, replayed = self.operations.reserve(
            operation, budget=self.policy.budget
        )
        if replayed:
            if reserved.status.is_terminal:
                raise RuntimeError("Terminal operation exists without its immutable call receipt")
            raise RuntimeError("Unsettled replay is fail-closed and cannot call the Judge")
        self.operations.commit_staged()
        return reserved

    def _assert_all_settled(self, evaluation_id: str) -> None:
        unsettled = tuple(
            item
            for item in self.operations.list_for_run(
                project_id=self._project_id(evaluation_id),
                workflow_run_id=evaluation_id,
            )
            if item.settlement_state is SettlementState.UNSETTLED
        )
        if unsettled:
            raise RuntimeError("Unsettled Judge operations cannot enter aggregation")

    def _persist_result(
        self,
        key: str,
        result: SyntheticSilverRun,
        fixtures: SyntheticFixtureSet,
    ) -> None:
        value = {
            "schema_version": SYNTHETIC_RUN_SCHEMA,
            "evaluation_id": result.evaluation_id,
            "fixture_version": fixtures.version,
            "fixture_checksum": fixtures.checksum,
            "synthetic_only": True,
            "real_candidate_labels_generated": False,
            "expert_gold_labels_present": False,
            "candidates": [item.to_dict() for item in result.candidates],
            "judgments": [item.to_dict() for item in result.judgments],
            "pairwise_results": [item.to_dict() for item in result.pairwise_results],
            "consensuses": [item.to_dict() for item in result.consensuses],
            "audit_queue": result.audit_queue.to_dict(),
            "metrics": result.metrics.to_dict(),
            "provider_operation_count": result.provider_operation_count,
        }
        self._write(key, value)

    def _result_from_dict(
        self,
        value: Mapping[str, Any],
        expected_candidates: tuple[EvaluationCandidate, ...],
    ) -> SyntheticSilverRun:
        if value.get("schema_version") != SYNTHETIC_RUN_SCHEMA:
            raise ValueError("Unsupported synthetic run schema")
        candidates = tuple(
            EvaluationCandidate.from_dict(item) for item in value["candidates"]
        )
        if tuple(item.identity_hash for item in candidates) != tuple(
            item.identity_hash for item in expected_candidates
        ):
            raise ValueError("Replay fixture candidate identity mismatch")
        return SyntheticSilverRun(
            evaluation_id=str(value["evaluation_id"]),
            candidates=candidates,
            judgments=tuple(_judgment_from_dict(item) for item in value["judgments"]),
            pairwise_results=tuple(
                _pairwise_from_dict(item) for item in value["pairwise_results"]
            ),
            consensuses=tuple(
                _consensus_from_dict(item) for item in value["consensuses"]
            ),
            audit_queue=_audit_queue_from_dict(value["audit_queue"]),
            metrics=_metrics_from_dict(value["metrics"]),
            provider_operation_count=int(value["provider_operation_count"]),
            resumed=True,
        )

    def _write(self, key: str, value: Mapping[str, Any]) -> None:
        self.storage.write_immutable(
            key,
            canonical_json(value).encode("utf-8"),
            media_type="application/json",
        )

    def _read_optional(self, key: str) -> Mapping[str, Any] | None:
        try:
            return json.loads(self.storage.read(key))
        except FileNotFoundError:
            return None

    @staticmethod
    def _project_id(evaluation_id: str) -> str:
        return f"synthetic-silver:{evaluation_id}"

    @staticmethod
    def _failure_usage(category: ProviderFailureCategory) -> ProviderUsage:
        return ProviderUsage(
            provider=FAKE_PROVIDER,
            model_or_endpoint=FAKE_MODEL,
            operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
            request_count=1,
            input_tokens=64,
            output_tokens=0,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=1,
            failure_category=category,
        )

    @staticmethod
    def _assert_synthetic(fixtures: SyntheticFixtureSet) -> None:
        if not fixtures.candidates:
            raise ValueError("Synthetic fixture set cannot be empty")
        if any(item.provider != SYNTHETIC_PROVIDER for item in fixtures.candidates):
            raise ValueError("Real or unmarked candidates cannot enter synthetic judging")


def _usage_from_dict(value: Mapping[str, Any]) -> ProviderUsage:
    return ProviderUsage(
        provider=str(value["provider"]),
        model_or_endpoint=str(value["model_or_endpoint"]),
        operation_kind=ProviderOperationKind(str(value["operation_kind"])),
        request_count=int(value["request_count"]),
        input_tokens=value.get("input_tokens"),
        output_tokens=value.get("output_tokens"),
        estimated_cost_minor_units=value.get("estimated_cost_minor_units"),
        cost_currency=value.get("cost_currency"),
        latency_ms=int(value["latency_ms"]),
        retry_count=int(value.get("retry_count", 0)),
        failure_category=(
            ProviderFailureCategory(str(value["failure_category"]))
            if value.get("failure_category")
            else None
        ),
        provider_request_ids=tuple(value.get("provider_request_ids", ())),
        schema_version=str(value.get("schema_version", "provider-usage/v1")),
    )


def _judgment_from_dict(value: Mapping[str, Any]) -> AutomatedJudgment:
    return AutomatedJudgment(
        **{
            **dict(value),
            "judgment_mode": JudgmentMode(str(value["judgment_mode"])),
            "label": RelevanceLabel(str(value["label"])),
            "supporting_spans": tuple(
                SupportingSpan(**item) for item in value["supporting_spans"]
            ),
            "uncertainties": tuple(value["uncertainties"]),
            "usage": _usage_from_dict(value["usage"]),
            "created_at": datetime.fromisoformat(str(value["created_at"])),
        }
    )


def _pairwise_from_dict(value: Mapping[str, Any]) -> PairwiseConsistencyResult:
    return PairwiseConsistencyResult(
        **{**dict(value), "usage": _usage_from_dict(value["usage"])}
    )


def _consensus_from_dict(value: Mapping[str, Any]) -> JudgmentConsensus:
    return JudgmentConsensus(
        **{
            **dict(value),
            "source_judgment_ids": tuple(value["source_judgment_ids"]),
            "confidence_values": tuple(value["confidence_values"]),
            "agreement_state": AgreementState(str(value["agreement_state"])),
            "supporting_evidence_state": EvidenceState(
                str(value["supporting_evidence_state"])
            ),
            "pairwise_consistency_state": ConsistencyState(
                str(value["pairwise_consistency_state"])
            ),
            "metadata_warning_state": MetadataWarningState(
                str(value["metadata_warning_state"])
            ),
            "disposition": SilverDisposition(str(value["disposition"])),
            "proposed_silver_label": (
                RelevanceLabel(str(value["proposed_silver_label"]))
                if value.get("proposed_silver_label")
                else None
            ),
            "audit_reasons": tuple(
                HumanAuditReason(str(item)) for item in value["audit_reasons"]
            ),
        }
    )


def _audit_request_from_dict(value: Mapping[str, Any]) -> HumanAuditRequest:
    return HumanAuditRequest(
        **{
            **dict(value),
            "proposed_silver_label": (
                RelevanceLabel(str(value["proposed_silver_label"]))
                if value.get("proposed_silver_label")
                else None
            ),
            "audit_reasons": tuple(
                HumanAuditReason(str(item)) for item in value["audit_reasons"]
            ),
            "judgment_ids": tuple(value["judgment_ids"]),
            "audit_type": HumanAuditType(str(value["audit_type"])),
            "status": HumanAuditStatus(str(value["status"])),
            "created_at": datetime.fromisoformat(str(value["created_at"])),
        }
    )


def _audit_queue_from_dict(value: Mapping[str, Any]) -> HumanAuditQueue:
    return HumanAuditQueue(
        evaluation_id=str(value["evaluation_id"]),
        requests=tuple(_audit_request_from_dict(item) for item in value["requests"]),
        required_count=int(value["required_count"]),
        random_sample_count=int(value["random_sample_count"]),
        maximum_burden=int(value["maximum_burden"]),
        state=AuditQueueState(str(value["state"])),
        policy_version=str(value["policy_version"]),
        schema_version=str(value["schema_version"]),
    )


def _metric(value: Mapping[str, Any]) -> MetricValue:
    return MetricValue(
        available=bool(value["available"]),
        value=value.get("value"),
        sample_size=int(value["sample_size"]),
        reason=value.get("reason"),
    )


def _metric_set(value: Mapping[str, Any]) -> SilverMetricSet:
    return SilverMetricSet(
        precision_at_5=_metric(value["precision_at_5"]),
        precision_at_10=_metric(value["precision_at_10"]),
        ndcg_at_10=_metric(value["ndcg_at_10"]),
    )


def _metrics_from_dict(value: Mapping[str, Any]) -> SilverMetricReport:
    return SilverMetricReport(
        raw_silver=_metric_set(value["raw_silver"]),
        audited_silver=_metric_set(value["audited_silver"]),
        human_audit_agreement=_metric(value["human_audit_agreement"]),
        human_override_rate=_metric(value["human_override_rate"]),
        needs_human_review_rate=_metric(value["needs_human_review_rate"]),
        cannot_judge_rate=_metric(value["cannot_judge_rate"]),
        label_source=str(value["label_source"]),
        expert_gold_labels_present=bool(value["expert_gold_labels_present"]),
        schema_version=str(value["schema_version"]),
    )
