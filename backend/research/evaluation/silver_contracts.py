"""Immutable contracts for synthetic automated-silver relevance evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import ProviderUsage, canonical_hash
from backend.research.contracts._serialization import (
    SerializableContract,
    freeze_json,
    require_aware,
    require_non_empty,
)

from .contracts import MetricValue, RelevanceLabel

AUTOMATED_REQUEST_SCHEMA = "reagent-automated-judgment-request/v1"
AUTOMATED_JUDGMENT_SCHEMA = "reagent-automated-judgment/v1"
PAIRWISE_SCHEMA = "reagent-pairwise-consistency/v1"
CONSENSUS_SCHEMA = "reagent-judgment-consensus/v1"
AUDIT_REQUEST_SCHEMA = "reagent-human-audit-request/v1"
AUDIT_RESULT_SCHEMA = "reagent-human-audit-result/v1"
AUDIT_QUEUE_SCHEMA = "reagent-human-audit-queue/v1"
SILVER_METRICS_SCHEMA = "reagent-silver-metrics/v1"


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be a sha256 checksum")


def _strings(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    result = tuple(values)
    for value in result:
        require_non_empty(value, name)
    return result


def _enum(value: Any, enum_type: type[Enum]) -> Enum:
    return value if isinstance(value, enum_type) else enum_type(value)


def _without(value: SerializableContract, field_name: str) -> dict[str, Any]:
    result = value.to_dict()
    result.pop(field_name, None)
    return result


class JudgmentMode(str, Enum):
    POINTWISE = "POINTWISE"
    PAIRWISE = "PAIRWISE"


class SilverDisposition(str, Enum):
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    AUTO_REJECTED = "AUTO_REJECTED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class AgreementState(str, Enum):
    AGREEMENT = "AGREEMENT"
    DISAGREEMENT = "DISAGREEMENT"
    INCOMPLETE = "INCOMPLETE"


class EvidenceState(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class ConsistencyState(str, Enum):
    CONSISTENT = "CONSISTENT"
    CONFLICT = "CONFLICT"
    NOT_CHECKED = "NOT_CHECKED"


class MetadataWarningState(str, Enum):
    CLEAR = "CLEAR"
    WARNING = "WARNING"


class HumanAuditReason(str, Enum):
    LABEL_DISAGREEMENT = "LABEL_DISAGREEMENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARTIAL_LABEL = "PARTIAL_LABEL"
    CANNOT_JUDGE = "CANNOT_JUDGE"
    MISSING_SUPPORTING_EVIDENCE = "MISSING_SUPPORTING_EVIDENCE"
    PAIRWISE_CONFLICT = "PAIRWISE_CONFLICT"
    NON_ENGLISH = "NON_ENGLISH"
    METADATA_WARNING = "METADATA_WARNING"
    RANDOM_CONSENSUS_AUDIT = "RANDOM_CONSENSUS_AUDIT"


class HumanAuditType(str, Enum):
    REQUIRED = "REQUIRED"
    RANDOM_CONSENSUS = "RANDOM_CONSENSUS"


class HumanAuditStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class AuditQueueState(str, Enum):
    READY = "READY"
    AUDIT_CAP_EXCEEDED = "AUDIT_CAP_EXCEEDED"


@dataclass(frozen=True, slots=True)
class SupportingSpan(SerializableContract):
    text: str
    start: int
    end: int

    def __post_init__(self) -> None:
        require_non_empty(self.text, "SupportingSpan.text")
        if len(self.text) > 240:
            raise ValueError("SupportingSpan.text exceeds 240 characters")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("SupportingSpan offsets are invalid")


@dataclass(frozen=True, slots=True)
class AutomatedJudgmentRequest(SerializableContract):
    evaluation_id: str
    topic_id: str
    candidate_id: str
    topic_description: str
    research_question: str | None
    inclusion_rubric: tuple[str, ...]
    exclusion_rubric: tuple[str, ...]
    title: str
    bounded_abstract_preview: str | None
    publication_year: int | None
    venue: str | None
    content_scope: str
    candidate_metadata_checksum: str
    prompt_version: str
    rubric_version: str
    content_language: str = "en"
    schema_version: str = AUTOMATED_REQUEST_SCHEMA
    request_checksum: str = ""

    def __post_init__(self) -> None:
        for value, name in (
            (self.evaluation_id, "evaluation_id"),
            (self.topic_id, "topic_id"),
            (self.candidate_id, "candidate_id"),
            (self.topic_description, "topic_description"),
            (self.title, "title"),
            (self.content_scope, "content_scope"),
            (self.prompt_version, "prompt_version"),
            (self.rubric_version, "rubric_version"),
            (self.content_language, "content_language"),
        ):
            require_non_empty(value, f"AutomatedJudgmentRequest.{name}")
        if self.research_question is not None:
            require_non_empty(self.research_question, "research_question")
        if self.bounded_abstract_preview is not None:
            preview = " ".join(self.bounded_abstract_preview.split())
            if len(preview) > 500:
                raise ValueError("bounded_abstract_preview exceeds 500 characters")
            object.__setattr__(self, "bounded_abstract_preview", preview or None)
        object.__setattr__(
            self, "inclusion_rubric", _strings(self.inclusion_rubric, "inclusion_rubric")
        )
        object.__setattr__(
            self, "exclusion_rubric", _strings(self.exclusion_rubric, "exclusion_rubric")
        )
        _sha(self.candidate_metadata_checksum, "candidate_metadata_checksum")
        expected = canonical_hash(_without(self, "request_checksum"))
        if self.request_checksum and self.request_checksum != expected:
            raise ValueError("AutomatedJudgmentRequest checksum mismatch")
        object.__setattr__(self, "request_checksum", expected)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AutomatedJudgmentRequest:
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Prohibited or unknown judgment request fields: {sorted(unknown)}")
        return cls(
            **{
                **dict(value),
                "inclusion_rubric": tuple(value["inclusion_rubric"]),
                "exclusion_rubric": tuple(value["exclusion_rubric"]),
            }
        )


@dataclass(frozen=True, slots=True)
class AutomatedJudgment(SerializableContract):
    judgment_id: str
    evaluation_id: str
    topic_id: str
    candidate_id: str
    run_index: int
    judgment_mode: JudgmentMode
    judge_provider: str
    judge_model: str
    model_version: str
    adapter_version: str
    prompt_version: str
    prompt_hash: str
    rubric_version: str
    label: RelevanceLabel
    confidence: float
    supporting_spans: tuple[SupportingSpan, ...]
    concise_reason: str
    uncertainties: tuple[str, ...]
    insufficient_information: bool
    input_checksum: str
    usage: ProviderUsage
    latency_ms: int
    created_at: datetime
    schema_version: str = AUTOMATED_JUDGMENT_SCHEMA
    output_checksum: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "judgment_mode", _enum(self.judgment_mode, JudgmentMode))
        object.__setattr__(self, "label", _enum(self.label, RelevanceLabel))
        for value, name in (
            (self.judgment_id, "judgment_id"),
            (self.evaluation_id, "evaluation_id"),
            (self.topic_id, "topic_id"),
            (self.candidate_id, "candidate_id"),
            (self.judge_provider, "judge_provider"),
            (self.judge_model, "judge_model"),
            (self.model_version, "model_version"),
            (self.adapter_version, "adapter_version"),
            (self.prompt_version, "prompt_version"),
            (self.rubric_version, "rubric_version"),
            (self.concise_reason, "concise_reason"),
        ):
            require_non_empty(value, f"AutomatedJudgment.{name}")
        if self.run_index <= 0:
            raise ValueError("run_index must be positive")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        spans = tuple(
            item if isinstance(item, SupportingSpan) else SupportingSpan(**item)
            for item in self.supporting_spans
        )
        object.__setattr__(self, "supporting_spans", spans)
        object.__setattr__(
            self, "uncertainties", _strings(self.uncertainties, "uncertainties")
        )
        if self.label is RelevanceLabel.CANNOT_JUDGE and not self.insufficient_information:
            raise ValueError("CANNOT_JUDGE requires insufficient_information")
        _sha(self.prompt_hash, "prompt_hash")
        _sha(self.input_checksum, "input_checksum")
        require_aware(self.created_at, "created_at")
        expected = canonical_hash(_without(self, "output_checksum"))
        if self.output_checksum and self.output_checksum != expected:
            raise ValueError("AutomatedJudgment checksum mismatch")
        object.__setattr__(self, "output_checksum", expected)


@dataclass(frozen=True, slots=True)
class PairwiseJudgmentRequest(SerializableContract):
    evaluation_id: str
    topic_id: str
    left_candidate_id: str
    right_candidate_id: str
    left_title: str
    right_title: str
    left_preview: str | None
    right_preview: str | None
    prompt_version: str
    prompt_hash: str
    rubric_version: str
    request_checksum: str = ""

    def __post_init__(self) -> None:
        if self.left_candidate_id == self.right_candidate_id:
            raise ValueError("Pairwise candidates must differ")
        for value in (
            self.evaluation_id, self.topic_id, self.left_candidate_id,
            self.right_candidate_id, self.left_title, self.right_title,
            self.prompt_version, self.rubric_version,
        ):
            require_non_empty(value, "PairwiseJudgmentRequest field")
        _sha(self.prompt_hash, "prompt_hash")
        expected = canonical_hash(_without(self, "request_checksum"))
        if self.request_checksum and self.request_checksum != expected:
            raise ValueError("PairwiseJudgmentRequest checksum mismatch")
        object.__setattr__(self, "request_checksum", expected)


@dataclass(frozen=True, slots=True)
class PairwiseConsistencyResult(SerializableContract):
    left_candidate_id: str
    right_candidate_id: str
    preferred_candidate_id: str
    mirrored_order_result: str
    order_consistent: bool
    reason: str
    prompt_version: str
    prompt_hash: str
    usage: ProviderUsage
    schema_version: str = PAIRWISE_SCHEMA
    checksum: str = ""

    def __post_init__(self) -> None:
        valid = {self.left_candidate_id, self.right_candidate_id, "TIE"}
        if self.preferred_candidate_id not in valid or self.mirrored_order_result not in valid:
            raise ValueError("Pairwise preference must be a candidate ID or TIE")
        require_non_empty(self.reason, "PairwiseConsistencyResult.reason")
        _sha(self.prompt_hash, "prompt_hash")
        expected = canonical_hash(_without(self, "checksum"))
        if self.checksum and self.checksum != expected:
            raise ValueError("PairwiseConsistencyResult checksum mismatch")
        object.__setattr__(self, "checksum", expected)


@dataclass(frozen=True, slots=True)
class JudgmentConsensus(SerializableContract):
    candidate_id: str
    source_judgment_ids: tuple[str, ...]
    label_distribution: Mapping[str, int]
    confidence_values: tuple[float, ...]
    agreement_state: AgreementState
    supporting_evidence_state: EvidenceState
    pairwise_consistency_state: ConsistencyState
    metadata_warning_state: MetadataWarningState
    disposition: SilverDisposition
    proposed_silver_label: RelevanceLabel | None
    disposition_reason: str
    aggregation_policy_version: str
    audit_reasons: tuple[HumanAuditReason, ...] = ()
    schema_version: str = CONSENSUS_SCHEMA
    checksum: str = ""

    def __post_init__(self) -> None:
        for name, enum_type in (
            ("agreement_state", AgreementState),
            ("supporting_evidence_state", EvidenceState),
            ("pairwise_consistency_state", ConsistencyState),
            ("metadata_warning_state", MetadataWarningState),
            ("disposition", SilverDisposition),
        ):
            object.__setattr__(self, name, _enum(getattr(self, name), enum_type))
        if self.proposed_silver_label is not None:
            object.__setattr__(
                self, "proposed_silver_label", _enum(self.proposed_silver_label, RelevanceLabel)
            )
        object.__setattr__(self, "source_judgment_ids", tuple(self.source_judgment_ids))
        object.__setattr__(self, "confidence_values", tuple(self.confidence_values))
        if any(not 0 <= value <= 1 for value in self.confidence_values):
            raise ValueError("Consensus confidence values must be between 0 and 1")
        object.__setattr__(
            self, "label_distribution", MappingProxyType(dict(self.label_distribution))
        )
        object.__setattr__(
            self,
            "audit_reasons",
            tuple(_enum(item, HumanAuditReason) for item in self.audit_reasons),
        )
        require_non_empty(self.disposition_reason, "disposition_reason")
        expected = canonical_hash(_without(self, "checksum"))
        if self.checksum and self.checksum != expected:
            raise ValueError("JudgmentConsensus checksum mismatch")
        object.__setattr__(self, "checksum", expected)


@dataclass(frozen=True, slots=True)
class HumanAuditRequest(SerializableContract):
    audit_request_id: str
    evaluation_id: str
    topic_id: str
    candidate_id: str
    proposed_silver_label: RelevanceLabel | None
    audit_reasons: tuple[HumanAuditReason, ...]
    judgment_ids: tuple[str, ...]
    consensus_checksum: str
    candidate_checksum: str
    audit_type: HumanAuditType
    sampling_seed: str
    sampling_version: str
    status: HumanAuditStatus
    created_at: datetime
    schema_version: str = AUDIT_REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.proposed_silver_label is not None:
            object.__setattr__(
                self, "proposed_silver_label", _enum(self.proposed_silver_label, RelevanceLabel)
            )
        object.__setattr__(
            self, "audit_reasons", tuple(_enum(item, HumanAuditReason) for item in self.audit_reasons)
        )
        object.__setattr__(self, "judgment_ids", tuple(self.judgment_ids))
        object.__setattr__(self, "audit_type", _enum(self.audit_type, HumanAuditType))
        object.__setattr__(self, "status", _enum(self.status, HumanAuditStatus))
        if not self.audit_reasons:
            raise ValueError("HumanAuditRequest requires an audit reason")
        _sha(self.consensus_checksum, "consensus_checksum")
        _sha(self.candidate_checksum, "candidate_checksum")
        require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class HumanAuditResult(SerializableContract):
    audit_request_id: str
    human_reviewer_id: str
    final_label: RelevanceLabel
    agrees_with_silver: bool
    override_reason: str | None
    confidence: float
    reviewed_at: datetime
    request_checksum: str
    schema_version: str = AUDIT_RESULT_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "final_label", _enum(self.final_label, RelevanceLabel))
        require_non_empty(self.audit_request_id, "audit_request_id")
        require_non_empty(self.human_reviewer_id, "human_reviewer_id")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Human audit confidence must be between 0 and 1")
        if not self.agrees_with_silver and not self.override_reason:
            raise ValueError("Human override requires a reason")
        _sha(self.request_checksum, "request_checksum")
        require_aware(self.reviewed_at, "reviewed_at")


@dataclass(frozen=True, slots=True)
class HumanAuditQueue(SerializableContract):
    evaluation_id: str
    requests: tuple[HumanAuditRequest, ...]
    required_count: int
    random_sample_count: int
    maximum_burden: int
    state: AuditQueueState
    policy_version: str
    schema_version: str = AUDIT_QUEUE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "requests", tuple(self.requests))
        object.__setattr__(self, "state", _enum(self.state, AuditQueueState))
        if min(self.required_count, self.random_sample_count, self.maximum_burden) < 0:
            raise ValueError("Audit counts cannot be negative")
        if len(self.requests) != self.required_count + self.random_sample_count:
            raise ValueError("Audit queue counts do not match requests")


@dataclass(frozen=True, slots=True)
class SilverMetricSet(SerializableContract):
    precision_at_5: MetricValue
    precision_at_10: MetricValue
    ndcg_at_10: MetricValue


@dataclass(frozen=True, slots=True)
class SilverMetricReport(SerializableContract):
    raw_silver: SilverMetricSet
    audited_silver: SilverMetricSet
    human_audit_agreement: MetricValue
    human_override_rate: MetricValue
    needs_human_review_rate: MetricValue
    cannot_judge_rate: MetricValue
    label_source: str = "synthetic automated silver labels"
    expert_gold_labels_present: bool = False
    schema_version: str = SILVER_METRICS_SCHEMA

    def __post_init__(self) -> None:
        if self.expert_gold_labels_present:
            raise ValueError("This report cannot claim expert-gold labels")
