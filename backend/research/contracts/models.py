"""Immutable serializable contracts for Guided Literature Review v2."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ._serialization import (
    SerializableContract,
    canonical_hash,
    freeze_json,
    require_aware,
    require_non_empty,
)

RESEARCH_QUERY_SCHEMA_VERSION = "research-query/v1"
PAPER_RECORD_SCHEMA_VERSION = "paper-record/v1"
SOURCE_CONTENT_SCHEMA_VERSION = "source-content/v1"
RANKED_PAPER_SCHEMA_VERSION = "ranked-paper/v1"
CITATION_REFERENCE_SCHEMA_VERSION = "citation-reference/v1"
EVIDENCE_UNIT_SCHEMA_VERSION = "evidence-unit/v1"
GROUNDED_CLAIM_SCHEMA_VERSION = "grounded-claim/v1"
RESEARCH_REPORT_SCHEMA_VERSION = "research-report/v1"
PROVIDER_USAGE_SCHEMA_VERSION = "provider-usage/v1"
PROVIDER_BUDGET_SCHEMA_VERSION = "provider-budget/v1"
PROVIDER_OPERATION_SCHEMA_VERSION = "provider-operation/v1"
PROVENANCE_MANIFEST_SCHEMA_VERSION = "provenance/v1"
SEARCH_PLAN_SCHEMA_VERSION = "search-plan/v1"
SEARCH_EXECUTION_SCHEMA_VERSION = "search-execution/v1"
SEARCH_STATISTICS_SCHEMA_VERSION = "search-statistics/v1"

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
_DOI_SHAPE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _DOI_PREFIX.sub("", value.strip()).strip().lower()
    if not normalized:
        return None
    if not _DOI_SHAPE.fullmatch(normalized):
        raise ValueError(f"Invalid DOI: {value!r}")
    return normalized


def require_sha256(value: str, field_name: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex characters>")


def _strings(values: tuple[str, ...] | list[str], field_name: str) -> tuple[str, ...]:
    result = tuple(item.strip() for item in values)
    if any(not item for item in result):
        raise ValueError(f"{field_name} cannot contain empty strings")
    return result


@dataclass(frozen=True, slots=True)
class ResearchQuery(SerializableContract):
    topic: str
    keywords: tuple[str, ...] = ()
    year_from: int | None = None
    year_to: int | None = None
    max_results: int = 8
    language: str = "en"
    inclusion_criteria: tuple[str, ...] = ()
    exclusion_criteria: tuple[str, ...] = ()
    schema_version: str = RESEARCH_QUERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        topic = self.topic.strip()
        require_non_empty(topic, "ResearchQuery.topic")
        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError("ResearchQuery.year_from cannot exceed year_to")
        if self.max_results <= 0:
            raise ValueError("ResearchQuery.max_results must be positive")
        require_non_empty(self.language, "ResearchQuery.language")
        keywords = _strings(self.keywords, "ResearchQuery.keywords")
        if len({item.casefold() for item in keywords}) != len(keywords):
            raise ValueError("ResearchQuery.keywords must be unique")
        object.__setattr__(self, "topic", topic)
        object.__setattr__(self, "keywords", keywords)
        object.__setattr__(
            self,
            "inclusion_criteria",
            _strings(self.inclusion_criteria, "ResearchQuery.inclusion_criteria"),
        )
        object.__setattr__(
            self,
            "exclusion_criteria",
            _strings(self.exclusion_criteria, "ResearchQuery.exclusion_criteria"),
        )

    @property
    def query_hash(self) -> str:
        return self.canonical_hash()


@dataclass(frozen=True, slots=True)
class SearchPlan(SerializableContract):
    """Versioned, provider-specific plan recorded before discovery."""

    topic: str
    research_question: str | None
    keywords: tuple[str, ...]
    exact_query: str
    year_from: int | None
    year_to: int | None
    language_policy: str
    document_type_policy: str
    inclusion_criteria: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    maximum_results: int
    pagination_policy: Mapping[str, Any]
    sort_policy: str
    provider: str
    adapter_version: str
    api_contract_snapshot: str
    planned_at: datetime
    schema_version: str = SEARCH_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.topic, "SearchPlan.topic"),
            (self.exact_query, "SearchPlan.exact_query"),
            (self.language_policy, "SearchPlan.language_policy"),
            (self.document_type_policy, "SearchPlan.document_type_policy"),
            (self.sort_policy, "SearchPlan.sort_policy"),
            (self.provider, "SearchPlan.provider"),
            (self.adapter_version, "SearchPlan.adapter_version"),
            (self.api_contract_snapshot, "SearchPlan.api_contract_snapshot"),
        ):
            require_non_empty(value, name)
        if self.maximum_results <= 0:
            raise ValueError("SearchPlan.maximum_results must be positive")
        require_aware(self.planned_at, "SearchPlan.planned_at")
        object.__setattr__(self, "keywords", _strings(self.keywords, "SearchPlan.keywords"))
        object.__setattr__(
            self,
            "inclusion_criteria",
            _strings(self.inclusion_criteria, "SearchPlan.inclusion_criteria"),
        )
        object.__setattr__(
            self,
            "exclusion_criteria",
            _strings(self.exclusion_criteria, "SearchPlan.exclusion_criteria"),
        )
        object.__setattr__(self, "pagination_policy", freeze_json(self.pagination_policy))

    @property
    def fingerprint(self) -> str:
        value = self.to_dict()
        value.pop("planned_at")
        return canonical_hash(value)


@dataclass(frozen=True, slots=True)
class SearchExecution(SerializableContract):
    """Sanitized evidence about one provider search execution."""

    search_plan_fingerprint: str
    provider: str
    adapter_version: str
    endpoint: str
    requested_fields: tuple[str, ...]
    request_count: int
    retry_count: int
    complete: bool
    cursor_pages: int
    retrieved_at: datetime
    provider_reported_cost_usd: str
    provider_request_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    identity_status: str = "discovery_only_unverified"
    schema_version: str = SEARCH_EXECUTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_sha256(
            self.search_plan_fingerprint,
            "SearchExecution.search_plan_fingerprint",
        )
        for value, name in (
            (self.provider, "SearchExecution.provider"),
            (self.adapter_version, "SearchExecution.adapter_version"),
            (self.endpoint, "SearchExecution.endpoint"),
            (self.provider_reported_cost_usd, "SearchExecution.provider_reported_cost_usd"),
            (self.identity_status, "SearchExecution.identity_status"),
        ):
            require_non_empty(value, name)
        if min(self.request_count, self.retry_count, self.cursor_pages) < 0:
            raise ValueError("SearchExecution counts cannot be negative")
        require_aware(self.retrieved_at, "SearchExecution.retrieved_at")
        object.__setattr__(
            self,
            "requested_fields",
            _strings(self.requested_fields, "SearchExecution.requested_fields"),
        )
        object.__setattr__(
            self,
            "provider_request_ids",
            _strings(self.provider_request_ids, "SearchExecution.provider_request_ids"),
        )
        object.__setattr__(
            self,
            "warnings",
            _strings(self.warnings, "SearchExecution.warnings"),
        )


@dataclass(frozen=True, slots=True)
class SearchStatistics(SerializableContract):
    """Provider-neutral accounting for one discovery result set."""

    search_plan_fingerprint: str
    provider_reported_count: int
    records_received: int
    records_normalized: int
    records_rejected: int
    duplicate_doi_count: int
    duplicate_provider_id_count: int
    advisory_title_year_clusters: int
    missing_abstract_count: int
    incomplete: bool
    schema_version: str = SEARCH_STATISTICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_sha256(
            self.search_plan_fingerprint,
            "SearchStatistics.search_plan_fingerprint",
        )
        values = (
            self.provider_reported_count,
            self.records_received,
            self.records_normalized,
            self.records_rejected,
            self.duplicate_doi_count,
            self.duplicate_provider_id_count,
            self.advisory_title_year_clusters,
            self.missing_abstract_count,
        )
        if min(values) < 0:
            raise ValueError("SearchStatistics counts cannot be negative")


@dataclass(frozen=True, slots=True)
class PaperAuthor(SerializableContract):
    name: str
    provider_author_id: str | None = None
    orcid: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.name, "PaperAuthor.name")


@dataclass(frozen=True, slots=True)
class PaperRecord(SerializableContract):
    paper_id: str
    provider_id: str
    title: str
    authors: tuple[PaperAuthor, ...]
    abstract: str | None
    publication_year: int | None
    publication_venue: str | None
    source_provider: str
    source_url: str | None
    doi: str | None
    retrieved_at: datetime
    raw_metadata_hash: str
    language: str | None = None
    normalized_metadata_version: str = "paper-normalization/v1"
    metadata_limitations: tuple[str, ...] = ()
    schema_version: str = PAPER_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.paper_id, "PaperRecord.paper_id"),
            (self.provider_id, "PaperRecord.provider_id"),
            (self.title, "PaperRecord.title"),
            (self.source_provider, "PaperRecord.source_provider"),
            (self.normalized_metadata_version, "PaperRecord.normalized_metadata_version"),
        ):
            require_non_empty(value, name)
        require_aware(self.retrieved_at, "PaperRecord.retrieved_at")
        require_sha256(self.raw_metadata_hash, "PaperRecord.raw_metadata_hash")
        if self.source_url is not None and not self.source_url.startswith("https://"):
            raise ValueError("PaperRecord.source_url must use HTTPS")
        if self.language is not None:
            require_non_empty(self.language, "PaperRecord.language")
        object.__setattr__(self, "authors", tuple(self.authors))
        object.__setattr__(self, "doi", normalize_doi(self.doi))
        object.__setattr__(
            self,
            "metadata_limitations",
            _strings(self.metadata_limitations, "PaperRecord.metadata_limitations"),
        )

    @classmethod
    def internal_id(
        cls,
        *,
        provider: str,
        provider_id: str,
        doi: str | None,
    ) -> str:
        normalized = normalize_doi(doi)
        identity = f"doi:{normalized}" if normalized else f"provider:{provider}:{provider_id}"
        return "paper:" + canonical_hash(identity).removeprefix("sha256:")


class ContentType(str, Enum):
    METADATA_ONLY = "metadata_only"
    ABSTRACT = "abstract"
    FULL_TEXT = "full_text"


class AccessLimitation(str, Enum):
    NONE = "none"
    UNAVAILABLE = "unavailable"
    RESTRICTED = "restricted"
    ABSTRACT_ONLY = "abstract_only"


@dataclass(frozen=True, slots=True)
class SourceContent(SerializableContract):
    paper_id: str
    content_type: ContentType
    abstract: str | None
    full_text: str | None
    content_source: str
    source_url: str | None
    retrieved_at: datetime
    content_hash: str
    access_limitation: AccessLimitation
    license_or_usage_metadata: Mapping[str, Any] | None = None
    source_locations: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = SOURCE_CONTENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_non_empty(self.paper_id, "SourceContent.paper_id")
        require_non_empty(self.content_source, "SourceContent.content_source")
        require_aware(self.retrieved_at, "SourceContent.retrieved_at")
        require_sha256(self.content_hash, "SourceContent.content_hash")
        if self.source_url is not None and not self.source_url.startswith("https://"):
            raise ValueError("SourceContent.source_url must use HTTPS")
        if self.content_type is ContentType.FULL_TEXT and not self.full_text:
            raise ValueError("Full-text SourceContent requires full_text")
        if self.content_type is not ContentType.FULL_TEXT and self.full_text is not None:
            raise ValueError("Abstract/metadata SourceContent cannot contain full_text")
        if self.content_type is ContentType.ABSTRACT and not self.abstract:
            raise ValueError("Abstract SourceContent requires abstract")
        if (
            self.access_limitation is AccessLimitation.ABSTRACT_ONLY
            and self.content_type is ContentType.FULL_TEXT
        ):
            raise ValueError("Abstract-only SourceContent cannot be full text")
        if self.license_or_usage_metadata is not None:
            object.__setattr__(
                self,
                "license_or_usage_metadata",
                freeze_json(self.license_or_usage_metadata),
            )
        object.__setattr__(
            self,
            "source_locations",
            tuple(freeze_json(item) for item in self.source_locations),
        )


class InclusionStatus(str, Enum):
    SELECTED = "selected"
    EXCLUDED = "excluded"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class RankedPaper(SerializableContract):
    paper_id: str
    relevance_score: float
    ranking_explanation: str
    inclusion_status: InclusionStatus
    exclusion_reason: str | None
    rank: int | None
    ranker_version: str
    score_components: Mapping[str, float] = field(default_factory=dict)
    schema_version: str = RANKED_PAPER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_non_empty(self.paper_id, "RankedPaper.paper_id")
        require_non_empty(self.ranking_explanation, "RankedPaper.ranking_explanation")
        require_non_empty(self.ranker_version, "RankedPaper.ranker_version")
        if not 0 <= self.relevance_score <= 1:
            raise ValueError("RankedPaper.relevance_score must be in [0, 1]")
        if self.rank is not None and self.rank <= 0:
            raise ValueError("RankedPaper.rank must be positive")
        if self.inclusion_status is InclusionStatus.SELECTED and self.rank is None:
            raise ValueError("Selected RankedPaper requires a rank")
        if self.inclusion_status is not InclusionStatus.SELECTED and not self.exclusion_reason:
            raise ValueError("Excluded/ineligible RankedPaper requires a reason")
        for name, value in self.score_components.items():
            require_non_empty(name, "RankedPaper.score component")
            if not 0 <= value <= 1:
                raise ValueError("RankedPaper score components must be in [0, 1]")
        object.__setattr__(self, "score_components", freeze_json(self.score_components))


@dataclass(frozen=True, slots=True)
class CitationReference(SerializableContract):
    citation_id: str
    paper_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    source_url: str | None
    doi: str | None
    report_citation_label: str
    schema_version: str = CITATION_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.citation_id, "CitationReference.citation_id"),
            (self.paper_id, "CitationReference.paper_id"),
            (self.title, "CitationReference.title"),
            (self.report_citation_label, "CitationReference.report_citation_label"),
        ):
            require_non_empty(value, name)
        if not re.fullmatch(r"\[P[1-9]\d*\]", self.report_citation_label):
            raise ValueError("CitationReference label must use [P1], [P2], ...")
        if self.source_url is not None and not self.source_url.startswith("https://"):
            raise ValueError("CitationReference.source_url must use HTTPS")
        object.__setattr__(self, "authors", _strings(self.authors, "CitationReference.authors"))
        object.__setattr__(self, "doi", normalize_doi(self.doi))


class EvidenceScope(str, Enum):
    METADATA = "metadata"
    ABSTRACT = "abstract"
    FULL_TEXT = "full_text"


@dataclass(frozen=True, slots=True)
class EvidenceUnit(SerializableContract):
    evidence_id: str
    paper_id: str
    source_content_hash: str
    source_location: Mapping[str, Any] | str
    source_excerpt: str | None
    source_summary: str | None
    evidence_hash: str
    supported_claim_ids: tuple[str, ...]
    content_scope: EvidenceScope
    schema_version: str = EVIDENCE_UNIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_non_empty(self.evidence_id, "EvidenceUnit.evidence_id")
        require_non_empty(self.paper_id, "EvidenceUnit.paper_id")
        require_sha256(self.source_content_hash, "EvidenceUnit.source_content_hash")
        require_sha256(self.evidence_hash, "EvidenceUnit.evidence_hash")
        if not self.source_excerpt and not self.source_summary:
            raise ValueError("EvidenceUnit requires an excerpt or source summary")
        if isinstance(self.source_location, Mapping):
            object.__setattr__(self, "source_location", freeze_json(self.source_location))
        else:
            require_non_empty(self.source_location, "EvidenceUnit.source_location")
        object.__setattr__(
            self,
            "supported_claim_ids",
            _strings(self.supported_claim_ids, "EvidenceUnit.supported_claim_ids"),
        )


class ClaimConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimKind(str, Enum):
    SOURCE_STATEMENT = "source_statement"
    CROSS_SOURCE_SYNTHESIS = "cross_source_synthesis"
    INFERENCE = "inference"


@dataclass(frozen=True, slots=True)
class GroundedClaim(SerializableContract):
    claim_id: str
    claim_text: str
    supporting_evidence_ids: tuple[str, ...]
    confidence: ClaimConfidence
    limitations: tuple[str, ...]
    claim_kind: ClaimKind
    generation_model: str
    prompt_version: str
    substantive: bool = True
    schema_version: str = GROUNDED_CLAIM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.claim_id, "GroundedClaim.claim_id"),
            (self.claim_text, "GroundedClaim.claim_text"),
            (self.generation_model, "GroundedClaim.generation_model"),
            (self.prompt_version, "GroundedClaim.prompt_version"),
        ):
            require_non_empty(value, name)
        evidence = _strings(
            self.supporting_evidence_ids,
            "GroundedClaim.supporting_evidence_ids",
        )
        object.__setattr__(self, "supporting_evidence_ids", evidence)
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "GroundedClaim.limitations"),
        )


@dataclass(frozen=True, slots=True)
class ResearchReport(SerializableContract):
    report_id: str
    project_id: str
    workflow_run_id: str
    title: str
    executive_summary: str
    methodology: Mapping[str, Any]
    selected_papers: tuple[CitationReference, ...]
    paper_summaries: tuple[Mapping[str, Any], ...]
    thematic_synthesis: Mapping[str, Any]
    disagreements: tuple[Mapping[str, Any], ...]
    limitations: tuple[str, ...]
    research_gaps: tuple[Mapping[str, Any], ...]
    references: tuple[CitationReference, ...]
    provenance_artifact_id: str
    generated_at: datetime
    markdown: str
    source_scope_by_paper: Mapping[str, str] = field(default_factory=dict)
    report_schema_version: str = RESEARCH_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.report_id, "ResearchReport.report_id"),
            (self.project_id, "ResearchReport.project_id"),
            (self.workflow_run_id, "ResearchReport.workflow_run_id"),
            (self.title, "ResearchReport.title"),
            (self.executive_summary, "ResearchReport.executive_summary"),
            (self.provenance_artifact_id, "ResearchReport.provenance_artifact_id"),
            (self.markdown, "ResearchReport.markdown"),
            (self.report_schema_version, "ResearchReport.report_schema_version"),
        ):
            require_non_empty(value, name)
        require_aware(self.generated_at, "ResearchReport.generated_at")
        object.__setattr__(self, "methodology", freeze_json(self.methodology))
        object.__setattr__(self, "selected_papers", tuple(self.selected_papers))
        object.__setattr__(
            self,
            "paper_summaries",
            tuple(freeze_json(item) for item in self.paper_summaries),
        )
        object.__setattr__(self, "thematic_synthesis", freeze_json(self.thematic_synthesis))
        object.__setattr__(
            self,
            "disagreements",
            tuple(freeze_json(item) for item in self.disagreements),
        )
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "ResearchReport.limitations"),
        )
        object.__setattr__(
            self,
            "research_gaps",
            tuple(freeze_json(item) for item in self.research_gaps),
        )
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(self, "source_scope_by_paper", freeze_json(self.source_scope_by_paper))


class ProviderCategory(str, Enum):
    PAPER_SEARCH = "paper_search"
    SOURCE_CONTENT = "source_content"
    LLM = "llm"


class ProviderOperationKind(str, Enum):
    SEARCH = "search"
    RETRIEVE = "retrieve"
    GENERATE_TEXT = "generate_text"
    GENERATE_STRUCTURED = "generate_structured"


class ProviderFailureCategory(str, Enum):
    INVALID_QUERY = "INVALID_QUERY"
    PROVIDER_AUTHENTICATION = "PROVIDER_AUTHENTICATION"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MALFORMED_PROVIDER_RESPONSE = "MALFORMED_PROVIDER_RESPONSE"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"
    LLM_STRUCTURED_OUTPUT = "LLM_STRUCTURED_OUTPUT"
    PROVENANCE_VALIDATION = "PROVENANCE_VALIDATION"
    ARTIFACT_STORAGE = "ARTIFACT_STORAGE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ProviderUsage(SerializableContract):
    provider: str
    model_or_endpoint: str
    operation_kind: ProviderOperationKind
    request_count: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_minor_units: int | None
    cost_currency: str | None
    latency_ms: int
    retry_count: int = 0
    failure_category: ProviderFailureCategory | None = None
    provider_request_ids: tuple[str, ...] = ()
    schema_version: str = PROVIDER_USAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_non_empty(self.provider, "ProviderUsage.provider")
        require_non_empty(self.model_or_endpoint, "ProviderUsage.model_or_endpoint")
        for value, name in (
            (self.request_count, "request_count"),
            (self.latency_ms, "latency_ms"),
            (self.retry_count, "retry_count"),
        ):
            if value < 0:
                raise ValueError(f"ProviderUsage.{name} cannot be negative")
        for value, name in (
            (self.input_tokens, "input_tokens"),
            (self.output_tokens, "output_tokens"),
            (self.estimated_cost_minor_units, "estimated_cost_minor_units"),
        ):
            if value is not None and value < 0:
                raise ValueError(f"ProviderUsage.{name} cannot be negative")
        if self.estimated_cost_minor_units is not None and not self.cost_currency:
            raise ValueError("ProviderUsage cost requires a currency")
        object.__setattr__(self, "provider_request_ids", tuple(self.provider_request_ids))

    @classmethod
    def zero_cost(
        cls,
        *,
        provider: str,
        model_or_endpoint: str,
        operation_kind: ProviderOperationKind,
    ) -> ProviderUsage:
        return cls(
            provider=provider,
            model_or_endpoint=model_or_endpoint,
            operation_kind=operation_kind,
            request_count=1,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=0,
        )


@dataclass(frozen=True, slots=True)
class ProviderReservation(SerializableContract):
    request_count: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    cost_minor_units: int = 0
    cost_currency: str = "USD"

    def __post_init__(self) -> None:
        if min(
            self.request_count,
            self.input_tokens,
            self.output_tokens,
            self.cost_minor_units,
        ) < 0:
            raise ValueError("ProviderReservation values cannot be negative")
        require_non_empty(self.cost_currency, "ProviderReservation.cost_currency")


@dataclass(frozen=True, slots=True)
class ProviderBudget(SerializableContract):
    max_provider_requests: int
    max_llm_calls: int
    max_input_tokens: int
    max_output_tokens: int
    max_cost_minor_units: int
    cost_currency: str = "USD"
    max_runtime_seconds: int = 1800
    max_artifact_bytes: int = 100 * 1024 * 1024
    live_provider_enabled: bool = False
    schema_version: str = PROVIDER_BUDGET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if min(
            self.max_provider_requests,
            self.max_llm_calls,
            self.max_input_tokens,
            self.max_output_tokens,
            self.max_cost_minor_units,
            self.max_runtime_seconds,
            self.max_artifact_bytes,
        ) < 0:
            raise ValueError("ProviderBudget limits cannot be negative")
        require_non_empty(self.cost_currency, "ProviderBudget.cost_currency")

    @classmethod
    def fake_only_default(cls) -> ProviderBudget:
        return cls(
            max_provider_requests=25,
            max_llm_calls=10,
            max_input_tokens=0,
            max_output_tokens=0,
            max_cost_minor_units=0,
            live_provider_enabled=False,
        )


class ProviderOperationStatus(str, Enum):
    RESERVED = "RESERVED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            ProviderOperationStatus.SUCCEEDED,
            ProviderOperationStatus.FAILED,
            ProviderOperationStatus.CANCELLED,
        }


class SettlementState(str, Enum):
    UNSETTLED = "UNSETTLED"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class ProviderOperation(SerializableContract):
    id: str
    project_id: str
    workflow_run_id: str
    logical_step_id: str
    step_run_id: str | None
    provider_category: ProviderCategory
    operation_kind: ProviderOperationKind
    provider_identity: str
    adapter_version: str
    model_or_endpoint: str
    idempotency_key: str
    request_fingerprint: str
    reservation: ProviderReservation
    is_live_provider: bool = False
    status: ProviderOperationStatus = ProviderOperationStatus.RESERVED
    settlement_state: SettlementState = SettlementState.UNSETTLED
    actual_usage: ProviderUsage | None = None
    failure_category: ProviderFailureCategory | None = None
    retry_count: int = 0
    diagnostic_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    row_version: int = 0
    schema_version: str = PROVIDER_OPERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "ProviderOperation.id"),
            (self.project_id, "ProviderOperation.project_id"),
            (self.workflow_run_id, "ProviderOperation.workflow_run_id"),
            (self.logical_step_id, "ProviderOperation.logical_step_id"),
            (self.provider_identity, "ProviderOperation.provider_identity"),
            (self.adapter_version, "ProviderOperation.adapter_version"),
            (self.model_or_endpoint, "ProviderOperation.model_or_endpoint"),
            (self.idempotency_key, "ProviderOperation.idempotency_key"),
        ):
            require_non_empty(value, name)
        require_sha256(self.request_fingerprint, "ProviderOperation.request_fingerprint")
        require_aware(self.created_at, "ProviderOperation.created_at")
        require_aware(self.updated_at, "ProviderOperation.updated_at")
        if self.started_at is not None:
            require_aware(self.started_at, "ProviderOperation.started_at")
        if self.finished_at is not None:
            require_aware(self.finished_at, "ProviderOperation.finished_at")
        if self.retry_count < 0 or self.row_version < 0:
            raise ValueError("ProviderOperation retry/version values cannot be negative")
        if self.status.is_terminal and self.finished_at is None:
            raise ValueError("Terminal ProviderOperation requires finished_at")
        if self.status is ProviderOperationStatus.RUNNING and self.started_at is None:
            raise ValueError("Running ProviderOperation requires started_at")
        if self.status.is_terminal and self.settlement_state is SettlementState.UNSETTLED:
            raise ValueError("Terminal ProviderOperation must be settled or released")
        if self.status is ProviderOperationStatus.SUCCEEDED:
            if self.actual_usage is None or self.settlement_state is not SettlementState.SETTLED:
                raise ValueError("Succeeded ProviderOperation must have settled usage")
            if self.failure_category is not None:
                raise ValueError("Succeeded ProviderOperation cannot have a failure")
        if self.status is ProviderOperationStatus.FAILED and self.failure_category is None:
            raise ValueError("Failed ProviderOperation requires a failure category")
        if (
            self.status is ProviderOperationStatus.CANCELLED
            and self.failure_category is not ProviderFailureCategory.CANCELLED
        ):
            raise ValueError("Cancelled ProviderOperation requires CANCELLED failure")
        if self.settlement_state is SettlementState.RELEASED and self.actual_usage is not None:
            raise ValueError("Released ProviderOperation cannot contain actual usage")
        if self.actual_usage is not None:
            if (
                self.actual_usage.provider != self.provider_identity
                or self.actual_usage.model_or_endpoint != self.model_or_endpoint
                or self.actual_usage.operation_kind is not self.operation_kind
            ):
                raise ValueError("ProviderOperation usage identity does not match operation")
            if (
                self.actual_usage.cost_currency is not None
                and self.actual_usage.cost_currency != self.reservation.cost_currency
            ):
                raise ValueError("ProviderOperation usage currency does not match reservation")
        object.__setattr__(self, "diagnostic_metadata", freeze_json(self.diagnostic_metadata))

    def mark_running(self, *, at: datetime) -> ProviderOperation:
        if self.status is not ProviderOperationStatus.RESERVED:
            raise ValueError("Only RESERVED ProviderOperation can start")
        return replace(
            self,
            status=ProviderOperationStatus.RUNNING,
            started_at=at,
            updated_at=at,
            row_version=self.row_version + 1,
        )

    def settle_success(
        self,
        usage: ProviderUsage,
        *,
        at: datetime,
    ) -> ProviderOperation:
        if self.status is not ProviderOperationStatus.RUNNING:
            raise ValueError("Only RUNNING ProviderOperation can succeed")
        return replace(
            self,
            status=ProviderOperationStatus.SUCCEEDED,
            settlement_state=SettlementState.SETTLED,
            actual_usage=usage,
            retry_count=usage.retry_count,
            failure_category=None,
            updated_at=at,
            finished_at=at,
            row_version=self.row_version + 1,
        )

    def settle_failure(
        self,
        *,
        failure_category: ProviderFailureCategory,
        at: datetime,
        usage: ProviderUsage | None = None,
        release_reservation: bool = False,
        diagnostic_metadata: Mapping[str, Any] | None = None,
    ) -> ProviderOperation:
        if self.status not in {ProviderOperationStatus.RESERVED, ProviderOperationStatus.RUNNING}:
            raise ValueError("ProviderOperation cannot fail from its current status")
        return replace(
            self,
            status=ProviderOperationStatus.FAILED,
            settlement_state=(
                SettlementState.RELEASED
                if release_reservation and usage is None
                else SettlementState.SETTLED
            ),
            actual_usage=usage,
            retry_count=usage.retry_count if usage is not None else self.retry_count,
            failure_category=failure_category,
            diagnostic_metadata=diagnostic_metadata or {},
            updated_at=at,
            finished_at=at,
            row_version=self.row_version + 1,
        )

    def cancel(self, *, at: datetime, release_reservation: bool) -> ProviderOperation:
        if self.status.is_terminal:
            raise ValueError("Terminal ProviderOperation cannot be cancelled")
        return replace(
            self,
            status=ProviderOperationStatus.CANCELLED,
            settlement_state=(
                SettlementState.RELEASED if release_reservation else SettlementState.SETTLED
            ),
            failure_category=ProviderFailureCategory.CANCELLED,
            updated_at=at,
            finished_at=at,
            row_version=self.row_version + 1,
        )


@dataclass(frozen=True, slots=True)
class ProviderVersion(SerializableContract):
    provider: str
    adapter_version: str
    model_or_endpoint: str

    def __post_init__(self) -> None:
        require_non_empty(self.provider, "ProviderVersion.provider")
        require_non_empty(self.adapter_version, "ProviderVersion.adapter_version")
        require_non_empty(self.model_or_endpoint, "ProviderVersion.model_or_endpoint")


@dataclass(frozen=True, slots=True)
class ProvenanceManifest(SerializableContract):
    project_id: str
    workflow_run_id: str
    workflow_id: str
    workflow_version: str
    workflow_hash: str
    skill_versions: Mapping[str, str]
    prompt_versions: Mapping[str, str]
    provider_versions: tuple[ProviderVersion, ...]
    papers: tuple[PaperRecord, ...]
    source_contents: tuple[SourceContent, ...]
    ranked_papers: tuple[RankedPaper, ...]
    citations: tuple[CitationReference, ...]
    evidence_units: tuple[EvidenceUnit, ...]
    grounded_claims: tuple[GroundedClaim, ...]
    report: ResearchReport
    report_artifact_id: str
    provenance_artifact_id: str
    artifact_checksums: Mapping[str, str]
    provider_operations: tuple[ProviderOperation, ...] = ()
    schema_version: str = PROVENANCE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.project_id, "ProvenanceManifest.project_id"),
            (self.workflow_run_id, "ProvenanceManifest.workflow_run_id"),
            (self.workflow_id, "ProvenanceManifest.workflow_id"),
            (self.workflow_version, "ProvenanceManifest.workflow_version"),
            (self.report_artifact_id, "ProvenanceManifest.report_artifact_id"),
            (self.provenance_artifact_id, "ProvenanceManifest.provenance_artifact_id"),
        ):
            require_non_empty(value, name)
        require_sha256(self.workflow_hash, "ProvenanceManifest.workflow_hash")
        object.__setattr__(self, "skill_versions", freeze_json(self.skill_versions))
        object.__setattr__(self, "prompt_versions", freeze_json(self.prompt_versions))
        object.__setattr__(self, "provider_versions", tuple(self.provider_versions))
        object.__setattr__(self, "papers", tuple(self.papers))
        object.__setattr__(self, "source_contents", tuple(self.source_contents))
        object.__setattr__(self, "ranked_papers", tuple(self.ranked_papers))
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(self, "evidence_units", tuple(self.evidence_units))
        object.__setattr__(self, "grounded_claims", tuple(self.grounded_claims))
        checksums = freeze_json(self.artifact_checksums)
        for artifact_id, checksum in checksums.items():
            require_non_empty(artifact_id, "ProvenanceManifest artifact ID")
            require_sha256(checksum, "ProvenanceManifest artifact checksum")
        object.__setattr__(self, "artifact_checksums", checksums)
        object.__setattr__(self, "provider_operations", tuple(self.provider_operations))
