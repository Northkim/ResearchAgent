#!/usr/bin/env python3
"""Self-contained validator for the immutable first Writing Revision Capsule."""

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
SUPPORT = {"SUPPORTED", "PLANNED", "UNAVAILABLE"}
DISPOSITIONS = {"ADDRESSED", "PARTIALLY_ADDRESSED", "NOT_ADDRESSED"}
ALLOWED_DYNAMIC_PREFIXES = (
    "outputs/artifacts/manuscript-draft/", "memory/progress/reports/",
    "memory/progress/receipts/",
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


def _object(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, Path):
        if value.is_symlink() or not value.is_file() or value.stat().st_nlink != 1:
            raise PackageValidationError(f"{label} must be one regular unlinked file")
        try:
            value = json.loads(value.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label} must be an object")
    return dict(value)


def _array(path: Path, label: str) -> list[Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise PackageValidationError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, list):
        raise PackageValidationError(f"{label} must be an array")
    return value


def _exact(value: dict[str, Any], fields: set[str], label: str) -> None:
    if set(value) != fields:
        raise PackageValidationError(f"{label} fields mismatch")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackageValidationError(f"{label} must be non-empty")
    return value


def _strings(value: Any, label: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(item, str) or not item.strip() for item in value):
        raise PackageValidationError(f"{label} must be a bounded string array")
    if required and not value:
        raise PackageValidationError(f"{label} is required")
    return list(value)


def _time(value: Any, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise PackageValidationError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise PackageValidationError(f"{label} requires timezone")


def artifact_ref(value: Any, expected_type: str | None = None) -> dict[str, str]:
    item = _object(value, "Artifact reference")
    _exact(item, {"artifact_id", "artifact_type", "sha256"}, "Artifact reference")
    if not ARTIFACT_ID.fullmatch(str(item["artifact_id"])) or not SHA256.fullmatch(str(item["sha256"])):
        raise PackageValidationError("Artifact identity is invalid")
    _text(item["artifact_type"], "Artifact type")
    if expected_type is not None and item["artifact_type"] != expected_type:
        raise PackageValidationError("Artifact type mismatch")
    return dict(item)


def validate_writing_brief(value: Any) -> dict[str, Any]:
    item = _object(value, "Writing Brief")
    _exact(item, {"document_type", "working_title", "target_audience", "target_words", "requested_sections", "citation_style", "abstract_requested", "owner_constraints"}, "Writing Brief")
    for field in ("document_type", "working_title", "target_audience", "citation_style"):
        _text(item[field], f"Writing Brief {field}")
    words = _object(item["target_words"], "target words")
    _exact(words, {"minimum", "maximum"}, "target words")
    if any(isinstance(words[key], bool) or not isinstance(words[key], int) for key in words) or not 100 <= words["minimum"] <= words["maximum"] <= 50_000:
        raise PackageValidationError("target words are invalid")
    _strings(item["requested_sections"], "requested sections", required=True)
    _strings(item["owner_constraints"], "owner constraints")
    if not isinstance(item["abstract_requested"], bool):
        raise PackageValidationError("abstract_requested must be boolean")
    return item


def validate_experiment_record_v2(value: Any) -> dict[str, Any]:
    item = _object(value, "experiment-record/v2")
    if item.get("schema") != "experiment-record/v2" or item.get("core_capability_maturity") != "REVIEWED_CORE":
        raise PackageValidationError("experiment-record/v2 identity is invalid")
    execution = _object(item.get("execution"), "Experiment execution")
    evaluation = _object(item.get("evaluation"), "Experiment evaluation")
    if item.get("result_status") == "SUCCEEDED" and (execution.get("status") != "SUCCEEDED" or execution.get("exit_code") != 0 or evaluation.get("status") != "VALID"):
        raise PackageValidationError("Experiment success lacks valid execution and evaluation")
    return item


def _input_state(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    _exact(provenance, {"schema_version", "workflow_instance_id", "artifacts"}, "input provenance")
    if provenance["schema_version"] != "reagent.writing-revision-input-provenance/v0.1" or not WORKFLOW_INSTANCE_ID.fullmatch(str(provenance["workflow_instance_id"])):
        raise PackageValidationError("input provenance identity is invalid")
    records = _object(provenance["artifacts"], "input Artifact records")
    required = {"prior_manuscript", "causal_review", "research_idea", "literature_library"}
    if set(records) not in (required, required | {"experiment_record"}):
        raise PackageValidationError("Writing revision input roles are invalid")
    expected = {
        "prior_manuscript": ("manuscript-draft/v2", "inputs/prior-manuscript.json"),
        "causal_review": ("review-report/v2", "inputs/review-report.json"),
        "research_idea": ("selected-research-idea/v1", "inputs/selected-research-idea.json"),
        "literature_library": ("selected-paper-library/v1", "inputs/selected-paper-library.json"),
        "experiment_record": ("experiment-record/v2", "inputs/experiment-record.json"),
    }
    normalized: dict[str, Any] = {}; values: dict[str, Any] = {}
    for key, record in records.items():
        ref = artifact_ref(record, expected[key][0]); path = root / expected[key][1]
        if sha256_bytes(path.read_bytes()) != ref["sha256"]:
            raise PackageValidationError("materialized input checksum drifted")
        normalized[key] = ref; values[key] = _object(path, f"{key} input")
    prior = values["prior_manuscript"]
    review = values["causal_review"]
    if prior.get("schema") != "manuscript-draft/v2" or review.get("schema") != "review-report/v2":
        raise PackageValidationError("causal revision input schema is invalid")
    if artifact_ref(review.get("source_manuscript"), "manuscript-draft/v2") != normalized["prior_manuscript"]:
        raise PackageValidationError("causal Review refers to a different prior manuscript")
    issues = review.get("issues")
    if not isinstance(issues, list):
        raise PackageValidationError("causal Review issues are invalid")
    if review.get("assessment") == "INSUFFICIENT_EVIDENCE" or (review.get("assessment") == "NO_BLOCKING_ISSUES" and not issues):
        raise PackageValidationError("causal Review has no legitimate W2 revision action")
    prior_sources = _object(prior.get("source_artifacts"), "prior manuscript sources")
    for role in ("research_idea", "literature_library", "experiment_record"):
        expected_ref = normalized.get(role)
        actual = prior_sources.get(role)
        if (None if actual is None else artifact_ref(actual)) != expected_ref:
            raise PackageValidationError("supporting evidence differs from prior manuscript lineage")
    exact_support = [normalized[key] for key in ("research_idea", "literature_library", "experiment_record") if key in normalized]
    if review.get("supporting_artifacts") != exact_support:
        raise PackageValidationError("causal Review support differs from exact bindings")
    library = values["literature_library"]
    if library.get("schema") != "selected-paper-library/v1" or not isinstance(library.get("papers"), list):
        raise PackageValidationError("selected paper library is invalid")
    experiment = values.get("experiment_record")
    if experiment is not None:
        validate_experiment_record_v2(experiment)
    return provenance, normalized, prior, review, library, experiment


def validate_evidence_refs(value: Any, sources: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 50:
        raise PackageValidationError("evidence references must be bounded")
    identities = list(sources.values())
    result = []
    for raw in value:
        item = _object(raw, "evidence reference")
        _exact(item, {"artifact_id", "artifact_type", "sha256", "evidence_item", "location", "availability", "limitation"}, "evidence reference")
        identity = artifact_ref({key: item[key] for key in ("artifact_id", "artifact_type", "sha256")})
        if identity not in identities:
            raise PackageValidationError("evidence reference points to an unbound Artifact")
        _text(item["evidence_item"], "evidence item"); _text(item["location"], "evidence location")
        if item["availability"] not in {"AVAILABLE", "LIMITED", "UNAVAILABLE"}:
            raise PackageValidationError("evidence availability is invalid")
        if item["limitation"] is not None:
            _text(item["limitation"], "evidence limitation")
        result.append(item)
    return result


def validate_citations(value: Any, sources: dict[str, Any], library: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 200:
        raise PackageValidationError("citations must be bounded")
    paper_ids = {item.get("candidate_id") for item in library["papers"] if isinstance(item, dict)}
    result = []; seen = set()
    for raw in value:
        item = _object(raw, "citation")
        _exact(item, {"citation_id", "paper_id", "source_artifact", "evidence_scope", "reference_markdown"}, "citation")
        if item["citation_id"] in seen or item["paper_id"] not in paper_ids:
            raise PackageValidationError("citation is duplicate or outside selected library")
        seen.add(item["citation_id"])
        if artifact_ref(item["source_artifact"], "selected-paper-library/v1") != sources["literature_library"] or item["evidence_scope"] not in {"METADATA_ONLY", "ABSTRACT"}:
            raise PackageValidationError("citation source or evidence scope is invalid")
        _text(item["reference_markdown"], "citation reference")
        result.append(item)
    return result


def validate_claims(value: Any, sources: dict[str, Any], citations: list[dict[str, Any]], experiment: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 300:
        raise PackageValidationError("claims must be non-empty and bounded")
    citation_ids = {item["citation_id"] for item in citations}; result = []; seen = set()
    experiment_valid = experiment is not None and experiment.get("result_status") == "SUCCEEDED" and experiment["execution"].get("status") == "SUCCEEDED" and experiment["evaluation"].get("status") == "VALID"
    for raw in value:
        item = _object(raw, "claim")
        _exact(item, {"claim_id", "claim_type", "section", "claim_text", "support_status", "evidence_refs", "citation_ids", "limitations"}, "claim")
        if item["claim_id"] in seen or item["claim_type"] not in {"LITERATURE", "PROPOSAL", "RESULT"} or item["support_status"] not in SUPPORT:
            raise PackageValidationError("claim identity, type, or status is invalid")
        seen.add(item["claim_id"]); refs = validate_evidence_refs(item["evidence_refs"], sources)
        cited = _strings(item["citation_ids"], "claim citations"); _strings(item["limitations"], "claim limitations")
        if any(citation not in citation_ids for citation in cited):
            raise PackageValidationError("claim cites outside the selected library")
        if item["support_status"] == "SUPPORTED" and not refs:
            raise PackageValidationError("SUPPORTED claim requires evidence")
        if item["support_status"] == "UNAVAILABLE" and refs:
            raise PackageValidationError("UNAVAILABLE claim cannot cite evidence")
        if item["claim_type"] == "LITERATURE" and item["support_status"] == "SUPPORTED" and not cited:
            raise PackageValidationError("supported literature claim requires citation")
        if item["claim_type"] == "RESULT" and item["support_status"] == "SUPPORTED":
            experiment_ref = sources.get("experiment_record")
            if not experiment_valid or not any(experiment_ref is not None and all(ref[key] == experiment_ref[key] for key in ("artifact_id", "artifact_type", "sha256")) for ref in refs):
                raise PackageValidationError("supported result lacks valid exact Experiment evidence")
        result.append(item)
    return result


def validate_revision_plan(value: Any, issues: list[dict[str, Any]], sources: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise PackageValidationError("Revision Plan must be non-empty and bounded")
    issue_ids = {item.get("issue_id") for item in issues}; seen = set(); result = []
    for raw in value:
        item = _object(raw, "Revision Plan item")
        _exact(item, {"issue_id", "intended_disposition", "planned_change", "affected_section", "affected_claims", "evidence_to_use", "known_limitation"}, "Revision Plan item")
        if item["issue_id"] in seen or item["issue_id"] not in issue_ids or item["intended_disposition"] not in DISPOSITIONS:
            raise PackageValidationError("Revision Plan issue or disposition is invalid")
        seen.add(item["issue_id"]); _text(item["planned_change"], "planned change"); _text(item["affected_section"], "affected section")
        _strings(item["affected_claims"], "affected claims"); validate_evidence_refs(item["evidence_to_use"], sources)
        if item["intended_disposition"] in {"PARTIALLY_ADDRESSED", "NOT_ADDRESSED"}:
            _text(item["known_limitation"], "known limitation")
        elif item["known_limitation"] is not None:
            _text(item["known_limitation"], "known limitation")
        result.append(item)
    if seen != issue_ids:
        raise PackageValidationError("Revision Plan must account for every Review issue")
    return result


def validate_issue_accounting(value: Any, issues: list[dict[str, Any]], claim_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise PackageValidationError("issue accounting must be non-empty and bounded")
    issue_ids = {item.get("issue_id") for item in issues}; seen = set(); result = []
    for raw in value:
        item = _object(raw, "issue accounting")
        _exact(item, {"issue_id", "disposition", "change_summary", "changed_sections", "changed_claims", "remaining_limitation"}, "issue accounting")
        if item["issue_id"] in seen or item["issue_id"] not in issue_ids or item["disposition"] not in DISPOSITIONS:
            raise PackageValidationError("issue accounting identity or disposition is invalid")
        seen.add(item["issue_id"]); _text(item["change_summary"], "change summary")
        _strings(item["changed_sections"], "changed sections"); changed_claims = _strings(item["changed_claims"], "changed claims")
        if any(claim not in claim_ids for claim in changed_claims):
            raise PackageValidationError("issue accounting targets an unknown revised claim")
        if item["disposition"] in {"PARTIALLY_ADDRESSED", "NOT_ADDRESSED"}:
            _text(item["remaining_limitation"], "remaining limitation")
        elif item["remaining_limitation"] is not None:
            _text(item["remaining_limitation"], "remaining limitation")
        result.append(item)
    if seen != issue_ids:
        raise PackageValidationError("every Review issue must be accounted exactly once")
    return result


def validate_manuscript_draft_v3(value: Any, *, root: Path) -> dict[str, Any]:
    item = _object(value, "manuscript-draft/v3")
    _exact(item, {"schema", "core_capability_maturity", "producer", "prior_manuscript", "causal_review", "supporting_artifacts", "revision_round", "writing_brief", "title", "content_markdown", "claims", "citations", "experiment_evidence_available", "unsupported_areas", "limitations", "revision_plan", "revision_plan_approval", "issue_accounting", "remaining_blocking_issue_ids", "remaining_blocking_issue_count", "revision_limitations", "owner_review"}, "manuscript-draft/v3")
    if item["schema"] != "manuscript-draft/v3" or item["core_capability_maturity"] != "REVIEWED_CORE" or item["revision_round"] != 1:
        raise PackageValidationError("manuscript-draft/v3 identity is invalid")
    provenance, inputs, prior, review, library, experiment = _input_state(root)
    producer = _object(item["producer"], "producer")
    _exact(producer, {"workflow_instance_id", "capsule_id", "capsule_version", "execution_round"}, "producer")
    if producer["workflow_instance_id"] != provenance["workflow_instance_id"] or not CAPSULE_ID.fullmatch(str(producer["capsule_id"])) or producer["execution_round"] != 1:
        raise PackageValidationError("producer identity is invalid")
    if artifact_ref(item["prior_manuscript"], "manuscript-draft/v2") != inputs["prior_manuscript"] or artifact_ref(item["causal_review"], "review-report/v2") != inputs["causal_review"]:
        raise PackageValidationError("revision causal lineage differs from exact inputs")
    sources = {key: inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in inputs}
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if key in sources]
    if item["supporting_artifacts"] != support:
        raise PackageValidationError("revision support differs from exact inputs")
    validate_writing_brief(item["writing_brief"])
    if item["writing_brief"] != prior.get("writing_brief"):
        raise PackageValidationError("revision changed the approved Writing Brief")
    citations = validate_citations(item["citations"], sources, library)
    claims = validate_claims(item["claims"], sources, citations, experiment)
    plan_box = _object(item["revision_plan"], "Revision Plan"); _exact(plan_box, {"sha256", "value"}, "Revision Plan")
    plan = validate_revision_plan(plan_box["value"], review["issues"], sources)
    if canonical_hash(plan) != plan_box["sha256"]:
        raise PackageValidationError("Revision Plan checksum mismatch")
    approval = _object(item["revision_plan_approval"], "Revision Plan approval")
    _exact(approval, {"sha256", "prior_manuscript_sha256", "causal_review_sha256", "issue_set_sha256", "revision_plan_sha256", "supporting_artifacts_sha256", "approved_at", "decision"}, "Revision Plan approval")
    payload = dict(approval); approval_sha = payload.pop("sha256")
    if canonical_hash(payload) != approval_sha or approval["prior_manuscript_sha256"] != inputs["prior_manuscript"]["sha256"] or approval["causal_review_sha256"] != inputs["causal_review"]["sha256"] or approval["issue_set_sha256"] != canonical_hash(review["issues"]) or approval["revision_plan_sha256"] != plan_box["sha256"] or approval["supporting_artifacts_sha256"] != canonical_hash(support) or approval["decision"] != "APPROVED":
        raise PackageValidationError("Revision Plan approval does not bind exact inputs")
    _time(approval["approved_at"], "Revision Plan approval time")
    accounting = validate_issue_accounting(item["issue_accounting"], review["issues"], {claim["claim_id"] for claim in claims})
    if {entry["issue_id"] for entry in accounting} != {entry["issue_id"] for entry in plan}:
        raise PackageValidationError("Revision Plan and issue accounting differ")
    disposition = {entry["issue_id"]: entry["disposition"] for entry in accounting}
    remaining = [issue["issue_id"] for issue in review["issues"] if issue["blocking"] and disposition[issue["issue_id"]] != "ADDRESSED"]
    if item["remaining_blocking_issue_ids"] != remaining or item["remaining_blocking_issue_count"] != len(remaining):
        raise PackageValidationError("remaining blocking issue accounting is inconsistent")
    if item["experiment_evidence_available"] is not ("experiment_record" in sources):
        raise PackageValidationError("Experiment evidence availability is inconsistent")
    _text(item["title"], "revised title"); _text(item["content_markdown"], "revised content")
    _strings(item["unsupported_areas"], "unsupported areas"); _strings(item["limitations"], "limitations"); _strings(item["revision_limitations"], "revision limitations")
    owner = _object(item["owner_review"], "owner review")
    _exact(owner, {"sha256", "revised_draft_sha256", "issue_accounting_sha256", "reviewed_at", "decision"}, "owner review")
    owner_payload = dict(owner); owner_sha = owner_payload.pop("sha256")
    draft_sha = canonical_hash({"title": item["title"], "content_markdown": item["content_markdown"], "claims": claims, "citations": citations})
    if canonical_hash(owner_payload) != owner_sha or owner["revised_draft_sha256"] != draft_sha or owner["issue_accounting_sha256"] != canonical_hash(accounting) or owner["decision"] != "APPROVED":
        raise PackageValidationError("owner review does not bind the exact revision")
    _time(owner["reviewed_at"], "owner review time")
    return item


def validate(root_value: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    supplied = Path(root_value)
    if supplied.is_symlink():
        raise PackageValidationError("Capsule root is unsafe")
    root = supplied.resolve(); manifest = _object(root / "package-manifest.json", "package manifest")
    if manifest.get("workflow_id") != "writing-local-experimental" or manifest.get("workflow_version") != "0.4.0" or manifest.get("package_template_version") != "0.6.0":
        raise PackageValidationError("Writing Revision Capsule identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise PackageValidationError("package file manifest is invalid")
    declared = {}; normalized = []
    for entry in files:
        if not isinstance(entry, dict) or "relative_path" not in entry:
            raise PackageValidationError("package file entry is invalid")
        relative = safe_relative_path(entry["relative_path"])
        if relative in declared:
            raise PackageValidationError("duplicate package file")
        declared[relative] = entry; normalized_entry = dict(entry)
        if entry.get("mutable_by_harness"):
            normalized_entry["sha256"] = None; normalized_entry["byte_size"] = None
        normalized.append(normalized_entry); path = root / relative
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
    config = _object(root / "workflow/writing-revision.json", "Writing Revision contract")
    if config.get("schema_version") != "reagent.writing-revision-workflow/v0.1" or config.get("output_artifact_type") != "manuscript-draft/v3":
        raise PackageValidationError("Writing Revision contract is invalid")
    materialized = set()
    for requirement in config.get("input_requirements", []):
        if not isinstance(requirement, dict) or requirement.get("materialization_mode") != "VERIFIED_COPY":
            raise PackageValidationError("Writing Revision input declaration is invalid")
        target = safe_relative_path(requirement.get("target_relative_path"))
        if not target.startswith("inputs/") or target in materialized:
            raise PackageValidationError("Writing Revision input target is invalid")
        materialized.add(target)
    runtime_dynamic = {safe_relative_path(path) for path in config.get("runtime_dynamic_paths", [])}
    for path in root.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise PackageValidationError("Capsule directory link rejected")
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "package-manifest.json" or relative in declared or relative in materialized or relative in runtime_dynamic or relative == "memory/current-artifact.json" or any(relative.startswith(prefix) for prefix in ALLOWED_DYNAMIC_PREFIXES):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("Capsule dynamic file is unsafe")
            continue
        raise PackageValidationError(f"undeclared Capsule file: {relative}")
    if (root / "memory/input-provenance.json").exists():
        _input_state(root)
    artifact_root = root / "outputs/artifacts/manuscript-draft"
    if artifact_root.exists():
        for path in artifact_root.iterdir():
            if path.is_symlink() or not path.is_file() or path.name != "sha256-" + sha256_bytes(path.read_bytes())[7:] + ".json":
                raise PackageValidationError("Writing revision Output address is invalid")
            validate_manuscript_draft_v3(_object(path, "manuscript-draft/v3"), root=root)
    return {"valid": True, "package_id": manifest["package_id"], "package_checksum": manifest["package_checksum"], "manifest_checksum": manifest["manifest_checksum"], "declared_file_count": len(files), "harness_acceptance_status": manifest["harness_acceptance_status"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path)
    args = parser.parse_args(); print(canonical_json(validate(args.root)))
