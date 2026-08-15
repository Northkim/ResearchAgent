#!/usr/bin/env python3
"""Self-contained validator for immutable Real Experiment Capsule 0.6."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
RESOURCE_ID = re.compile(r"^resource-[0-9a-f]{32}$")
ATTEMPT_ID = re.compile(r"^attempt-[0-9a-f]{32}$")
ALLOWED_DYNAMIC = (
    "inputs/experiment-package/", "outputs/artifacts/experiment-record/",
    "memory/execution/", "memory/progress/reports/", "memory/progress/receipts/",
    "memory/input-provenance.json", "memory/resource-provenance.json",
    "memory/plan-context.json", "memory/experiment-requirements.json",
    "memory/experiment-plan.json", "memory/experiment-approval.json",
    "memory/approval-consumption.json", "memory/current-artifact.json",
)


class PackageValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def safe_relative_path(value: Any, *, allow_dot: bool = False) -> str:
    if allow_dot and value == ".":
        return value
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PackageValidationError("unsafe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise PackageValidationError("unsafe relative path")
    return value


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise PackageValidationError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label} must be an object")
    return value


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


def _artifact_ref(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise PackageValidationError("Artifact reference must be an object")
    _exact(value, {"artifact_id", "artifact_type", "sha256"}, "Artifact reference")
    if not ARTIFACT_ID.fullmatch(str(value["artifact_id"])):
        raise PackageValidationError("Artifact ID is invalid")
    _text(value["artifact_type"], "Artifact type")
    _checksum(value["sha256"], "Artifact checksum")
    return dict(value)


def _limits(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise PackageValidationError("limits must be an object")
    _exact(value, {"wall_seconds", "cpu_seconds", "max_output_bytes"}, "limits")
    bounds = {"wall_seconds": (1, 300), "cpu_seconds": (1, 300), "max_output_bytes": (1024, 10_485_760)}
    for field, (minimum, maximum) in bounds.items():
        number = value[field]
        if isinstance(number, bool) or not isinstance(number, int) or not minimum <= number <= maximum:
            raise PackageValidationError(f"limit {field} is invalid")
    return dict(value)


def _metrics(value: Any, *, results: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not results and not value) or len(value) > 50:
        raise PackageValidationError("metrics are invalid")
    fields = {"name", "value", "unit"} if results else {"name", "description", "unit"}
    validated = []
    for raw in value:
        if not isinstance(raw, dict):
            raise PackageValidationError("metric must be an object")
        _exact(raw, fields, "metric")
        _text(raw["name"], "metric name")
        if results:
            if isinstance(raw["value"], bool) or not isinstance(raw["value"], (int, float)) or not math.isfinite(raw["value"]):
                raise PackageValidationError("metric value is invalid")
        else:
            _text(raw["description"], "metric description")
        if raw["unit"] is not None:
            _text(raw["unit"], "metric unit")
        validated.append(dict(raw))
    if len({item["name"] for item in validated}) != len(validated):
        raise PackageValidationError("metric names are duplicated")
    return validated


def validate_requirements(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackageValidationError("Experiment Requirements must be an object")
    _exact(value, {
        "research_question", "hypothesis", "scientific_inputs", "configuration",
        "seeds", "repetitions", "metrics", "runtime", "limits", "stopping_conditions",
    }, "Experiment Requirements")
    _text(value["research_question"], "research question")
    if value["hypothesis"] is not None:
        _text(value["hypothesis"], "hypothesis")
    if not isinstance(value["scientific_inputs"], list) or not value["scientific_inputs"]:
        raise PackageValidationError("scientific inputs are required")
    for need in value["scientific_inputs"]:
        if not isinstance(need, dict):
            raise PackageValidationError("scientific input must be an object")
        _exact(need, {"kind", "role", "required"}, "scientific input")
        if need["kind"] not in {"SOURCE_CODE", "DATASET", "EVENTS", "MODEL", "CHECKPOINT", "BASELINE"} or not isinstance(need["required"], bool):
            raise PackageValidationError("scientific input is invalid")
        _text(need["role"], "scientific input role")
    if not isinstance(value["configuration"], dict):
        raise PackageValidationError("configuration must be an object")
    if not isinstance(value["seeds"], list) or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in value["seeds"]):
        raise PackageValidationError("seeds are invalid")
    if isinstance(value["repetitions"], bool) or not isinstance(value["repetitions"], int) or not 1 <= value["repetitions"] <= 100:
        raise PackageValidationError("repetitions are invalid")
    _metrics(value["metrics"])
    _text(value["runtime"], "runtime")
    _limits(value["limits"])
    if not isinstance(value["stopping_conditions"], list) or any(not isinstance(item, str) or not item.strip() for item in value["stopping_conditions"]):
        raise PackageValidationError("stopping conditions are invalid")
    return dict(value)


def validate_plan(value: Any, context: dict[str, Any], requirements_checksum: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackageValidationError("Experiment Plan must be an object")
    _exact(value, {
        "research_question", "hypothesis", "requirements_sha256", "source_artifacts",
        "resource", "entrypoint", "argv", "working_directory", "configuration",
        "seeds", "repetitions", "metrics", "environment", "network_policy",
        "limits", "stopping_conditions", "known_limitations",
    }, "Experiment Plan")
    _text(value["research_question"], "plan research question")
    if value["hypothesis"] is not None:
        _text(value["hypothesis"], "plan hypothesis")
    if value["requirements_sha256"] != requirements_checksum:
        raise PackageValidationError("plan Requirements checksum mismatch")
    sources = [_artifact_ref(item) for item in value["source_artifacts"]] if isinstance(value["source_artifacts"], list) else []
    if sources != context["source_artifacts"]:
        raise PackageValidationError("plan source identity mismatch")
    if value["resource"] != context["resource"] or value["entrypoint"] != context["entrypoint"] or value["argv"] != context["argv"]:
        raise PackageValidationError("plan Resource or command differs from readiness evidence")
    if value["working_directory"] != context["working_directory"] or value["environment"] != context["environment"] or value["network_policy"] != "DISABLED":
        raise PackageValidationError("plan runtime boundary differs from readiness evidence")
    safe_relative_path(value["entrypoint"])
    if not isinstance(value["argv"], list) or len(value["argv"]) != 3 or any(not isinstance(item, str) or not item for item in value["argv"]):
        raise PackageValidationError("plan argv is invalid")
    safe_relative_path(value["working_directory"], allow_dot=True)
    if not isinstance(value["configuration"], dict):
        raise PackageValidationError("plan configuration must be an object")
    if not isinstance(value["seeds"], list) or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in value["seeds"]):
        raise PackageValidationError("plan seeds are invalid")
    if isinstance(value["repetitions"], bool) or not isinstance(value["repetitions"], int) or not 1 <= value["repetitions"] <= 100:
        raise PackageValidationError("plan repetitions are invalid")
    _metrics(value["metrics"])
    _limits(value["limits"])
    for field in ("stopping_conditions", "known_limitations"):
        if not isinstance(value[field], list) or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise PackageValidationError(f"plan {field} is invalid")
    return dict(value)


def _evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackageValidationError("evidence reference must be an object")
    _exact(value, {"relative_path", "sha256", "availability", "limitation"}, "evidence reference")
    safe_relative_path(value["relative_path"])
    _checksum(value["sha256"], "evidence checksum")
    if value["availability"] != "AVAILABLE" or (value["limitation"] is not None and not isinstance(value["limitation"], str)):
        raise PackageValidationError("evidence availability is invalid")
    return dict(value)


def validate_experiment_record_v2(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackageValidationError("experiment-record/v2 must be an object")
    _exact(value, {
        "schema", "core_capability_maturity", "mode", "source_artifacts",
        "requirements", "approved_plan", "approval", "execution", "evaluation",
        "result_status", "limitations",
    }, "experiment-record/v2")
    if value["schema"] != "experiment-record/v2" or value["core_capability_maturity"] != "REVIEWED_CORE" or value["mode"] != "IDEA_EXPERIMENT":
        raise PackageValidationError("experiment-record/v2 identity is invalid")
    sources = [_artifact_ref(item) for item in value["source_artifacts"]]
    if not sources or sources[0]["artifact_type"] != "selected-research-idea/v1":
        raise PackageValidationError("selected Idea provenance is required first")
    requirements = value["requirements"]
    plan = value["approved_plan"]
    for item, label in ((requirements, "requirements"), (plan, "plan")):
        if not isinstance(item, dict):
            raise PackageValidationError(f"{label} identity is invalid")
        _exact(item, {"sha256", "value"}, label)
        if canonical_hash(item["value"]) != item["sha256"]:
            raise PackageValidationError(f"{label} checksum mismatch")
    validate_requirements(requirements["value"])
    plan_context = {
        key: plan["value"][key] for key in (
            "source_artifacts", "resource", "entrypoint", "argv",
            "working_directory", "environment",
        )
    }
    validate_plan(plan["value"], plan_context, requirements["sha256"])
    approval = value["approval"]
    if not isinstance(approval, dict):
        raise PackageValidationError("approval is invalid")
    _exact(approval, {"sha256", "plan_sha256", "attempt_id", "approved_at", "decision", "scope"}, "approval")
    payload = dict(approval)
    approval_checksum = payload.pop("sha256")
    if canonical_hash(payload) != approval_checksum or approval["plan_sha256"] != plan["sha256"] or approval["decision"] != "APPROVED" or approval["scope"] != "ONE_ATTEMPT" or not ATTEMPT_ID.fullmatch(str(approval["attempt_id"])):
        raise PackageValidationError("approval identity is invalid")
    _time(approval["approved_at"], "approval time")
    execution = value["execution"]
    if not isinstance(execution, dict):
        raise PackageValidationError("execution is invalid")
    _exact(execution, {"attempt_id", "approval_sha256", "status", "started_at", "completed_at", "argv", "working_directory", "environment", "network_policy", "limits", "exit_code", "signal", "stdout", "stderr"}, "execution")
    if execution["attempt_id"] != approval["attempt_id"] or execution["approval_sha256"] != approval_checksum or execution["argv"] != plan["value"]["argv"] or execution["environment"] != plan["value"]["environment"] or execution["limits"] != plan["value"]["limits"] or execution["network_policy"] != "DISABLED":
        raise PackageValidationError("execution differs from approved plan")
    if execution["status"] not in {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED", "INTERRUPTED"}:
        raise PackageValidationError("execution status is invalid")
    if _time(execution["completed_at"], "execution completion") < _time(execution["started_at"], "execution start"):
        raise PackageValidationError("execution timestamps are invalid")
    _evidence(execution["stdout"]); _evidence(execution["stderr"])
    evaluation = value["evaluation"]
    if not isinstance(evaluation, dict):
        raise PackageValidationError("evaluation is invalid")
    _exact(evaluation, {"status", "metrics", "raw_result", "summary"}, "evaluation")
    if evaluation["status"] not in {"VALID", "INVALID", "NOT_RUN"}:
        raise PackageValidationError("evaluation status is invalid")
    _metrics(evaluation["metrics"], results=True)
    if evaluation["raw_result"] is not None:
        _evidence(evaluation["raw_result"])
    _text(evaluation["summary"], "evaluation summary")
    if value["result_status"] not in {"SUCCEEDED", "FAILED", "PARTIAL"}:
        raise PackageValidationError("result status is invalid")
    if value["result_status"] == "SUCCEEDED" and (execution["status"] != "SUCCEEDED" or execution["exit_code"] != 0 or evaluation["status"] != "VALID"):
        raise PackageValidationError("successful result lacks valid execution and evaluation")
    if execution["status"] == "SUCCEEDED" and evaluation["status"] == "INVALID" and value["result_status"] != "PARTIAL":
        raise PackageValidationError("invalid evaluation must be partial")
    if not isinstance(value["limitations"], list) or any(not isinstance(item, str) or not item.strip() for item in value["limitations"]):
        raise PackageValidationError("limitations are invalid")
    return dict(value)


def _tree_manifest(root: Path) -> tuple[str, list[dict[str, Any]]]:
    if root.is_symlink() or not root.is_dir():
        raise PackageValidationError("Resource package root is unsafe")
    entries = []
    for base, directories, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in (*directories, *names):
            path = base_path / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or (not stat.S_ISDIR(mode) and not stat.S_ISREG(mode)) or (stat.S_ISREG(mode) and path.stat().st_nlink != 1):
                raise PackageValidationError("Resource package contains unsafe bytes")
        for name in names:
            path = base_path / name
            relative = path.relative_to(root).as_posix()
            entries.append({"path": relative, "sha256": sha256_bytes(path.read_bytes()), "size_bytes": path.stat().st_size})
    entries.sort(key=lambda item: item["path"])
    return canonical_hash(entries), entries


def _validate_resource(root: Path) -> None:
    provenance_path = root / "memory/resource-provenance.json"
    if not provenance_path.exists():
        return
    value = _object(provenance_path, "Resource provenance")
    _exact(value, {"schema_version", "workflow_instance_id", "resource_id", "resource_kind", "provider", "locator", "exact_revision", "content_checksum", "target_relative_path", "package"}, "Resource provenance")
    if value["schema_version"] != "reagent.real-experiment-resource-provenance/v0.1" or value["resource_kind"] != "SOURCE_REPOSITORY" or value["provider"] != "GITHUB" or not RESOURCE_ID.fullmatch(str(value["resource_id"])):
        raise PackageValidationError("Resource provenance identity is invalid")
    target = safe_relative_path(value["target_relative_path"])
    if target != "inputs/experiment-package":
        raise PackageValidationError("Resource target is invalid")
    checksum, _ = _tree_manifest(root / target)
    if checksum != value["content_checksum"]:
        raise PackageValidationError("staged Resource package checksum drifted")
    package = value["package"]
    if not isinstance(package, dict):
        raise PackageValidationError("package readiness evidence is invalid")
    _exact(package, {"manifest_checksum", "entrypoint", "entrypoint_checksum", "lock_file", "lock_checksum", "runtime", "runtime_version"}, "package readiness")
    manifest_path = root / target / ".reagent-experiment.json"
    if sha256_bytes(manifest_path.read_bytes()) != package["manifest_checksum"]:
        raise PackageValidationError("Experiment package manifest drifted")
    for relative, expected in ((package["entrypoint"], package["entrypoint_checksum"]), (package["lock_file"], package["lock_checksum"])):
        path = root / target / safe_relative_path(relative)
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1 or sha256_bytes(path.read_bytes()) != expected:
            raise PackageValidationError("Experiment package runtime identity drifted")


def validate(root_value: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    supplied = Path(root_value)
    if supplied.is_symlink():
        raise PackageValidationError("Capsule root is unsafe")
    root = supplied.resolve()
    manifest = _object(root / "package-manifest.json", "package manifest")
    if manifest.get("workflow_id") != "reproduction-experiment-local-experimental" or manifest.get("workflow_version") != "0.4.0" or manifest.get("package_template_version") != "0.6.0":
        raise PackageValidationError("Real Experiment Capsule identity mismatch")
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
    for path in root.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise PackageValidationError("Capsule directory link rejected")
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "package-manifest.json" or relative in declared or any(relative.startswith(prefix) for prefix in ALLOWED_DYNAMIC):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("Capsule dynamic file is unsafe")
            continue
        raise PackageValidationError(f"undeclared Capsule file: {relative}")
    config = _object(root / "workflow/real-experiment.json", "Real Experiment contract")
    if config.get("schema_version") != "reagent.real-experiment-workflow/v0.1" or config.get("output_artifact_type") != "experiment-record/v2" or config.get("network_policy") != "DISABLED":
        raise PackageValidationError("Real Experiment contract is invalid")
    _validate_resource(root)
    artifact_root = root / "outputs/artifacts/experiment-record"
    if artifact_root.exists():
        for path in artifact_root.iterdir():
            if path.is_symlink() or not path.is_file() or path.name != "sha256-" + sha256_bytes(path.read_bytes())[7:] + ".json":
                raise PackageValidationError("Experiment Output address is invalid")
            validate_experiment_record_v2(_object(path, "experiment-record/v2"))
    return {"valid": True, "package_id": manifest["package_id"], "package_checksum": manifest["package_checksum"], "manifest_checksum": manifest["manifest_checksum"], "declared_file_count": len(files), "harness_acceptance_status": manifest["harness_acceptance_status"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(canonical_json(validate(args.root)))
