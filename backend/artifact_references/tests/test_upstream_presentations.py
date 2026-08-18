from __future__ import annotations

import pytest

from backend.application.errors import ApplicationConflictError, ApplicationValidationError
from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.artifact_references.service import ArtifactReferenceService
from backend.artifact_references.upstream_presentations import (
    MANUSCRIPT_PRESENTATION_SCHEMA,
    PAPER_LIBRARY_PRESENTATION_SCHEMA,
    REVIEW_PRESENTATION_SCHEMA,
    RESEARCH_IDEA_PRESENTATION_SCHEMA,
    UpstreamPresentationError,
    validate_manuscript_presentation,
    validate_paper_library_presentation,
    validate_review_presentation,
    validate_research_idea_presentation,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.workflow_packages.serialization import canonical_hash

from .test_service import (
    ARTIFACT_ID,
    HASH_A,
    HASH_B,
    NOW,
    PRODUCER_CAPSULE,
    PRODUCER_ID,
    PROJECT_ID,
    _seed,
)


def _paper_payload(**changes):
    value = {
        "schema": PAPER_LIBRARY_PRESENTATION_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "artifact_checksum": HASH_B,
        "selected_count": 2,
        "selection_status": "SELECTED",
        "evidence_basis": ["METADATA_AND_ABSTRACT", "METADATA_ONLY"],
        "limitations": ["Full text is not represented."],
        "papers": [
            {
                "title": "Bounded non-ML study",
                "authors": ["Fictional Author"],
                "year": 2025,
                "identifier_kind": "DOI",
                "identifier": "10.1000/fictional.1",
                "why_selected": "Directly addresses the bounded question.",
                "evidence_availability": "METADATA_AND_ABSTRACT",
                "limitation": "Abstract only; full text is not represented.",
            },
            {
                "title": "Categorical field observation",
                "authors": ["Second Fictional Author"],
                "year": None,
                "identifier_kind": "PROVIDER_ID",
                "identifier": "provider-record-2",
                "why_selected": "Supplies a contrasting observation.",
                "evidence_availability": "METADATA_ONLY",
                "limitation": "Metadata only.",
            },
        ],
        "papers_truncated": False,
    }
    value.update(changes)
    return {**value, "presentation_checksum": canonical_hash(value)}


def _idea_payload(**changes):
    value = {
        "schema": RESEARCH_IDEA_PRESENTATION_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "artifact_checksum": HASH_B,
        "title": "Compare two archival classification practices",
        "summary": "Investigate how the practices shape categorical outcomes.",
        "research_question": "Where do the classifications diverge?",
        "observed_gap": "The selected abstracts do not compare them directly.",
        "proposed_direction": "Use a bounded comparative protocol.",
        "assumptions": ["The selected metadata is internally consistent."],
        "risks": ["Available literature is abstract-limited."],
        "validation_needed": ["Confirm access to the archival records."],
        "literature_basis_count": 2,
        "source_literature_artifact": {
            "artifact_id": "artifact-" + "5" * 32,
            "artifact_type": "selected-paper-library/v1",
            "artifact_checksum": HASH_A,
        },
    }
    value.update(changes)
    return {**value, "presentation_checksum": canonical_hash(value)}


def _service_for(artifact_type: str) -> tuple[ArtifactReferenceService, InMemoryDatabase]:
    database = InMemoryDatabase()
    uow = _seed(database)
    uow.artifact_references.add_artifact(ArtifactReference(
        artifact_id=ARTIFACT_ID,
        project_id=PROJECT_ID,
        producer_workflow_instance_id=PRODUCER_ID,
        producer_progress_receipt_id="receipt-upstream",
        producer_progress_report_id="report-upstream",
        producer_execution_round=1,
        producer_capsule_id=PRODUCER_CAPSULE,
        producer_capsule_version="1.0.0",
        artifact_type=artifact_type,
        artifact_schema_version=artifact_type,
        media_type="application/json",
        state=ArtifactState.LOCAL_AVAILABLE,
        relative_path="outputs/final.json",
        content_checksum=HASH_B,
        size_bytes=1024,
        cloud_metadata_available=True,
        produced_at=NOW,
        retired_at=None,
        created_at=NOW,
        updated_at=NOW,
    ))
    uow.commit()
    return ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    ), database


def _manuscript_payload(mode="INITIAL", **changes):
    value = {
        "schema": MANUSCRIPT_PRESENTATION_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "artifact_checksum": HASH_B,
        "mode": mode,
        "title": "A bounded manuscript",
        "summary": "The manuscript reports exact bounded evidence and its limitations.",
        "sections": ["Introduction", "Results", "Limitations"],
        "evidence_coverage": {
            "claim_count": 2, "supported_claim_count": 1,
            "planned_claim_count": 0, "unavailable_claim_count": 1,
        },
        "result_availability": "AVAILABLE",
        "limitations": ["The evidence supports only a bounded observation."],
        "owner_review_status": "APPROVED",
        "source_artifacts": [{
            "role": "research_idea", "artifact_id": "artifact-" + "1" * 32,
            "artifact_type": "selected-research-idea/v1", "artifact_checksum": HASH_A,
        }],
        "parent_manuscript": None,
        "causal_review": None,
        "changed_sections": [],
        "change_summary": None,
        "issue_dispositions": [],
        "unresolved_issue_count": 0,
    }
    if mode == "REVISION":
        value.update({
            "parent_manuscript": {"artifact_id": "artifact-" + "2" * 32, "artifact_type": "manuscript-draft/v4", "artifact_checksum": HASH_A},
            "causal_review": {"artifact_id": "artifact-" + "3" * 32, "artifact_type": "review-report/v3", "artifact_checksum": HASH_A},
            "changed_sections": ["Results"], "change_summary": "One Review issue addressed.",
            "issue_dispositions": [{"issue_id": "issue-1", "disposition": "ADDRESSED"}],
        })
    value.update(changes)
    return {**value, "presentation_checksum": canonical_hash(value)}


def _review_payload(**changes):
    value = {
        "schema": REVIEW_PRESENTATION_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "artifact_checksum": HASH_B,
        "reviewed_manuscript": {"artifact_id": "artifact-" + "2" * 32, "artifact_type": "manuscript-draft/v4", "artifact_checksum": HASH_A},
        "scope": "Exact manuscript and selected supporting evidence.",
        "status": "REVISION_REQUIRED",
        "summary": "One bounded wording revision is required.",
        "issues": [{"issue_id": "issue-1", "severity": "MINOR", "blocking": True, "anchor": "Results", "rationale": "The boundary needs clearer wording.", "requested_revision": "State the limitation explicitly."}],
        "requested_revisions": ["State the limitation explicitly."],
        "unresolved_evidence_gaps": ["No full-text evidence is available."],
        "reproducibility_findings": [],
        "limitations": ["Review used exact supplied evidence only."],
        "owner_review_status": "APPROVED",
    }
    value.update(changes)
    return {**value, "presentation_checksum": canonical_hash(value)}


def test_upstream_contracts_preserve_doi_stable_identity_and_generic_idea() -> None:
    papers = validate_paper_library_presentation(_paper_payload())
    idea = validate_research_idea_presentation(_idea_payload())
    assert [item["identifier_kind"] for item in papers["papers"]] == ["DOI", "PROVIDER_ID"]
    assert idea["research_question"].startswith("Where")
    assert "dataset" not in idea


def test_downstream_contracts_preserve_small_initial_revision_and_review_previews() -> None:
    initial = validate_manuscript_presentation(_manuscript_payload())
    revision = validate_manuscript_presentation(_manuscript_payload("REVISION"))
    review = validate_review_presentation(_review_payload())
    assert initial["mode"] == "INITIAL" and initial["parent_manuscript"] is None
    assert revision["issue_dispositions"] == [{"issue_id": "issue-1", "disposition": "ADDRESSED"}]
    assert review["status"] == "REVISION_REQUIRED" and review["issues"][0]["severity"] == "MINOR"


def test_downstream_contracts_reject_full_private_or_ambiguous_content() -> None:
    with pytest.raises(UpstreamPresentationError):
        validate_manuscript_presentation(_manuscript_payload(summary="/Users/owner/private.md"))
    with pytest.raises(UpstreamPresentationError):
        validate_review_presentation(_review_payload(summary="x" * 2_001))
    with pytest.raises(UpstreamPresentationError):
        validate_manuscript_presentation(_manuscript_payload(parent_manuscript={"artifact_id": "artifact-" + "2" * 32, "artifact_type": "manuscript-draft/v4", "artifact_checksum": HASH_A}))


@pytest.mark.parametrize("unsafe", ("password=fictional", "/Users/owner/private.json", "<script>alert(1)</script>", "https://credential@example.test"))
def test_upstream_contracts_reject_private_unsafe_or_stale_content(unsafe: str) -> None:
    changed = _idea_payload(summary=unsafe)
    with pytest.raises(UpstreamPresentationError):
        validate_research_idea_presentation(changed)
    oversized = _paper_payload(limitations=["x" * 501])
    with pytest.raises(UpstreamPresentationError):
        validate_paper_library_presentation(oversized)


def test_service_registry_is_exact_immutable_and_unknown_pairs_fail_closed() -> None:
    service, database = _service_for("selected-paper-library/v1")
    payload = _paper_payload()
    first = service.report_presentation(
        project_id=PROJECT_ID, artifact_id=ARTIFACT_ID, payload=payload
    )
    replay = ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    ).report_presentation(project_id=PROJECT_ID, artifact_id=ARTIFACT_ID, payload=payload)
    assert replay == first

    wrong_schema = _idea_payload()
    with pytest.raises(ApplicationValidationError):
        service.report_presentation(
            project_id=PROJECT_ID, artifact_id=ARTIFACT_ID, payload=wrong_schema
        )

    stale = _paper_payload(artifact_checksum=HASH_A)
    with pytest.raises(ApplicationConflictError, match="exact current Artifact"):
        service.report_presentation(
            project_id=PROJECT_ID, artifact_id=ARTIFACT_ID, payload=stale
        )
    validate_manuscript_presentation,
    validate_review_presentation,
