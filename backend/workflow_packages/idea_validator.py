#!/usr/bin/env python3
"""Self-contained validator bundled in the reviewed Idea Discovery Capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
IDEA_STATUSES = {"candidate", "shortlisted", "selected", "rejected"}
ALLOWED_DYNAMIC = (
    "memory/progress/reports/",
    "memory/progress/receipts/",
)


class PackageValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
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
    result: list[dict[str, Any]] = []
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
    return canonical_hash(
        {
            "package_id": manifest["package_id"],
            "package_schema_version": manifest["package_schema_version"],
            "file_manifest_checksum": manifest["file_manifest_checksum"],
            "manifest_checksum": manifest["manifest_checksum"],
        }
    )


def _validate_selected_library(path: Path) -> set[str]:
    value = _object(path, "selected paper library")
    if set(value) != {"schema", "source_schemas", "source_checksums", "papers"}:
        raise PackageValidationError("selected paper library fields mismatch")
    if value["schema"] != "selected-paper-library/v1":
        raise PackageValidationError("selected paper library schema mismatch")
    if value["source_schemas"] != {
        "candidate_papers": "candidate-papers/v0.2",
        "selected_papers": "selected-papers/v0.2",
    }:
        raise PackageValidationError("selected paper library source schema mismatch")
    checksums = value["source_checksums"]
    if not isinstance(checksums, dict) or set(checksums) != {
        "candidate_papers_sha256",
        "selected_papers_sha256",
    } or not all(SHA256.fullmatch(str(item)) for item in checksums.values()):
        raise PackageValidationError("selected paper library source checksums are invalid")
    papers = value["papers"]
    if not isinstance(papers, list) or len(papers) > 15:
        raise PackageValidationError("selected paper library is outside reviewed bounds")
    ids: set[str] = set()
    for item in papers:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "paper", "selection"}:
            raise PackageValidationError("selected paper entry fields mismatch")
        candidate_id = item["candidate_id"]
        if (
            not isinstance(candidate_id, str)
            or not re.fullmatch(r"candidate-[0-9a-f]{16,64}", candidate_id)
            or candidate_id in ids
            or not isinstance(item["paper"], dict)
            or item["paper"].get("candidate_id") != candidate_id
            or not isinstance(item["selection"], dict)
            or item["selection"].get("candidate_id") != candidate_id
        ):
            raise PackageValidationError("selected paper identity mismatch")
        ids.add(candidate_id)
    return ids


def _validate_candidate_ideas(path: Path, source_ids: set[str]) -> None:
    value = _object(path, "candidate ideas")
    if set(value) != {"schema", "source_artifact", "ideas"}:
        raise PackageValidationError("candidate ideas fields mismatch")
    if value["schema"] != "candidate-ideas/v0.1":
        raise PackageValidationError("candidate ideas schema mismatch")
    source = value["source_artifact"]
    if (
        not isinstance(source, dict)
        or set(source) != {"artifact_id", "artifact_type", "sha256"}
        or not re.fullmatch(r"artifact-[0-9a-f]{32}", str(source.get("artifact_id", "")))
        or source.get("artifact_type") != "selected-paper-library/v1"
        or not SHA256.fullmatch(str(source.get("sha256", "")))
    ):
        raise PackageValidationError("candidate ideas source Artifact identity is invalid")
    ideas = value["ideas"]
    if not isinstance(ideas, list) or len(ideas) > 100:
        raise PackageValidationError("candidate ideas are outside reviewed bounds")
    required = {
        "idea_id", "title", "research_question", "motivation",
        "literature_basis", "observed_gap", "proposed_direction",
        "assumptions", "risks", "validation_needed", "status",
    }
    seen: set[str] = set()
    for item in ideas:
        if not isinstance(item, dict) or set(item) != required:
            raise PackageValidationError("candidate idea fields mismatch")
        idea_id = item["idea_id"]
        if not re.fullmatch(r"idea-[0-9]{3,}", str(idea_id)) or idea_id in seen:
            raise PackageValidationError("candidate idea identity is invalid")
        seen.add(idea_id)
        if item["status"] not in IDEA_STATUSES:
            raise PackageValidationError("candidate idea status is invalid")
        for field in (
            "title", "research_question", "motivation", "observed_gap",
            "proposed_direction",
        ):
            if not isinstance(item[field], str) or not item[field].strip():
                raise PackageValidationError(f"candidate idea {field} is required")
        basis = item["literature_basis"]
        if not isinstance(basis, list) or not basis or any(value not in source_ids for value in basis):
            raise PackageValidationError("candidate idea literature basis is invalid")
        for field in ("assumptions", "risks", "validation_needed"):
            if not isinstance(item[field], list) or not all(
                isinstance(value, str) and value.strip() for value in item[field]
            ):
                raise PackageValidationError(f"candidate idea {field} is invalid")


def validate(root: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    package_root = Path(root)
    if package_root.is_symlink() or not package_root.is_dir():
        raise PackageValidationError("package root must be a real directory")
    manifest = _object(package_root / "package-manifest.json", "package manifest")
    if (
        manifest.get("package_schema_version") != "workflow-package/v0.1"
        or manifest.get("workflow_id") != "idea-discovery-local-experimental"
        or manifest.get("workflow_version") != "0.1.0"
        or manifest.get("package_template_version") != "0.1.0"
    ):
        raise PackageValidationError("Idea Discovery package identity mismatch")
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
    output_paths = {
        item["required_output_path"] for item in manifest.get("output_contracts", [])
    }
    allowed_input = "inputs/selected-paper-library.json"
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
            if (
                entry is None
                and relative not in output_paths
                and relative != allowed_input
                and not relative.startswith(ALLOWED_DYNAMIC)
            ):
                raise PackageValidationError(f"undeclared file rejected: {relative}")
            if candidate.stat().st_nlink != 1:
                raise PackageValidationError("hard-linked package file rejected")
            if entry is not None:
                seen.add(relative)
                if pristine or not entry.get("mutable_by_harness"):
                    content = candidate.read_bytes()
                    if entry.get("sha256") != sha256_bytes(content) or entry.get("byte_size") != len(content):
                        raise PackageValidationError(f"file integrity mismatch: {relative}")
    required = {
        item["relative_path"] for item in files if item.get("requirement") == "REQUIRED"
    }
    if required - seen:
        raise PackageValidationError("required package files are missing")
    workflow = _object(package_root / "workflow/workflow.json", "workflow contract")
    if manifest.get("workflow_checksum") != canonical_hash(workflow):
        raise PackageValidationError("workflow checksum mismatch")
    input_path = package_root / allowed_input
    source_ids: set[str] = set()
    if input_path.exists():
        source_ids = _validate_selected_library(input_path)
    ideas_path = package_root / "outputs/candidate_ideas.json"
    report_path = package_root / "outputs/idea_discovery_report.md"
    if ideas_path.exists():
        if not source_ids:
            raise PackageValidationError("candidate ideas require materialized literature")
        _validate_candidate_ideas(ideas_path, source_ids)
    if report_path.exists():
        if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_nlink != 1:
            raise PackageValidationError("Idea Discovery report must be a regular file")
        text = report_path.read_text(encoding="utf-8").casefold()
        for heading in (
            "literature landscape", "observed patterns", "gaps", "candidate research",
            "user choices", "uncertainties", "next validation",
        ):
            if heading not in text:
                raise PackageValidationError(f"Idea Discovery report is missing {heading}")
        if "global novelty" not in text or "not proven" not in text:
            raise PackageValidationError("Idea Discovery report must retain the novelty boundary")
    return {
        "valid": True,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(files),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--pristine", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate(args.root, pristine=args.pristine)
    except PackageValidationError as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
