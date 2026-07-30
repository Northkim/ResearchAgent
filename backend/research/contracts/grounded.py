"""Immutable contracts for the Guided Literature Review v3 grounded path.

The v3 records are additive.  The v2 contracts in ``models.py`` remain frozen
because existing report/provenance bytes depend on their exact serialization.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum
from typing import Any

from ._serialization import (
    SerializableContract,
    canonical_hash,
    freeze_json,
    require_aware,
    require_non_empty,
    to_json_value,
)
from .models import GroundedClaimCategory, require_sha256

GROUNDING_SCOPE = "abstract_only"
GROUNDING_DISCLOSURE = (
    "This report is based only on approved paper metadata and abstracts. "
    "It is not a full-text or systematic review, expert peer review, or a "
    "determination of scientific correctness. Check claims against the originals."
)
_LABEL = re.compile(r"^\[P([1-5])\]$")


class InformationStatus(str, Enum):
    EXPLICIT = "EXPLICIT"
    UNAVAILABLE = "UNAVAILABLE"
    INFERRED = "INFERRED"


def declared_checksum(value: SerializableContract, field_name: str = "checksum") -> str:
    payload = {
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value)
        if item.name != field_name
    }
    return canonical_hash(payload)


def checksum_for_payload(payload: Mapping[str, Any], field_name: str = "checksum") -> str:
    return canonical_hash({key: value for key, value in payload.items() if key != field_name})


def _verify_declared(value: SerializableContract, field_name: str = "checksum") -> None:
    actual = getattr(value, field_name)
    require_sha256(actual, f"{type(value).__name__}.{field_name}")
    if actual != declared_checksum(value, field_name):
        raise ValueError(f"{type(value).__name__}.{field_name} does not match content")


def _unique_strings(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if any(not value for value in result):
        raise ValueError(f"{name} cannot contain empty values")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must be unique")
    return result


@dataclass(frozen=True, slots=True)
class GroundedReportInput(SerializableContract):
    project_id: str
    workflow_run_id: str
    workflow_id: str
    workflow_version: str
    selected_paper_artifact_id: str
    selected_paper_artifact_checksum: str
    approval_request_id: str
    approval_fingerprint: str
    query_hash: str
    ordered_paper_ids: tuple[str, ...]
    ordered_source_content_ids: tuple[str, ...]
    source_content_checksums: Mapping[str, str]
    citation_label_mapping: Mapping[str, str]
    content_scope: str
    prompt_policy: Mapping[str, Any]
    provider_policy: Mapping[str, Any]
    budget_policy: Mapping[str, Any]
    schema_version: str
    input_checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.project_id, "project_id"),
            (self.workflow_run_id, "workflow_run_id"),
            (self.workflow_id, "workflow_id"),
            (self.workflow_version, "workflow_version"),
            (self.selected_paper_artifact_id, "selected_paper_artifact_id"),
            (self.approval_request_id, "approval_request_id"),
        ):
            require_non_empty(value, f"GroundedReportInput.{name}")
        for value, name in (
            (self.selected_paper_artifact_checksum, "selected_paper_artifact_checksum"),
            (self.approval_fingerprint, "approval_fingerprint"),
            (self.query_hash, "query_hash"),
        ):
            require_sha256(value, f"GroundedReportInput.{name}")
        papers = _unique_strings(self.ordered_paper_ids, "ordered_paper_ids")
        sources = _unique_strings(
            self.ordered_source_content_ids, "ordered_source_content_ids"
        )
        if not 3 <= len(papers) <= 5:
            raise ValueError("GroundedReportInput requires exactly 3 to 5 papers")
        if len(sources) != len(papers):
            raise ValueError("GroundedReportInput requires one SourceContent per paper")
        checksums = freeze_json(self.source_content_checksums)
        labels = freeze_json(self.citation_label_mapping)
        if set(checksums) != set(sources):
            raise ValueError("SourceContent checksum keys must match ordered IDs")
        if set(labels) != set(papers):
            raise ValueError("Citation mapping keys must match ordered paper IDs")
        expected_labels = [f"[P{index}]" for index in range(1, len(papers) + 1)]
        if [labels[paper_id] for paper_id in papers] != expected_labels:
            raise ValueError("Citation labels must follow approved paper order")
        for checksum in checksums.values():
            require_sha256(checksum, "GroundedReportInput SourceContent checksum")
        if self.content_scope != GROUNDING_SCOPE:
            raise ValueError("GroundedReportInput permits abstract_only content only")
        object.__setattr__(self, "ordered_paper_ids", papers)
        object.__setattr__(self, "ordered_source_content_ids", sources)
        object.__setattr__(self, "source_content_checksums", checksums)
        object.__setattr__(self, "citation_label_mapping", labels)
        object.__setattr__(self, "prompt_policy", freeze_json(self.prompt_policy))
        object.__setattr__(self, "provider_policy", freeze_json(self.provider_policy))
        object.__setattr__(self, "budget_policy", freeze_json(self.budget_policy))
        _verify_declared(self, "input_checksum")


@dataclass(frozen=True, slots=True)
class GroundedCitationReference(SerializableContract):
    citation_label: str
    paper_id: str
    title: str
    year: int | None
    venue: str | None
    doi: str | None
    source_url: str | None
    source_checksum: str
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        if not _LABEL.fullmatch(self.citation_label):
            raise ValueError("Citation label must be [P1] through [P5]")
        require_non_empty(self.paper_id, "GroundedCitationReference.paper_id")
        require_non_empty(self.title, "GroundedCitationReference.title")
        if self.source_url is not None and not self.source_url.startswith("https://"):
            raise ValueError("Citation source URL must use HTTPS")
        require_sha256(self.source_checksum, "GroundedCitationReference.source_checksum")
        _verify_declared(self)


@dataclass(frozen=True, slots=True)
class GroundedEvidenceUnit(SerializableContract):
    evidence_id: str
    paper_id: str
    source_content_id: str
    source_content_checksum: str
    source_field: str
    source_locator: Mapping[str, Any]
    bounded_private_span: str
    paraphrased_evidence: str
    span_checksum: str
    evidence_type: str
    content_scope: str
    supported_claim_ids: tuple[str, ...]
    extraction_prompt_version: str
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.evidence_id, "evidence_id"),
            (self.paper_id, "paper_id"),
            (self.source_content_id, "source_content_id"),
            (self.paraphrased_evidence, "paraphrased_evidence"),
            (self.evidence_type, "evidence_type"),
            (self.extraction_prompt_version, "extraction_prompt_version"),
        ):
            require_non_empty(value, f"GroundedEvidenceUnit.{name}")
        if self.source_field != "abstract":
            raise ValueError("V3 EvidenceUnit source_field must be abstract")
        if self.content_scope != GROUNDING_SCOPE:
            raise ValueError("V3 EvidenceUnit content_scope must be abstract_only")
        if not self.bounded_private_span or len(self.bounded_private_span) > 200:
            raise ValueError("Private evidence spans must contain 1 to 200 characters")
        require_sha256(
            self.source_content_checksum,
            "GroundedEvidenceUnit.source_content_checksum",
        )
        require_sha256(self.span_checksum, "GroundedEvidenceUnit.span_checksum")
        if canonical_hash(self.bounded_private_span) != self.span_checksum:
            raise ValueError("GroundedEvidenceUnit.span_checksum does not match span")
        object.__setattr__(self, "source_locator", freeze_json(self.source_locator))
        object.__setattr__(
            self,
            "supported_claim_ids",
            _unique_strings(self.supported_claim_ids, "supported_claim_ids"),
        )
        _verify_declared(self)


@dataclass(frozen=True, slots=True)
class PerPaperSummary(SerializableContract):
    paper_id: str
    citation_label: str
    objective: str
    methodology: Mapping[str, Any]
    key_findings: tuple[str, ...]
    contribution: str
    stated_limitations: Mapping[str, Any]
    relevance_to_topic: str
    uncertainties: tuple[str, ...]
    missing_information: tuple[str, ...]
    abstract_only: bool
    evidence_unit_ids: tuple[str, ...]
    provider_identity: str
    model_identity: str
    prompt_version: str
    generated_at: datetime
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.paper_id, "paper_id"),
            (self.objective, "objective"),
            (self.contribution, "contribution"),
            (self.relevance_to_topic, "relevance_to_topic"),
            (self.provider_identity, "provider_identity"),
            (self.model_identity, "model_identity"),
            (self.prompt_version, "prompt_version"),
        ):
            require_non_empty(value, f"PerPaperSummary.{name}")
        if not _LABEL.fullmatch(self.citation_label):
            raise ValueError("PerPaperSummary citation label is invalid")
        if not self.abstract_only:
            raise ValueError("PerPaperSummary must disclose abstract-only scope")
        require_aware(self.generated_at, "PerPaperSummary.generated_at")
        object.__setattr__(self, "methodology", freeze_json(self.methodology))
        object.__setattr__(
            self, "stated_limitations", freeze_json(self.stated_limitations)
        )
        object.__setattr__(
            self, "key_findings", _unique_strings(self.key_findings, "key_findings")
        )
        object.__setattr__(
            self, "uncertainties", _unique_strings(self.uncertainties, "uncertainties")
        )
        object.__setattr__(
            self,
            "missing_information",
            _unique_strings(self.missing_information, "missing_information"),
        )
        object.__setattr__(
            self,
            "evidence_unit_ids",
            _unique_strings(self.evidence_unit_ids, "evidence_unit_ids"),
        )
        _verify_declared(self)


@dataclass(frozen=True, slots=True)
class GroundedClaimV2(SerializableContract):
    claim_id: str
    claim_text: str
    claim_category: GroundedClaimCategory
    supporting_evidence_ids: tuple[str, ...]
    supporting_paper_ids: tuple[str, ...]
    confidence: str
    inference_flag: bool
    limitations: tuple[str, ...]
    generation_prompt_version: str
    provider_identity: str
    model_identity: str
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.claim_id, "claim_id"),
            (self.claim_text, "claim_text"),
            (self.confidence, "confidence"),
            (self.generation_prompt_version, "generation_prompt_version"),
            (self.provider_identity, "provider_identity"),
            (self.model_identity, "model_identity"),
        ):
            require_non_empty(value, f"GroundedClaimV2.{name}")
        evidence = _unique_strings(
            self.supporting_evidence_ids, "supporting_evidence_ids"
        )
        papers = _unique_strings(self.supporting_paper_ids, "supporting_paper_ids")
        minimum = (
            2
            if self.claim_category
            in {
                GroundedClaimCategory.CROSS_SOURCE_THEME,
                GroundedClaimCategory.AGREEMENT,
                GroundedClaimCategory.DISAGREEMENT,
            }
            else 1
        )
        if len(papers) < minimum:
            raise ValueError(
                f"{self.claim_category.value} requires {minimum} supporting papers"
            )
        if self.claim_category in {
            GroundedClaimCategory.RESEARCH_GAP,
            GroundedClaimCategory.SYSTEM_INFERENCE,
        } and not self.inference_flag:
            raise ValueError(f"{self.claim_category.value} must be marked as inference")
        object.__setattr__(self, "supporting_evidence_ids", evidence)
        object.__setattr__(self, "supporting_paper_ids", papers)
        object.__setattr__(
            self, "limitations", _unique_strings(self.limitations, "limitations")
        )
        _verify_declared(self)


@dataclass(frozen=True, slots=True)
class GroundedResearchReport(SerializableContract):
    report_id: str
    title: str
    scope_disclosure: str
    methodology: str
    executive_summary: str
    selected_papers: tuple[Mapping[str, Any], ...]
    per_paper_sections: tuple[Mapping[str, Any], ...]
    cross_paper_themes: tuple[Mapping[str, Any], ...]
    agreements: tuple[Mapping[str, Any], ...]
    disagreements: tuple[Mapping[str, Any], ...]
    limitations: tuple[str, ...]
    possible_research_gaps: tuple[Mapping[str, Any], ...]
    conclusions: str
    references: tuple[GroundedCitationReference, ...]
    provenance_note: str
    claim_ids: tuple[str, ...]
    citation_labels: tuple[str, ...]
    workflow_version: str
    provider_identity: str
    model_identity: str
    prompt_versions: Mapping[str, str]
    generated_at: datetime
    markdown: str
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.report_id, "report_id"),
            (self.title, "title"),
            (self.scope_disclosure, "scope_disclosure"),
            (self.methodology, "methodology"),
            (self.executive_summary, "executive_summary"),
            (self.conclusions, "conclusions"),
            (self.provenance_note, "provenance_note"),
            (self.workflow_version, "workflow_version"),
            (self.provider_identity, "provider_identity"),
            (self.model_identity, "model_identity"),
            (self.markdown, "markdown"),
        ):
            require_non_empty(value, f"GroundedResearchReport.{name}")
        if "abstract" not in self.scope_disclosure.casefold():
            raise ValueError("GroundedResearchReport requires an abstract-only disclosure")
        prohibited = ("systematic review", "full-paper analysis", "expert peer review")
        lowered = self.markdown.casefold()
        if any(f"this is a {phrase}" in lowered for phrase in prohibited):
            raise ValueError("GroundedResearchReport contains a prohibited scope claim")
        require_aware(self.generated_at, "GroundedResearchReport.generated_at")
        object.__setattr__(
            self,
            "selected_papers",
            tuple(freeze_json(value) for value in self.selected_papers),
        )
        object.__setattr__(
            self,
            "per_paper_sections",
            tuple(freeze_json(value) for value in self.per_paper_sections),
        )
        for name in (
            "cross_paper_themes",
            "agreements",
            "disagreements",
            "possible_research_gaps",
        ):
            object.__setattr__(
                self,
                name,
                tuple(freeze_json(value) for value in getattr(self, name)),
            )
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(
            self, "claim_ids", _unique_strings(self.claim_ids, "claim_ids")
        )
        labels = _unique_strings(self.citation_labels, "citation_labels")
        if any(not _LABEL.fullmatch(label) for label in labels):
            raise ValueError("GroundedResearchReport has an invalid citation label")
        object.__setattr__(self, "citation_labels", labels)
        object.__setattr__(
            self, "limitations", _unique_strings(self.limitations, "limitations")
        )
        object.__setattr__(self, "prompt_versions", freeze_json(self.prompt_versions))
        _verify_declared(self)


@dataclass(frozen=True, slots=True)
class LiteratureCorpus(SerializableContract):
    corpus_id: str
    source_workflow_run_id: str
    source_report_id: str
    source_report_checksum: str
    topic: str
    approved_papers: tuple[Mapping[str, Any], ...]
    summaries: tuple[Mapping[str, Any], ...]
    evidence: tuple[Mapping[str, Any], ...]
    claims: tuple[Mapping[str, Any], ...]
    citations: tuple[Mapping[str, Any], ...]
    inference_disclosures: tuple[str, ...]
    content_scope: str
    downstream_use_policy: Mapping[str, Any]
    generated_at: datetime
    schema_version: str
    checksum: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.corpus_id, "corpus_id"),
            (self.source_workflow_run_id, "source_workflow_run_id"),
            (self.source_report_id, "source_report_id"),
            (self.topic, "topic"),
        ):
            require_non_empty(value, f"LiteratureCorpus.{name}")
        require_sha256(self.source_report_checksum, "LiteratureCorpus.source_report_checksum")
        if self.content_scope != GROUNDING_SCOPE:
            raise ValueError("LiteratureCorpus must remain abstract_only")
        require_aware(self.generated_at, "LiteratureCorpus.generated_at")
        for name in ("approved_papers", "summaries", "evidence", "claims", "citations"):
            object.__setattr__(
                self,
                name,
                tuple(freeze_json(value) for value in getattr(self, name)),
            )
        object.__setattr__(
            self,
            "inference_disclosures",
            _unique_strings(self.inference_disclosures, "inference_disclosures"),
        )
        object.__setattr__(
            self, "downstream_use_policy", freeze_json(self.downstream_use_policy)
        )
        _verify_declared(self)

