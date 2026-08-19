from __future__ import annotations

from dataclasses import replace

import pytest

from backend.artifact_references.forward_downstream_contracts import (
    ForwardDownstreamContractError, experiment_summary,
    validate_claims, validate_manuscript_draft_v4, validate_manuscript_draft_v5,
    validate_review_report_v3,
)
from backend.artifact_references.review_contract_compatibility import (
    validate_review_report_v3 as validate_scoped_review_report_v3,
)
from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind, ScientificEvidenceBlock, finalize_experiment_record_v5,
)
from backend.artifact_references.tests.test_generic_experiment_record_v5 import _result, _source
from backend.workflow_packages.experiment_capability_runtime import CapabilityEvaluationResult
from backend.workflow_packages.generic_experiment_contracts import (
    EvaluationValidity, NormalizedExperimentResult, ProcessOutcome,
    ScientificEvidenceStatus,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes

SHA = "sha256:" + "a" * 64


def _ref(kind: str, letter: str) -> dict[str, str]:
    return {"artifact_id": "artifact-" + letter * 32, "artifact_type": kind, "sha256": "sha256:" + letter * 64}


def _v5(status=ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS, validity=EvaluationValidity.VALID):
    lifecycle, result = _result()
    receipt = replace(result.receipt, validity=validity)
    normalized = NormalizedExperimentResult(ProcessOutcome.SUCCEEDED, validity, status, ("Preserve the bounded source limitation.",))
    lifecycle = replace(lifecycle, capability_evaluation=receipt, normalized_result=normalized, limitations=normalized.limitations)
    result = CapabilityEvaluationResult(receipt, status.value, result.result_payload)
    block = ScientificEvidenceBlock("evidence-finding", EvidenceKind.PROSE, "Finding", "A bounded categorical finding was observed.", _source(result))
    value = finalize_experiment_record_v5(lifecycle, result, (block,)).to_dict()
    return value, block


def _inputs(v5):
    experiment = {**_ref("experiment-record/v5", "e"), "sha256": sha256_bytes(canonical_json(v5).encode())}
    return {
        "research_idea": _ref("selected-research-idea/v1", "a"),
        "literature_library": _ref("selected-paper-library/v1", "b"),
        "experiment_record": experiment,
    }


def _evidence_ref(inputs, block, *, limitation=None):
    return {
        **inputs["experiment_record"], "evidence_item": block.block_id,
        "location": f"bounded_scientific_evidence.blocks/{block.block_id}",
        "availability": "AVAILABLE", "limitation": limitation,
        "evidence_block_id": block.block_id,
        "evidence_block_checksum": block.block_checksum,
    }


def _claim(inputs, block, *, qualification="BOUNDED_SCIENTIFIC_CLAIM", boundaries=None, limitations=None):
    return {
        "claim_id": "claim-result-1", "claim_type": "RESULT", "section": "Results",
        "claim_text": "The bounded categorical finding was observed.",
        "support_status": "SUPPORTED", "evidence_refs": [_evidence_ref(inputs, block, limitation="Bounded observation")],
        "citation_ids": [], "limitations": limitations or ["Preserve the bounded source limitation."],
        "evidence_qualification": qualification,
        "claim_boundary_refs": boundaries or ["Claims are limited to this synthetic reference."],
    }


def _manuscript(v5, block, *, qualification="BOUNDED_SCIENTIFIC_CLAIM", inputs=None):
    inputs = _inputs(v5) if inputs is None else inputs
    summary = experiment_summary(v5, inputs["experiment_record"])
    claim = _claim(inputs, block, qualification=qualification, boundaries=summary["claim_boundaries"])
    outline = {"sha256": canonical_hash([]), "value": []}
    approval_payload = {
        "outline_sha256": outline["sha256"], "brief_sha256": canonical_hash({"document_type": "article"}),
        "evidence_map_sha256": canonical_hash([]), "source_artifacts_sha256": canonical_hash(inputs),
        "approved_at": "2026-08-18T00:00:00Z", "decision": "APPROVED",
    }
    value = {
        "schema": "manuscript-draft/v4", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "1" * 32, "capsule_id": "capsule-" + "1" * 32, "capsule_version": "0.7.0", "execution_round": 1},
        "source_artifacts": inputs, "writing_brief": {"document_type": "article"},
        "evidence_map": [], "approved_outline": outline,
        "outline_approval": {"sha256": canonical_hash(approval_payload), **approval_payload}, "title": "Bounded result",
        "content_markdown": "# Bounded result\n\nThe exact observation is reported within its boundary.",
        "claims": [claim], "citations": [], "experiment_evidence_available": True,
        "experiment_evidence": summary, "unsupported_areas": [],
        "limitations": [*summary["limitations"], "No external evidence was acquired."],
        "owner_review": None,
    }
    review_payload = {
        "draft_sha256": canonical_hash({"title": value["title"], "content_markdown": value["content_markdown"], "claims": value["claims"], "citations": value["citations"]}),
        "reviewed_at": "2026-08-18T00:01:00Z", "decision": "APPROVED",
    }
    value["owner_review"] = {"sha256": canonical_hash(review_payload), **review_payload}
    return value, inputs


def _review(manuscript, inputs, v5, *, manuscript_ref=None):
    manuscript_ref = _ref("manuscript-draft/v4", "c") if manuscript_ref is None else manuscript_ref
    bound = {"manuscript": manuscript_ref, **inputs}
    support = [inputs[key] for key in ("research_idea", "literature_library", "experiment_record")]
    audit = {
        "experiment_artifact": inputs["experiment_record"],
        "process_outcome": manuscript["experiment_evidence"]["process_outcome"],
        "evaluation_validity": manuscript["experiment_evidence"]["evaluation_validity"],
        "scientific_evidence_status": manuscript["experiment_evidence"]["scientific_evidence_status"],
        "evidence_checksum": manuscript["experiment_evidence"]["evidence_checksum"],
        "claim_boundary_compliance": "VALIDATED_BY_EXACT_GROUNDING",
        "limitations_preserved": True,
    }
    scope = {"sha256": canonical_hash({}), "value": {}}
    approval_payload = {
        "scope_sha256": scope["sha256"], "manuscript_sha256": manuscript_ref["sha256"],
        "bound_artifacts_sha256": canonical_hash(support), "approved_at": "2026-08-18T00:02:00Z", "decision": "APPROVED",
    }
    value = {
        "schema": "review-report/v3", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "2" * 32},
        "source_manuscript": manuscript_ref, "supporting_artifacts": support,
        "review_scope": scope, "scope_approval": {"sha256": canonical_hash(approval_payload), **approval_payload},
        "evidence_availability": [], "assessment": "REVISION_REQUIRED",
        "summary": "One bounded wording revision is required.",
        "issues": [{"issue_id": "issue-1", "severity": "MINOR", "blocking": True, "evidence_refs": []}],
        "limitations": ["Review used exact supplied evidence only."],
        "experiment_evidence_audit": audit, "owner_review": None,
    }
    result_payload = {
        "source_manuscript": manuscript_ref, "supporting_artifacts": support,
        "review_scope": scope, "scope_approval": value["scope_approval"],
        "evidence_availability": value["evidence_availability"],
        "experiment_evidence_audit": audit,
        **{key: value[key] for key in ("assessment", "summary", "issues", "limitations")},
    }
    owner_payload = {"review_result_sha256": canonical_hash(result_payload), "reviewed_at": "2026-08-18T00:03:00Z", "decision": "APPROVED"}
    value["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}
    validate_review_report_v3(value, manuscript=manuscript, bound_inputs=bound, experiment=v5)
    return value, bound


def _without_experiment(review, bound):
    scoped_bound = {
        key: value for key, value in bound.items() if key != "experiment_record"
    }
    support = [scoped_bound[key] for key in ("research_idea", "literature_library")]
    experiment_ref = bound["experiment_record"]
    availability = [{
        **experiment_ref,
        "evidence_item": "evidence-finding",
        "location": "bounded_scientific_evidence.blocks/evidence-finding",
        "availability": "UNAVAILABLE",
        "limitation": "Referenced Artifact is not explicitly bound to Review",
    }]
    approval_payload = {
        "scope_sha256": review["review_scope"]["sha256"],
        "manuscript_sha256": review["source_manuscript"]["sha256"],
        "bound_artifacts_sha256": canonical_hash(support),
        "approved_at": "2026-08-18T00:02:00Z",
        "decision": "APPROVED",
    }
    scoped = {
        **review,
        "supporting_artifacts": support,
        "scope_approval": {"sha256": canonical_hash(approval_payload), **approval_payload},
        "evidence_availability": availability,
        "experiment_evidence_audit": None,
    }
    result_payload = {
        "source_manuscript": scoped["source_manuscript"],
        "supporting_artifacts": support,
        "review_scope": scoped["review_scope"],
        "scope_approval": scoped["scope_approval"],
        "evidence_availability": availability,
        "experiment_evidence_audit": None,
        **{key: scoped[key] for key in ("assessment", "summary", "issues", "limitations")},
    }
    owner_payload = {
        "review_result_sha256": canonical_hash(result_payload),
        "reviewed_at": "2026-08-18T00:03:00Z",
        "decision": "APPROVED",
    }
    scoped["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}
    return scoped, scoped_bound


def _rehash_review_owner(review):
    result_payload = {
        "source_manuscript": review["source_manuscript"],
        "supporting_artifacts": review["supporting_artifacts"],
        "review_scope": review["review_scope"],
        "scope_approval": review["scope_approval"],
        "evidence_availability": review["evidence_availability"],
        "experiment_evidence_audit": review["experiment_evidence_audit"],
        **{key: review[key] for key in ("assessment", "summary", "issues", "limitations")},
    }
    owner_payload = {
        "review_result_sha256": canonical_hash(result_payload),
        "reviewed_at": "2026-08-18T00:03:00Z",
        "decision": "APPROVED",
    }
    review["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}


def test_review_may_omit_optional_manuscript_source_when_explicitly_unverified() -> None:
    v5, block = _v5()
    manuscript, sources = _manuscript(v5, block)
    review, bound = _review(manuscript, sources, v5)
    scoped, scoped_bound = _without_experiment(review, bound)

    assert validate_scoped_review_report_v3(
        scoped, manuscript=manuscript, bound_inputs=scoped_bound,
    )["evidence_availability"][0]["availability"] == "UNAVAILABLE"


def test_review_cannot_use_an_omitted_source_as_evidence() -> None:
    v5, block = _v5()
    manuscript, sources = _manuscript(v5, block)
    review, bound = _review(manuscript, sources, v5)
    scoped, scoped_bound = _without_experiment(review, bound)
    scoped["issues"] = [{
        **scoped["issues"][0],
        "evidence_refs": [_evidence_ref(sources, block, limitation="Unavailable")],
    }]
    _rehash_review_owner(scoped)
    with pytest.raises(ForwardDownstreamContractError, match="not explicitly bound"):
        validate_scoped_review_report_v3(
            scoped, manuscript=manuscript, bound_inputs=scoped_bound,
        )


def test_review_rejects_bound_source_identity_mismatch() -> None:
    v5, block = _v5()
    manuscript, sources = _manuscript(v5, block)
    review, bound = _review(manuscript, sources, v5)
    bound["research_idea"] = _ref("selected-research-idea/v1", "f")
    with pytest.raises(ForwardDownstreamContractError, match="differs from manuscript lineage"):
        validate_scoped_review_report_v3(
            review, manuscript=manuscript, bound_inputs=bound, experiment=v5,
        )


def test_review_rejects_missing_required_manuscript_binding() -> None:
    v5, block = _v5()
    manuscript, sources = _manuscript(v5, block)
    review, bound = _review(manuscript, sources, v5)
    bound.pop("manuscript")
    with pytest.raises(ForwardDownstreamContractError, match="requires an exact manuscript"):
        validate_scoped_review_report_v3(
            review, manuscript=manuscript, bound_inputs=bound, experiment=v5,
        )


def test_forward_claim_grounding_preserves_v5_status_boundary_and_block_identity() -> None:
    v5, block = _v5()
    manuscript, inputs = _manuscript(v5, block)
    assert validate_manuscript_draft_v4(manuscript, bound_inputs=inputs, experiment=v5)["claims"][0]["evidence_refs"][0]["evidence_block_checksum"] == block.block_checksum

    broken = dict(manuscript)
    broken["claims"] = [{**manuscript["claims"][0], "claim_boundary_refs": ["Unreported global boundary"]}]
    with pytest.raises(ForwardDownstreamContractError, match="boundary violation"):
        validate_manuscript_draft_v4(broken, bound_inputs=inputs, experiment=v5)


@pytest.mark.parametrize("validity,status", (
    (EvaluationValidity.INVALID, ScientificEvidenceStatus.INCONCLUSIVE),
    (EvaluationValidity.VALID, ScientificEvidenceStatus.LIMITED),
))
def test_invalid_or_insufficient_v5_cannot_ground_broad_claim(validity, status) -> None:
    v5, block = _v5(status, validity)
    inputs = _inputs(v5)
    summary = experiment_summary(v5, inputs["experiment_record"])
    broad = _claim(inputs, block, boundaries=summary["claim_boundaries"])
    with pytest.raises(ForwardDownstreamContractError, match="exceeds v5 authority"):
        validate_claims([broad], inputs, [], v5)
    descriptive = {**broad, "evidence_qualification": "DESCRIPTIVE_OBSERVATION"}
    assert validate_claims([descriptive], inputs, [], v5)[0]["evidence_qualification"] == "DESCRIPTIVE_OBSERVATION"


def test_review_and_new_revision_preserve_exact_causal_v5_lineage() -> None:
    v5, block = _v5()
    manuscript, sources = _manuscript(v5, block)
    review, review_inputs = _review(manuscript, sources, v5)
    prior_ref = review_inputs["manuscript"]
    review_ref = _ref("review-report/v3", "d")
    bound = {"prior_manuscript": prior_ref, "causal_review": review_ref, **sources}
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record")]
    plan = {"sha256": canonical_hash([]), "value": []}
    plan_approval = {
        "prior_manuscript_sha256": prior_ref["sha256"], "causal_review_sha256": review_ref["sha256"],
        "issue_set_sha256": canonical_hash(review["issues"]), "revision_plan_sha256": plan["sha256"],
        "supporting_artifacts_sha256": canonical_hash(support), "approved_at": "2026-08-18T00:04:00Z", "decision": "APPROVED",
    }
    revision = {
        "schema": "manuscript-draft/v5", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "3" * 32},
        "prior_manuscript": prior_ref, "causal_review": review_ref,
        "supporting_artifacts": support,
        "revision_round": 1, "writing_brief": manuscript["writing_brief"], "title": manuscript["title"],
        "content_markdown": manuscript["content_markdown"], "claims": manuscript["claims"],
        "citations": [], "experiment_evidence_available": True,
        "experiment_evidence": manuscript["experiment_evidence"], "unsupported_areas": [],
        "limitations": manuscript["limitations"], "revision_plan": plan,
        "revision_plan_approval": {"sha256": canonical_hash(plan_approval), **plan_approval},
        "issue_accounting": [{"issue_id": "issue-1", "disposition": "NOT_ADDRESSED"}],
        "remaining_blocking_issue_ids": ["issue-1"], "remaining_blocking_issue_count": 1,
        "revision_limitations": ["The requested wording remains unresolved."],
        "owner_review": None,
    }
    owner_payload = {
        "revised_draft_sha256": canonical_hash({"title": revision["title"], "content_markdown": revision["content_markdown"], "claims": revision["claims"], "citations": revision["citations"]}),
        "issue_accounting_sha256": canonical_hash(revision["issue_accounting"]), "reviewed_at": "2026-08-18T00:05:00Z", "decision": "APPROVED",
    }
    revision["owner_review"] = {"sha256": canonical_hash(owner_payload), **owner_payload}
    assert validate_manuscript_draft_v5(revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=bound, experiment=v5)["causal_review"] == review_ref
    wrong = {**bound, "prior_manuscript": _ref("manuscript-draft/v4", "f")}
    with pytest.raises(ForwardDownstreamContractError, match="different Draft|causal lineage"):
        validate_manuscript_draft_v5(revision, prior_manuscript=manuscript, causal_review=review, bound_inputs=wrong, experiment=v5)


@pytest.mark.parametrize("kind", ("experiment-record/v1", "experiment-record/v2", "experiment-record/v3", "experiment-record/v4"))
def test_forward_experiment_role_rejects_every_pre_v5_version(kind: str) -> None:
    v5, block = _v5()
    manuscript, inputs = _manuscript(v5, block)
    manuscript["source_artifacts"] = {**inputs, "experiment_record": _ref(kind, "e")}
    with pytest.raises(ForwardDownstreamContractError, match="experiment-record/v5"):
        validate_manuscript_draft_v4(manuscript, bound_inputs=inputs, experiment=v5)
