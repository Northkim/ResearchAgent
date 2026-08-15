#!/usr/bin/env python3
"""Self-contained validator for the immutable first Real Writing Capsule."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
SUPPORT = {"SUPPORTED", "PLANNED", "UNAVAILABLE"}
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
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(item, str) or not item.strip() for item in value):
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


def _input_state(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    _exact(provenance, {"schema_version", "workflow_instance_id", "artifacts"}, "input provenance")
    if provenance["schema_version"] != "reagent.real-writing-input-provenance/v0.1" or not WORKFLOW_INSTANCE_ID.fullmatch(str(provenance["workflow_instance_id"])):
        raise PackageValidationError("input provenance identity is invalid")
    records = _object(provenance["artifacts"], "input Artifact records")
    if set(records) not in ({"research_idea", "literature_library"}, {"research_idea", "literature_library", "experiment_record"}):
        raise PackageValidationError("Writing input roles are invalid")
    expected = {
        "research_idea": ("selected-research-idea/v1", "inputs/selected-research-idea.json"),
        "literature_library": ("selected-paper-library/v1", "inputs/selected-paper-library.json"),
        "experiment_record": ("experiment-record/v2", "inputs/experiment-record.json"),
    }
    normalized = {}
    values = {}
    for key, record in records.items():
        ref = artifact_ref(record, expected[key][0])
        path = root / expected[key][1]
        if sha256_bytes(path.read_bytes()) != ref["sha256"]:
            raise PackageValidationError("materialized input checksum drifted")
        normalized[key] = ref
        values[key] = _object(path, f"{key} input")
    if values["research_idea"].get("schema") != "selected-research-idea/v1":
        raise PackageValidationError("selected Idea schema is invalid")
    library = values["literature_library"]
    if library.get("schema") != "selected-paper-library/v1" or not isinstance(library.get("papers"), list):
        raise PackageValidationError("selected paper library is invalid")
    experiment = values.get("experiment_record")
    if experiment is not None:
        validate_experiment_record_v2(experiment)
    return provenance, normalized, library, experiment


def validate_experiment_record_v2(value: Any) -> dict[str, Any]:
    item = _object(value, "experiment-record/v2")
    _exact(item, {"schema", "core_capability_maturity", "mode", "source_artifacts", "requirements", "approved_plan", "approval", "execution", "evaluation", "result_status", "limitations"}, "experiment-record/v2")
    if item["schema"] != "experiment-record/v2" or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise PackageValidationError("experiment-record/v2 identity is invalid")
    execution = _object(item["execution"], "Experiment execution")
    evaluation = _object(item["evaluation"], "Experiment evaluation")
    if item["result_status"] not in {"SUCCEEDED", "FAILED", "PARTIAL"}:
        raise PackageValidationError("Experiment result status is invalid")
    if item["result_status"] == "SUCCEEDED" and (execution.get("status") != "SUCCEEDED" or execution.get("exit_code") != 0 or evaluation.get("status") != "VALID"):
        raise PackageValidationError("Experiment success lacks valid execution and evaluation")
    return item


def validate_evidence_map(value: Any, sources: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 50:
        raise PackageValidationError("Evidence Map must be non-empty and bounded")
    result = []
    seen = set()
    for raw in value:
        item = _object(raw, "Evidence Map item")
        _exact(item, {"section", "support_status", "evidence_refs", "limitations"}, "Evidence Map item")
        _text(item["section"], "Evidence Map section")
        if item["section"] in seen or item["support_status"] not in SUPPORT:
            raise PackageValidationError("Evidence Map section or status is invalid")
        seen.add(item["section"])
        refs = validate_evidence_refs(item["evidence_refs"], sources)
        if item["support_status"] == "SUPPORTED" and not refs:
            raise PackageValidationError("SUPPORTED Evidence Map item requires evidence")
        if item["support_status"] == "UNAVAILABLE" and refs:
            raise PackageValidationError("UNAVAILABLE Evidence Map item cannot cite evidence")
        _strings(item["limitations"], "Evidence Map limitations")
        result.append(item)
    return result


def validate_outline(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value or len(value) > 30:
        raise PackageValidationError("Outline must be non-empty and bounded")
    for raw in value:
        item = _object(raw, "Outline section")
        _exact(item, {"heading", "support_status"}, "Outline section")
        _text(item["heading"], "Outline heading")
        if item["support_status"] not in SUPPORT:
            raise PackageValidationError("Outline support status is invalid")
    return list(value)


def validate_evidence_refs(value: Any, sources: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 50:
        raise PackageValidationError("evidence references must be bounded")
    identities = [item for item in sources.values() if item is not None]
    result = []
    for raw in value:
        item = _object(raw, "evidence reference")
        _exact(item, {"artifact_id", "artifact_type", "sha256", "evidence_item", "location", "availability", "limitation"}, "evidence reference")
        identity = artifact_ref({key: item[key] for key in ("artifact_id", "artifact_type", "sha256")})
        if identity not in identities:
            raise PackageValidationError("evidence reference points to an unbound Artifact")
        _text(item["evidence_item"], "evidence item")
        _text(item["location"], "evidence location")
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
    result = []
    seen = set()
    for raw in value:
        item = _object(raw, "citation")
        _exact(item, {"citation_id", "paper_id", "source_artifact", "evidence_scope", "reference_markdown"}, "citation")
        _text(item["citation_id"], "citation ID"); _text(item["paper_id"], "paper ID"); _text(item["reference_markdown"], "reference")
        if item["citation_id"] in seen or item["paper_id"] not in paper_ids:
            raise PackageValidationError("citation is duplicate or outside selected library")
        seen.add(item["citation_id"])
        if artifact_ref(item["source_artifact"], "selected-paper-library/v1") != sources["literature_library"]:
            raise PackageValidationError("citation source is not the exact selected library")
        if item["evidence_scope"] not in {"METADATA_ONLY", "ABSTRACT"}:
            raise PackageValidationError("citation evidence scope is invalid")
        result.append(item)
    return result


def validate_claims(value: Any, sources: dict[str, Any], citations: list[dict[str, Any]], experiment: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 300:
        raise PackageValidationError("claims must be non-empty and bounded")
    known_citations = {item["citation_id"] for item in citations}
    experiment_valid = experiment is not None and experiment["result_status"] == "SUCCEEDED" and experiment["execution"]["status"] == "SUCCEEDED" and experiment["evaluation"]["status"] == "VALID"
    result = []
    seen = set()
    for raw in value:
        item = _object(raw, "claim")
        _exact(item, {"claim_id", "claim_type", "section", "claim_text", "support_status", "evidence_refs", "citation_ids", "limitations"}, "claim")
        for field in ("claim_id", "section", "claim_text"):
            _text(item[field], f"claim {field}")
        if item["claim_id"] in seen or item["claim_type"] not in {"LITERATURE", "PROPOSAL", "RESULT"} or item["support_status"] not in SUPPORT:
            raise PackageValidationError("claim identity, type, or status is invalid")
        seen.add(item["claim_id"])
        refs = validate_evidence_refs(item["evidence_refs"], sources)
        citation_ids = _strings(item["citation_ids"], "claim citations")
        _strings(item["limitations"], "claim limitations")
        if any(item_id not in known_citations for item_id in citation_ids):
            raise PackageValidationError("claim cites outside the selected library")
        if item["support_status"] == "SUPPORTED" and not refs:
            raise PackageValidationError("SUPPORTED claim requires evidence")
        if item["support_status"] == "UNAVAILABLE" and refs:
            raise PackageValidationError("UNAVAILABLE claim cannot cite evidence")
        if item["claim_type"] == "LITERATURE" and item["support_status"] == "SUPPORTED" and not citation_ids:
            raise PackageValidationError("supported literature claim requires citation")
        if item["claim_type"] == "RESULT" and item["support_status"] == "SUPPORTED":
            experiment_source = sources.get("experiment_record")
            if not experiment_valid or not any(experiment_source is not None and all(ref[key] == experiment_source[key] for key in ("artifact_id", "artifact_type", "sha256")) for ref in refs):
                raise PackageValidationError("supported result lacks valid exact Experiment evidence")
        result.append(item)
    return result


def validate_manuscript_draft_v2(value: Any, *, root: Path | None = None) -> dict[str, Any]:
    item = _object(value, "manuscript-draft/v2")
    _exact(item, {"schema", "core_capability_maturity", "producer", "source_artifacts", "writing_brief", "evidence_map", "approved_outline", "outline_approval", "title", "content_markdown", "claims", "citations", "experiment_evidence_available", "unsupported_areas", "limitations", "owner_review"}, "manuscript-draft/v2")
    if item["schema"] != "manuscript-draft/v2" or item["core_capability_maturity"] != "REVIEWED_CORE":
        raise PackageValidationError("manuscript-draft/v2 identity is invalid")
    producer = _object(item["producer"], "producer")
    _exact(producer, {"workflow_instance_id", "capsule_id", "capsule_version", "execution_round"}, "producer")
    if not WORKFLOW_INSTANCE_ID.fullmatch(str(producer["workflow_instance_id"])) or not CAPSULE_ID.fullmatch(str(producer["capsule_id"])) or producer["execution_round"] != 1:
        raise PackageValidationError("producer identity is invalid")
    validate_writing_brief(item["writing_brief"])
    sources = _object(item["source_artifacts"], "source Artifacts")
    _exact(sources, {"research_idea", "literature_library", "experiment_record"}, "source Artifacts")
    sources = {"research_idea": artifact_ref(sources["research_idea"], "selected-research-idea/v1"), "literature_library": artifact_ref(sources["literature_library"], "selected-paper-library/v1"), "experiment_record": None if sources["experiment_record"] is None else artifact_ref(sources["experiment_record"], "experiment-record/v2")}
    if root is None:
        library = {"papers": []}
        experiment = None
    else:
        provenance, exact_sources, library, experiment = _input_state(root)
        if provenance["workflow_instance_id"] != producer["workflow_instance_id"] or sources != {"research_idea": exact_sources["research_idea"], "literature_library": exact_sources["literature_library"], "experiment_record": exact_sources.get("experiment_record")}:
            raise PackageValidationError("manuscript lineage differs from exact inputs")
    evidence_map = validate_evidence_map(item["evidence_map"], sources)
    outline = _object(item["approved_outline"], "approved outline")
    _exact(outline, {"sha256", "value"}, "approved outline")
    if canonical_hash(validate_outline(outline["value"])) != outline["sha256"]:
        raise PackageValidationError("approved Outline checksum mismatch")
    approval = _object(item["outline_approval"], "outline approval")
    _exact(approval, {"sha256", "outline_sha256", "brief_sha256", "evidence_map_sha256", "source_artifacts_sha256", "approved_at", "decision"}, "outline approval")
    payload = dict(approval); approval_sha = payload.pop("sha256")
    if canonical_hash(payload) != approval_sha or approval["outline_sha256"] != outline["sha256"] or approval["brief_sha256"] != canonical_hash(item["writing_brief"]) or approval["evidence_map_sha256"] != canonical_hash(evidence_map) or approval["source_artifacts_sha256"] != canonical_hash(sources) or approval["decision"] != "APPROVED":
        raise PackageValidationError("outline approval identity is invalid")
    _time(approval["approved_at"], "outline approval time")
    citations = validate_citations(item["citations"], sources, library) if root is not None else list(item["citations"])
    claims = validate_claims(item["claims"], sources, citations, experiment) if root is not None else list(item["claims"])
    _text(item["title"], "manuscript title"); _text(item["content_markdown"], "manuscript content")
    if item["experiment_evidence_available"] is not (sources["experiment_record"] is not None):
        raise PackageValidationError("Experiment evidence availability is inconsistent")
    _strings(item["unsupported_areas"], "unsupported areas"); _strings(item["limitations"], "limitations")
    review = _object(item["owner_review"], "owner review")
    _exact(review, {"sha256", "draft_sha256", "reviewed_at", "decision"}, "owner review")
    review_payload = dict(review); review_sha = review_payload.pop("sha256")
    expected_draft = canonical_hash({"title": item["title"], "content_markdown": item["content_markdown"], "claims": claims, "citations": citations})
    if canonical_hash(review_payload) != review_sha or review["draft_sha256"] != expected_draft or review["decision"] != "APPROVED":
        raise PackageValidationError("owner review identity is invalid")
    _time(review["reviewed_at"], "owner review time")
    return item


def validate(root_value: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    supplied = Path(root_value)
    if supplied.is_symlink():
        raise PackageValidationError("Capsule root is unsafe")
    root = supplied.resolve()
    manifest = _object(root / "package-manifest.json", "package manifest")
    if manifest.get("workflow_id") != "writing-local-experimental" or manifest.get("workflow_version") != "0.3.0" or manifest.get("package_template_version") != "0.5.0":
        raise PackageValidationError("Real Writing Capsule identity mismatch")
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
    config = _object(root / "workflow/real-writing.json", "Real Writing contract")
    if config.get("schema_version") != "reagent.real-writing-workflow/v0.1" or config.get("output_artifact_type") != "manuscript-draft/v2":
        raise PackageValidationError("Real Writing contract is invalid")
    requirements = config.get("input_requirements")
    if not isinstance(requirements, list):
        raise PackageValidationError("Real Writing Artifact inputs are invalid")
    materialized_inputs = set()
    for requirement in requirements:
        if not isinstance(requirement, dict) or requirement.get("materialization_mode") != "VERIFIED_COPY":
            raise PackageValidationError("Real Writing input declaration is invalid")
        target = safe_relative_path(requirement.get("target_relative_path"))
        if not target.startswith("inputs/") or target.endswith("/") or target in materialized_inputs:
            raise PackageValidationError("Real Writing input target is invalid")
        materialized_inputs.add(target)
    runtime_dynamic = config.get("runtime_dynamic_paths")
    if not isinstance(runtime_dynamic, list) or not runtime_dynamic:
        raise PackageValidationError("Real Writing dynamic paths are invalid")
    runtime_dynamic_paths = set()
    for raw in runtime_dynamic:
        target = safe_relative_path(raw)
        if (
            target.endswith("/")
            or not target.startswith(("memory/", "outputs/"))
            or target in runtime_dynamic_paths
        ):
            raise PackageValidationError("Real Writing dynamic path is invalid")
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
    provenance = root / "memory/input-provenance.json"
    if provenance.exists():
        _input_state(root)
    artifact_root = root / "outputs/artifacts/manuscript-draft"
    if artifact_root.exists():
        for path in artifact_root.iterdir():
            if path.is_symlink() or not path.is_file() or path.name != "sha256-" + sha256_bytes(path.read_bytes())[7:] + ".json":
                raise PackageValidationError("Writing Output address is invalid")
            validate_manuscript_draft_v2(_object(path, "manuscript-draft/v2"), root=root)
    return {"valid": True, "package_id": manifest["package_id"], "package_checksum": manifest["package_checksum"], "manifest_checksum": manifest["manifest_checksum"], "declared_file_count": len(files), "harness_acceptance_status": manifest["harness_acceptance_status"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(canonical_json(validate(args.root)))
