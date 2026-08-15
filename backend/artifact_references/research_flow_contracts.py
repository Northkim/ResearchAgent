"""Canonical Artifact contracts for the owner-ratified full research flow.

Only Literature Search and Idea Discovery are production Workflows in F1A.
The downstream schemas and dependency maps in this module are validation
contracts for later immutable Workflow versions, not Registry seeds.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping

from backend.project_workspaces.contracts import CoreCapabilityMaturity
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes

SELECTED_RESEARCH_IDEA_TYPE = "selected-research-idea/v1"
SELECTED_RESEARCH_IDEA_SCHEMA = "selected-research-idea/v1"
MANUSCRIPT_DRAFT_TYPE = "manuscript-draft/v1"
MANUSCRIPT_DRAFT_SCHEMA = "manuscript-draft/v1"
REVIEW_REPORT_TYPE = "review-report/v1"
REVIEW_REPORT_SCHEMA = "review-report/v1"
EXPERIMENT_RECORD_TYPE = "experiment-record/v1"
EXPERIMENT_RECORD_SCHEMA = "experiment-record/v1"
EXPERIMENT_RECORD_V2_TYPE = "experiment-record/v2"
EXPERIMENT_RECORD_V2_SCHEMA = "experiment-record/v2"
SELECTED_PAPER_LIBRARY_TYPE = "selected-paper-library/v1"
CANDIDATE_IDEAS_SCHEMA = "candidate-ideas/v0.1"
JSON_MEDIA_TYPE = "application/json"

_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_CHECKSUM = re.compile(r"^sha256:[0-9a-f]{64}$")
_ARTIFACT_TYPE = re.compile(
    r"^[a-z][a-z0-9._-]{1,139}(?:/v[0-9]+(?:\.[0-9]+)?)?$"
)
_RESOURCE_ID = re.compile(r"^resource-[0-9a-f]{32}$")
_ATTEMPT_ID = re.compile(r"^attempt-[0-9a-f]{32}$")
_IDEA_ID = re.compile(r"^idea-[0-9]{3,}$")
_CANDIDATE_ID = re.compile(r"^candidate-[0-9a-f]{16,64}$")
_IDEA_STATUSES = {"candidate", "shortlisted", "selected", "rejected"}
_RECOMMENDATIONS = {"REVISION", "ACCEPT_CURRENT_DRAFT", "INSUFFICIENT_EVIDENCE"}
_PRIORITIES = {"MAJOR", "MINOR"}
_EXPERIMENT_MODES = {"IDEA_EXPERIMENT", "PAPER_REPRODUCTION"}
_EXECUTION_STATUSES = {
    "PLACEHOLDER_NOT_EXECUTED", "PLANNED", "RUNNING", "COMPLETED", "FAILED"
}


class ResearchFlowContractError(ValueError):
    """An immutable research-flow Artifact violates its reviewed contract."""


@dataclass(frozen=True, slots=True)
class ArtifactContract:
    artifact_type: str
    schema: str
    media_type: str
    validator: Callable[[Mapping[str, Any]], dict[str, Any]]
    production_producer_available: bool


@dataclass(frozen=True, slots=True)
class FutureDependency:
    requirement_key: str
    artifact_type: str
    required: bool
    cardinality: str = "ONE"
    selection_policy: str = "EXPLICIT_SPECIFIC_ARTIFACT"
    project_scope: str = "SAME_PROJECT"
    identity_binding: str = "ARTIFACT_ID_AND_CHECKSUM"


@dataclass(frozen=True, slots=True)
class FutureWorkflowContract:
    stable_key: str
    inputs: tuple[FutureDependency, ...]
    output_artifact_type: str
    production_seeded: bool = False


def validate_selected_research_idea(
    value: Mapping[str, Any],
    *,
    candidate_ideas: Mapping[str, Any] | None = None,
    candidate_ideas_bytes: bytes | None = None,
    literature_library: Mapping[str, Any] | None = None,
    expected_literature_artifact_id: str | None = None,
    expected_literature_checksum: str | None = None,
    producer_maturity: CoreCapabilityMaturity = CoreCapabilityMaturity.REVIEWED_CORE,
) -> dict[str, Any]:
    result = _object(value, "selected research idea")
    _exact_keys(
        result,
        {
            "schema", "core_capability_maturity", "source_candidate_ideas",
            "source_literature_artifact", "selected_idea",
        },
        "selected research idea",
    )
    if result["schema"] != SELECTED_RESEARCH_IDEA_SCHEMA:
        raise ResearchFlowContractError("selected research idea schema mismatch")
    maturity = _maturity(result["core_capability_maturity"])
    if maturity is not producer_maturity:
        raise ResearchFlowContractError(
            "Artifact maturity does not match the producer Workflow Version"
        )
    if maturity is not CoreCapabilityMaturity.REVIEWED_CORE:
        raise ResearchFlowContractError("selected research idea requires REVIEWED_CORE")
    source_candidates = _object(result["source_candidate_ideas"], "candidate source")
    _exact_keys(
        source_candidates, {"schema", "relative_path", "sha256"}, "candidate source"
    )
    if source_candidates["schema"] != CANDIDATE_IDEAS_SCHEMA:
        raise ResearchFlowContractError("candidate source schema mismatch")
    if source_candidates["relative_path"] != "outputs/candidate_ideas.json":
        raise ResearchFlowContractError("candidate source path mismatch")
    _checksum(source_candidates["sha256"], "candidate source checksum")
    source_literature = _artifact_ref(
        result["source_literature_artifact"],
        expected_type=SELECTED_PAPER_LIBRARY_TYPE,
        label="literature source",
    )
    if expected_literature_artifact_id is not None and (
        source_literature["artifact_id"] != expected_literature_artifact_id
    ):
        raise ResearchFlowContractError("literature source Artifact ID mismatch")
    if expected_literature_checksum is not None and (
        source_literature["sha256"] != expected_literature_checksum
    ):
        raise ResearchFlowContractError("literature source checksum mismatch")
    selected = _candidate_idea(result["selected_idea"])
    if selected["status"] != "selected":
        raise ResearchFlowContractError("selected_idea must have selected status")
    if candidate_ideas is not None:
        ideas_value = validate_candidate_ideas(
            candidate_ideas,
            literature_library=literature_library,
            expected_artifact_id=source_literature["artifact_id"],
            expected_checksum=source_literature["sha256"],
        )
        selected_values = [item for item in ideas_value["ideas"] if item["status"] == "selected"]
        if len(selected_values) != 1:
            raise ResearchFlowContractError("exactly one candidate idea must be selected")
        if selected_values[0] != selected:
            raise ResearchFlowContractError("selected_idea is not the exact candidate record")
    if candidate_ideas_bytes is not None and (
        sha256_bytes(candidate_ideas_bytes) != source_candidates["sha256"]
    ):
        raise ResearchFlowContractError("candidate source checksum mismatch")
    return _copy_json(result)


def validate_candidate_ideas(
    value: Mapping[str, Any],
    *,
    literature_library: Mapping[str, Any] | None = None,
    expected_artifact_id: str | None = None,
    expected_checksum: str | None = None,
) -> dict[str, Any]:
    result = _object(value, "candidate ideas")
    _exact_keys(result, {"schema", "source_artifact", "ideas"}, "candidate ideas")
    if result["schema"] != CANDIDATE_IDEAS_SCHEMA:
        raise ResearchFlowContractError("candidate ideas schema mismatch")
    source = _artifact_ref(
        result["source_artifact"],
        expected_type=SELECTED_PAPER_LIBRARY_TYPE,
        label="candidate ideas source",
    )
    if expected_artifact_id is not None and source["artifact_id"] != expected_artifact_id:
        raise ResearchFlowContractError("candidate ideas source Artifact ID mismatch")
    if expected_checksum is not None and source["sha256"] != expected_checksum:
        raise ResearchFlowContractError("candidate ideas source checksum mismatch")
    ideas = result["ideas"]
    if not isinstance(ideas, list) or len(ideas) > 100:
        raise ResearchFlowContractError("candidate ideas are outside reviewed bounds")
    source_ids = None if literature_library is None else _literature_candidate_ids(literature_library)
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for raw in ideas:
        idea = _candidate_idea(raw)
        if idea["idea_id"] in seen:
            raise ResearchFlowContractError("duplicate candidate idea ID")
        seen.add(idea["idea_id"])
        if source_ids is not None and any(item not in source_ids for item in idea["literature_basis"]):
            raise ResearchFlowContractError("candidate idea literature basis is unknown")
        validated.append(idea)
    return {"schema": CANDIDATE_IDEAS_SCHEMA, "source_artifact": source, "ideas": validated}


def build_selected_research_idea(
    *,
    candidate_ideas: Mapping[str, Any],
    candidate_ideas_bytes: bytes,
    literature_library: Mapping[str, Any],
    literature_artifact_id: str,
    literature_checksum: str,
) -> dict[str, Any]:
    ideas = validate_candidate_ideas(
        candidate_ideas,
        literature_library=literature_library,
        expected_artifact_id=literature_artifact_id,
        expected_checksum=literature_checksum,
    )
    selected = [item for item in ideas["ideas"] if item["status"] == "selected"]
    if len(selected) != 1:
        raise ResearchFlowContractError("exactly one candidate idea must be selected")
    artifact = {
        "schema": SELECTED_RESEARCH_IDEA_SCHEMA,
        "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        "source_candidate_ideas": {
            "schema": CANDIDATE_IDEAS_SCHEMA,
            "relative_path": "outputs/candidate_ideas.json",
            "sha256": sha256_bytes(candidate_ideas_bytes),
        },
        "source_literature_artifact": {
            "artifact_id": literature_artifact_id,
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "sha256": literature_checksum,
        },
        "selected_idea": selected[0],
    }
    return validate_selected_research_idea(
        artifact,
        candidate_ideas=ideas,
        candidate_ideas_bytes=candidate_ideas_bytes,
        literature_library=literature_library,
        expected_literature_artifact_id=literature_artifact_id,
        expected_literature_checksum=literature_checksum,
    )


def validate_manuscript_draft(
    value: Mapping[str, Any],
    *,
    producer_maturity: CoreCapabilityMaturity | None = None,
) -> dict[str, Any]:
    result = _object(value, "manuscript draft")
    _exact_keys(
        result,
        {"schema", "core_capability_maturity", "source_artifacts", "title", "content_markdown"},
        "manuscript draft",
    )
    if result["schema"] != MANUSCRIPT_DRAFT_SCHEMA:
        raise ResearchFlowContractError("manuscript draft schema mismatch")
    maturity = _maturity(result["core_capability_maturity"])
    _require_producer_maturity(maturity, producer_maturity)
    sources = _object(result["source_artifacts"], "manuscript sources")
    _exact_keys(
        sources,
        {"research_idea", "literature_library", "experiment_record", "review_feedback", "prior_manuscript"},
        "manuscript sources",
    )
    normalized = {
        "research_idea": _artifact_ref(sources["research_idea"], expected_type=SELECTED_RESEARCH_IDEA_TYPE, label="research idea"),
        "literature_library": _artifact_ref(sources["literature_library"], expected_type=SELECTED_PAPER_LIBRARY_TYPE, label="literature library"),
        "experiment_record": _optional_ref(sources["experiment_record"], EXPERIMENT_RECORD_TYPE, "experiment record"),
        "review_feedback": _optional_ref(sources["review_feedback"], REVIEW_REPORT_TYPE, "review feedback"),
        "prior_manuscript": _optional_ref(sources["prior_manuscript"], MANUSCRIPT_DRAFT_TYPE, "prior manuscript"),
    }
    _unique_artifact_roles(normalized)
    _nonempty(result["title"], "manuscript title")
    if not isinstance(result["content_markdown"], str):
        raise ResearchFlowContractError("content_markdown must be a string")
    return {
        "schema": MANUSCRIPT_DRAFT_SCHEMA,
        "core_capability_maturity": result["core_capability_maturity"],
        "source_artifacts": normalized,
        "title": result["title"],
        "content_markdown": result["content_markdown"],
    }


def validate_review_report(
    value: Mapping[str, Any],
    *,
    producer_maturity: CoreCapabilityMaturity | None = None,
) -> dict[str, Any]:
    result = _object(value, "review report")
    _exact_keys(
        result,
        {"schema", "core_capability_maturity", "source_manuscript", "supporting_artifacts", "summary", "major_issues", "minor_issues", "requested_revisions", "recommendation"},
        "review report",
    )
    if result["schema"] != REVIEW_REPORT_SCHEMA:
        raise ResearchFlowContractError("review report schema mismatch")
    maturity = _maturity(result["core_capability_maturity"])
    _require_producer_maturity(maturity, producer_maturity)
    manuscript = _artifact_ref(result["source_manuscript"], expected_type=MANUSCRIPT_DRAFT_TYPE, label="source manuscript")
    supporting = _artifact_ref_list(result["supporting_artifacts"], "supporting artifacts")
    if any(item["artifact_id"] == manuscript["artifact_id"] for item in supporting):
        raise ResearchFlowContractError("source manuscript cannot repeat as supporting evidence")
    _nonempty(result["summary"], "review summary")
    issue_ids: set[str] = set()
    major = _issues(result["major_issues"], issue_ids, "major issues")
    minor = _issues(result["minor_issues"], issue_ids, "minor issues")
    revisions = _revisions(result["requested_revisions"])
    if result["recommendation"] not in _RECOMMENDATIONS:
        raise ResearchFlowContractError("review recommendation is invalid")
    return {
        "schema": REVIEW_REPORT_SCHEMA,
        "core_capability_maturity": result["core_capability_maturity"],
        "source_manuscript": manuscript,
        "supporting_artifacts": supporting,
        "summary": result["summary"],
        "major_issues": major,
        "minor_issues": minor,
        "requested_revisions": revisions,
        "recommendation": result["recommendation"],
    }


def validate_experiment_record(
    value: Mapping[str, Any],
    *,
    producer_maturity: CoreCapabilityMaturity | None = None,
) -> dict[str, Any]:
    result = _object(value, "experiment record")
    _exact_keys(
        result,
        {"schema", "core_capability_maturity", "mode", "source_artifacts", "execution_status", "plan", "actual_results", "limitations"},
        "experiment record",
    )
    if result["schema"] != EXPERIMENT_RECORD_SCHEMA:
        raise ResearchFlowContractError("experiment record schema mismatch")
    maturity = _maturity(result["core_capability_maturity"])
    _require_producer_maturity(maturity, producer_maturity)
    if result["mode"] not in _EXPERIMENT_MODES:
        raise ResearchFlowContractError("experiment mode is invalid")
    sources = _artifact_ref_list(result["source_artifacts"], "experiment sources")
    if not sources:
        raise ResearchFlowContractError("experiment record requires source provenance")
    if result["execution_status"] not in _EXECUTION_STATUSES:
        raise ResearchFlowContractError("experiment execution status is invalid")
    if maturity is CoreCapabilityMaturity.SCAFFOLD_CORE and (
        result["execution_status"] != "PLACEHOLDER_NOT_EXECUTED"
        or result["actual_results"] is not None
    ):
        raise ResearchFlowContractError("SCAFFOLD_CORE cannot claim experiment execution")
    plan = _object(result["plan"], "experiment plan")
    _exact_keys(plan, {"objective", "hypothesis", "method", "metrics", "baselines"}, "experiment plan")
    _nonempty(plan["objective"], "experiment objective")
    if plan["hypothesis"] is not None:
        _nonempty(plan["hypothesis"], "experiment hypothesis")
    _nonempty(plan["method"], "experiment method")
    metrics = _string_list(plan["metrics"], "experiment metrics")
    baselines = _string_list(plan["baselines"], "experiment baselines")
    actual = None if result["actual_results"] is None else _actual_results(result["actual_results"])
    limitations = _string_list(result["limitations"], "experiment limitations")
    return {
        "schema": EXPERIMENT_RECORD_SCHEMA,
        "core_capability_maturity": maturity.value,
        "mode": result["mode"],
        "source_artifacts": sources,
        "execution_status": result["execution_status"],
        "plan": {"objective": plan["objective"], "hypothesis": plan["hypothesis"], "method": plan["method"], "metrics": metrics, "baselines": baselines},
        "actual_results": actual,
        "limitations": limitations,
    }


def validate_experiment_record_v2(
    value: Mapping[str, Any],
    *,
    producer_maturity: CoreCapabilityMaturity | None = None,
) -> dict[str, Any]:
    """Validate the immutable, approval-bound Real Experiment Output."""

    result = _object(value, "experiment record v2")
    _exact_keys(result, {
        "schema", "core_capability_maturity", "mode", "source_artifacts",
        "requirements", "approved_plan", "approval", "execution",
        "evaluation", "result_status", "limitations",
    }, "experiment record v2")
    if result["schema"] != EXPERIMENT_RECORD_V2_SCHEMA:
        raise ResearchFlowContractError("experiment record v2 schema mismatch")
    maturity = _maturity(result["core_capability_maturity"])
    _require_producer_maturity(maturity, producer_maturity)
    if maturity is not CoreCapabilityMaturity.REVIEWED_CORE:
        raise ResearchFlowContractError("real experiment output requires REVIEWED_CORE")
    if result["mode"] != "IDEA_EXPERIMENT":
        raise ResearchFlowContractError("experiment record v2 mode is invalid")
    sources = _artifact_ref_list(result["source_artifacts"], "experiment v2 sources")
    if not sources or sources[0]["artifact_type"] != SELECTED_RESEARCH_IDEA_TYPE:
        raise ResearchFlowContractError("experiment v2 requires the exact selected Idea first")

    requirements = _checksummed_value(result["requirements"], "requirements")
    plan = _checksummed_value(result["approved_plan"], "approved plan")
    _validate_requirements(requirements["value"])
    _validate_experiment_plan(plan["value"], sources, requirements["sha256"])

    approval = _object(result["approval"], "approval")
    _exact_keys(approval, {
        "sha256", "plan_sha256", "attempt_id", "approved_at", "decision", "scope",
    }, "approval")
    _checksum(approval["sha256"], "approval checksum")
    _attempt(approval["attempt_id"])
    _time(approval["approved_at"], "approval time")
    if approval["plan_sha256"] != plan["sha256"] or approval["decision"] != "APPROVED" or approval["scope"] != "ONE_ATTEMPT":
        raise ResearchFlowContractError("approval is not bound to the exact plan and one attempt")
    approval_payload = dict(approval)
    approval_checksum = approval_payload.pop("sha256")
    if canonical_hash(approval_payload) != approval_checksum:
        raise ResearchFlowContractError("approval checksum mismatch")

    execution = _object(result["execution"], "execution")
    _exact_keys(execution, {
        "attempt_id", "approval_sha256", "status", "started_at", "completed_at",
        "argv", "working_directory", "environment", "network_policy", "limits",
        "exit_code", "signal", "stdout", "stderr",
    }, "execution")
    _attempt(execution["attempt_id"])
    if execution["attempt_id"] != approval["attempt_id"] or execution["approval_sha256"] != approval["sha256"]:
        raise ResearchFlowContractError("execution identity differs from approval")
    if execution["status"] not in {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED", "INTERRUPTED"}:
        raise ResearchFlowContractError("execution status is invalid")
    started = _time(execution["started_at"], "execution start")
    completed = _time(execution["completed_at"], "execution completion")
    if completed < started:
        raise ResearchFlowContractError("execution timestamps are not monotonic")
    argv = _string_list(execution["argv"], "execution argv")
    if not argv or argv != plan["value"]["argv"]:
        raise ResearchFlowContractError("execution command differs from approved plan")
    if execution["working_directory"] != plan["value"]["working_directory"]:
        raise ResearchFlowContractError("execution working directory differs from plan")
    if execution["environment"] != plan["value"]["environment"] or execution["limits"] != plan["value"]["limits"]:
        raise ResearchFlowContractError("execution environment or limits differ from plan")
    if execution["network_policy"] != "DISABLED" or plan["value"]["network_policy"] != "DISABLED":
        raise ResearchFlowContractError("real experiment network policy must be disabled")
    if execution["exit_code"] is not None and (isinstance(execution["exit_code"], bool) or not isinstance(execution["exit_code"], int)):
        raise ResearchFlowContractError("execution exit code is invalid")
    if execution["signal"] is not None:
        _nonempty(execution["signal"], "execution signal")
    stdout = _evidence_ref(execution["stdout"], "stdout")
    stderr = _evidence_ref(execution["stderr"], "stderr")

    evaluation = _object(result["evaluation"], "evaluation")
    _exact_keys(evaluation, {"status", "metrics", "raw_result", "summary"}, "evaluation")
    if evaluation["status"] not in {"VALID", "INVALID", "NOT_RUN"}:
        raise ResearchFlowContractError("evaluation status is invalid")
    metrics = _result_metrics(evaluation["metrics"])
    raw_result = None if evaluation["raw_result"] is None else _evidence_ref(evaluation["raw_result"], "raw result")
    _nonempty(evaluation["summary"], "evaluation summary")
    if evaluation["status"] == "VALID" and raw_result is None:
        raise ResearchFlowContractError("valid evaluation requires raw result evidence")
    if result["result_status"] not in {"SUCCEEDED", "FAILED", "PARTIAL"}:
        raise ResearchFlowContractError("result status is invalid")
    if result["result_status"] == "SUCCEEDED" and (
        execution["status"] != "SUCCEEDED" or execution["exit_code"] != 0
        or evaluation["status"] != "VALID"
    ):
        raise ResearchFlowContractError("successful result lacks execution and evaluation proof")
    if execution["status"] == "SUCCEEDED" and evaluation["status"] == "INVALID" and result["result_status"] != "PARTIAL":
        raise ResearchFlowContractError("invalid evaluation after process success must be partial")
    limitations = _string_list(result["limitations"], "experiment v2 limitations")
    return {
        "schema": EXPERIMENT_RECORD_V2_SCHEMA,
        "core_capability_maturity": maturity.value,
        "mode": result["mode"],
        "source_artifacts": sources,
        "requirements": requirements,
        "approved_plan": plan,
        "approval": dict(approval),
        "execution": {**execution, "argv": argv, "stdout": stdout, "stderr": stderr},
        "evaluation": {**evaluation, "metrics": metrics, "raw_result": raw_result},
        "result_status": result["result_status"],
        "limitations": limitations,
    }


def validate_writing_review_revision(
    *, manuscript: Mapping[str, Any], review: Mapping[str, Any]
) -> None:
    draft = validate_manuscript_draft(manuscript)
    report = validate_review_report(review)
    prior = draft["source_artifacts"]["prior_manuscript"]
    feedback = draft["source_artifacts"]["review_feedback"]
    if prior is None or feedback is None:
        raise ResearchFlowContractError("a reviewed revision requires prior manuscript and review")
    if report["source_manuscript"] != prior:
        raise ResearchFlowContractError("review report refers to a different prior manuscript")
    if feedback["artifact_type"] != REVIEW_REPORT_TYPE:
        raise ResearchFlowContractError("review feedback type mismatch")


def canonical_artifact_bytes(value: Mapping[str, Any]) -> bytes:
    return canonical_json(value).encode("utf-8")


def _candidate_idea(value: Any) -> dict[str, Any]:
    item = _object(value, "candidate idea")
    fields = {
        "idea_id", "title", "research_question", "motivation", "literature_basis",
        "observed_gap", "proposed_direction", "assumptions", "risks",
        "validation_needed", "status",
    }
    _exact_keys(item, fields, "candidate idea")
    if not isinstance(item["idea_id"], str) or not _IDEA_ID.fullmatch(item["idea_id"]):
        raise ResearchFlowContractError("candidate idea ID is invalid")
    if item["status"] not in _IDEA_STATUSES:
        raise ResearchFlowContractError("candidate idea status is invalid")
    for field in ("title", "research_question", "motivation", "observed_gap", "proposed_direction"):
        _nonempty(item[field], f"candidate idea {field}")
    basis = item["literature_basis"]
    if not isinstance(basis, list) or not basis or any(
        not isinstance(entry, str) or not _CANDIDATE_ID.fullmatch(entry) for entry in basis
    ):
        raise ResearchFlowContractError("candidate idea literature basis is invalid")
    if len(basis) != len(set(basis)):
        raise ResearchFlowContractError("candidate idea literature basis is duplicated")
    for field in ("assumptions", "risks", "validation_needed"):
        _string_list(item[field], f"candidate idea {field}")
    return _copy_json(item)


def _literature_candidate_ids(value: Mapping[str, Any]) -> set[str]:
    library = _object(value, "selected paper library")
    if library.get("schema") != SELECTED_PAPER_LIBRARY_TYPE:
        raise ResearchFlowContractError("selected paper library schema mismatch")
    papers = library.get("papers")
    if not isinstance(papers, list):
        raise ResearchFlowContractError("selected paper library papers must be an array")
    ids: set[str] = set()
    for item in papers:
        if not isinstance(item, Mapping) or set(item) != {"candidate_id", "paper", "selection"}:
            raise ResearchFlowContractError("selected paper library entry mismatch")
        candidate_id = item["candidate_id"]
        if not isinstance(candidate_id, str) or not _CANDIDATE_ID.fullmatch(candidate_id) or candidate_id in ids:
            raise ResearchFlowContractError("selected paper candidate identity is invalid")
        if not isinstance(item["paper"], Mapping) or item["paper"].get("candidate_id") != candidate_id:
            raise ResearchFlowContractError("selected paper record identity mismatch")
        if not isinstance(item["selection"], Mapping) or item["selection"].get("candidate_id") != candidate_id:
            raise ResearchFlowContractError("selected paper decision identity mismatch")
        ids.add(candidate_id)
    return ids


def _artifact_ref(value: Any, *, expected_type: str | None, label: str) -> dict[str, str]:
    item = _object(value, label)
    _exact_keys(item, {"artifact_id", "artifact_type", "sha256"}, label)
    if not isinstance(item["artifact_id"], str) or not _ARTIFACT_ID.fullmatch(item["artifact_id"]):
        raise ResearchFlowContractError(f"{label} Artifact ID is invalid")
    if not isinstance(item["artifact_type"], str) or not _ARTIFACT_TYPE.fullmatch(item["artifact_type"]):
        raise ResearchFlowContractError(f"{label} Artifact type is invalid")
    if expected_type is not None and item["artifact_type"] != expected_type:
        raise ResearchFlowContractError(f"{label} Artifact type mismatch")
    _checksum(item["sha256"], f"{label} checksum")
    return dict(item)


def _optional_ref(value: Any, expected_type: str, label: str) -> dict[str, str] | None:
    return None if value is None else _artifact_ref(value, expected_type=expected_type, label=label)


def _artifact_ref_list(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 100:
        raise ResearchFlowContractError(f"{label} must be a bounded array")
    result = [_artifact_ref(item, expected_type=None, label=label) for item in value]
    if len({item["artifact_id"] for item in result}) != len(result):
        raise ResearchFlowContractError(f"{label} contain duplicate Artifact IDs")
    return result


def _issues(value: Any, seen: set[str], label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 100:
        raise ResearchFlowContractError(f"{label} must be a bounded array")
    result = []
    for raw in value:
        item = _object(raw, label)
        _exact_keys(item, {"issue_id", "title", "description"}, label)
        for field in ("issue_id", "title", "description"):
            _nonempty(item[field], f"{label} {field}")
        if item["issue_id"] in seen:
            raise ResearchFlowContractError("duplicate review issue ID")
        seen.add(item["issue_id"])
        result.append(dict(item))
    return result


def _revisions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 100:
        raise ResearchFlowContractError("requested revisions must be a bounded array")
    seen: set[str] = set()
    result = []
    for raw in value:
        item = _object(raw, "requested revision")
        _exact_keys(item, {"revision_id", "description", "priority"}, "requested revision")
        _nonempty(item["revision_id"], "revision ID")
        _nonempty(item["description"], "revision description")
        if item["revision_id"] in seen:
            raise ResearchFlowContractError("duplicate requested revision ID")
        if item["priority"] not in _PRIORITIES:
            raise ResearchFlowContractError("requested revision priority is invalid")
        seen.add(item["revision_id"])
        result.append(dict(item))
    return result


def _actual_results(value: Any) -> dict[str, Any]:
    result = _object(value, "actual results")
    _exact_keys(result, {"summary", "metrics", "observations"}, "actual results")
    _nonempty(result["summary"], "actual result summary")
    raw_metrics = result["metrics"]
    if not isinstance(raw_metrics, list) or len(raw_metrics) > 100:
        raise ResearchFlowContractError("actual result metrics must be a bounded array")
    metrics = []
    for raw in raw_metrics:
        metric = _object(raw, "actual result metric")
        _exact_keys(metric, {"name", "value", "unit"}, "actual result metric")
        _nonempty(metric["name"], "metric name")
        if isinstance(metric["value"], bool) or not isinstance(metric["value"], (str, int, float)):
            raise ResearchFlowContractError("metric value must be a number or string")
        if isinstance(metric["value"], float) and not math.isfinite(metric["value"]):
            raise ResearchFlowContractError("metric value must be finite")
        if metric["unit"] is not None:
            _nonempty(metric["unit"], "metric unit")
        metrics.append(dict(metric))
    return {
        "summary": result["summary"],
        "metrics": metrics,
        "observations": _string_list(result["observations"], "actual result observations"),
    }


def _checksummed_value(value: Any, label: str) -> dict[str, Any]:
    item = _object(value, label)
    _exact_keys(item, {"sha256", "value"}, label)
    _checksum(item["sha256"], f"{label} checksum")
    payload = _copy_json(_object(item["value"], f"{label} value"))
    if canonical_hash(payload) != item["sha256"]:
        raise ResearchFlowContractError(f"{label} checksum mismatch")
    return {"sha256": item["sha256"], "value": payload}


def _validate_requirements(value: Any) -> None:
    item = _object(value, "experiment requirements")
    _exact_keys(item, {
        "research_question", "hypothesis", "scientific_inputs", "configuration",
        "seeds", "repetitions", "metrics", "runtime", "limits",
        "stopping_conditions",
    }, "experiment requirements")
    _nonempty(item["research_question"], "requirements research question")
    if item["hypothesis"] is not None:
        _nonempty(item["hypothesis"], "requirements hypothesis")
    if not isinstance(item["scientific_inputs"], list) or not item["scientific_inputs"]:
        raise ResearchFlowContractError("requirements scientific inputs are invalid")
    for raw in item["scientific_inputs"]:
        need = _object(raw, "scientific input")
        _exact_keys(need, {"kind", "role", "required"}, "scientific input")
        if need["kind"] not in {"SOURCE_CODE", "DATASET", "EVENTS", "MODEL", "CHECKPOINT", "BASELINE"} or not isinstance(need["required"], bool):
            raise ResearchFlowContractError("scientific input is invalid")
        _nonempty(need["role"], "scientific input role")
    if not isinstance(item["configuration"], Mapping):
        raise ResearchFlowContractError("requirements configuration must be an object")
    if not isinstance(item["seeds"], list) or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in item["seeds"]):
        raise ResearchFlowContractError("requirements seeds are invalid")
    if isinstance(item["repetitions"], bool) or not isinstance(item["repetitions"], int) or not 1 <= item["repetitions"] <= 100:
        raise ResearchFlowContractError("requirements repetitions are invalid")
    _metric_definitions(item["metrics"])
    _nonempty(item["runtime"], "requirements runtime")
    _limits(item["limits"])
    _string_list(item["stopping_conditions"], "requirements stopping conditions")


def _validate_experiment_plan(value: Any, sources: list[dict[str, str]], requirements_checksum: str) -> None:
    plan = _object(value, "experiment plan")
    _exact_keys(plan, {
        "research_question", "hypothesis", "requirements_sha256", "source_artifacts",
        "resource", "entrypoint", "argv", "working_directory", "configuration",
        "seeds", "repetitions", "metrics", "environment", "network_policy",
        "limits", "stopping_conditions", "known_limitations",
    }, "experiment plan")
    _nonempty(plan["research_question"], "plan research question")
    if plan["hypothesis"] is not None:
        _nonempty(plan["hypothesis"], "plan hypothesis")
    if plan["requirements_sha256"] != requirements_checksum or plan["source_artifacts"] != sources:
        raise ResearchFlowContractError("plan input identity mismatch")
    resource = _object(plan["resource"], "plan resource")
    _exact_keys(resource, {
        "resource_id", "resource_kind", "provider", "locator", "exact_revision",
        "content_checksum", "package_manifest_checksum", "entrypoint_checksum",
        "lock_checksum",
    }, "plan resource")
    if not isinstance(resource["resource_id"], str) or not _RESOURCE_ID.fullmatch(resource["resource_id"]):
        raise ResearchFlowContractError("plan Resource ID is invalid")
    if resource["resource_kind"] != "SOURCE_REPOSITORY" or resource["provider"] != "GITHUB":
        raise ResearchFlowContractError("plan Resource mode is unsupported")
    for field in ("locator", "exact_revision"):
        _nonempty(resource[field], f"plan Resource {field}")
    for field in ("content_checksum", "package_manifest_checksum", "entrypoint_checksum", "lock_checksum"):
        _checksum(resource[field], f"plan Resource {field}")
    _safe_relative(plan["entrypoint"], "plan entrypoint")
    argv = _string_list(plan["argv"], "plan argv")
    if (
        len(argv) != 3
        or argv[1] != plan["entrypoint"]
        or argv[2] != "memory/execution/config.json"
    ):
        raise ResearchFlowContractError("plan argv must be the exact Python entrypoint")
    if plan["working_directory"] != ".":
        raise ResearchFlowContractError("plan working directory must be the Capsule root")
    if not isinstance(plan["configuration"], Mapping):
        raise ResearchFlowContractError("plan configuration must be an object")
    if not isinstance(plan["seeds"], list) or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in plan["seeds"]):
        raise ResearchFlowContractError("plan seeds are invalid")
    if isinstance(plan["repetitions"], bool) or not isinstance(plan["repetitions"], int) or not 1 <= plan["repetitions"] <= 100:
        raise ResearchFlowContractError("plan repetitions are invalid")
    _metric_definitions(plan["metrics"])
    environment = _object(plan["environment"], "plan environment")
    _exact_keys(environment, {"python_version", "implementation", "platform", "lock_checksum"}, "plan environment")
    for field in environment:
        _nonempty(environment[field], f"plan environment {field}")
    _checksum(environment["lock_checksum"], "plan environment lock checksum")
    if plan["network_policy"] != "DISABLED":
        raise ResearchFlowContractError("plan network policy must be disabled")
    _limits(plan["limits"])
    _string_list(plan["stopping_conditions"], "plan stopping conditions")
    _string_list(plan["known_limitations"], "plan limitations")


def _metric_definitions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 50:
        raise ResearchFlowContractError("metric definitions are invalid")
    result = []
    for raw in value:
        metric = _object(raw, "metric definition")
        _exact_keys(metric, {"name", "description", "unit"}, "metric definition")
        _nonempty(metric["name"], "metric name")
        _nonempty(metric["description"], "metric description")
        if metric["unit"] is not None:
            _nonempty(metric["unit"], "metric unit")
        result.append(dict(metric))
    if len({item["name"] for item in result}) != len(result):
        raise ResearchFlowContractError("metric names are duplicated")
    return result


def _result_metrics(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 50:
        raise ResearchFlowContractError("result metrics are invalid")
    result = []
    for raw in value:
        metric = _object(raw, "result metric")
        _exact_keys(metric, {"name", "value", "unit"}, "result metric")
        _nonempty(metric["name"], "result metric name")
        if isinstance(metric["value"], bool) or not isinstance(metric["value"], (int, float)) or not math.isfinite(metric["value"]):
            raise ResearchFlowContractError("result metric value must be finite")
        if metric["unit"] is not None:
            _nonempty(metric["unit"], "result metric unit")
        result.append(dict(metric))
    return result


def _limits(value: Any) -> dict[str, int]:
    item = _object(value, "execution limits")
    _exact_keys(item, {"wall_seconds", "cpu_seconds", "max_output_bytes"}, "execution limits")
    bounds = {"wall_seconds": (1, 300), "cpu_seconds": (1, 300), "max_output_bytes": (1024, 10_485_760)}
    for field, (minimum, maximum) in bounds.items():
        number = item[field]
        if isinstance(number, bool) or not isinstance(number, int) or not minimum <= number <= maximum:
            raise ResearchFlowContractError(f"execution limit {field} is invalid")
    return dict(item)


def _evidence_ref(value: Any, label: str) -> dict[str, Any]:
    item = _object(value, label)
    _exact_keys(item, {"relative_path", "sha256", "availability", "limitation"}, label)
    _safe_relative(item["relative_path"], f"{label} path")
    _checksum(item["sha256"], f"{label} checksum")
    if item["availability"] not in {"AVAILABLE", "UNAVAILABLE"}:
        raise ResearchFlowContractError(f"{label} availability is invalid")
    if item["limitation"] is not None:
        _nonempty(item["limitation"], f"{label} limitation")
    return dict(item)


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ResearchFlowContractError(f"{label} is unsafe")
    return value


def _attempt(value: Any) -> str:
    if not isinstance(value, str) or not _ATTEMPT_ID.fullmatch(value):
        raise ResearchFlowContractError("attempt identity is invalid")
    return value


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ResearchFlowContractError(f"{label} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ResearchFlowContractError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise ResearchFlowContractError(f"{label} requires a timezone")
    return parsed


def _unique_artifact_roles(values: Mapping[str, dict[str, str] | None]) -> None:
    ids = [item["artifact_id"] for item in values.values() if item is not None]
    if len(ids) != len(set(ids)):
        raise ResearchFlowContractError("source Artifact roles must not repeat")


def _maturity(value: Any) -> CoreCapabilityMaturity:
    try:
        return CoreCapabilityMaturity(value)
    except (TypeError, ValueError) as error:
        raise ResearchFlowContractError("core capability maturity is invalid") from error


def _require_producer_maturity(
    artifact_maturity: CoreCapabilityMaturity,
    producer_maturity: CoreCapabilityMaturity | None,
) -> None:
    if producer_maturity is not None and artifact_maturity is not producer_maturity:
        raise ResearchFlowContractError(
            "Artifact maturity does not match the producer Workflow Version"
        )


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ResearchFlowContractError(f"{label} must be an object")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ResearchFlowContractError(f"{label} fields mismatch")


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ResearchFlowContractError(f"{label} must be a non-empty string")


def _checksum(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _CHECKSUM.fullmatch(value):
        raise ResearchFlowContractError(f"{label} is invalid")


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 100 or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ResearchFlowContractError(f"{label} must be a bounded string array")
    return list(value)


def _copy_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ResearchFlowContractError("contract contains a non-JSON value")


ARTIFACT_CONTRACTS: Mapping[str, ArtifactContract] = MappingProxyType({
    SELECTED_RESEARCH_IDEA_TYPE: ArtifactContract(
        SELECTED_RESEARCH_IDEA_TYPE, SELECTED_RESEARCH_IDEA_SCHEMA,
        JSON_MEDIA_TYPE, validate_selected_research_idea, True,
    ),
    MANUSCRIPT_DRAFT_TYPE: ArtifactContract(
        MANUSCRIPT_DRAFT_TYPE, MANUSCRIPT_DRAFT_SCHEMA,
        JSON_MEDIA_TYPE, validate_manuscript_draft, True,
    ),
    REVIEW_REPORT_TYPE: ArtifactContract(
        REVIEW_REPORT_TYPE, REVIEW_REPORT_SCHEMA,
        JSON_MEDIA_TYPE, validate_review_report, True,
    ),
    EXPERIMENT_RECORD_TYPE: ArtifactContract(
        EXPERIMENT_RECORD_TYPE, EXPERIMENT_RECORD_SCHEMA,
        JSON_MEDIA_TYPE, validate_experiment_record, True,
    ),
    EXPERIMENT_RECORD_V2_TYPE: ArtifactContract(
        EXPERIMENT_RECORD_V2_TYPE, EXPERIMENT_RECORD_V2_SCHEMA,
        JSON_MEDIA_TYPE, validate_experiment_record_v2, True,
    ),
})

FUTURE_WORKFLOW_CONTRACTS: Mapping[str, FutureWorkflowContract] = MappingProxyType({
    "writing": FutureWorkflowContract(
        stable_key="writing-local-experimental",
        inputs=(
            FutureDependency("research_idea", SELECTED_RESEARCH_IDEA_TYPE, True),
            FutureDependency("literature_library", SELECTED_PAPER_LIBRARY_TYPE, True),
            FutureDependency("experiment_record", EXPERIMENT_RECORD_TYPE, False),
            FutureDependency("review_feedback", REVIEW_REPORT_TYPE, False),
            FutureDependency("prior_manuscript", MANUSCRIPT_DRAFT_TYPE, False),
        ),
        output_artifact_type=MANUSCRIPT_DRAFT_TYPE,
        production_seeded=True,
    ),
    "review": FutureWorkflowContract(
        stable_key="review-local-experimental",
        inputs=(
            FutureDependency("manuscript", MANUSCRIPT_DRAFT_TYPE, True),
            FutureDependency("literature_library", SELECTED_PAPER_LIBRARY_TYPE, False),
            FutureDependency("experiment_record", EXPERIMENT_RECORD_TYPE, False),
        ),
        output_artifact_type=REVIEW_REPORT_TYPE,
        production_seeded=True,
    ),
    "reproduction-experiment": FutureWorkflowContract(
        stable_key="reproduction-experiment-local-experimental",
        inputs=(
            FutureDependency("research_idea", SELECTED_RESEARCH_IDEA_TYPE, True),
            FutureDependency("literature_library", SELECTED_PAPER_LIBRARY_TYPE, False),
        ),
        output_artifact_type=EXPERIMENT_RECORD_TYPE,
        production_seeded=True,
    ),
})
