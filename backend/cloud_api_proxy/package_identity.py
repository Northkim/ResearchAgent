"""Read-only identity derivation from a validated external Workflow Package."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.workflow_packages import validate_package


@dataclass(frozen=True, slots=True)
class PackageIdentity:
    root: Path
    project_id: str
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str


def read_validated_package_identity(package_root: str | Path) -> PackageIdentity:
    supplied = Path(package_root)
    if supplied.is_symlink():
        raise ValueError("package root must not be a symbolic link")
    root = supplied.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("package root must be a directory")
    validation = validate_package(root, pristine=False)
    if not validation.valid:
        raise ValueError("Workflow Package validation failed")
    manifest_path = root / "package-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("package manifest must be a regular file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("package manifest must be UTF-8 JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError("package manifest must be a JSON object")
    return PackageIdentity(
        root=root,
        project_id=manifest["experimental_project_identity"],
        package_id=manifest["package_id"],
        package_checksum=manifest["package_checksum"],
        workflow_id=manifest["workflow_id"],
        workflow_version=manifest["workflow_version"],
        workflow_checksum=manifest["workflow_checksum"],
    )
