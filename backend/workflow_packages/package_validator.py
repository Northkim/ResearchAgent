#!/usr/bin/env python3
"""Self-contained standard-library validator copied into each package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE_SCHEMA = "workflow-package/v0.1"
EXPERIMENTAL_STATUS = "EXPERIMENTAL_V0_1"
PENDING_STATUS = "HARNESS_ACCEPTANCE_PENDING"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_PATTERNS = (
    re.compile(b"sk-" + rb"ant-[A-Za-z0-9_-]{8,}"),
    re.compile(b"sk-" + rb"proj-[A-Za-z0-9_-]{8,}"),
    re.compile(b"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:ANTHROPIC|OPENAI)" + rb"_API_KEY\s*=[^\s<]+"),
    re.compile(b"postgres" + rb"(?:ql)?://[^\s/:]+:[^\s/@]+@"),
    re.compile(b"/" + b"Users/"),
    re.compile(b"/" + b"Volumes/"),
    re.compile(rb"[A-Za-z]:\\\\"),
    re.compile(b'"raw_provider_' + rb'response"\s*:'),
    re.compile(b'"raw_response_' + rb'body"\s*:'),
)


class PackageValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PackageValidationError("unsafe or empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise PackageValidationError(f"unsafe relative path: {value}")
    if re.match(r"^[A-Za-z]:", value):
        raise PackageValidationError(f"absolute Windows path rejected: {value}")
    if any(part == ".env" or part.startswith(".env.") for part in value.split("/")):
        raise PackageValidationError("environment files are forbidden")
    if value.lower().endswith((".sqlite", ".sqlite3", ".db", ".pem", ".key")):
        raise PackageValidationError(f"sensitive/runtime file rejected: {value}")
    return value


def _normalized_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        item = dict(entry)
        if item.get("mutable_by_harness"):
            item["sha256"] = None
            item["byte_size"] = None
        normalized.append(item)
    return normalized


def _manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload["manifest_checksum"] = None
    payload["package_checksum"] = None
    payload["files"] = _normalized_entries(payload["files"])
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


def _reject_sensitive(content: bytes, relative_path: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise PackageValidationError(f"sensitive or machine-specific content: {relative_path}")


def validate(root: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    package_root = Path(root)
    if package_root.is_symlink() or not package_root.is_dir():
        raise PackageValidationError("package root must be a real directory")
    manifest_path = package_root / "package-manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        _reject_sensitive(manifest_bytes, "package-manifest.json")
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageValidationError("package manifest is missing or invalid") from exc
    if not isinstance(manifest, dict):
        raise PackageValidationError("package manifest must be an object")
    if manifest.get("package_schema_version") != PACKAGE_SCHEMA:
        raise PackageValidationError("unsupported package schema")
    if manifest.get("experimental_status_declaration") != EXPERIMENTAL_STATUS:
        raise PackageValidationError("experimental status declaration missing")
    if manifest.get("harness_acceptance_status") != PENDING_STATUS:
        raise PackageValidationError("R1A Harness acceptance status must remain pending")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise PackageValidationError("manifest files must be a non-empty array")
    paths = [safe_relative_path(entry.get("relative_path")) for entry in entries if isinstance(entry, dict)]
    if len(paths) != len(entries) or len(paths) != len(set(paths)):
        raise PackageValidationError("manifest contains duplicate or invalid file entries")
    if manifest.get("file_manifest_checksum") != canonical_hash(_normalized_entries(entries)):
        raise PackageValidationError("file manifest checksum mismatch")
    if manifest.get("manifest_checksum") != _manifest_hash(manifest):
        raise PackageValidationError("manifest checksum mismatch")
    if manifest.get("package_checksum") != _package_hash(manifest):
        raise PackageValidationError("package checksum mismatch")

    required = {entry["relative_path"]: entry for entry in entries if entry.get("requirement") == "REQUIRED"}
    output_paths = {item["required_output_path"] for item in manifest.get("output_contracts", [])}
    allowed_dynamic_prefix = "memory/progress/reports/"
    seen: set[str] = set()
    for base, directories, files in os.walk(package_root, followlinks=False):
        base_path = Path(base)
        for name in (*directories, *files):
            candidate = base_path / name
            if candidate.is_symlink():
                raise PackageValidationError(f"symbolic link rejected: {candidate.name}")
        for name in files:
            candidate = base_path / name
            relative = candidate.relative_to(package_root).as_posix()
            safe_relative_path(relative)
            content = candidate.read_bytes()
            _reject_sensitive(content, relative)
            if relative == "package-manifest.json":
                continue
            entry = next((item for item in entries if item["relative_path"] == relative), None)
            if entry is None and relative not in output_paths and not relative.startswith(allowed_dynamic_prefix):
                raise PackageValidationError(f"undeclared file rejected: {relative}")
            if entry is not None:
                seen.add(relative)
                if not entry.get("mutable_by_harness") or pristine:
                    if entry.get("sha256") != sha256_bytes(content) or entry.get("byte_size") != len(content):
                        raise PackageValidationError(f"file integrity mismatch: {relative}")

    missing = sorted(set(required) - seen)
    if missing:
        raise PackageValidationError("required files missing: " + ", ".join(missing))
    _validate_semantics(manifest, package_root)
    return {
        "valid": True,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(entries),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }


def _validate_semantics(manifest: dict[str, Any], package_root: Path) -> None:
    entries = {entry["relative_path"]: entry for entry in manifest["files"]}
    for required_path in ("AGENT.md", "AGENTS.md", "CLAUDE.md", "workflow/workflow.json", "memory/context.md"):
        if required_path not in entries:
            raise PackageValidationError(f"required semantic path missing: {required_path}")
    for entry in entries.values():
        path = entry["relative_path"]
        if path.startswith("inputs/") and (entry.get("mutable_by_harness") or entry.get("state_classification") != "INPUT"):
            raise PackageValidationError("inputs must be immutable and classified INPUT")
    context = entries["memory/context.md"]
    if not context.get("mutable_by_harness") or context.get("state_classification") != "STATE":
        raise PackageValidationError("local context must be mutable Harness state")
    if not manifest.get("skill_pins") or not manifest.get("prompt_pins"):
        raise PackageValidationError("pinned Skill and prompt identities are required")
    if not SHA256.fullmatch(str(manifest.get("workflow_checksum", ""))):
        raise PackageValidationError("workflow checksum pin is invalid")
    workflow = json.loads((package_root / "workflow/workflow.json").read_text(encoding="utf-8"))
    if manifest["workflow_checksum"] != canonical_hash(workflow):
        raise PackageValidationError("pinned Workflow checksum does not match workflow file")
    for pin in manifest["prompt_pins"]:
        prompt_path = safe_relative_path(pin["relative_path"])
        if pin.get("checksum") != sha256_bytes((package_root / prompt_path).read_bytes()):
            raise PackageValidationError("pinned prompt checksum does not match prompt file")
    for pin in manifest["skill_pins"]:
        skill_path = safe_relative_path(pin["relative_path"])
        contract_path = str(PurePosixPath(skill_path).parent / "skill.json")
        skill_checksum = canonical_hash(
            {
                "instructions": sha256_bytes((package_root / skill_path).read_bytes()),
                "contract": sha256_bytes((package_root / contract_path).read_bytes()),
            }
        )
        if pin.get("checksum") != skill_checksum:
            raise PackageValidationError("pinned Skill checksum does not match Skill files")
    for item in manifest.get("input_manifest", []):
        input_path = safe_relative_path(item["relative_path"])
        entry = entries.get(input_path)
        if entry is None or entry.get("mutable_by_harness") or item.get("read_only_required") is not True:
            raise PackageValidationError("input manifest must bind an immutable declared input")
        if item.get("checksum") != sha256_bytes((package_root / input_path).read_bytes()):
            raise PackageValidationError("input manifest checksum does not match input file")
    for output in manifest.get("output_contracts", []):
        if not safe_relative_path(output["required_output_path"]).startswith("outputs/"):
            raise PackageValidationError("output contract escapes outputs/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an experimental ReAgent Workflow Package")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--pristine", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate(args.root, pristine=args.pristine)
    except PackageValidationError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
