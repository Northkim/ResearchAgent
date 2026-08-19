"""Forward Review v3 validation for optional, explicitly scoped evidence."""

from __future__ import annotations

from typing import Any, Mapping

from .forward_downstream_contracts import (
    MANUSCRIPT_DRAFT_V4,
    ForwardDownstreamContractError,
    artifact_ref,
    experiment_evidence_audit,
    manuscript_surface,
    validate_evidence_refs,
    validate_review_report_v3 as _validate_review_report_v3_published,
)

_OPTIONAL_ROLES = ("research_idea", "literature_library", "experiment_record")


def _evidence_availability(
    manuscript: Mapping[str, Any], bound_inputs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Project the published Review availability rules from exact bindings."""

    bound = {
        (item["artifact_id"], item["artifact_type"], item["sha256"])
        for role in _OPTIONAL_ROLES
        if (item := bound_inputs.get(role)) is not None
    }
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for ref in manuscript_surface(manuscript)["evidence_refs"]:
        key = (
            ref["artifact_id"], ref["artifact_type"], ref["sha256"],
            ref["evidence_item"], ref["location"],
        )
        if key in seen:
            continue
        seen.add(key)
        if key[:3] not in bound:
            availability = "UNAVAILABLE"
            limitation = "Referenced Artifact is not explicitly bound to Review"
        elif ref.get("availability") != "AVAILABLE" or ref.get("limitation"):
            availability = "SCOPE_LIMITED"
            limitation = ref.get("limitation") or "Manuscript records limited evidence scope"
        else:
            availability = "AVAILABLE"
            limitation = None
        result.append({
            "artifact_id": ref["artifact_id"],
            "artifact_type": ref["artifact_type"],
            "sha256": ref["sha256"],
            "evidence_item": ref["evidence_item"],
            "location": ref["location"],
            "availability": availability,
            "limitation": limitation,
        })
    return result


def validate_review_report_v3(
    value: Any,
    *,
    manuscript: Mapping[str, Any] | None = None,
    bound_inputs: Mapping[str, Any] | None = None,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate actual Review evidence without requiring full lineage binding.

    The immutable manuscript retains its complete provenance. Review authority
    is limited to the required manuscript plus optional sources that the Owner
    explicitly bound for this Review.
    """

    item = _validate_review_report_v3_published(value)
    if manuscript is None and bound_inputs is None:
        return item
    if manuscript is None or bound_inputs is None or "manuscript" not in bound_inputs:
        raise ForwardDownstreamContractError("Review requires an exact manuscript binding")
    if set(bound_inputs) - {"manuscript", *_OPTIONAL_ROLES}:
        raise ForwardDownstreamContractError("Review contains an unknown input binding")

    surface = manuscript_surface(manuscript)
    manuscript_ref = artifact_ref(bound_inputs["manuscript"], MANUSCRIPT_DRAFT_V4)
    if artifact_ref(item["source_manuscript"], MANUSCRIPT_DRAFT_V4) != manuscript_ref:
        raise ForwardDownstreamContractError("Review refers to a different Draft")

    support: list[dict[str, str]] = []
    issue_sources: dict[str, Any] = {"manuscript": manuscript_ref}
    for role in _OPTIONAL_ROLES:
        supplied = bound_inputs.get(role)
        if supplied is None:
            continue
        exact = artifact_ref(supplied)
        if surface["sources"].get(role) != exact:
            raise ForwardDownstreamContractError(
                f"bound Review source {role} differs from manuscript lineage"
            )
        support.append(exact)
        issue_sources[role] = exact
    if [artifact_ref(raw) for raw in item["supporting_artifacts"]] != support:
        raise ForwardDownstreamContractError("Review support differs from exact bindings")

    if item["evidence_availability"] != _evidence_availability(manuscript, bound_inputs):
        raise ForwardDownstreamContractError(
            "Review evidence availability differs from exact bindings"
        )
    bound_experiment = bound_inputs.get("experiment_record")
    expected_audit = (
        None
        if bound_experiment is None
        else experiment_evidence_audit(manuscript, experiment)
    )
    if item["experiment_evidence_audit"] != expected_audit:
        raise ForwardDownstreamContractError("Review v5 evidence audit is inconsistent")
    for issue in item["issues"]:
        if not isinstance(issue, Mapping) or issue.get("severity") not in {"MAJOR", "MINOR"}:
            raise ForwardDownstreamContractError("Review issue severity is invalid")
        validate_evidence_refs(issue.get("evidence_refs"), issue_sources, experiment)
    return item
