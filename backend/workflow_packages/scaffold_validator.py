#!/usr/bin/env python3
"""Self-contained validator shared by immutable scaffold Capsules."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
SCAFFOLD_MARKERS = {
    "WRITING": "SCAFFOLD PLACEHOLDER",
    "REVIEW": "SCAFFOLD REVIEW PLACEHOLDER",
    "EXPERIMENT": "SCAFFOLD EXPERIMENT PLACEHOLDER",
}
ALLOWED_DYNAMIC = (
    "outputs/artifacts/",
    "memory/progress/reports/",
    "memory/progress/receipts/",
)


class PackageValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PackageValidationError("unsafe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise PackageValidationError("unsafe relative path")
    if re.match(r"^[A-Za-z]:", value):
        raise PackageValidationError("absolute path rejected")
    return value


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise PackageValidationError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label} must be a JSON object")
    return value


def _normalized_files(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for value in values:
        item = dict(value)
        if item.get("mutable_by_harness"):
            item["sha256"] = None
            item["byte_size"] = None
        result.append(item)
    return result


def _manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload["manifest_checksum"] = None
    payload["package_checksum"] = None
    payload["files"] = _normalized_files(payload["files"])
    return canonical_hash(payload)


def _package_hash(manifest: dict[str, Any]) -> str:
    return canonical_hash({
        "package_id": manifest["package_id"],
        "package_schema_version": manifest["package_schema_version"],
        "file_manifest_checksum": manifest["file_manifest_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
    })


def _artifact_ref(value: Any, expected_type: str, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {
        "artifact_id", "artifact_type", "sha256"
    }:
        raise PackageValidationError(f"{label} provenance fields mismatch")
    if not ARTIFACT_ID.fullmatch(str(value["artifact_id"])):
        raise PackageValidationError(f"{label} Artifact ID is invalid")
    if value["artifact_type"] != expected_type:
        raise PackageValidationError(f"{label} Artifact type mismatch")
    if not SHA256.fullmatch(str(value["sha256"])):
        raise PackageValidationError(f"{label} checksum is invalid")
    return dict(value)


def _optional_ref(value: Any, expected_type: str, label: str):
    return None if value is None else _artifact_ref(value, expected_type, label)


def validate_scaffold_artifact(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackageValidationError("scaffold Artifact must be an object")
    schema = value.get("schema")
    if value.get("core_capability_maturity") != "SCAFFOLD_CORE":
        raise PackageValidationError("scaffold Artifact maturity mismatch")
    if schema == "manuscript-draft/v1":
        if set(value) != {
            "schema", "core_capability_maturity", "source_artifacts", "title",
            "content_markdown",
        }:
            raise PackageValidationError("manuscript Artifact fields mismatch")
        sources = value["source_artifacts"]
        if not isinstance(sources, dict) or set(sources) != {
            "research_idea", "literature_library", "experiment_record",
            "review_feedback", "prior_manuscript",
        }:
            raise PackageValidationError("manuscript source roles mismatch")
        refs = [
            _artifact_ref(sources["research_idea"], "selected-research-idea/v1", "research idea"),
            _artifact_ref(sources["literature_library"], "selected-paper-library/v1", "literature library"),
            _optional_ref(sources["experiment_record"], "experiment-record/v1", "experiment record"),
            _optional_ref(sources["review_feedback"], "review-report/v1", "review feedback"),
            _optional_ref(sources["prior_manuscript"], "manuscript-draft/v1", "prior manuscript"),
        ]
        identities = [item["artifact_id"] for item in refs if item is not None]
        if len(identities) != len(set(identities)):
            raise PackageValidationError("manuscript source Artifact identity is duplicated")
        if not isinstance(value["title"], str) or not value["title"].startswith("SCAFFOLD PLACEHOLDER"):
            raise PackageValidationError("manuscript scaffold title marker is required")
        content = value["content_markdown"]
        if (
            not isinstance(content, str)
            or "SCAFFOLD PLACEHOLDER" not in content
            or "No substantive academic manuscript was generated" not in content
        ):
            raise PackageValidationError("manuscript scaffold safety marker is required")
        return dict(value)
    if schema == "review-report/v1":
        if set(value) != {
            "schema", "core_capability_maturity", "source_manuscript",
            "supporting_artifacts", "summary", "major_issues", "minor_issues",
            "requested_revisions", "recommendation",
        }:
            raise PackageValidationError("review Artifact fields mismatch")
        _artifact_ref(value["source_manuscript"], "manuscript-draft/v1", "source manuscript")
        supporting = value["supporting_artifacts"]
        if not isinstance(supporting, list):
            raise PackageValidationError("review supporting Artifacts are invalid")
        for item in supporting:
            artifact_type = item.get("artifact_type") if isinstance(item, dict) else None
            if artifact_type not in {"selected-paper-library/v1", "experiment-record/v1"}:
                raise PackageValidationError("review supporting Artifact type is invalid")
            _artifact_ref(item, artifact_type, "supporting Artifact")
        if value["major_issues"] != [] or value["minor_issues"] != []:
            raise PackageValidationError("scaffold review cannot claim manuscript issues")
        if value["recommendation"] != "INSUFFICIENT_EVIDENCE":
            raise PackageValidationError("scaffold review recommendation must be insufficient evidence")
        if "SCAFFOLD REVIEW PLACEHOLDER" not in str(value["summary"]):
            raise PackageValidationError("review scaffold marker is required")
        revisions = value["requested_revisions"]
        if not isinstance(revisions, list) or len(revisions) != 1:
            raise PackageValidationError("scaffold review safety revision is required")
        revision = revisions[0]
        if (
            not isinstance(revision, dict)
            or set(revision) != {"revision_id", "description", "priority"}
            or revision["priority"] != "MAJOR"
            or "does not perform substantive academic review" not in str(revision["description"])
        ):
            raise PackageValidationError("scaffold review safety revision is invalid")
        return dict(value)
    if schema == "experiment-record/v1":
        if set(value) != {
            "schema", "core_capability_maturity", "mode", "source_artifacts",
            "execution_status", "plan", "actual_results", "limitations",
        }:
            raise PackageValidationError("experiment Artifact fields mismatch")
        if value["mode"] != "IDEA_EXPERIMENT":
            raise PackageValidationError("paper reproduction is not enabled")
        sources = value["source_artifacts"]
        if not isinstance(sources, list) or not sources:
            raise PackageValidationError("experiment source provenance is required")
        allowed = {"selected-research-idea/v1", "selected-paper-library/v1"}
        for item in sources:
            artifact_type = item.get("artifact_type") if isinstance(item, dict) else None
            if artifact_type not in allowed:
                raise PackageValidationError("experiment source Artifact type is invalid")
            _artifact_ref(item, artifact_type, "experiment source")
        if (
            value["execution_status"] != "PLACEHOLDER_NOT_EXECUTED"
            or value["actual_results"] is not None
        ):
            raise PackageValidationError("scaffold experiment cannot claim execution")
        plan = value["plan"]
        if not isinstance(plan, dict) or set(plan) != {
            "objective", "hypothesis", "method", "metrics", "baselines"
        }:
            raise PackageValidationError("experiment plan fields mismatch")
        if plan["metrics"] != [] or plan["baselines"] != []:
            raise PackageValidationError("scaffold experiment metrics and baselines must be empty")
        if "No real experiment or reproduction was executed" not in str(plan["method"]):
            raise PackageValidationError("experiment scaffold method marker is required")
        return dict(value)
    raise PackageValidationError("unknown scaffold Artifact schema")


def _validate_outputs(root: Path, config: dict[str, Any]) -> None:
    human = root.joinpath(*config["human_output_path"].split("/"))
    if human.exists() or human.is_symlink():
        if human.is_symlink() or not human.is_file() or human.stat().st_nlink != 1:
            raise PackageValidationError("human scaffold output must be a regular file")
        text = human.read_text(encoding="utf-8")
        if SCAFFOLD_MARKERS[config["workflow_kind"]] not in text:
            raise PackageValidationError("human scaffold output marker is missing")
    artifact_root = root.joinpath(*config["artifact_path_prefix"].split("/"))
    if not artifact_root.exists():
        return
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise PackageValidationError("scaffold Artifact root is unsafe")
    for path in sorted(artifact_root.iterdir()):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise PackageValidationError("scaffold Artifact must be a regular unlinked file")
        content = path.read_bytes()
        if path.name != "sha256-" + sha256_bytes(content)[7:] + ".json":
            raise PackageValidationError("scaffold Artifact content address mismatch")
        value = _object(path, "scaffold Artifact")
        if value.get("schema") != config["output_artifact_type"]:
            raise PackageValidationError("scaffold Artifact output type mismatch")
        validate_scaffold_artifact(value)


def _validate_pinned_skills(
    root: Path, manifest: dict[str, Any], config: dict[str, Any]
) -> None:
    """Fail closed on missing, drifted, floating, or undeclared Skill content."""

    expected = config.get("pinned_skills")
    if expected is None:
        return  # Immutable F1B 0.1.0 Capsule contract.
    pins = manifest.get("skill_pins")
    if not isinstance(expected, list) or not expected or not isinstance(pins, list):
        raise PackageValidationError("required built-in Skill pins are invalid")
    if len(expected) != len(pins):
        raise PackageValidationError("required built-in Skill pin count mismatch")
    expected_by_id = {
        item.get("skill_id"): item for item in expected if isinstance(item, dict)
    }
    if len(expected_by_id) != len(expected):
        raise PackageValidationError("required built-in Skill pins are duplicated")
    for pin in pins:
        if not isinstance(pin, dict):
            raise PackageValidationError("required built-in Skill pin is invalid")
        skill_id = pin.get("name")
        declared = expected_by_id.get(skill_id)
        if (
            declared is None
            or pin.get("semantic_version") != declared.get("skill_version")
            or pin.get("checksum") != declared.get("content_checksum")
            or declared.get("trust") != "BUILT_IN_REVIEWED"
        ):
            raise PackageValidationError("required built-in Skill identity mismatch")
        entrypoint = safe_relative_path(pin.get("relative_path"))
        skill_root = f"workflow/skills/{skill_id}"
        if entrypoint != f"{skill_root}/SKILL.md":
            raise PackageValidationError("required built-in Skill entrypoint mismatch")
        instructions_path = root.joinpath(*entrypoint.split("/"))
        contract_path = root.joinpath(*f"{skill_root}/skill.json".split("/"))
        if (
            instructions_path.is_symlink()
            or contract_path.is_symlink()
            or not instructions_path.is_file()
            or not contract_path.is_file()
            or instructions_path.stat().st_nlink != 1
            or contract_path.stat().st_nlink != 1
        ):
            raise PackageValidationError("required built-in Skill is missing or unsafe")
        contract = _object(contract_path, "built-in Skill contract")
        if (
            contract.get("schema_version") != "local-skill/v0.1"
            or contract.get("name") != skill_id
            or contract.get("version") != declared.get("skill_version")
            or contract.get("trust") != "BUILT_IN_REVIEWED_ONLY"
        ):
            raise PackageValidationError("required built-in Skill contract mismatch")
        files = contract.get("files")
        instruction_checksum = sha256_bytes(instructions_path.read_bytes())
        if not isinstance(files, list) or files != [{
            "path": "SKILL.md", "sha256": instruction_checksum,
        }]:
            raise PackageValidationError("required built-in Skill file manifest mismatch")
        checksum = canonical_hash({
            "instructions": instruction_checksum,
            "contract": sha256_bytes(contract_path.read_bytes()),
        })
        if checksum != pin.get("checksum"):
            raise PackageValidationError("required built-in Skill checksum mismatch")


def validate(root: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    package_root = Path(root)
    if package_root.is_symlink() or not package_root.is_dir():
        raise PackageValidationError("package root must be a real directory")
    manifest = _object(package_root / "package-manifest.json", "package manifest")
    config = _object(package_root / "workflow/scaffold.json", "scaffold contract")
    if (
        manifest.get("package_schema_version") != "workflow-package/v0.1"
        or manifest.get("workflow_id") != config.get("workflow_id")
        or manifest.get("workflow_version") != config.get("workflow_version")
        or manifest.get("package_template_version") not in {"0.1.0", "0.2.0", "0.3.0"}
    ):
        raise PackageValidationError("scaffold Capsule identity mismatch")
    if config.get("core_capability_maturity") != "SCAFFOLD_CORE":
        raise PackageValidationError("scaffold Capsule maturity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise PackageValidationError("manifest files must be non-empty")
    paths = [safe_relative_path(item.get("relative_path")) for item in files]
    if len(paths) != len(set(paths)):
        raise PackageValidationError("manifest contains duplicate paths")
    if manifest.get("file_manifest_checksum") != canonical_hash(_normalized_files(files)):
        raise PackageValidationError("file manifest checksum mismatch")
    if manifest.get("manifest_checksum") != _manifest_hash(manifest):
        raise PackageValidationError("manifest checksum mismatch")
    if manifest.get("package_checksum") != _package_hash(manifest):
        raise PackageValidationError("package checksum mismatch")
    entries = {item["relative_path"]: item for item in files}
    allowed_inputs = {
        "inputs/project.json",
        *(
            item["target_relative_path"]
            for item in config.get("input_requirements", [])
        ),
    }
    output_paths = {
        item["required_output_path"] for item in manifest.get("output_contracts", [])
    }
    seen: set[str] = set()
    for base, directories, names in os.walk(package_root, followlinks=False):
        base_path = Path(base)
        for name in (*directories, *names):
            candidate = base_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or (not candidate.is_dir() and not stat.S_ISREG(mode)):
                raise PackageValidationError("symbolic links and special files are forbidden")
        for name in names:
            candidate = base_path / name
            relative = candidate.relative_to(package_root).as_posix()
            safe_relative_path(relative)
            if relative == "package-manifest.json":
                continue
            entry = entries.get(relative)
            dynamic = relative in output_paths or relative in allowed_inputs or relative in {
                "memory/input-provenance.json", "memory/current-artifact.json"
            } or relative.startswith(ALLOWED_DYNAMIC)
            if entry is None and not dynamic:
                raise PackageValidationError(f"undeclared file rejected: {relative}")
            if candidate.stat().st_nlink != 1:
                raise PackageValidationError("hard-linked package file rejected")
            if entry is not None:
                seen.add(relative)
                if pristine or not entry.get("mutable_by_harness"):
                    content = candidate.read_bytes()
                    if (
                        entry.get("sha256") != sha256_bytes(content)
                        or entry.get("byte_size") != len(content)
                    ):
                        raise PackageValidationError(f"file integrity mismatch: {relative}")
    required = {
        item["relative_path"] for item in files if item.get("requirement") == "REQUIRED"
    }
    if required - seen:
        raise PackageValidationError("required package files are missing")
    workflow = _object(package_root / "workflow/workflow.json", "workflow contract")
    if manifest.get("workflow_checksum") != canonical_hash(workflow):
        raise PackageValidationError("workflow checksum mismatch")
    _validate_pinned_skills(package_root, manifest, config)
    _validate_outputs(package_root, config)
    return {
        "valid": True,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(files),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }
