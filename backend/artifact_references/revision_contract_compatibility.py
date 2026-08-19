"""Forward Revision v5 validation with inherited manuscript context."""

from __future__ import annotations

from typing import Any, Mapping

from backend.workflow_packages.serialization import canonical_hash

from .forward_downstream_contracts import (
    MANUSCRIPT_DRAFT_V4,
    REVIEW_REPORT_V3,
    ForwardDownstreamContractError,
    _citations,
    _exact_approval,
    _hash_box,
    artifact_ref,
    experiment_evidence_audit,
    validate_claims,
    validate_evidence_refs,
    validate_experiment_summary,
    validate_manuscript_draft_v4,
    validate_manuscript_draft_v5 as _validate_manuscript_draft_v5_published,
)
from .review_contract_compatibility import validate_review_report_v3

_CONTEXT_ROLES = ("research_idea", "literature_library", "experiment_record")
_ROLES_BY_TYPE = {
    "selected-research-idea/v1": "research_idea",
    "selected-paper-library/v1": "literature_library",
    "experiment-record/v5": "experiment_record",
}


def validate_manuscript_draft_v5(
    value: Any,
    *,
    prior_manuscript: Mapping[str, Any] | None = None,
    causal_review: Mapping[str, Any] | None = None,
    bound_inputs: Mapping[str, Any] | None = None,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate Review support as an exact subset of inherited context."""

    item = _validate_manuscript_draft_v5_published(value)
    if prior_manuscript is None and causal_review is None and bound_inputs is None:
        return item
    if prior_manuscript is None or causal_review is None or bound_inputs is None:
        raise ForwardDownstreamContractError("Revision contextual validation is incomplete")
    required = {"prior_manuscript", "causal_review", "research_idea", "literature_library"}
    if required - set(bound_inputs):
        raise ForwardDownstreamContractError("Revision required exact bindings are missing")
    if set(bound_inputs) - {"prior_manuscript", "causal_review", *_CONTEXT_ROLES}:
        raise ForwardDownstreamContractError("Revision contains an unknown input binding")

    prior = validate_manuscript_draft_v4(prior_manuscript)
    prior_ref = artifact_ref(bound_inputs["prior_manuscript"], MANUSCRIPT_DRAFT_V4)
    causal_ref = artifact_ref(bound_inputs["causal_review"], REVIEW_REPORT_V3)
    if artifact_ref(item["prior_manuscript"], MANUSCRIPT_DRAFT_V4) != prior_ref or artifact_ref(
        item["causal_review"], REVIEW_REPORT_V3
    ) != causal_ref:
        raise ForwardDownstreamContractError("Revision causal lineage differs from exact bindings")

    context = {
        "research_idea": artifact_ref(bound_inputs["research_idea"]),
        "literature_library": artifact_ref(bound_inputs["literature_library"]),
        "experiment_record": (
            artifact_ref(bound_inputs["experiment_record"])
            if bound_inputs.get("experiment_record") is not None
            else None
        ),
    }
    if prior["source_artifacts"] != context:
        raise ForwardDownstreamContractError("Revision support differs from prior manuscript lineage")
    support = [context[role] for role in _CONTEXT_ROLES if context[role] is not None]
    if [artifact_ref(raw) for raw in item["supporting_artifacts"]] != support:
        raise ForwardDownstreamContractError("Revision support differs from exact bindings")

    review_sources: dict[str, Any] = {"manuscript": prior_ref}
    review_bound: dict[str, Any] = {"manuscript": prior_ref}
    seen_review_roles: set[str] = set()
    for raw in causal_review.get("supporting_artifacts", []):
        ref = artifact_ref(raw)
        role = _ROLES_BY_TYPE.get(ref["artifact_type"])
        if role is None or role in seen_review_roles or context.get(role) != ref:
            raise ForwardDownstreamContractError(
                "causal Review support differs from Revision context"
            )
        seen_review_roles.add(role)
        review_sources[role] = ref
        review_bound[role] = ref
    review_experiment = experiment if "experiment_record" in seen_review_roles else None
    review = validate_review_report_v3(
        causal_review,
        manuscript=prior,
        bound_inputs=review_bound,
        experiment=review_experiment,
    )
    if artifact_ref(review["source_manuscript"], MANUSCRIPT_DRAFT_V4) != prior_ref:
        raise ForwardDownstreamContractError(
            "causal Review refers to a different prior manuscript"
        )
    expected_audit = (
        experiment_evidence_audit(prior, experiment)
        if "experiment_record" in seen_review_roles
        else None
    )
    if review["experiment_evidence_audit"] != expected_audit:
        raise ForwardDownstreamContractError(
            "causal Review Experiment audit exceeds its support scope"
        )
    for issue in review["issues"]:
        validate_evidence_refs(issue.get("evidence_refs"), review_sources, review_experiment)

    if item["writing_brief"] != prior["writing_brief"]:
        raise ForwardDownstreamContractError("Revision changed the approved Writing Brief")
    if item["experiment_evidence"] != prior["experiment_evidence"]:
        raise ForwardDownstreamContractError("Revision changed Experiment evidence authority")
    validate_experiment_summary(item["experiment_evidence"], experiment, context["experiment_record"])
    citations = _citations(item["citations"], context)
    validate_claims(item["claims"], context, citations, experiment)

    issues = {issue["issue_id"]: issue for issue in review["issues"]}
    accounting = item["issue_accounting"]
    if not isinstance(accounting, list) or {entry.get("issue_id") for entry in accounting} != set(issues):
        raise ForwardDownstreamContractError("Revision must account for every causal Review issue")
    allowed = {"ADDRESSED", "PARTIALLY_ADDRESSED", "NOT_ADDRESSED", "NOT_APPLICABLE"}
    if any(entry.get("disposition") not in allowed for entry in accounting):
        raise ForwardDownstreamContractError("Revision issue disposition is invalid")
    plan = _hash_box(item["revision_plan"], "Revision Plan")
    _exact_approval(
        item["revision_plan_approval"],
        label="Revision Plan approval",
        fields={
            "prior_manuscript_sha256", "causal_review_sha256", "issue_set_sha256",
            "revision_plan_sha256", "supporting_artifacts_sha256", "approved_at", "decision",
        },
        expected={
            "prior_manuscript_sha256": prior_ref["sha256"],
            "causal_review_sha256": causal_ref["sha256"],
            "issue_set_sha256": canonical_hash(review["issues"]),
            "revision_plan_sha256": plan["sha256"],
            "supporting_artifacts_sha256": canonical_hash(support),
            "decision": "APPROVED",
        },
    )
    disposition = {entry["issue_id"]: entry["disposition"] for entry in accounting}
    remaining = [
        issue["issue_id"]
        for issue in review["issues"]
        if issue.get("blocking") and disposition[issue["issue_id"]] != "ADDRESSED"
    ]
    if item["remaining_blocking_issue_ids"] != remaining or item[
        "remaining_blocking_issue_count"
    ] != len(remaining):
        raise ForwardDownstreamContractError("remaining blocking issue accounting is inconsistent")
    if item["experiment_evidence_available"] is not (context["experiment_record"] is not None):
        raise ForwardDownstreamContractError("Experiment evidence availability is inconsistent")
    return item
