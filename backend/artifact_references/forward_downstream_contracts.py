"""Forward reviewed downstream Artifact contracts for exact Experiment v5 evidence."""

from __future__ import annotations

import re
from typing import Any, Mapping

from backend.workflow_packages.serialization import canonical_hash

from .generic_experiment_v5_contracts import validate_experiment_record_v5

MANUSCRIPT_DRAFT_V4 = "manuscript-draft/v4"
REVIEW_REPORT_V3 = "review-report/v3"
MANUSCRIPT_DRAFT_V5 = "manuscript-draft/v5"

_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_WFI = re.compile(r"^wfi-[0-9a-f]{32}$")
_SUPPORT = {"SUPPORTED", "PLANNED", "UNAVAILABLE"}
_QUALIFICATION = {
    "LITERATURE_BOUND", "PROPOSED", "UNAVAILABLE",
    "DESCRIPTIVE_OBSERVATION", "BOUNDED_SCIENTIFIC_CLAIM",
}


class ForwardDownstreamContractError(ValueError):
    pass


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ForwardDownstreamContractError(f"{label} must be an object")
    return dict(value)


def _exact(value: Mapping[str, Any], fields: set[str], label: str) -> None:
    if set(value) != fields:
        raise ForwardDownstreamContractError(f"{label} fields mismatch")


def _text(value: Any, label: str, maximum: int = 10_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ForwardDownstreamContractError(f"{label} must be bounded text")
    return value


def _strings(value: Any, label: str, *, maximum: int = 100) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ForwardDownstreamContractError(f"{label} must be a bounded list")
    return [_text(item, label, 2_000) for item in value]


def artifact_ref(value: Any, expected_type: str | None = None) -> dict[str, str]:
    item = _object(value, "Artifact reference")
    _exact(item, {"artifact_id", "artifact_type", "sha256"}, "Artifact reference")
    if not isinstance(item["artifact_id"], str) or not item["artifact_id"].startswith("artifact-"):
        raise ForwardDownstreamContractError("Artifact identity is invalid")
    if expected_type is not None and item["artifact_type"] != expected_type:
        raise ForwardDownstreamContractError(f"Artifact must be exact {expected_type}")
    if not isinstance(item["sha256"], str) or _SHA.fullmatch(item["sha256"]) is None:
        raise ForwardDownstreamContractError("Artifact checksum is invalid")
    return item


def _hash_box(value: Any, label: str) -> dict[str, Any]:
    item = _object(value, label)
    _exact(item, {"sha256", "value"}, label)
    if item["sha256"] != canonical_hash(item["value"]):
        raise ForwardDownstreamContractError(f"{label} checksum mismatch")
    return item


def _exact_approval(
    value: Any, *, label: str, fields: set[str], expected: Mapping[str, Any],
) -> dict[str, Any]:
    item = _object(value, label)
    _exact(item, {"sha256", *fields}, label)
    payload = dict(item)
    checksum = payload.pop("sha256")
    if checksum != canonical_hash(payload) or any(item[key] != expected_value for key, expected_value in expected.items()):
        raise ForwardDownstreamContractError(f"{label} identity is invalid")
    return item


def experiment_summary(experiment: Mapping[str, Any] | None, reference: Any) -> dict[str, Any] | None:
    if experiment is None:
        if reference is not None:
            raise ForwardDownstreamContractError("Experiment reference has no materialized v5")
        return None
    record = validate_experiment_record_v5(experiment)
    ref = artifact_ref(reference, "experiment-record/v5")
    lifecycle = record["lifecycle_record"]
    normalized = lifecycle["normalized_result"]
    methodology = lifecycle["methodology"]
    evidence = record["bounded_scientific_evidence"]
    return {
        "artifact": ref,
        "process_outcome": normalized["process_outcome"],
        "evaluation_validity": normalized["evaluation_validity"],
        "scientific_evidence_status": normalized["scientific_evidence_status"],
        "claim_boundaries": list(methodology["claim_boundaries"]),
        "limitations": list(dict.fromkeys([
            *normalized["limitations"], *lifecycle["limitations"],
        ])),
        "evidence_checksum": evidence["evidence_checksum"],
        "blocks": [{
            "block_id": block["block_id"], "kind": block["kind"],
            "label": block["label"], "block_checksum": block["block_checksum"],
        } for block in evidence["blocks"]],
    }


def validate_experiment_summary(value: Any, experiment: Mapping[str, Any] | None, reference: Any) -> dict[str, Any] | None:
    if experiment is None and value is not None:
        item = _object(value, "Experiment evidence summary")
        _exact(item, {
            "artifact", "process_outcome", "evaluation_validity",
            "scientific_evidence_status", "claim_boundaries", "limitations",
            "evidence_checksum", "blocks",
        }, "Experiment evidence summary")
        if artifact_ref(item["artifact"], "experiment-record/v5") != artifact_ref(reference, "experiment-record/v5"):
            raise ForwardDownstreamContractError("Experiment summary reference differs")
        if _SHA.fullmatch(str(item["evidence_checksum"])) is None:
            raise ForwardDownstreamContractError("Experiment evidence checksum is invalid")
        _strings(item["claim_boundaries"], "claim boundaries")
        _strings(item["limitations"], "Experiment limitations")
        if not isinstance(item["blocks"], list) or len(item["blocks"]) > 80:
            raise ForwardDownstreamContractError("Experiment evidence blocks are invalid")
        for block in item["blocks"]:
            block = _object(block, "Experiment evidence block")
            _exact(block, {"block_id", "kind", "label", "block_checksum"}, "Experiment evidence block")
            if _SHA.fullmatch(str(block["block_checksum"])) is None:
                raise ForwardDownstreamContractError("Experiment evidence block checksum is invalid")
        return item
    expected = experiment_summary(experiment, reference)
    if value != expected:
        raise ForwardDownstreamContractError("Experiment evidence summary differs from exact v5")
    return expected


def _sources(value: Any, *, revision: bool = False) -> dict[str, Any]:
    item = _object(value, "source Artifacts")
    expected = {"research_idea", "literature_library", "experiment_record"}
    _exact(item, expected, "source Artifacts")
    result: dict[str, Any] = {
        "research_idea": artifact_ref(item["research_idea"], "selected-research-idea/v1"),
        "literature_library": artifact_ref(item["literature_library"], "selected-paper-library/v1"),
        "experiment_record": None,
    }
    if item["experiment_record"] is not None:
        result["experiment_record"] = artifact_ref(item["experiment_record"], "experiment-record/v5")
    return result


def validate_evidence_refs(
    value: Any, sources: Mapping[str, Any], experiment: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 200:
        raise ForwardDownstreamContractError("evidence references must be bounded")
    allowed = {
        (item["artifact_id"], item["artifact_type"], item["sha256"])
        for item in sources.values() if item is not None
    }
    summary = (
        None if experiment is None
        else experiment_summary(experiment, sources.get("experiment_record"))
    )
    blocks = {} if summary is None else {
        item["block_id"]: item["block_checksum"] for item in summary["blocks"]
    }
    result = []
    for raw in value:
        item = _object(raw, "evidence reference")
        base = {
            "artifact_id", "artifact_type", "sha256", "evidence_item", "location",
            "availability", "limitation",
        }
        experiment_fields = {"evidence_block_id", "evidence_block_checksum"}
        if set(item) not in (base, base | experiment_fields):
            raise ForwardDownstreamContractError("evidence reference fields mismatch")
        ref = artifact_ref({key: item[key] for key in ("artifact_id", "artifact_type", "sha256")})
        if (ref["artifact_id"], ref["artifact_type"], ref["sha256"]) not in allowed:
            raise ForwardDownstreamContractError("evidence reference is not explicitly bound")
        _text(item["evidence_item"], "evidence item", 500)
        _text(item["location"], "evidence location", 500)
        if item["availability"] not in {"AVAILABLE", "LIMITED", "UNAVAILABLE"}:
            raise ForwardDownstreamContractError("evidence availability is invalid")
        if item["limitation"] is not None:
            _text(item["limitation"], "evidence limitation", 2_000)
        if ref["artifact_type"] == "experiment-record/v5":
            if experiment is None and set(item) == base:
                result.append(item)
                continue
            if set(item) != base | experiment_fields:
                raise ForwardDownstreamContractError("v5 evidence requires exact block grounding")
            if blocks.get(item["evidence_block_id"]) != item["evidence_block_checksum"]:
                raise ForwardDownstreamContractError("v5 evidence block identity is invalid")
        elif set(item) != base:
            raise ForwardDownstreamContractError("non-Experiment evidence cannot claim v5 block identity")
        result.append(item)
    return result


def validate_claims(
    value: Any, sources: Mapping[str, Any], citations: list[dict[str, Any]],
    experiment: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 500:
        raise ForwardDownstreamContractError("claims must be a bounded non-empty list")
    citation_ids = {item["citation_id"] for item in citations}
    summary = experiment_summary(experiment, sources.get("experiment_record"))
    boundaries = set() if summary is None else set(summary["claim_boundaries"])
    seen: set[str] = set()
    result = []
    for raw in value:
        item = _object(raw, "claim")
        _exact(item, {
            "claim_id", "claim_type", "section", "claim_text", "support_status",
            "evidence_refs", "citation_ids", "limitations",
            "evidence_qualification", "claim_boundary_refs",
        }, "claim")
        claim_id = _text(item["claim_id"], "claim identity", 160)
        if claim_id in seen:
            raise ForwardDownstreamContractError("claim identities must be unique")
        seen.add(claim_id)
        if item["claim_type"] not in {"LITERATURE", "PROPOSAL", "RESULT"}:
            raise ForwardDownstreamContractError("claim type is invalid")
        if item["support_status"] not in _SUPPORT or item["evidence_qualification"] not in _QUALIFICATION:
            raise ForwardDownstreamContractError("claim support qualification is invalid")
        refs = validate_evidence_refs(item["evidence_refs"], sources, experiment)
        citations_used = _strings(item["citation_ids"], "claim citations")
        if not set(citations_used) <= citation_ids:
            raise ForwardDownstreamContractError("claim uses an unknown citation")
        limitations = _strings(item["limitations"], "claim limitations")
        boundary_refs = _strings(item["claim_boundary_refs"], "claim boundaries")
        if not set(boundary_refs) <= boundaries:
            raise ForwardDownstreamContractError("claim boundary violation")
        if item["support_status"] == "SUPPORTED" and not refs:
            raise ForwardDownstreamContractError("SUPPORTED claim requires exact evidence")
        if item["support_status"] == "UNAVAILABLE" and refs:
            raise ForwardDownstreamContractError("UNAVAILABLE claim cannot cite evidence")
        if item["claim_type"] == "RESULT":
            experiment_refs = [ref for ref in refs if ref["artifact_type"] == "experiment-record/v5"]
            qualification = item["evidence_qualification"]
            if item["support_status"] == "SUPPORTED" and not experiment_refs:
                raise ForwardDownstreamContractError("supported result lacks exact v5 block evidence")
            if qualification == "BOUNDED_SCIENTIFIC_CLAIM":
                if summary is None or summary["process_outcome"] != "SUCCEEDED" or summary["evaluation_validity"] != "VALID" or summary["scientific_evidence_status"] != "SUPPORTS_BOUNDED_FINDINGS" or not boundary_refs:
                    raise ForwardDownstreamContractError("bounded scientific claim exceeds v5 authority")
            elif qualification == "DESCRIPTIVE_OBSERVATION":
                if summary is None or summary["scientific_evidence_status"] == "NOT_AVAILABLE" or not limitations:
                    raise ForwardDownstreamContractError("descriptive observation must preserve v5 limitations")
            elif item["support_status"] == "SUPPORTED":
                raise ForwardDownstreamContractError("supported result needs an evidence qualification")
        result.append(item)
    return result


def _citations(value: Any, sources: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 500:
        raise ForwardDownstreamContractError("citations must be bounded")
    result = []
    seen = set()
    for raw in value:
        item = _object(raw, "citation")
        _exact(item, {"citation_id", "paper_id", "source_artifact", "evidence_scope", "reference_markdown"}, "citation")
        if item["citation_id"] in seen or item["evidence_scope"] not in {"METADATA_ONLY", "ABSTRACT"}:
            raise ForwardDownstreamContractError("citation identity or evidence scope is invalid")
        seen.add(item["citation_id"])
        if artifact_ref(item["source_artifact"], "selected-paper-library/v1") != sources["literature_library"]:
            raise ForwardDownstreamContractError("citation is outside exact literature input")
        result.append(item)
    return result


def validate_manuscript_draft_v4(
    value: Any, *, bound_inputs: Mapping[str, Any] | None = None,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = _object(value, MANUSCRIPT_DRAFT_V4)
    _exact(item, {
        "schema", "core_capability_maturity", "producer", "source_artifacts",
        "writing_brief", "evidence_map", "approved_outline", "outline_approval",
        "title", "content_markdown", "claims", "citations",
        "experiment_evidence_available", "experiment_evidence", "unsupported_areas",
        "limitations", "owner_review",
    }, MANUSCRIPT_DRAFT_V4)
    if item["schema"] != MANUSCRIPT_DRAFT_V4 or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise ForwardDownstreamContractError("manuscript-draft/v4 identity is invalid")
    producer = _object(item["producer"], "producer")
    if _WFI.fullmatch(str(producer.get("workflow_instance_id"))) is None:
        raise ForwardDownstreamContractError("producer Workflow identity is invalid")
    sources = _sources(item["source_artifacts"])
    if bound_inputs is not None:
        expected = {key: bound_inputs.get(key) for key in sources}
        if sources != expected:
            raise ForwardDownstreamContractError("manuscript sources differ from exact bindings")
    summary = validate_experiment_summary(item["experiment_evidence"], experiment, sources["experiment_record"])
    if item["experiment_evidence_available"] is not (summary is not None):
        raise ForwardDownstreamContractError("Experiment evidence availability is inconsistent")
    citations = _citations(item["citations"], sources)
    if experiment is None and summary is not None:
        if not isinstance(item["claims"], list) or not item["claims"]:
            raise ForwardDownstreamContractError("claims must be a bounded non-empty list")
    else:
        validate_claims(item["claims"], sources, citations, experiment)
    _text(item["content_markdown"], "manuscript content", 2_000_000)
    limitations = _strings(item["limitations"], "manuscript limitations")
    if summary is not None and not set(summary["limitations"]) <= set(limitations):
        raise ForwardDownstreamContractError("manuscript does not preserve v5 limitations")
    outline = _hash_box(item["approved_outline"], "approved Outline")
    approval = _exact_approval(
        item["outline_approval"], label="outline approval",
        fields={"outline_sha256", "brief_sha256", "evidence_map_sha256", "source_artifacts_sha256", "approved_at", "decision"},
        expected={
            "outline_sha256": outline["sha256"],
            "brief_sha256": canonical_hash(item["writing_brief"]),
            "evidence_map_sha256": canonical_hash(item["evidence_map"]),
            "source_artifacts_sha256": canonical_hash(sources),
            "decision": "APPROVED",
        },
    )
    draft_checksum = canonical_hash({
        "title": item["title"], "content_markdown": item["content_markdown"],
        "claims": item["claims"], "citations": item["citations"],
    })
    _exact_approval(
        item["owner_review"], label="Owner review",
        fields={"draft_sha256", "reviewed_at", "decision"},
        expected={"draft_sha256": draft_checksum, "decision": "APPROVED"},
    )
    return item


def manuscript_surface(value: Any) -> dict[str, Any]:
    manuscript = validate_manuscript_draft_v4(value)
    return {
        "sources": manuscript["source_artifacts"],
        "claims": manuscript["claims"],
        "sections": [item.get("section") for item in manuscript["claims"]],
        "evidence_refs": [ref for claim in manuscript["claims"] for ref in claim["evidence_refs"]],
        "experiment_evidence": manuscript["experiment_evidence"],
    }


def experiment_evidence_audit(
    manuscript: Mapping[str, Any], experiment: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    summary = manuscript.get("experiment_evidence")
    if summary is None:
        return None
    validate_experiment_summary(summary, experiment, summary["artifact"])
    return {
        "experiment_artifact": summary["artifact"],
        "process_outcome": summary["process_outcome"],
        "evaluation_validity": summary["evaluation_validity"],
        "scientific_evidence_status": summary["scientific_evidence_status"],
        "evidence_checksum": summary["evidence_checksum"],
        "claim_boundary_compliance": "VALIDATED_BY_EXACT_GROUNDING",
        "limitations_preserved": set(summary["limitations"]) <= set(manuscript["limitations"]),
    }


def validate_review_report_v3(
    value: Any, *, manuscript: Mapping[str, Any] | None = None,
    bound_inputs: Mapping[str, Any] | None = None,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = _object(value, REVIEW_REPORT_V3)
    _exact(item, {
        "schema", "core_capability_maturity", "producer", "source_manuscript",
        "supporting_artifacts", "review_scope", "scope_approval",
        "evidence_availability", "assessment", "summary", "issues", "limitations",
        "experiment_evidence_audit", "owner_review",
    }, REVIEW_REPORT_V3)
    if item["schema"] != REVIEW_REPORT_V3 or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise ForwardDownstreamContractError("review-report/v3 identity is invalid")
    if _WFI.fullmatch(str(_object(item["producer"], "Review producer").get("workflow_instance_id"))) is None:
        raise ForwardDownstreamContractError("Review producer identity is invalid")
    source_ref = artifact_ref(item["source_manuscript"], MANUSCRIPT_DRAFT_V4)
    support = [artifact_ref(raw) for raw in item["supporting_artifacts"]]
    if manuscript is None or bound_inputs is None:
        if item["assessment"] not in {"NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
            raise ForwardDownstreamContractError("Review assessment is invalid")
        scope = _hash_box(item["review_scope"], "Review Scope")
        approval = _exact_approval(
            item["scope_approval"], label="Scope approval",
            fields={"scope_sha256", "manuscript_sha256", "bound_artifacts_sha256", "approved_at", "decision"},
            expected={
                "scope_sha256": scope["sha256"], "manuscript_sha256": source_ref["sha256"],
                "bound_artifacts_sha256": canonical_hash(support), "decision": "APPROVED",
            },
        )
        result_checksum = canonical_hash({
            "source_manuscript": source_ref, "supporting_artifacts": support,
            "review_scope": scope, "scope_approval": approval,
            "evidence_availability": item["evidence_availability"],
            "experiment_evidence_audit": item["experiment_evidence_audit"],
            **{key: item[key] for key in ("assessment", "summary", "issues", "limitations")},
        })
        _exact_approval(
            item["owner_review"], label="Owner review",
            fields={"review_result_sha256", "reviewed_at", "decision"},
            expected={"review_result_sha256": result_checksum, "decision": "APPROVED"},
        )
        return item
    draft = validate_manuscript_draft_v4(
        manuscript,
        bound_inputs={key: bound_inputs.get(key) for key in ("research_idea", "literature_library", "experiment_record")},
        experiment=experiment,
    )
    manuscript_ref = artifact_ref(bound_inputs["manuscript"], MANUSCRIPT_DRAFT_V4)
    if source_ref != manuscript_ref:
        raise ForwardDownstreamContractError("Review refers to a different Draft")
    expected_support = [bound_inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in bound_inputs]
    if support != expected_support:
        raise ForwardDownstreamContractError("Review support differs from exact bindings")
    if draft["source_artifacts"].get("experiment_record") != bound_inputs.get("experiment_record"):
        raise ForwardDownstreamContractError("Review Experiment lineage differs from Draft")
    if item["experiment_evidence_audit"] != experiment_evidence_audit(draft, experiment):
        raise ForwardDownstreamContractError("Review v5 evidence audit is inconsistent")
    issue_sources = {**draft["source_artifacts"], "manuscript": source_ref}
    for issue in item["issues"]:
        issue = _object(issue, "Review issue")
        if issue.get("severity") not in {"MAJOR", "MINOR"}:
            raise ForwardDownstreamContractError("Review issue severity is invalid")
        validate_evidence_refs(issue.get("evidence_refs"), issue_sources, experiment)
    if item["assessment"] not in {"NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
        raise ForwardDownstreamContractError("Review assessment is invalid")
    scope = _hash_box(item["review_scope"], "Review Scope")
    approval = _exact_approval(
        item["scope_approval"], label="Scope approval",
        fields={"scope_sha256", "manuscript_sha256", "bound_artifacts_sha256", "approved_at", "decision"},
        expected={
            "scope_sha256": scope["sha256"], "manuscript_sha256": source_ref["sha256"],
            "bound_artifacts_sha256": canonical_hash(support), "decision": "APPROVED",
        },
    )
    result_checksum = canonical_hash({
        "source_manuscript": source_ref, "supporting_artifacts": support,
        "review_scope": scope, "scope_approval": approval,
        "evidence_availability": item["evidence_availability"],
        "experiment_evidence_audit": item["experiment_evidence_audit"],
        **{key: item[key] for key in ("assessment", "summary", "issues", "limitations")},
    })
    _exact_approval(
        item["owner_review"], label="Owner review",
        fields={"review_result_sha256", "reviewed_at", "decision"},
        expected={"review_result_sha256": result_checksum, "decision": "APPROVED"},
    )
    return item


def validate_manuscript_draft_v5(
    value: Any, *, prior_manuscript: Mapping[str, Any] | None = None,
    causal_review: Mapping[str, Any] | None = None,
    bound_inputs: Mapping[str, Any] | None = None,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = _object(value, MANUSCRIPT_DRAFT_V5)
    required = {
        "schema", "core_capability_maturity", "producer", "prior_manuscript",
        "causal_review", "supporting_artifacts", "revision_round", "writing_brief",
        "title", "content_markdown", "claims", "citations",
        "experiment_evidence_available", "experiment_evidence", "unsupported_areas",
        "limitations", "revision_plan", "revision_plan_approval", "issue_accounting",
        "remaining_blocking_issue_ids", "remaining_blocking_issue_count",
        "revision_limitations", "owner_review",
    }
    _exact(item, required, MANUSCRIPT_DRAFT_V5)
    if item["schema"] != MANUSCRIPT_DRAFT_V5 or item["core_capability_maturity"] != "REVIEWED_CORE" or item["revision_round"] != 1:
        raise ForwardDownstreamContractError("manuscript-draft/v5 identity is invalid")
    if _WFI.fullmatch(str(_object(item["producer"], "Revision producer").get("workflow_instance_id"))) is None:
        raise ForwardDownstreamContractError("Revision producer identity is invalid")
    prior_ref = artifact_ref(item["prior_manuscript"], MANUSCRIPT_DRAFT_V4)
    causal_ref = artifact_ref(item["causal_review"], REVIEW_REPORT_V3)
    if prior_manuscript is None or causal_review is None or bound_inputs is None:
        support = [artifact_ref(raw) for raw in item["supporting_artifacts"]]
        plan = _hash_box(item["revision_plan"], "Revision Plan")
        _exact_approval(
            item["revision_plan_approval"], label="Revision Plan approval",
            fields={"prior_manuscript_sha256", "causal_review_sha256", "issue_set_sha256", "revision_plan_sha256", "supporting_artifacts_sha256", "approved_at", "decision"},
            expected={
                "prior_manuscript_sha256": prior_ref["sha256"],
                "causal_review_sha256": causal_ref["sha256"],
                "revision_plan_sha256": plan["sha256"],
                "supporting_artifacts_sha256": canonical_hash(support), "decision": "APPROVED",
            },
        )
        accounting = item["issue_accounting"]
        if not isinstance(accounting, list) or item["remaining_blocking_issue_count"] != len(item["remaining_blocking_issue_ids"]):
            raise ForwardDownstreamContractError("Revision issue accounting is invalid")
        draft_checksum = canonical_hash({
            "title": item["title"], "content_markdown": item["content_markdown"],
            "claims": item["claims"], "citations": item["citations"],
        })
        _exact_approval(
            item["owner_review"], label="Owner review",
            fields={"revised_draft_sha256", "issue_accounting_sha256", "reviewed_at", "decision"},
            expected={
                "revised_draft_sha256": draft_checksum,
                "issue_accounting_sha256": canonical_hash(accounting), "decision": "APPROVED",
            },
        )
        return item
    prior = validate_manuscript_draft_v4(prior_manuscript)
    review = validate_review_report_v3(
        causal_review, manuscript=prior, bound_inputs={
            "manuscript": bound_inputs["prior_manuscript"],
            **{key: bound_inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in bound_inputs},
        }, experiment=experiment,
    )
    if artifact_ref(item["prior_manuscript"], MANUSCRIPT_DRAFT_V4) != bound_inputs["prior_manuscript"] or artifact_ref(item["causal_review"], REVIEW_REPORT_V3) != bound_inputs["causal_review"]:
        raise ForwardDownstreamContractError("Revision causal lineage differs from exact bindings")
    sources = {
        "research_idea": bound_inputs["research_idea"],
        "literature_library": bound_inputs["literature_library"],
        "experiment_record": bound_inputs.get("experiment_record"),
    }
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if sources[key] is not None]
    if item["supporting_artifacts"] != support:
        raise ForwardDownstreamContractError("Revision support differs from exact bindings")
    if item["writing_brief"] != prior["writing_brief"]:
        raise ForwardDownstreamContractError("Revision changed the approved Writing Brief")
    if item["experiment_evidence"] != prior["experiment_evidence"]:
        raise ForwardDownstreamContractError("Revision changed Experiment evidence authority")
    validate_experiment_summary(item["experiment_evidence"], experiment, sources["experiment_record"])
    citations = _citations(item["citations"], sources)
    validate_claims(item["claims"], sources, citations, experiment)
    issues = {issue["issue_id"]: issue for issue in review["issues"]}
    accounting = item["issue_accounting"]
    if not isinstance(accounting, list) or {entry.get("issue_id") for entry in accounting} != set(issues):
        raise ForwardDownstreamContractError("Revision must account for every causal Review issue")
    allowed = {"ADDRESSED", "PARTIALLY_ADDRESSED", "NOT_ADDRESSED", "NOT_APPLICABLE"}
    if any(entry.get("disposition") not in allowed for entry in accounting):
        raise ForwardDownstreamContractError("Revision issue disposition is invalid")
    plan = _hash_box(item["revision_plan"], "Revision Plan")
    approval = _exact_approval(
        item["revision_plan_approval"], label="Revision Plan approval",
        fields={"prior_manuscript_sha256", "causal_review_sha256", "issue_set_sha256", "revision_plan_sha256", "supporting_artifacts_sha256", "approved_at", "decision"},
        expected={
            "prior_manuscript_sha256": bound_inputs["prior_manuscript"]["sha256"],
            "causal_review_sha256": bound_inputs["causal_review"]["sha256"],
            "issue_set_sha256": canonical_hash(review["issues"]),
            "revision_plan_sha256": plan["sha256"],
            "supporting_artifacts_sha256": canonical_hash(support),
            "decision": "APPROVED",
        },
    )
    disposition = {entry["issue_id"]: entry["disposition"] for entry in accounting}
    remaining = [issue["issue_id"] for issue in review["issues"] if issue.get("blocking") and disposition[issue["issue_id"]] != "ADDRESSED"]
    if item["remaining_blocking_issue_ids"] != remaining or item["remaining_blocking_issue_count"] != len(remaining):
        raise ForwardDownstreamContractError("remaining blocking issue accounting is inconsistent")
    if item["experiment_evidence_available"] is not (sources["experiment_record"] is not None):
        raise ForwardDownstreamContractError("Experiment evidence availability is inconsistent")
    draft_checksum = canonical_hash({
        "title": item["title"], "content_markdown": item["content_markdown"],
        "claims": item["claims"], "citations": item["citations"],
    })
    _exact_approval(
        item["owner_review"], label="Owner review",
        fields={"revised_draft_sha256", "issue_accounting_sha256", "reviewed_at", "decision"},
        expected={
            "revised_draft_sha256": draft_checksum,
            "issue_accounting_sha256": canonical_hash(accounting), "decision": "APPROVED",
        },
    )
    return item
