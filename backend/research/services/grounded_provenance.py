"""Fail-closed publication validation for grounded report v3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Mapping

from backend.research.contracts import (
    GroundedClaimCategory,
    GroundedClaimV2,
    GroundedEvidenceUnit,
    GroundedReportInput,
    GroundedResearchReport,
    PerPaperSummary,
    ProviderOperation,
    ProviderOperationStatus,
    SettlementState,
    SourceContent,
)


@dataclass(frozen=True, slots=True)
class GroundedProvenanceIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class GroundedProvenanceResult:
    publishable: bool
    issues: tuple[GroundedProvenanceIssue, ...]
    validator_version: str


class GroundedProvenanceValidator:
    VERSION = "grounded-provenance-validator/v1"

    def validate(
        self,
        *,
        report_input: GroundedReportInput,
        source_contents: Mapping[str, SourceContent],
        summaries: tuple[PerPaperSummary, ...],
        evidence: tuple[GroundedEvidenceUnit, ...],
        claims: tuple[GroundedClaimV2, ...],
        report: GroundedResearchReport,
        provider_operations: tuple[ProviderOperation, ...],
    ) -> GroundedProvenanceResult:
        issues: list[GroundedProvenanceIssue] = []
        paper_ids = report_input.ordered_paper_ids
        paper_set = set(paper_ids)
        source_ids = report_input.ordered_source_content_ids
        source_set = set(source_ids)
        summary_by_paper = {item.paper_id: item for item in summaries}
        evidence_by_id = {item.evidence_id: item for item in evidence}
        claim_by_id = {item.claim_id: item for item in claims}

        if tuple(summary_by_paper) != paper_ids:
            self._add(issues, "SUMMARY_ORDER_MISMATCH", "summaries", "Summary order/set changed")
        if set(source_contents) != source_set:
            self._add(issues, "SOURCE_SET_MISMATCH", "source_contents", "Source set changed")
        for source_id, source in source_contents.items():
            expected = report_input.source_content_checksums.get(source_id)
            if expected != source.content_hash:
                self._add(
                    issues,
                    "SOURCE_CHECKSUM_MISMATCH",
                    f"source_contents.{source_id}",
                    "SourceContent checksum changed",
                )
            if source.content_type.value != "abstract" or source.full_text is not None:
                self._add(
                    issues,
                    "NON_ABSTRACT_CONTENT",
                    f"source_contents.{source_id}",
                    "Only abstract content is permitted",
                )
        for summary in summaries:
            if summary.paper_id not in paper_set:
                self._add(issues, "UNKNOWN_SUMMARY_PAPER", summary.paper_id, "Unknown paper")
            if report_input.citation_label_mapping.get(summary.paper_id) != summary.citation_label:
                self._add(
                    issues,
                    "SUMMARY_CITATION_MISMATCH",
                    summary.paper_id,
                    "Summary citation differs from approved mapping",
                )
            if not summary.abstract_only:
                self._add(
                    issues,
                    "MISSING_ABSTRACT_DISCLOSURE",
                    summary.paper_id,
                    "Summary lacks abstract-only disclosure",
                )
        for item in evidence:
            if item.paper_id not in paper_set or item.source_content_id not in source_set:
                self._add(issues, "UNKNOWN_EVIDENCE_SOURCE", item.evidence_id, "Unknown source")
                continue
            source = source_contents[item.source_content_id]
            if item.source_content_checksum != source.content_hash:
                self._add(
                    issues,
                    "EVIDENCE_SOURCE_CHECKSUM_MISMATCH",
                    item.evidence_id,
                    "Evidence source checksum changed",
                )
            if source.abstract is None or item.bounded_private_span not in source.abstract:
                self._add(
                    issues,
                    "EVIDENCE_SPAN_MISMATCH",
                    item.evidence_id,
                    "Private span is not present in approved abstract",
                )
            for claim_id in item.supported_claim_ids:
                if claim_id not in claim_by_id:
                    self._add(
                        issues,
                        "UNKNOWN_SUPPORTED_CLAIM",
                        f"{item.evidence_id}.{claim_id}",
                        "Evidence links an unknown claim",
                    )
        for claim in claims:
            unknown_evidence = set(claim.supporting_evidence_ids) - set(evidence_by_id)
            unknown_papers = set(claim.supporting_paper_ids) - paper_set
            if unknown_evidence:
                self._add(
                    issues,
                    "UNSUPPORTED_CLAIM",
                    claim.claim_id,
                    "Claim references unknown evidence",
                )
            if unknown_papers:
                self._add(
                    issues,
                    "UNAPPROVED_CLAIM_PAPER",
                    claim.claim_id,
                    "Claim references an unapproved paper",
                )
            if claim.claim_category is GroundedClaimCategory.DISAGREEMENT:
                supported = {
                    evidence_by_id[item].paper_id
                    for item in claim.supporting_evidence_ids
                    if item in evidence_by_id
                }
                if len(supported) < 2:
                    self._add(
                        issues,
                        "DISAGREEMENT_MISSING_BOTH_SIDES",
                        claim.claim_id,
                        "Disagreement needs evidence from at least two papers",
                    )
            if claim.claim_category in {
                GroundedClaimCategory.RESEARCH_GAP,
                GroundedClaimCategory.SYSTEM_INFERENCE,
            } and not claim.inference_flag:
                self._add(
                    issues,
                    "UNMARKED_INFERENCE",
                    claim.claim_id,
                    "Inference is not explicitly marked",
                )
        if set(report.claim_ids) != set(claim_by_id):
            self._add(issues, "REPORT_CLAIM_SET_MISMATCH", "report.claim_ids", "Claim set changed")
        expected_labels = tuple(
            report_input.citation_label_mapping[paper_id] for paper_id in paper_ids
        )
        if report.citation_labels != expected_labels:
            self._add(
                issues,
                "REPORT_CITATION_ORDER_MISMATCH",
                "report.citation_labels",
                "Report citation order changed",
            )
        emitted_labels = set(re.findall(r"\[P[1-9]\d*\]", report.markdown))
        if not emitted_labels.issubset(set(expected_labels)):
            self._add(
                issues,
                "UNKNOWN_REPORT_CITATION",
                "report.markdown",
                "Report contains an unknown citation",
            )
        if "abstract" not in report.scope_disclosure.casefold():
            self._add(
                issues,
                "MISSING_ABSTRACT_DISCLOSURE",
                "report.scope_disclosure",
                "Report lacks abstract-only disclosure",
            )
        for operation in provider_operations:
            if (
                operation.status is not ProviderOperationStatus.SUCCEEDED
                or operation.settlement_state is not SettlementState.SETTLED
                or operation.actual_usage is None
            ):
                self._add(
                    issues,
                    "UNSETTLED_PROVIDER_OPERATION",
                    operation.id,
                    "Every generation operation must be settled with usage",
                )
        return GroundedProvenanceResult(
            publishable=not issues,
            issues=tuple(issues),
            validator_version=self.VERSION,
        )

    @staticmethod
    def _add(
        issues: list[GroundedProvenanceIssue],
        code: str,
        path: str,
        message: str,
    ) -> None:
        issues.append(GroundedProvenanceIssue(code, path, message))

