from __future__ import annotations

from copy import deepcopy
import json
import runpy

import pytest

from backend.artifact_references.forward_downstream_contracts import (
    ForwardDownstreamContractError,
)
from backend.artifact_references.revision_contract_compatibility import (
    validate_manuscript_draft_v5,
)
from backend.workflow_packages.revision_optional_support_publication import (
    build_writing_revision_v0_9_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes


def _ref(kind: str, letter: str) -> dict[str, str]:
    return {
        "artifact_id": "artifact-" + letter * 32,
        "artifact_type": kind,
        "sha256": "sha256:" + letter * 64,
    }


def _evidence(ref: dict[str, str]) -> dict[str, object]:
    return {
        **ref,
        "evidence_item": "selected_idea.proposed_direction",
        "location": "selected_idea.proposed_direction",
        "availability": "AVAILABLE",
        "limitation": None,
    }


def _manuscript() -> tuple[dict, dict[str, object], dict[str, str]]:
    idea = _ref("selected-research-idea/v1", "a")
    literature = _ref("selected-paper-library/v1", "b")
    sources = {
        "research_idea": idea,
        "literature_library": literature,
        "experiment_record": None,
    }
    brief = {"document_type": "article"}
    evidence_map: list[object] = []
    outline = {"sha256": canonical_hash([]), "value": []}
    outline_payload = {
        "outline_sha256": outline["sha256"],
        "brief_sha256": canonical_hash(brief),
        "evidence_map_sha256": canonical_hash(evidence_map),
        "source_artifacts_sha256": canonical_hash(sources),
        "approved_at": "2026-08-19T00:00:00Z",
        "decision": "APPROVED",
    }
    claims = [{
        "claim_id": "claim-proposal-1",
        "claim_type": "PROPOSAL",
        "section": "Method",
        "claim_text": "The selected direction proposes a bounded study.",
        "support_status": "PLANNED",
        "evidence_refs": [_evidence(idea)],
        "citation_ids": [],
        "limitations": [],
        "evidence_qualification": "PROPOSED",
        "claim_boundary_refs": [],
    }]
    content = "# Bounded manuscript\n\nThe selected direction proposes a bounded study."
    owner_payload = {
        "draft_sha256": canonical_hash({
            "title": "Bounded manuscript",
            "content_markdown": content,
            "claims": claims,
            "citations": [],
        }),
        "reviewed_at": "2026-08-19T00:01:00Z",
        "decision": "APPROVED",
    }
    manuscript = {
        "schema": "manuscript-draft/v4",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "1" * 32},
        "source_artifacts": sources,
        "writing_brief": brief,
        "evidence_map": evidence_map,
        "approved_outline": outline,
        "outline_approval": {"sha256": canonical_hash(outline_payload), **outline_payload},
        "title": "Bounded manuscript",
        "content_markdown": content,
        "claims": claims,
        "citations": [],
        "experiment_evidence_available": False,
        "experiment_evidence": None,
        "unsupported_areas": ["Results"],
        "limitations": ["No Experiment evidence is available."],
        "owner_review": {"sha256": canonical_hash(owner_payload), **owner_payload},
    }
    return manuscript, sources, _ref("manuscript-draft/v4", "c")


def _review(
    manuscript_ref: dict[str, str],
    sources: dict[str, object],
    *,
    include_idea: bool,
) -> tuple[dict, dict[str, str]]:
    support = [sources["literature_library"]]
    availability = [{
        **_evidence(sources["research_idea"]),
        "availability": "UNAVAILABLE",
        "limitation": "Referenced Artifact is not explicitly bound to Review",
    }]
    if include_idea:
        support = [sources["research_idea"], *support]
        availability = [_evidence(sources["research_idea"])]
    scope = {"sha256": canonical_hash([]), "value": []}
    scope_payload = {
        "scope_sha256": scope["sha256"],
        "manuscript_sha256": manuscript_ref["sha256"],
        "bound_artifacts_sha256": canonical_hash(support),
        "approved_at": "2026-08-19T00:02:00Z",
        "decision": "APPROVED",
    }
    issues = [{
        "issue_id": "issue-1",
        "severity": "MINOR",
        "blocking": True,
        "evidence_refs": [],
    }]
    review = {
        "schema": "review-report/v3",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "2" * 32},
        "source_manuscript": manuscript_ref,
        "supporting_artifacts": support,
        "review_scope": scope,
        "scope_approval": {"sha256": canonical_hash(scope_payload), **scope_payload},
        "evidence_availability": availability,
        "assessment": "REVISION_REQUIRED",
        "summary": "A bounded revision is requested.",
        "issues": issues,
        "limitations": ["The Research Idea was not independently reviewed."],
        "experiment_evidence_audit": None,
        "owner_review": None,
    }
    _rehash_review(review)
    return review, _ref("review-report/v3", "d")


def _rehash_review(review: dict) -> None:
    payload = {
        "source_manuscript": review["source_manuscript"],
        "supporting_artifacts": review["supporting_artifacts"],
        "review_scope": review["review_scope"],
        "scope_approval": review["scope_approval"],
        "evidence_availability": review["evidence_availability"],
        "experiment_evidence_audit": review["experiment_evidence_audit"],
        **{key: review[key] for key in ("assessment", "summary", "issues", "limitations")},
    }
    owner_payload = {
        "review_result_sha256": canonical_hash(payload),
        "reviewed_at": "2026-08-19T00:03:00Z",
        "decision": "APPROVED",
    }
    review["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}


def _revision(
    manuscript: dict,
    manuscript_ref: dict[str, str],
    review: dict,
    review_ref: dict[str, str],
    sources: dict[str, object],
) -> tuple[dict, dict[str, object]]:
    support = [sources["research_idea"], sources["literature_library"]]
    bound = {
        "prior_manuscript": manuscript_ref,
        "causal_review": review_ref,
        **sources,
    }
    plan = {"sha256": canonical_hash([]), "value": []}
    approval_payload = {
        "prior_manuscript_sha256": manuscript_ref["sha256"],
        "causal_review_sha256": review_ref["sha256"],
        "issue_set_sha256": canonical_hash(review["issues"]),
        "revision_plan_sha256": plan["sha256"],
        "supporting_artifacts_sha256": canonical_hash(support),
        "approved_at": "2026-08-19T00:04:00Z",
        "decision": "APPROVED",
    }
    accounting = [{"issue_id": "issue-1", "disposition": "NOT_ADDRESSED"}]
    owner_payload = {
        "revised_draft_sha256": canonical_hash({
            "title": manuscript["title"],
            "content_markdown": manuscript["content_markdown"],
            "claims": manuscript["claims"],
            "citations": manuscript["citations"],
        }),
        "issue_accounting_sha256": canonical_hash(accounting),
        "reviewed_at": "2026-08-19T00:05:00Z",
        "decision": "APPROVED",
    }
    revision = {
        "schema": "manuscript-draft/v5",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "3" * 32},
        "prior_manuscript": manuscript_ref,
        "causal_review": review_ref,
        "supporting_artifacts": support,
        "revision_round": 1,
        "writing_brief": manuscript["writing_brief"],
        "title": manuscript["title"],
        "content_markdown": manuscript["content_markdown"],
        "claims": manuscript["claims"],
        "citations": manuscript["citations"],
        "experiment_evidence_available": False,
        "experiment_evidence": None,
        "unsupported_areas": manuscript["unsupported_areas"],
        "limitations": manuscript["limitations"],
        "revision_plan": plan,
        "revision_plan_approval": {
            "sha256": canonical_hash(approval_payload), **approval_payload,
        },
        "issue_accounting": accounting,
        "remaining_blocking_issue_ids": ["issue-1"],
        "remaining_blocking_issue_count": 1,
        "revision_limitations": ["The issue remains unresolved."],
        "owner_review": {"sha256": canonical_hash(owner_payload), **owner_payload},
    }
    return revision, bound


def _case(*, include_idea: bool = False):
    manuscript, sources, manuscript_ref = _manuscript()
    review, review_ref = _review(manuscript_ref, sources, include_idea=include_idea)
    revision, bound = _revision(manuscript, manuscript_ref, review, review_ref, sources)
    return revision, manuscript, review, bound


@pytest.mark.parametrize("include_idea", (False, True))
def test_review_support_may_be_exact_subset_or_equal_revision_context(
    include_idea: bool,
) -> None:
    revision, manuscript, review, bound = _case(include_idea=include_idea)
    assert validate_manuscript_draft_v5(
        revision,
        prior_manuscript=manuscript,
        causal_review=review,
        bound_inputs=bound,
    )["supporting_artifacts"] == [
        bound["research_idea"], bound["literature_library"]
    ]


def test_review_support_identity_mismatch_is_rejected() -> None:
    revision, manuscript, review, bound = _case()
    review["supporting_artifacts"] = [_ref("selected-paper-library/v1", "f")]
    _rehash_review(review)
    with pytest.raises(ForwardDownstreamContractError, match="differs from Revision context"):
        validate_manuscript_draft_v5(
            revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=bound,
        )


def test_review_cannot_use_omitted_source_as_evidence() -> None:
    revision, manuscript, review, bound = _case()
    review["issues"][0]["evidence_refs"] = [_evidence(bound["research_idea"])]
    _rehash_review(review)
    with pytest.raises(ForwardDownstreamContractError, match="not explicitly bound"):
        validate_manuscript_draft_v5(
            revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=bound,
        )


def test_required_prior_manuscript_missing_or_mismatched_is_rejected() -> None:
    revision, manuscript, review, bound = _case()
    missing = deepcopy(bound)
    missing.pop("prior_manuscript")
    with pytest.raises(ForwardDownstreamContractError, match="required exact bindings"):
        validate_manuscript_draft_v5(
            revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=missing,
        )
    mismatch = deepcopy(bound)
    mismatch["prior_manuscript"] = _ref("manuscript-draft/v4", "f")
    with pytest.raises(ForwardDownstreamContractError, match="causal lineage"):
        validate_manuscript_draft_v5(
            revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=mismatch,
        )


def test_review_source_manuscript_mismatch_is_rejected() -> None:
    revision, manuscript, review, bound = _case()
    review["source_manuscript"] = _ref("manuscript-draft/v4", "f")
    review["scope_approval"]["manuscript_sha256"] = review["source_manuscript"]["sha256"]
    scope_payload = dict(review["scope_approval"])
    scope_payload.pop("sha256")
    review["scope_approval"]["sha256"] = canonical_hash(scope_payload)
    _rehash_review(review)
    with pytest.raises(ForwardDownstreamContractError, match="different Draft|different prior"):
        validate_manuscript_draft_v5(
            revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=bound,
        )


def test_revision_capsule_startup_accepts_exact_review_support_subset(tmp_path) -> None:
    root = build_writing_revision_v0_9_package(
        project_id="project-" + "7" * 32,
        project_name="Optional Review support",
        research_topic="Bounded support context",
        output_root=tmp_path,
        package_id="optional-review-support",
    ).package_root

    def write(relative: str, value: object) -> bytes:
        content = (canonical_json(value) + "\n").encode()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return content

    idea_bytes = write("inputs/selected-research-idea.json", {"schema": "fixture-idea"})
    literature_bytes = write(
        "inputs/selected-paper-library.json",
        {"schema": "selected-paper-library/v1", "papers": []},
    )
    idea_ref = {
        "artifact_id": "artifact-" + "a" * 32,
        "artifact_type": "selected-research-idea/v1",
        "sha256": sha256_bytes(idea_bytes),
    }
    literature_ref = {
        "artifact_id": "artifact-" + "b" * 32,
        "artifact_type": "selected-paper-library/v1",
        "sha256": sha256_bytes(literature_bytes),
    }
    manuscript, sources, _ = _manuscript()
    sources.update(research_idea=idea_ref, literature_library=literature_ref)
    manuscript["source_artifacts"] = sources
    manuscript["claims"][0]["evidence_refs"] = [_evidence(idea_ref)]
    outline_payload = dict(manuscript["outline_approval"])
    outline_payload.pop("sha256")
    outline_payload["source_artifacts_sha256"] = canonical_hash(sources)
    manuscript["outline_approval"] = {
        "sha256": canonical_hash(outline_payload), **outline_payload,
    }
    owner_payload = dict(manuscript["owner_review"])
    owner_payload.pop("sha256")
    owner_payload["draft_sha256"] = canonical_hash({
        "title": manuscript["title"],
        "content_markdown": manuscript["content_markdown"],
        "claims": manuscript["claims"],
        "citations": manuscript["citations"],
    })
    manuscript["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}
    manuscript_bytes = write("inputs/prior-manuscript.json", manuscript)
    manuscript_ref = {
        "artifact_id": "artifact-" + "c" * 32,
        "artifact_type": "manuscript-draft/v4",
        "sha256": sha256_bytes(manuscript_bytes),
    }
    review, _ = _review(manuscript_ref, sources, include_idea=False)
    review_bytes = write("inputs/review-report.json", review)
    review_ref = {
        "artifact_id": "artifact-" + "d" * 32,
        "artifact_type": "review-report/v3",
        "sha256": sha256_bytes(review_bytes),
    }
    provenance = {
        "schema_version": "reagent.writing-revision-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "9" * 32,
        "artifacts": {
            "prior_manuscript": manuscript_ref,
            "causal_review": review_ref,
            "research_idea": idea_ref,
            "literature_library": literature_ref,
        },
    }
    write("memory/input-provenance.json", provenance)
    validator = runpy.run_path(str(root / "validate_package.py"))
    _, normalized, *_ = validator["_input_state"](root)
    assert normalized == provenance["artifacts"]
    assert json.loads((root / "inputs/review-report.json").read_text())[
        "supporting_artifacts"
    ] == [literature_ref]
