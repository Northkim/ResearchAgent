"""Immutable contracts for human-reviewed paper-discovery evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.research.contracts._serialization import (
    SerializableContract,
    freeze_json,
    require_aware,
    require_non_empty,
)
from backend.research.contracts.models import require_sha256

EVALUATION_TOPIC_SCHEMA_VERSION = "openalex-evaluation-topic/v1"
EVALUATION_CANDIDATE_SCHEMA_VERSION = "openalex-evaluation-candidate/v1"
CANDIDATE_JUDGMENT_SCHEMA_VERSION = "openalex-candidate-judgment/v1"
ADJUDICATED_JUDGMENT_SCHEMA_VERSION = "openalex-adjudicated-judgment/v1"
EVALUATION_RUN_SCHEMA_VERSION = "openalex-evaluation-run/v1"
EVALUATION_METRICS_SCHEMA_VERSION = "openalex-evaluation-metrics/v1"
TOPIC_SET_SCHEMA_VERSION = "openalex-evaluation-topic-set/v1"


def _strings(values: tuple[str, ...] | list[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{field_name} cannot contain empty strings")
    return normalized


class RelevanceLabel(str, Enum):
    HIGHLY_RELEVANT = "HIGHLY_RELEVANT"
    RELEVANT = "RELEVANT"
    PARTIALLY_RELEVANT = "PARTIALLY_RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"
    CANNOT_JUDGE = "CANNOT_JUDGE"


class EvaluationCompletionState(str, Enum):
    INITIALIZED = "INITIALIZED"
    CANDIDATES_COMPLETE = "CANDIDATES_COMPLETE"
    JUDGMENTS_PARTIAL = "JUDGMENTS_PARTIAL"
    READY_FOR_ADJUDICATION = "READY_FOR_ADJUDICATION"
    ADJUDICATED = "ADJUDICATED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class EvaluationTopic(SerializableContract):
    topic_id: str
    title: str
    topic: str
    research_question: str | None
    keywords: tuple[str, ...]
    year_from: int | None
    year_to: int | None
    language_policy: str
    document_type_policy: str
    intended_discipline: str
    difficulty_tags: tuple[str, ...]
    rationale: str
    expected_ambiguity_cases: tuple[str, ...]
    maximum_candidates: int = 20
    schema_version: str = EVALUATION_TOPIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_TOPIC_SCHEMA_VERSION:
            raise ValueError("Unsupported EvaluationTopic schema version")
        for value, name in (
            (self.topic_id, "EvaluationTopic.topic_id"),
            (self.title, "EvaluationTopic.title"),
            (self.topic, "EvaluationTopic.topic"),
            (self.language_policy, "EvaluationTopic.language_policy"),
            (self.document_type_policy, "EvaluationTopic.document_type_policy"),
            (self.intended_discipline, "EvaluationTopic.intended_discipline"),
            (self.rationale, "EvaluationTopic.rationale"),
        ):
            require_non_empty(value, name)
        if self.research_question is not None:
            require_non_empty(self.research_question, "EvaluationTopic.research_question")
        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError("EvaluationTopic.year_from cannot exceed year_to")
        if not 1 <= self.maximum_candidates <= 20:
            raise ValueError("EvaluationTopic.maximum_candidates must be in [1, 20]")
        object.__setattr__(self, "keywords", _strings(self.keywords, "keywords"))
        object.__setattr__(
            self,
            "difficulty_tags",
            _strings(self.difficulty_tags, "difficulty_tags"),
        )
        object.__setattr__(
            self,
            "expected_ambiguity_cases",
            _strings(self.expected_ambiguity_cases, "expected_ambiguity_cases"),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvaluationTopic:
        return cls(
            topic_id=str(value["topic_id"]),
            title=str(value["title"]),
            topic=str(value["topic"]),
            research_question=(
                None
                if value.get("research_question") is None
                else str(value["research_question"])
            ),
            keywords=tuple(str(item) for item in value.get("keywords", ())),
            year_from=(
                None if value.get("year_from") is None else int(value["year_from"])
            ),
            year_to=None if value.get("year_to") is None else int(value["year_to"]),
            language_policy=str(value["language_policy"]),
            document_type_policy=str(value["document_type_policy"]),
            intended_discipline=str(value["intended_discipline"]),
            difficulty_tags=tuple(
                str(item) for item in value.get("difficulty_tags", ())
            ),
            rationale=str(value["rationale"]),
            expected_ambiguity_cases=tuple(
                str(item) for item in value.get("expected_ambiguity_cases", ())
            ),
            maximum_candidates=int(value.get("maximum_candidates", 20)),
            schema_version=str(
                value.get("schema_version", EVALUATION_TOPIC_SCHEMA_VERSION)
            ),
        )


@dataclass(frozen=True, slots=True)
class EvaluationCandidate(SerializableContract):
    topic_id: str
    topic_title: str
    topic: str
    research_question: str | None
    candidate_id: str
    rank: int
    paper_id: str
    openalex_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str | None
    doi: str | None
    abstract_available: bool
    normalized_metadata_hash: str
    search_execution_id: str
    provider: str
    adapter_version: str
    abstract_preview: str | None = None
    schema_version: str = EVALUATION_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_CANDIDATE_SCHEMA_VERSION:
            raise ValueError("Unsupported EvaluationCandidate schema version")
        for value, name in (
            (self.topic_id, "EvaluationCandidate.topic_id"),
            (self.topic_title, "EvaluationCandidate.topic_title"),
            (self.topic, "EvaluationCandidate.topic"),
            (self.candidate_id, "EvaluationCandidate.candidate_id"),
            (self.paper_id, "EvaluationCandidate.paper_id"),
            (self.openalex_id, "EvaluationCandidate.openalex_id"),
            (self.title, "EvaluationCandidate.title"),
            (self.search_execution_id, "EvaluationCandidate.search_execution_id"),
            (self.provider, "EvaluationCandidate.provider"),
            (self.adapter_version, "EvaluationCandidate.adapter_version"),
        ):
            require_non_empty(value, name)
        if self.research_question is not None:
            require_non_empty(
                self.research_question,
                "EvaluationCandidate.research_question",
            )
        if self.rank <= 0:
            raise ValueError("EvaluationCandidate.rank must be positive")
        require_sha256(
            self.normalized_metadata_hash,
            "EvaluationCandidate.normalized_metadata_hash",
        )
        object.__setattr__(self, "authors", _strings(self.authors, "authors"))
        if self.abstract_preview is not None:
            preview = " ".join(self.abstract_preview.split())
            if len(preview) > 500:
                raise ValueError("EvaluationCandidate.abstract_preview exceeds 500 chars")
            object.__setattr__(self, "abstract_preview", preview or None)

    @property
    def identity_hash(self) -> str:
        return self.canonical_identity_hash()

    def canonical_identity_hash(self) -> str:
        from backend.research.contracts import canonical_hash

        return canonical_hash(
            {
                "topic_id": self.topic_id,
                "topic_title": self.topic_title,
                "topic": self.topic,
                "research_question": self.research_question,
                "candidate_id": self.candidate_id,
                "paper_id": self.paper_id,
                "openalex_id": self.openalex_id,
                "normalized_metadata_hash": self.normalized_metadata_hash,
                "search_execution_id": self.search_execution_id,
                "provider": self.provider,
                "adapter_version": self.adapter_version,
            }
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvaluationCandidate:
        return cls(
            topic_id=str(value["topic_id"]),
            topic_title=str(value["topic_title"]),
            topic=str(value["topic"]),
            research_question=(
                None
                if value.get("research_question") is None
                else str(value["research_question"])
            ),
            candidate_id=str(value["candidate_id"]),
            rank=int(value["rank"]),
            paper_id=str(value["paper_id"]),
            openalex_id=str(value["openalex_id"]),
            title=str(value["title"]),
            authors=tuple(str(item) for item in value.get("authors", ())),
            year=None if value.get("year") is None else int(value["year"]),
            venue=None if value.get("venue") is None else str(value["venue"]),
            doi=None if value.get("doi") is None else str(value["doi"]),
            abstract_available=bool(value["abstract_available"]),
            normalized_metadata_hash=str(value["normalized_metadata_hash"]),
            search_execution_id=str(value["search_execution_id"]),
            provider=str(value["provider"]),
            adapter_version=str(value["adapter_version"]),
            abstract_preview=(
                None
                if value.get("abstract_preview") is None
                else str(value["abstract_preview"])
            ),
            schema_version=str(
                value.get("schema_version", EVALUATION_CANDIDATE_SCHEMA_VERSION)
            ),
        )


@dataclass(frozen=True, slots=True)
class CandidateJudgment(SerializableContract):
    topic_id: str
    candidate_id: str
    candidate_identity_hash: str
    reviewer_id: str
    relevance_label: RelevanceLabel
    confidence: int
    exclusion_reason: str | None
    duplicate_cluster: str | None
    identity_ambiguity: bool
    metadata_error_flags: tuple[str, ...]
    reviewer_note: str | None
    judged_at: datetime
    schema_version: str = CANDIDATE_JUDGMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_JUDGMENT_SCHEMA_VERSION:
            raise ValueError("Unsupported CandidateJudgment schema version")
        for value, name in (
            (self.topic_id, "CandidateJudgment.topic_id"),
            (self.candidate_id, "CandidateJudgment.candidate_id"),
            (self.reviewer_id, "CandidateJudgment.reviewer_id"),
        ):
            require_non_empty(value, name)
        require_sha256(
            self.candidate_identity_hash,
            "CandidateJudgment.candidate_identity_hash",
        )
        if not 1 <= self.confidence <= 5:
            raise ValueError("CandidateJudgment.confidence must be in [1, 5]")
        require_aware(self.judged_at, "CandidateJudgment.judged_at")
        object.__setattr__(
            self,
            "metadata_error_flags",
            _strings(self.metadata_error_flags, "metadata_error_flags"),
        )
        if self.reviewer_note is not None and len(self.reviewer_note) > 500:
            raise ValueError("CandidateJudgment.reviewer_note exceeds 500 chars")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CandidateJudgment:
        try:
            label = RelevanceLabel(str(value["relevance_label"]))
        except ValueError as error:
            raise ValueError("Invalid relevance label") from error
        return cls(
            topic_id=str(value["topic_id"]),
            candidate_id=str(value["candidate_id"]),
            candidate_identity_hash=str(value["candidate_identity_hash"]),
            reviewer_id=str(value["reviewer_id"]),
            relevance_label=label,
            confidence=int(value["confidence"]),
            exclusion_reason=(
                None
                if value.get("exclusion_reason") in {None, ""}
                else str(value["exclusion_reason"])
            ),
            duplicate_cluster=(
                None
                if value.get("duplicate_cluster") in {None, ""}
                else str(value["duplicate_cluster"])
            ),
            identity_ambiguity=bool(value.get("identity_ambiguity", False)),
            metadata_error_flags=tuple(
                str(item) for item in value.get("metadata_error_flags", ())
            ),
            reviewer_note=(
                None
                if value.get("reviewer_note") in {None, ""}
                else str(value["reviewer_note"])
            ),
            judged_at=datetime.fromisoformat(str(value["judged_at"])),
            schema_version=str(
                value.get("schema_version", CANDIDATE_JUDGMENT_SCHEMA_VERSION)
            ),
        )


@dataclass(frozen=True, slots=True)
class AdjudicatedJudgment(SerializableContract):
    topic_id: str
    candidate_id: str
    final_relevance_label: RelevanceLabel
    adjudicator_id: str
    source_judgment_hashes: tuple[str, ...]
    disagreement_reason: str | None
    final_notes: str | None
    adjudicated_at: datetime
    schema_version: str = ADJUDICATED_JUDGMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ADJUDICATED_JUDGMENT_SCHEMA_VERSION:
            raise ValueError("Unsupported AdjudicatedJudgment schema version")
        for value, name in (
            (self.topic_id, "AdjudicatedJudgment.topic_id"),
            (self.candidate_id, "AdjudicatedJudgment.candidate_id"),
            (self.adjudicator_id, "AdjudicatedJudgment.adjudicator_id"),
        ):
            require_non_empty(value, name)
        if len(self.source_judgment_hashes) < 2:
            raise ValueError("Adjudication requires at least two source judgments")
        if len(set(self.source_judgment_hashes)) != len(
            self.source_judgment_hashes
        ):
            raise ValueError("Adjudication source judgments must be unique")
        for value in self.source_judgment_hashes:
            require_sha256(value, "AdjudicatedJudgment.source_judgment_hash")
        require_aware(self.adjudicated_at, "AdjudicatedJudgment.adjudicated_at")
        if self.final_notes is not None and len(self.final_notes) > 500:
            raise ValueError("AdjudicatedJudgment.final_notes exceeds 500 chars")


@dataclass(frozen=True, slots=True)
class EvaluationRun(SerializableContract):
    evaluation_id: str
    topic_set_version: str
    provider: str
    adapter_version: str
    api_contract_snapshot: str
    query_fingerprints: Mapping[str, str]
    candidate_pool_checksums: Mapping[str, str]
    started_at: datetime
    completed_at: datetime | None
    request_count: int
    latency_ms: int
    retry_count: int
    provider_usage: tuple[Mapping[str, Any], ...]
    completion_state: EvaluationCompletionState
    schema_version: str = EVALUATION_RUN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_RUN_SCHEMA_VERSION:
            raise ValueError("Unsupported EvaluationRun schema version")
        for value, name in (
            (self.evaluation_id, "EvaluationRun.evaluation_id"),
            (self.topic_set_version, "EvaluationRun.topic_set_version"),
            (self.provider, "EvaluationRun.provider"),
            (self.adapter_version, "EvaluationRun.adapter_version"),
            (self.api_contract_snapshot, "EvaluationRun.api_contract_snapshot"),
        ):
            require_non_empty(value, name)
        require_aware(self.started_at, "EvaluationRun.started_at")
        if self.completed_at is not None:
            require_aware(self.completed_at, "EvaluationRun.completed_at")
        if min(self.request_count, self.latency_ms, self.retry_count) < 0:
            raise ValueError("EvaluationRun operational counts cannot be negative")
        for value in self.query_fingerprints.values():
            require_sha256(value, "EvaluationRun.query_fingerprint")
        for value in self.candidate_pool_checksums.values():
            require_sha256(value, "EvaluationRun.candidate_pool_checksum")
        if set(self.query_fingerprints) != set(self.candidate_pool_checksums):
            raise ValueError(
                "EvaluationRun query and candidate-pool topic IDs must match"
            )
        object.__setattr__(
            self, "query_fingerprints", freeze_json(self.query_fingerprints)
        )
        object.__setattr__(
            self,
            "candidate_pool_checksums",
            freeze_json(self.candidate_pool_checksums),
        )
        object.__setattr__(
            self,
            "provider_usage",
            tuple(freeze_json(item) for item in self.provider_usage),
        )


@dataclass(frozen=True, slots=True)
class MetricValue(SerializableContract):
    available: bool
    value: float | int | None
    sample_size: int
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.sample_size < 0:
            raise ValueError("MetricValue.sample_size cannot be negative")
        if self.available and self.value is None:
            raise ValueError("Available metric requires a value")
        if not self.available and not self.reason:
            raise ValueError("Unavailable metric requires a reason")


@dataclass(frozen=True, slots=True)
class EvaluationMetricSummary(SerializableContract):
    precision_at_5: MetricValue
    precision_at_10: MetricValue
    ndcg_at_10: MetricValue
    pooled_recall_at_k: MetricValue
    relevant_paper_yield: MetricValue
    judgment_coverage: MetricValue
    doi_resolution_rate: MetricValue
    abstract_availability_rate: MetricValue
    author_completeness_rate: MetricValue
    venue_completeness_rate: MetricValue
    duplicate_rate: MetricValue
    unresolved_cluster_rate: MetricValue
    false_merge_rate: MetricValue
    request_count: MetricValue
    latency_ms: MetricValue
    retry_rate: MetricValue
    failure_rate: MetricValue
    manual_review_burden: MetricValue
    reviewer_agreement: MetricValue
    per_topic_retrieval: Mapping[str, Mapping[str, Any]]
    limitations: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = EVALUATION_METRICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_METRICS_SCHEMA_VERSION:
            raise ValueError("Unsupported EvaluationMetricSummary schema version")
        object.__setattr__(
            self,
            "per_topic_retrieval",
            freeze_json(self.per_topic_retrieval),
        )
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "EvaluationMetricSummary.limitations"),
        )
