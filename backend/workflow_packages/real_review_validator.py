#!/usr/bin/env python3
"""Self-contained validator for the immutable first Real Review Capsule."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
CATEGORIES = {
    "EVIDENCE_SUPPORT", "CLAIM_SCOPE", "CITATION", "METHOD_CONSISTENCY",
    "RESULT_SUPPORT", "REPRODUCIBILITY",
}
ASSESSMENTS = {
    "NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE",
}
AVAILABILITY = {"AVAILABLE", "UNAVAILABLE", "SCOPE_LIMITED"}
ALLOWED_DYNAMIC_PREFIXES = (
    "outputs/artifacts/review-report/", "memory/progress/reports/",
    "memory/progress/receipts/",
)
PROHIBITED = re.compile(
    r"\b(?:ACCEPT|REJECT|WEAK_ACCEPT|WEAK_REJECT)\b|"
    r"publication\s+probability|scientific\s+(?:quality\s+)?score",
    re.IGNORECASE,
)


class PackageValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PackageValidationError("unsafe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise PackageValidationError("unsafe relative path")
    return value


def _object(path_or_value: Any, label: str) -> dict[str, Any]:
    if isinstance(path_or_value, Path):
        path = path_or_value
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise PackageValidationError(f"{label} must be one regular unlinked file")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    else:
        value = path_or_value
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label} must be an object")
    return dict(value)


def _array(path_or_value: Any, label: str) -> list[Any]:
    if isinstance(path_or_value, Path):
        path = path_or_value
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise PackageValidationError(f"{label} must be one regular unlinked file")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    else:
        value = path_or_value
    if not isinstance(value, list):
        raise PackageValidationError(f"{label} must be an array")
    return list(value)


def _exact(value: dict[str, Any], fields: set[str], label: str) -> None:
    if set(value) != fields:
        raise PackageValidationError(f"{label} fields mismatch")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackageValidationError(f"{label} must be non-empty")
    return value


def _checksum(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise PackageValidationError(f"{label} is invalid")
    return value


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise PackageValidationError(f"{label} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PackageValidationError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise PackageValidationError(f"{label} requires timezone")
    return parsed


def _strings(value: Any, label: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > 100 or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise PackageValidationError(f"{label} must be a bounded string array")
    if required and not value:
        raise PackageValidationError(f"{label} is required")
    return list(value)


def artifact_ref(value: Any, expected_type: str | None = None) -> dict[str, str]:
    item = _object(value, "Artifact reference")
    _exact(item, {"artifact_id", "artifact_type", "sha256"}, "Artifact reference")
    if not ARTIFACT_ID.fullmatch(str(item["artifact_id"])):
        raise PackageValidationError("Artifact ID is invalid")
    _text(item["artifact_type"], "Artifact type")
    if expected_type is not None and item["artifact_type"] != expected_type:
        raise PackageValidationError("Artifact type mismatch")
    _checksum(item["sha256"], "Artifact checksum")
    return dict(item)


def _input_state(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, str]], dict[str, Any]]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    _exact(provenance, {"schema_version", "workflow_instance_id", "artifacts"}, "input provenance")
    if provenance["schema_version"] != "reagent.real-review-input-provenance/v0.1" or not WORKFLOW_INSTANCE_ID.fullmatch(str(provenance["workflow_instance_id"])):
        raise PackageValidationError("input provenance identity is invalid")
    records = _object(provenance["artifacts"], "input Artifact records")
    allowed = {"manuscript", "research_idea", "literature_library", "experiment_record"}
    if "manuscript" not in records or not set(records).issubset(allowed):
        raise PackageValidationError("Review input roles are invalid")
    expected = {
        "manuscript": ("manuscript-draft/v2", "inputs/manuscript-draft.json"),
        "research_idea": ("selected-research-idea/v1", "inputs/selected-research-idea.json"),
        "literature_library": ("selected-paper-library/v1", "inputs/selected-paper-library.json"),
        "experiment_record": ("experiment-record/v2", "inputs/experiment-record.json"),
    }
    normalized: dict[str, dict[str, str]] = {}
    values: dict[str, Any] = {}
    for key, record in records.items():
        ref = artifact_ref(record, expected[key][0])
        path = root / expected[key][1]
        if sha256_bytes(path.read_bytes()) != ref["sha256"]:
            raise PackageValidationError("materialized Review input checksum drifted")
        normalized[key] = ref
        values[key] = _object(path, f"{key} input")
    surface = manuscript_surface(values["manuscript"])
    if surface["sources"]["research_idea"] != normalized.get("research_idea") and "research_idea" in normalized:
        raise PackageValidationError("bound Idea differs from manuscript lineage")
    if surface["sources"]["literature_library"] != normalized.get("literature_library") and "literature_library" in normalized:
        raise PackageValidationError("bound literature differs from manuscript lineage")
    if surface["sources"].get("experiment_record") != normalized.get("experiment_record") and "experiment_record" in normalized:
        raise PackageValidationError("bound Experiment differs from manuscript lineage")
    return provenance, normalized, values


def manuscript_surface(value: Any) -> dict[str, Any]:
    item = _object(value, "manuscript-draft/v2")
    _exact(item, {
        "schema", "core_capability_maturity", "producer", "source_artifacts",
        "writing_brief", "evidence_map", "approved_outline", "outline_approval",
        "title", "content_markdown", "claims", "citations",
        "experiment_evidence_available", "unsupported_areas", "limitations",
        "owner_review",
    }, "manuscript-draft/v2")
    if item["schema"] != "manuscript-draft/v2" or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise PackageValidationError("manuscript-draft/v2 identity is invalid")
    sources_raw = _object(item["source_artifacts"], "manuscript sources")
    _exact(sources_raw, {"research_idea", "literature_library", "experiment_record"}, "manuscript sources")
    sources = {
        "research_idea": artifact_ref(sources_raw["research_idea"], "selected-research-idea/v1"),
        "literature_library": artifact_ref(sources_raw["literature_library"], "selected-paper-library/v1"),
        "experiment_record": None if sources_raw["experiment_record"] is None else artifact_ref(sources_raw["experiment_record"], "experiment-record/v2"),
    }
    outline = _object(item["approved_outline"], "approved Outline")
    _exact(outline, {"sha256", "value"}, "approved Outline")
    if not isinstance(outline["value"], list) or canonical_hash(outline["value"]) != outline["sha256"]:
        raise PackageValidationError("approved Outline checksum is invalid")
    sections = set()
    for raw in outline["value"]:
        section = _object(raw, "Outline section")
        _exact(section, {"heading", "support_status"}, "Outline section")
        _text(section["heading"], "Outline heading")
        sections.add(section["heading"])
    citations = _array(item["citations"], "citations")
    citation_ids = set()
    for raw in citations:
        citation = _object(raw, "citation")
        _exact(citation, {"citation_id", "paper_id", "source_artifact", "evidence_scope", "reference_markdown"}, "citation")
        _text(citation["citation_id"], "citation ID")
        if citation["citation_id"] in citation_ids or artifact_ref(citation["source_artifact"], "selected-paper-library/v1") != sources["literature_library"]:
            raise PackageValidationError("citation identity is invalid")
        citation_ids.add(citation["citation_id"])
        if citation["evidence_scope"] not in {"METADATA_ONLY", "ABSTRACT"}:
            raise PackageValidationError("citation evidence scope is invalid")
    claims = _array(item["claims"], "claims")
    if not claims:
        raise PackageValidationError("manuscript claims are required")
    claim_ids = set()
    refs = []
    normalized_claims = []
    exact_sources = [source for source in sources.values() if source is not None]
    for raw in claims:
        claim = _object(raw, "claim")
        _exact(claim, {"claim_id", "claim_type", "section", "claim_text", "support_status", "evidence_refs", "citation_ids", "limitations"}, "claim")
        for field in ("claim_id", "section", "claim_text"):
            _text(claim[field], f"claim {field}")
        if claim["claim_id"] in claim_ids:
            raise PackageValidationError("claim ID is duplicated")
        claim_ids.add(claim["claim_id"]); sections.add(claim["section"])
        claim_refs = []
        for raw_ref in _array(claim["evidence_refs"], "claim evidence"):
            ref = _object(raw_ref, "claim evidence")
            _exact(ref, {"artifact_id", "artifact_type", "sha256", "evidence_item", "location", "availability", "limitation"}, "claim evidence")
            identity = artifact_ref({key: ref[key] for key in ("artifact_id", "artifact_type", "sha256")})
            if identity not in exact_sources:
                raise PackageValidationError("claim evidence is outside manuscript lineage")
            _text(ref["evidence_item"], "evidence item"); _text(ref["location"], "evidence location")
            claim_refs.append(dict(ref)); refs.append(dict(ref))
        claim_citations = _strings(claim["citation_ids"], "claim citations")
        if any(value not in citation_ids for value in claim_citations):
            raise PackageValidationError("claim cites an unknown citation")
        normalized_claims.append(dict(claim))
    _text(item["title"], "manuscript title"); _text(item["content_markdown"], "manuscript content")
    return {"sources": sources, "claims": normalized_claims, "sections": sections, "evidence_refs": refs}


def supporting_refs(sources: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if key in sources]


def derive_evidence_availability(manuscript: dict[str, Any], sources: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    surface = manuscript_surface(manuscript)
    bound = {(item["artifact_id"], item["artifact_type"], item["sha256"]) for item in supporting_refs(sources)}
    result = []
    seen = set()
    for ref in surface["evidence_refs"]:
        key = (ref["artifact_id"], ref["artifact_type"], ref["sha256"], ref["evidence_item"], ref["location"])
        if key in seen:
            continue
        seen.add(key)
        identity = key[:3]
        if identity not in bound:
            availability, limitation = "UNAVAILABLE", "Referenced Artifact is not explicitly bound to Review"
        elif ref.get("availability") != "AVAILABLE" or ref.get("limitation"):
            availability, limitation = "SCOPE_LIMITED", ref.get("limitation") or "Manuscript records limited evidence scope"
        else:
            availability, limitation = "AVAILABLE", None
        result.append({
            "artifact_id": ref["artifact_id"], "artifact_type": ref["artifact_type"],
            "sha256": ref["sha256"], "evidence_item": ref["evidence_item"],
            "location": ref["location"], "availability": availability,
            "limitation": limitation,
        })
    return result


def validate_review_scope(value: Any, manuscript_ref: dict[str, str], support: list[dict[str, str]]) -> dict[str, Any]:
    item = _object(value, "Review Scope")
    _exact(item, {"manuscript_identity", "available_evidence", "categories", "known_evidence_limitations", "owner_focus"}, "Review Scope")
    if artifact_ref(item["manuscript_identity"], "manuscript-draft/v2") != manuscript_ref:
        raise PackageValidationError("Review Scope manuscript is not the exact binding")
    available = [artifact_ref(raw) for raw in _array(item["available_evidence"], "Review Scope evidence")]
    if available != support:
        raise PackageValidationError("Review Scope evidence differs from exact bindings")
    categories = _strings(item["categories"], "Review Scope categories", required=True)
    if len(categories) != len(set(categories)) or any(category not in CATEGORIES for category in categories):
        raise PackageValidationError("Review Scope categories are invalid")
    _strings(item["known_evidence_limitations"], "Review Scope limitations")
    _strings(item["owner_focus"], "Review Scope Owner focus")
    return item


def validate_review_result(value: Any, *, manuscript_ref: dict[str, str], support: list[dict[str, str]], surface: dict[str, Any]) -> dict[str, Any]:
    item = _object(value, "Review result")
    _exact(item, {"assessment", "summary", "issues", "limitations"}, "Review result")
    if item["assessment"] not in ASSESSMENTS:
        raise PackageValidationError("Review assessment is invalid")
    _text(item["summary"], "Review summary")
    if PROHIBITED.search(item["summary"]):
        raise PackageValidationError("Review summary contains prohibited publication semantics")
    available = {"manuscript": manuscript_ref}
    available.update({ref["artifact_id"]: ref for ref in support})
    issues = []
    seen = set()
    claims = {claim["claim_id"]: claim for claim in surface["claims"]}
    for raw in _array(item["issues"], "Review issues"):
        issue = _object(raw, "Review issue")
        _exact(issue, {"issue_id", "category", "severity", "target", "summary", "evidence_refs", "recommended_action", "blocking"}, "Review issue")
        _text(issue["issue_id"], "Review issue ID")
        if issue["issue_id"] in seen:
            raise PackageValidationError("Review issue ID is duplicated")
        seen.add(issue["issue_id"])
        if issue["category"] not in CATEGORIES or issue["severity"] not in {"MAJOR", "MINOR"}:
            raise PackageValidationError("Review issue category or severity is invalid")
        target = _object(issue["target"], "Review issue target")
        _exact(target, {"section", "claim_id"}, "Review issue target")
        _text(target["section"], "Review issue section")
        if target["section"] not in surface["sections"]:
            raise PackageValidationError("Review issue targets an unknown section")
        if target["claim_id"] is not None:
            _text(target["claim_id"], "Review issue claim ID")
            if target["claim_id"] not in claims or claims[target["claim_id"]]["section"] != target["section"]:
                raise PackageValidationError("Review issue targets an unknown claim")
        _text(issue["summary"], "Review issue summary"); _text(issue["recommended_action"], "recommended action")
        if PROHIBITED.search(issue["summary"]) or PROHIBITED.search(issue["recommended_action"]):
            raise PackageValidationError("Review issue contains prohibited publication semantics")
        if not isinstance(issue["blocking"], bool):
            raise PackageValidationError("Review issue blocking flag is invalid")
        for raw_ref in _array(issue["evidence_refs"], "Review issue evidence"):
            ref = _object(raw_ref, "Review issue evidence")
            _exact(ref, {"artifact_id", "artifact_type", "sha256", "evidence_item", "location", "availability", "limitation"}, "Review issue evidence")
            identity = artifact_ref({key: ref[key] for key in ("artifact_id", "artifact_type", "sha256")})
            if identity not in available.values():
                raise PackageValidationError("Review issue evidence is not explicitly bound")
            _text(ref["evidence_item"], "Review issue evidence item"); _text(ref["location"], "Review issue evidence location")
            if ref["availability"] not in {"AVAILABLE", "LIMITED", "UNAVAILABLE"}:
                raise PackageValidationError("Review issue evidence availability is invalid")
            if ref["limitation"] is not None:
                _text(ref["limitation"], "Review issue evidence limitation")
        issues.append(issue)
    has_blocking = any(issue["blocking"] for issue in issues)
    if item["assessment"] == "NO_BLOCKING_ISSUES" and has_blocking:
        raise PackageValidationError("NO_BLOCKING_ISSUES conflicts with a blocking issue")
    if item["assessment"] == "REVISION_REQUIRED" and not has_blocking:
        raise PackageValidationError("REVISION_REQUIRED requires a blocking issue")
    _strings(item["limitations"], "Review limitations")
    return item


def validate_review_report_v2(value: Any, *, root: Path) -> dict[str, Any]:
    item = _object(value, "review-report/v2")
    _exact(item, {"schema", "core_capability_maturity", "producer", "source_manuscript", "supporting_artifacts", "review_scope", "scope_approval", "evidence_availability", "assessment", "summary", "issues", "limitations", "owner_review"}, "review-report/v2")
    if item["schema"] != "review-report/v2" or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise PackageValidationError("review-report/v2 identity is invalid")
    producer = _object(item["producer"], "Review producer")
    _exact(producer, {"workflow_instance_id", "capsule_id", "capsule_version", "execution_round"}, "Review producer")
    if not WORKFLOW_INSTANCE_ID.fullmatch(str(producer["workflow_instance_id"])) or not CAPSULE_ID.fullmatch(str(producer["capsule_id"])) or producer["execution_round"] != 1:
        raise PackageValidationError("Review producer identity is invalid")
    provenance, sources, values = _input_state(root)
    if provenance["workflow_instance_id"] != producer["workflow_instance_id"]:
        raise PackageValidationError("Review producer differs from input provenance")
    manuscript_ref = artifact_ref(item["source_manuscript"], "manuscript-draft/v2")
    if manuscript_ref != sources["manuscript"]:
        raise PackageValidationError("Review manuscript differs from exact binding")
    support = [artifact_ref(raw) for raw in _array(item["supporting_artifacts"], "supporting Artifacts")]
    if support != supporting_refs(sources):
        raise PackageValidationError("Review support differs from exact bindings")
    scope_wrapper = _object(item["review_scope"], "Review Scope wrapper")
    _exact(scope_wrapper, {"sha256", "value"}, "Review Scope wrapper")
    scope = validate_review_scope(scope_wrapper["value"], manuscript_ref, support)
    if canonical_hash(scope) != scope_wrapper["sha256"]:
        raise PackageValidationError("Review Scope checksum mismatch")
    approval = _object(item["scope_approval"], "Scope approval")
    _exact(approval, {"sha256", "scope_sha256", "manuscript_sha256", "bound_artifacts_sha256", "approved_at", "decision"}, "Scope approval")
    payload = dict(approval); approval_sha = payload.pop("sha256")
    if canonical_hash(payload) != approval_sha or approval["scope_sha256"] != scope_wrapper["sha256"] or approval["manuscript_sha256"] != manuscript_ref["sha256"] or approval["bound_artifacts_sha256"] != canonical_hash(support) or approval["decision"] != "APPROVED":
        raise PackageValidationError("Review Scope approval is invalid")
    _time(approval["approved_at"], "Scope approval time")
    surface = manuscript_surface(values["manuscript"])
    expected_availability = derive_evidence_availability(values["manuscript"], sources)
    if item["evidence_availability"] != expected_availability:
        raise PackageValidationError("Review evidence availability differs from exact inputs")
    review_result = validate_review_result({key: item[key] for key in ("assessment", "summary", "issues", "limitations")}, manuscript_ref=manuscript_ref, support=support, surface=surface)
    if item["assessment"] == "INSUFFICIENT_EVIDENCE" and not any(entry["availability"] == "UNAVAILABLE" for entry in expected_availability):
        raise PackageValidationError("INSUFFICIENT_EVIDENCE requires unavailable evidence")
    owner = _object(item["owner_review"], "Owner review")
    _exact(owner, {"sha256", "review_result_sha256", "reviewed_at", "decision"}, "Owner review")
    owner_payload = dict(owner); owner_sha = owner_payload.pop("sha256")
    expected_result = canonical_hash({"source_manuscript": manuscript_ref, "supporting_artifacts": support, "review_scope": scope_wrapper, "scope_approval": approval, "evidence_availability": expected_availability, **review_result})
    if canonical_hash(owner_payload) != owner_sha or owner["review_result_sha256"] != expected_result or owner["decision"] != "APPROVED":
        raise PackageValidationError("Owner review is not exact and approved")
    _time(owner["reviewed_at"], "Owner review time")
    return item


def validate(root_value: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    supplied = Path(root_value)
    if supplied.is_symlink():
        raise PackageValidationError("Capsule root is unsafe")
    root = supplied.resolve()
    manifest = _object(root / "package-manifest.json", "package manifest")
    if manifest.get("workflow_id") != "review-local-experimental" or manifest.get("workflow_version") != "0.3.0" or manifest.get("package_template_version") != "0.5.0":
        raise PackageValidationError("Real Review Capsule identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise PackageValidationError("package file manifest is invalid")
    declared = {}
    normalized = []
    for entry in files:
        if not isinstance(entry, dict) or "relative_path" not in entry:
            raise PackageValidationError("package file entry is invalid")
        relative = safe_relative_path(entry["relative_path"])
        if relative in declared:
            raise PackageValidationError("duplicate package file")
        declared[relative] = entry
        normalized_entry = dict(entry)
        if entry.get("mutable_by_harness"):
            normalized_entry["sha256"] = None; normalized_entry["byte_size"] = None
        normalized.append(normalized_entry)
        path = root / relative
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("declared package file is unsafe")
            if not entry.get("mutable_by_harness") and (sha256_bytes(path.read_bytes()) != entry.get("sha256") or path.stat().st_size != entry.get("byte_size")):
                raise PackageValidationError("immutable package file drifted")
        elif entry.get("requirement") == "REQUIRED":
            raise PackageValidationError("required package file is missing")
    if canonical_hash(normalized) != manifest.get("file_manifest_checksum"):
        raise PackageValidationError("file manifest checksum mismatch")
    payload = dict(manifest); payload["manifest_checksum"] = None; payload["package_checksum"] = None; payload["files"] = normalized
    if canonical_hash(payload) != manifest.get("manifest_checksum"):
        raise PackageValidationError("manifest checksum mismatch")
    package_hash = canonical_hash({"package_id": manifest["package_id"], "package_schema_version": manifest["package_schema_version"], "file_manifest_checksum": manifest["file_manifest_checksum"], "manifest_checksum": manifest["manifest_checksum"]})
    if package_hash != manifest.get("package_checksum"):
        raise PackageValidationError("package checksum mismatch")
    config = _object(root / "workflow/real-review.json", "Real Review contract")
    if config.get("schema_version") != "reagent.real-review-workflow/v0.1" or config.get("output_artifact_type") != "review-report/v2":
        raise PackageValidationError("Real Review contract is invalid")
    materialized_inputs = set()
    for requirement in config.get("input_requirements", []):
        if not isinstance(requirement, dict) or requirement.get("materialization_mode") != "VERIFIED_COPY":
            raise PackageValidationError("Real Review input declaration is invalid")
        target = safe_relative_path(requirement.get("target_relative_path"))
        if not target.startswith("inputs/") or target.endswith("/") or target in materialized_inputs:
            raise PackageValidationError("Real Review input target is invalid")
        materialized_inputs.add(target)
    runtime_dynamic_paths = set()
    for raw in config.get("runtime_dynamic_paths", []):
        target = safe_relative_path(raw)
        if target.endswith("/") or not target.startswith(("memory/", "outputs/")) or target in runtime_dynamic_paths:
            raise PackageValidationError("Real Review dynamic path is invalid")
        runtime_dynamic_paths.add(target)
    for path in root.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise PackageValidationError("Capsule directory link rejected")
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "package-manifest.json" or relative in declared or relative in materialized_inputs or relative in runtime_dynamic_paths or relative == "memory/current-artifact.json" or any(relative.startswith(prefix) for prefix in ALLOWED_DYNAMIC_PREFIXES):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("Capsule dynamic file is unsafe")
            continue
        raise PackageValidationError(f"undeclared Capsule file: {relative}")
    if (root / "memory/input-provenance.json").exists():
        _input_state(root)
    artifact_root = root / "outputs/artifacts/review-report"
    if artifact_root.exists():
        for path in artifact_root.iterdir():
            if path.is_symlink() or not path.is_file() or path.name != "sha256-" + sha256_bytes(path.read_bytes())[7:] + ".json":
                raise PackageValidationError("Review Output address is invalid")
            validate_review_report_v2(_object(path, "review-report/v2"), root=root)
    return {"valid": True, "package_id": manifest["package_id"], "package_checksum": manifest["package_checksum"], "manifest_checksum": manifest["manifest_checksum"], "declared_file_count": len(files), "harness_acceptance_status": manifest["harness_acceptance_status"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(canonical_json(validate(args.root)))
