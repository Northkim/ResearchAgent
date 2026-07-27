"""Research schema and provenance contract tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from backend.research.contracts import (
    AccessLimitation,
    ClaimConfidence,
    ClaimKind,
    ContentType,
    EvidenceScope,
    GroundedClaim,
    ProviderOperation,
    ResearchQuery,
    SourceContent,
    normalize_doi,
)
from backend.research.services import ProvenanceValidator
from backend.research.tests.fixtures import FIXED_TIME, valid_manifest


def test_research_query_is_immutable_serializable_and_canonically_hashed() -> None:
    first = ResearchQuery(
        topic=" persistent research agents ",
        keywords=("agent memory", "recovery"),
        year_from=2020,
        year_to=2026,
        max_results=3,
    )
    second = replace(first, topic="persistent research agents")
    assert first.to_dict()["keywords"] == ["agent memory", "recovery"]
    assert first.canonical_hash() == second.canonical_hash()
    with pytest.raises(FrozenInstanceError):
        first.topic = "changed"  # type: ignore[misc]


def test_doi_normalization_and_abstract_full_text_distinction() -> None:
    assert normalize_doi("https://doi.org/10.5555/Synthetic.1") == "10.5555/synthetic.1"
    with pytest.raises(ValueError):
        normalize_doi("not-a-doi")
    with pytest.raises(ValueError):
        SourceContent(
            paper_id="paper-1",
            content_type=ContentType.ABSTRACT,
            abstract="Synthetic abstract.",
            full_text="This must not be accepted.",
            content_source="synthetic@1.0.0",
            source_url="https://example.invalid/source",
            retrieved_at=FIXED_TIME,
            content_hash="sha256:" + "0" * 64,
            access_limitation=AccessLimitation.ABSTRACT_ONLY,
        )


def test_valid_provenance_passes() -> None:
    result = ProvenanceValidator().validate(valid_manifest())
    assert result.publishable
    assert result.errors == ()


def test_duplicate_doi_and_unknown_report_citation_fail() -> None:
    manifest = valid_manifest()
    duplicated = replace(manifest.papers[1], doi=manifest.papers[0].doi)
    changed_report = replace(manifest.report, markdown="Unknown citation [P99].")
    result = ProvenanceValidator().validate(
        replace(
            manifest,
            papers=(manifest.papers[0], duplicated, manifest.papers[2]),
            report=changed_report,
        )
    )
    assert {issue.code for issue in result.errors} >= {
        "DUPLICATE_DOI",
        "UNKNOWN_REPORT_CITATION_LABEL",
    }


def test_citation_and_evidence_referencing_unknown_papers_fail() -> None:
    manifest = valid_manifest()
    unknown_citation = replace(manifest.citations[0], paper_id="missing-paper")
    unknown_evidence = replace(manifest.evidence_units[0], paper_id="missing-paper")
    changed_report = replace(
        manifest.report,
        references=(unknown_citation,) + manifest.report.references[1:],
    )
    result = ProvenanceValidator().validate(
        replace(
            manifest,
            citations=(unknown_citation,) + manifest.citations[1:],
            evidence_units=(unknown_evidence,) + manifest.evidence_units[1:],
            report=changed_report,
        )
    )

    assert {issue.code for issue in result.errors} >= {
        "UNKNOWN_CITATION_PAPER",
        "UNKNOWN_EVIDENCE_PAPER",
        "UNKNOWN_REPORT_REFERENCE_PAPER",
    }


def test_unsupported_claim_unknown_evidence_and_content_hash_mismatch_fail() -> None:
    manifest = valid_manifest()
    unsupported = GroundedClaim(
        claim_id="unsupported",
        claim_text="Unsupported substantive claim.",
        supporting_evidence_ids=(),
        confidence=ClaimConfidence.LOW,
        limitations=(),
        claim_kind=ClaimKind.INFERENCE,
        generation_model="synthetic-llm/v1",
        prompt_version="prompt/v1",
    )
    unknown = replace(
        manifest.grounded_claims[0],
        supporting_evidence_ids=("missing-evidence",),
    )
    mismatched_evidence = replace(
        manifest.evidence_units[0],
        source_content_hash="sha256:" + "f" * 64,
        content_scope=EvidenceScope.FULL_TEXT,
    )
    result = ProvenanceValidator().validate(
        replace(
            manifest,
            evidence_units=(mismatched_evidence,) + manifest.evidence_units[1:],
            grounded_claims=(unsupported, unknown),
        )
    )
    codes = {issue.code for issue in result.errors}
    assert "UNSUPPORTED_CLAIM" in codes
    assert "UNKNOWN_CLAIM_EVIDENCE" in codes
    assert "CONTENT_HASH_MISMATCH" in codes


def test_unsettled_provider_operation_blocks_publication() -> None:
    manifest = valid_manifest()
    settled = manifest.provider_operations[0]
    unsettled = ProviderOperation(
        id="operation-unsettled",
        project_id=settled.project_id,
        workflow_run_id=settled.workflow_run_id,
        logical_step_id=settled.logical_step_id,
        step_run_id=settled.step_run_id,
        provider_category=settled.provider_category,
        operation_kind=settled.operation_kind,
        provider_identity=settled.provider_identity,
        adapter_version=settled.adapter_version,
        model_or_endpoint=settled.model_or_endpoint,
        idempotency_key="unsettled-operation",
        request_fingerprint=settled.request_fingerprint,
        reservation=settled.reservation,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )
    result = ProvenanceValidator().validate(
        replace(manifest, provider_operations=(unsettled,))
    )
    assert not result.publishable
    assert "UNSETTLED_PROVIDER_OPERATION" in {issue.code for issue in result.errors}


def test_abstract_evidence_cannot_be_marked_as_full_text() -> None:
    manifest = valid_manifest()
    overstated = replace(
        manifest.evidence_units[0],
        content_scope=EvidenceScope.FULL_TEXT,
    )
    result = ProvenanceValidator().validate(
        replace(
            manifest,
            evidence_units=(overstated,) + manifest.evidence_units[1:],
        )
    )
    assert "SOURCE_SCOPE_MISMATCH" in {issue.code for issue in result.errors}


def test_report_and_provenance_artifacts_require_checksum_links() -> None:
    manifest = valid_manifest()
    result = ProvenanceValidator().validate(
        replace(
            manifest,
            artifact_checksums={manifest.report_artifact_id: "sha256:" + "1" * 64},
        )
    )
    assert "MISSING_ARTIFACT_CHECKSUM_LINK" in {
        issue.code for issue in result.errors
    }
