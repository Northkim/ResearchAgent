"""Pure, fail-closed provenance validation for research publication."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from backend.research.contracts import (
    ContentType,
    EvidenceScope,
    InclusionStatus,
    ProviderOperationStatus,
    ProvenanceManifest,
    SettlementState,
)


class ProvenanceIssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True, slots=True)
class ProvenanceIssue:
    code: str
    message: str
    path: str
    severity: ProvenanceIssueSeverity = ProvenanceIssueSeverity.ERROR


@dataclass(frozen=True, slots=True)
class ProvenanceValidationResult:
    issues: tuple[ProvenanceIssue, ...]
    validator_version: str = "provenance-validator/v1"

    @property
    def errors(self) -> tuple[ProvenanceIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity is ProvenanceIssueSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ProvenanceIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity is ProvenanceIssueSeverity.WARNING
        )

    @property
    def publishable(self) -> bool:
        return not self.errors

    @property
    def is_valid(self) -> bool:
        return self.publishable


class ProvenanceValidator:
    """Validate claim/evidence/paper/citation/artifact relationships."""

    VERSION = "provenance-validator/v1"
    MIN_ACCEPTED_PAPERS = 3
    _REPORT_LABEL = re.compile(r"\[P[1-9]\d*\]")

    def validate(self, manifest: ProvenanceManifest) -> ProvenanceValidationResult:
        issues: list[ProvenanceIssue] = []
        papers = {paper.paper_id: paper for paper in manifest.papers}
        selected_ids = {
            ranked.paper_id
            for ranked in manifest.ranked_papers
            if ranked.inclusion_status is InclusionStatus.SELECTED
        }
        citation_labels = {
            citation.report_citation_label: citation for citation in manifest.citations
        }
        evidence = {unit.evidence_id: unit for unit in manifest.evidence_units}
        claims = {claim.claim_id: claim for claim in manifest.grounded_claims}
        sources_by_paper: dict[str, list] = {}
        for source in manifest.source_contents:
            sources_by_paper.setdefault(source.paper_id, []).append(source)

        if len(selected_ids) < self.MIN_ACCEPTED_PAPERS:
            self._error(
                issues,
                "INSUFFICIENT_SELECTED_PAPERS",
                f"Publication requires at least {self.MIN_ACCEPTED_PAPERS} selected papers",
                "ranked_papers",
            )

        self._duplicates(
            issues,
            [paper.paper_id for paper in manifest.papers],
            "DUPLICATE_PAPER_ID",
            "papers",
        )
        self._duplicates(
            issues,
            [citation.citation_id for citation in manifest.citations],
            "DUPLICATE_CITATION_ID",
            "citations",
        )
        self._duplicates(
            issues,
            [citation.report_citation_label for citation in manifest.citations],
            "DUPLICATE_CITATION_LABEL",
            "citations",
        )
        self._duplicates(
            issues,
            [unit.evidence_id for unit in manifest.evidence_units],
            "DUPLICATE_EVIDENCE_ID",
            "evidence_units",
        )
        self._duplicates(
            issues,
            [claim.claim_id for claim in manifest.grounded_claims],
            "DUPLICATE_CLAIM_ID",
            "grounded_claims",
        )

        dois: dict[str, str] = {}
        for index, paper in enumerate(manifest.papers):
            if paper.doi is None:
                continue
            previous = dois.get(paper.doi)
            if previous is not None and previous != paper.paper_id:
                self._error(
                    issues,
                    "DUPLICATE_DOI",
                    f"DOI {paper.doi} resolves to multiple PaperRecords",
                    f"papers[{index}].doi",
                )
            dois[paper.doi] = paper.paper_id

        for index, citation in enumerate(manifest.citations):
            paper = papers.get(citation.paper_id)
            if paper is None:
                self._error(
                    issues,
                    "UNKNOWN_CITATION_PAPER",
                    f"Citation {citation.citation_id} references an unknown paper",
                    f"citations[{index}].paper_id",
                )
            elif citation.paper_id not in selected_ids:
                self._error(
                    issues,
                    "UNSELECTED_CITATION_PAPER",
                    f"Citation {citation.citation_id} references an unapproved paper",
                    f"citations[{index}].paper_id",
                )

        for index, unit in enumerate(manifest.evidence_units):
            if unit.paper_id not in papers:
                self._error(
                    issues,
                    "UNKNOWN_EVIDENCE_PAPER",
                    f"Evidence {unit.evidence_id} references an unknown paper",
                    f"evidence_units[{index}].paper_id",
                )
                continue
            sources = sources_by_paper.get(unit.paper_id, [])
            if not sources:
                self._error(
                    issues,
                    "MISSING_SOURCE_CONTENT",
                    f"Evidence {unit.evidence_id} has no SourceContent",
                    f"evidence_units[{index}].source_content_hash",
                )
                continue
            source = next(
                (
                    item
                    for item in sources
                    if item.content_hash == unit.source_content_hash
                ),
                None,
            )
            if source is None:
                self._error(
                    issues,
                    "CONTENT_HASH_MISMATCH",
                    f"Evidence {unit.evidence_id} does not match SourceContent",
                    f"evidence_units[{index}].source_content_hash",
                )
            elif (
                unit.content_scope is EvidenceScope.FULL_TEXT
                and source.content_type is not ContentType.FULL_TEXT
            ):
                self._error(
                    issues,
                    "SOURCE_SCOPE_MISMATCH",
                    f"Evidence {unit.evidence_id} claims full-text scope without full text",
                    f"evidence_units[{index}].content_scope",
                )
            for claim_id in unit.supported_claim_ids:
                if claim_id not in claims:
                    self._error(
                        issues,
                        "UNKNOWN_SUPPORTED_CLAIM",
                        f"Evidence {unit.evidence_id} names unknown claim {claim_id}",
                        f"evidence_units[{index}].supported_claim_ids",
                    )

        for index, claim in enumerate(manifest.grounded_claims):
            if claim.substantive and not claim.supporting_evidence_ids:
                self._error(
                    issues,
                    "UNSUPPORTED_CLAIM",
                    f"Claim {claim.claim_id} has no supporting evidence",
                    f"grounded_claims[{index}].supporting_evidence_ids",
                )
            for evidence_id in claim.supporting_evidence_ids:
                unit = evidence.get(evidence_id)
                if unit is None:
                    self._error(
                        issues,
                        "UNKNOWN_CLAIM_EVIDENCE",
                        f"Claim {claim.claim_id} references unknown evidence {evidence_id}",
                        f"grounded_claims[{index}].supporting_evidence_ids",
                    )
                elif claim.claim_id not in unit.supported_claim_ids:
                    self._error(
                        issues,
                        "EVIDENCE_LINK_MISMATCH",
                        f"Evidence {evidence_id} does not link back to claim {claim.claim_id}",
                        f"grounded_claims[{index}].supporting_evidence_ids",
                    )

        for paper_id, scope in manifest.report.source_scope_by_paper.items():
            sources = sources_by_paper.get(paper_id, [])
            if not sources:
                self._error(
                    issues,
                    "UNKNOWN_REPORT_SOURCE_SCOPE",
                    f"Report scope references unknown source paper {paper_id}",
                    "report.source_scope_by_paper",
                )
            elif scope == "full_text" and not any(
                source.content_type is ContentType.FULL_TEXT for source in sources
            ):
                self._error(
                    issues,
                    "REPORT_FULL_TEXT_MISSTATEMENT",
                    f"Report marks {paper_id} as full-text reviewed without full text",
                    "report.source_scope_by_paper",
                )

        report_reference_labels = {
            citation.report_citation_label for citation in manifest.report.references
        }
        if report_reference_labels != set(citation_labels):
            self._error(
                issues,
                "REPORT_REFERENCE_MISMATCH",
                "Report references and provenance citations do not contain the same labels",
                "report.references",
            )
        for index, report_reference in enumerate(manifest.report.references):
            canonical = citation_labels.get(report_reference.report_citation_label)
            if report_reference.paper_id not in papers:
                self._error(
                    issues,
                    "UNKNOWN_REPORT_REFERENCE_PAPER",
                    f"Report reference {report_reference.report_citation_label} "
                    "resolves to an unknown paper",
                    f"report.references[{index}].paper_id",
                )
            if canonical is not None and canonical != report_reference:
                self._error(
                    issues,
                    "REPORT_REFERENCE_CONTENT_MISMATCH",
                    f"Report reference {report_reference.report_citation_label} "
                    "differs from its provenance CitationReference",
                    f"report.references[{index}]",
                )
        for label in sorted(set(self._REPORT_LABEL.findall(manifest.report.markdown))):
            if label not in citation_labels:
                self._error(
                    issues,
                    "UNKNOWN_REPORT_CITATION_LABEL",
                    f"Report contains unknown citation label {label}",
                    "report.markdown",
                )

        self._validate_versions(manifest, issues)
        self._validate_artifact_links(manifest, issues)
        self._validate_provider_operations(manifest, issues)
        return ProvenanceValidationResult(tuple(issues), self.VERSION)

    @staticmethod
    def _validate_versions(
        manifest: ProvenanceManifest,
        issues: list[ProvenanceIssue],
    ) -> None:
        if not manifest.skill_versions:
            ProvenanceValidator._error(
                issues,
                "MISSING_SKILL_VERSIONS",
                "Provenance must record Skill versions",
                "skill_versions",
            )
        if not manifest.prompt_versions:
            ProvenanceValidator._error(
                issues,
                "MISSING_PROMPT_VERSIONS",
                "Provenance must record prompt versions",
                "prompt_versions",
            )
        if not manifest.provider_versions:
            ProvenanceValidator._error(
                issues,
                "MISSING_PROVIDER_VERSIONS",
                "Provenance must record provider/model/adapter versions",
                "provider_versions",
            )
        for index, claim in enumerate(manifest.grounded_claims):
            if not claim.generation_model or not claim.prompt_version:
                ProvenanceValidator._error(
                    issues,
                    "MISSING_CLAIM_GENERATION_VERSION",
                    f"Claim {claim.claim_id} lacks model or prompt version",
                    f"grounded_claims[{index}]",
                )

    @staticmethod
    def _validate_artifact_links(
        manifest: ProvenanceManifest,
        issues: list[ProvenanceIssue],
    ) -> None:
        for artifact_id, path in (
            (manifest.report_artifact_id, "report_artifact_id"),
            (manifest.provenance_artifact_id, "provenance_artifact_id"),
        ):
            if artifact_id not in manifest.artifact_checksums:
                ProvenanceValidator._error(
                    issues,
                    "MISSING_ARTIFACT_CHECKSUM_LINK",
                    f"Artifact {artifact_id} has no checksum link",
                    path,
                )
        if manifest.report.provenance_artifact_id != manifest.provenance_artifact_id:
            ProvenanceValidator._error(
                issues,
                "PROVENANCE_ARTIFACT_LINK_MISMATCH",
                "Report points to a different provenance artifact",
                "report.provenance_artifact_id",
            )

    @staticmethod
    def _validate_provider_operations(
        manifest: ProvenanceManifest,
        issues: list[ProvenanceIssue],
    ) -> None:
        for index, operation in enumerate(manifest.provider_operations):
            if operation.status in {
                ProviderOperationStatus.RESERVED,
                ProviderOperationStatus.RUNNING,
            } or operation.settlement_state is SettlementState.UNSETTLED:
                ProvenanceValidator._error(
                    issues,
                    "UNSETTLED_PROVIDER_OPERATION",
                    f"Provider operation {operation.id} is not settled",
                    f"provider_operations[{index}]",
                )

    @staticmethod
    def _duplicates(
        issues: list[ProvenanceIssue],
        values: list[str],
        code: str,
        path: str,
    ) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for value in values:
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        for value in sorted(duplicates):
            ProvenanceValidator._error(
                issues,
                code,
                f"Duplicate value {value}",
                path,
            )

    @staticmethod
    def _error(
        issues: list[ProvenanceIssue],
        code: str,
        message: str,
        path: str,
    ) -> None:
        issues.append(ProvenanceIssue(code=code, message=message, path=path))
