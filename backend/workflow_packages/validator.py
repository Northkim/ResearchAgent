"""Repository-side package and deterministic archive validation."""

from __future__ import annotations

import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .package_validator import PackageValidationError, safe_relative_path, validate


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    package_id: str
    package_checksum: str
    manifest_checksum: str
    declared_file_count: int
    harness_acceptance_status: str


def validate_package(root: str | Path, *, pristine: bool = False) -> ValidationResult:
    result = validate(root, pristine=pristine)
    return ValidationResult(**result)


def validate_archive(archive_path: str | Path, *, pristine: bool = True) -> ValidationResult:
    archive = Path(archive_path)
    with zipfile.ZipFile(archive, "r") as bundle:
        names: list[str] = []
        for info in bundle.infolist():
            name = info.filename.rstrip("/")
            if not name:
                continue
            safe_relative_path(name)
            if name in names:
                raise PackageValidationError(f"duplicate archive member: {name}")
            names.append(name)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise PackageValidationError(f"archive symbolic link rejected: {name}")
        with tempfile.TemporaryDirectory(prefix="reagent-package-validation-") as temporary:
            root = Path(temporary)
            bundle.extractall(root)
            return validate_package(root, pristine=pristine)


__all__ = ["PackageValidationError", "ValidationResult", "validate_archive", "validate_package"]
