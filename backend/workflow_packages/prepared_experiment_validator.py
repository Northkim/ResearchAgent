"""Self-contained Capsule/package validator for reviewed Experiment 0.5 Path A."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any


class PreparedExperimentValidationError(ValueError):
    pass


def _runtime_imports(root: Path) -> None:
    library = root / "runtime_lib"
    if str(library) not in sys.path:
        sys.path.insert(0, str(library))


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise PreparedExperimentValidationError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreparedExperimentValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PreparedExperimentValidationError(f"{label} must be an object")
    return value


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PreparedExperimentValidationError("Capsule path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PreparedExperimentValidationError("Capsule path is unsafe")
    return value


def validate(root: Path, *, pristine: bool = False) -> dict[str, Any]:
    root = root.resolve()
    manifest = _object(root / "package-manifest.json", "package manifest")
    if (
        manifest.get("workflow_id") != "reproduction-experiment-local-experimental"
        or manifest.get("workflow_version") != "0.5.0"
        or manifest.get("package_template_version") != "0.8.0"
    ):
        raise PreparedExperimentValidationError("Experiment 0.5 Capsule identity is invalid")
    declared = {
        _safe_relative(item.get("relative_path"))
        for item in manifest.get("files", []) if isinstance(item, dict)
    }
    dynamic = ("inputs/", "outputs/", "memory/")
    folded: dict[str, str] = {}
    for base, directories, files in os.walk(root, followlinks=False):
        for name in (*directories, *files):
            path = Path(base) / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or (not stat.S_ISDIR(mode) and not stat.S_ISREG(mode)):
                raise PreparedExperimentValidationError("Capsule contains a link or special file")
            if stat.S_ISREG(mode) and path.stat().st_nlink != 1:
                raise PreparedExperimentValidationError("Capsule contains a hard-linked file")
            prior = folded.setdefault(relative.casefold(), relative)
            if prior != relative:
                raise PreparedExperimentValidationError("Capsule contains a case collision")
        for name in files:
            relative = (Path(base) / name).relative_to(root).as_posix()
            if relative != "package-manifest.json" and relative not in declared and not any(relative.startswith(prefix) for prefix in dynamic):
                raise PreparedExperimentValidationError(f"undeclared Capsule file: {relative}")
    workflow = _object(root / "workflow/prepared-experiment.json", "prepared Experiment contract")
    if (
        workflow.get("schema") != "reagent.prepared-experiment-workflow/v0.1"
        or workflow.get("mode") != "PREPARE_WITH_REAGENT"
        or workflow.get("output_artifact_type") != "experiment-record/v3"
        or workflow.get("network_policy") != "DISABLED"
        or workflow.get("builder_family") != "SKLEARN_TABULAR_CLASSIFICATION_V1"
    ):
        raise PreparedExperimentValidationError("prepared Experiment contract is invalid")
    if pristine and any((root / path).exists() for path in ("memory/methodology.json", "memory/design-approval.json", "memory/preparation/validated")):
        raise PreparedExperimentValidationError("pristine Capsule contains prepared state")
    return {
        "valid": True, "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(manifest["files"]),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }


def validate_experiment_record_v3(value: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    base = (root or Path(__file__).resolve().parent).resolve()
    _runtime_imports(base)
    from backend.artifact_references.research_flow_contracts import (  # noqa: PLC0415
        validate_experiment_record_v3 as canonical_validator,
    )
    return canonical_validator(value)
