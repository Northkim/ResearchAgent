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
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE_SCHEMA = "workflow-package/v0.1"
EXPERIMENTAL_STATUS = "EXPERIMENTAL_V0_1"
PENDING_STATUS = "HARNESS_ACCEPTANCE_PENDING"
PROVEN_STATUS = "CODEX_LOCAL_FOLDER_BOUNDARY_PROVEN_CLAUDE_UNTESTED"
UPLOAD_PENDING_STATUS = "UPLOAD_ACCEPTANCE_PENDING"
UPLOAD_AUTOMATIC_STATUS = "AUTOMATIC_UPLOAD_SUPPORTED"
PROGRESS_V1 = "progress-report/v0.1"
PROGRESS_V2 = "progress-report/v0.2"
V2_EXPERIMENTAL = "EXPERIMENTAL_PROGRESS_REPORT_V0_2"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
REPORT_ID_V2 = re.compile(r"^prv2-[0-9a-f]{64}$")
PORTABLE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{1,255}$")
V2_FIELDS = {
    "schema_version", "report_id", "report_content_checksum", "report_checksum",
    "package_id", "package_schema_version", "package_checksum", "project_id",
    "workflow_id", "workflow_version", "workflow_checksum", "execution_round",
    "harness_type", "harness_version", "harness_session_id", "previous_report_id",
    "previous_report_checksum", "started_at", "completed_at", "status",
    "completed_work", "current_state", "next_recommended_action",
    "continuation_reason", "output_artifacts", "context_before_checksum",
    "context_after_checksum", "warnings", "errors", "unresolved_questions",
    "continuation_instructions", "skill_pins", "template_pins", "generated_at",
    "experimental_declaration",
}
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
    if manifest.get("harness_acceptance_status") not in {PENDING_STATUS, PROVEN_STATUS}:
        raise PackageValidationError("unknown Harness acceptance status")
    progress_schema = manifest.get("progress_report_schema_version", PROGRESS_V1)
    if progress_schema not in {PROGRESS_V1, PROGRESS_V2}:
        raise PackageValidationError("unsupported Progress Report schema declaration")
    if progress_schema == PROGRESS_V2:
        if manifest.get("harness_acceptance_status") != PROVEN_STATUS:
            raise PackageValidationError("v0.2 package must retain the R1B Harness status")
        if manifest.get("progress_upload_status") not in {
            UPLOAD_PENDING_STATUS,
            UPLOAD_AUTOMATIC_STATUS,
        }:
            raise PackageValidationError("Progress upload status is not recognized")

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
    allowed_dynamic_prefixes = (
        "memory/progress/reports/",
        "memory/progress/receipts/",
        "memory/search/operations/",
    )
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
            if candidate.name == ".DS_Store":
                if len(content) > 1024 * 1024:
                    raise PackageValidationError("macOS metadata file exceeds the safe bound")
                continue
            if relative == "package-manifest.json":
                continue
            entry = next((item for item in entries if item["relative_path"] == relative), None)
            if entry is None and relative not in output_paths and not relative.startswith(allowed_dynamic_prefixes):
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
    _validate_progress_reports(manifest, package_root)
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
    _validate_local_context(manifest, package_root)
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
    _validate_literature_outputs(package_root)


def _validate_local_context(manifest: dict[str, Any], package_root: Path) -> None:
    content = (package_root / "memory/context.md").read_text(encoding="utf-8")
    marker = "```json\n"
    if marker not in content or "\n```" not in content:
        raise PackageValidationError("local context must contain one JSON state block")
    try:
        payload = json.loads(content.split(marker, 1)[1].split("\n```", 1)[0])
    except json.JSONDecodeError as error:
        raise PackageValidationError("local context state must be valid JSON") from error
    required = {
        "schema_version", "package_id", "package_checksum", "workflow_id",
        "workflow_version", "current_workflow_state", "completed_outputs",
        "relevant_decisions", "unresolved_issues", "next_action",
        "latest_progress_report", "previous_session_history_pointer",
        "updated_at", "context_checksum",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise PackageValidationError("local context fields mismatch")
    if (
        payload["schema_version"] != "local-context/v0.1"
        or payload["package_id"] != manifest["package_id"]
        or payload["package_checksum"] != manifest["package_checksum"]
        or payload["workflow_id"] != manifest["workflow_id"]
        or payload["workflow_version"] != manifest["workflow_version"]
        or not isinstance(payload["current_workflow_state"], str)
        or not payload["current_workflow_state"].strip()
        or not isinstance(payload["next_action"], str)
        or not payload["next_action"].strip()
        or any(
            not isinstance(payload[field], list)
            or not all(isinstance(item, str) for item in payload[field])
            for field in ("completed_outputs", "relevant_decisions", "unresolved_issues")
        )
        or not all(
            isinstance(item, str) and item.startswith("outputs/")
            for item in payload["completed_outputs"]
        )
        or payload["context_checksum"]
        != canonical_hash({**payload, "context_checksum": None})
    ):
        raise PackageValidationError("local context identity or checksum is invalid")


def _read_json_if_present(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise PackageValidationError(f"{label} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageValidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label} must be a JSON object")
    return value


def _validate_literature_outputs(package_root: Path) -> None:
    search_plan_path = package_root / "outputs/search_plan.md"
    candidates = _read_json_if_present(
        package_root / "outputs/candidate_papers.json",
        "candidate library",
    )
    selected = _read_json_if_present(
        package_root / "outputs/selected_papers.json",
        "selected-paper library",
    )
    report_path = package_root / "outputs/literature_search_report.md"
    present = (
        search_plan_path.exists(),
        candidates is not None,
        selected is not None,
        report_path.exists(),
    )
    if not any(present):
        return
    if not all(present):
        # The one-command controller may persist the planning artifact before
        # transport. That partial state is recoverable only by owner review.
        if present == (True, False, False, False):
            return
        raise PackageValidationError("Literature Search outputs are incomplete")
    if search_plan_path.is_symlink() or report_path.is_symlink():
        raise PackageValidationError("Literature Search Markdown must be regular files")
    search_plan = search_plan_path.read_text(encoding="utf-8")
    for heading in (
        "Interpreted topic",
        "Concepts and synonyms",
        "Query variants",
        "Search bounds",
        "Screening rules",
        "Evidence limitations",
    ):
        if heading.casefold() not in search_plan.casefold():
            raise PackageValidationError(f"search plan is missing {heading}")

    assert candidates is not None and selected is not None
    if set(candidates) != {"schema_version", "mode", "candidates"}:
        raise PackageValidationError("candidate library fields mismatch")
    if candidates["schema_version"] != "candidate-papers/v0.2" or candidates["mode"] not in {"NORMAL", "DEMO"}:
        raise PackageValidationError("candidate library version or mode is invalid")
    records = candidates["candidates"]
    if not isinstance(records, list) or len(records) > 15:
        raise PackageValidationError("candidate library exceeds the retained bound")
    required_candidate = {
        "candidate_id", "provider_id", "openalex_id", "title", "authors",
        "publication_year", "doi", "source", "language", "abstract",
        "source_query_ids", "provenance_checksum", "deduplication_status",
    }
    candidate_ids: list[str] = []
    provider_ids: set[str] = set()
    openalex_ids: set[str] = set()
    dois: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != required_candidate:
            raise PackageValidationError("candidate entry fields mismatch")
        candidate_id = record["candidate_id"]
        if not isinstance(candidate_id, str) or not re.fullmatch(r"candidate-[0-9a-f]{16,64}", candidate_id):
            raise PackageValidationError("candidate identity is invalid")
        if candidate_id in candidate_ids:
            raise PackageValidationError("candidate identity is duplicated")
        candidate_ids.append(candidate_id)
        provider_id = record["provider_id"]
        if not isinstance(provider_id, str) or not provider_id.strip() or provider_id in provider_ids:
            raise PackageValidationError("provider identity is missing or duplicated")
        provider_ids.add(provider_id)
        openalex_id = record["openalex_id"]
        if candidates["mode"] == "NORMAL":
            if not isinstance(openalex_id, str) or not openalex_id.strip():
                raise PackageValidationError("normal candidate requires an OpenAlex identity")
        elif openalex_id is not None:
            raise PackageValidationError("demo candidate must not claim an OpenAlex identity")
        if isinstance(openalex_id, str):
            if openalex_id in openalex_ids:
                raise PackageValidationError("OpenAlex identity was not deduplicated")
            openalex_ids.add(openalex_id)
        doi = record["doi"]
        if isinstance(doi, str):
            normalized_doi = doi.casefold()
            if normalized_doi in dois:
                raise PackageValidationError("DOI was not deduplicated")
            dois.add(normalized_doi)
        if (
            not isinstance(record["title"], str)
            or not record["title"].strip()
            or not isinstance(record["authors"], list)
            or not all(isinstance(author, str) and author.strip() for author in record["authors"])
            or (
                record["publication_year"] is not None
                and (
                    isinstance(record["publication_year"], bool)
                    or not isinstance(record["publication_year"], int)
                )
            )
            or any(
                record[field] is not None and not isinstance(record[field], str)
                for field in ("doi", "source", "language", "abstract")
            )
            or not isinstance(record["source_query_ids"], list)
            or not record["source_query_ids"]
            or not all(re.fullmatch(r"query-[1-3]", str(item)) for item in record["source_query_ids"])
            or not SHA256.fullmatch(str(record["provenance_checksum"]))
            or record["deduplication_status"] not in {"UNIQUE", "MERGED"}
        ):
            raise PackageValidationError("candidate evidence fields are invalid")

    if set(selected) != {
        "schema_version", "mode", "selection_status", "selected",
        "exclusions", "exclusion_summary",
    }:
        raise PackageValidationError("selected-paper library fields mismatch")
    if (
        selected["schema_version"] != "selected-papers/v0.2"
        or selected["mode"] != candidates["mode"]
        or selected["selection_status"] not in {"SUFFICIENT", "INSUFFICIENT"}
        or not isinstance(selected["selected"], list)
        or not isinstance(selected["exclusions"], list)
        or not isinstance(selected["exclusion_summary"], str)
    ):
        raise PackageValidationError("selected-paper library is invalid")
    if len(selected["selected"]) > 6:
        raise PackageValidationError("selected-paper target maximum exceeded")
    if selected["selection_status"] == "SUFFICIENT" and len(selected["selected"]) < 3:
        raise PackageValidationError("sufficient selection must contain at least three papers")
    selected_ids: set[str] = set()
    for item in selected["selected"]:
        if not isinstance(item, dict) or set(item) != {
            "candidate_id", "relevance_decision", "inclusion_reason",
            "evidence_availability",
        }:
            raise PackageValidationError("selected-paper entry fields mismatch")
        if (
            item["candidate_id"] not in candidate_ids
            or item["candidate_id"] in selected_ids
            or item["relevance_decision"] != "INCLUDE"
            or not isinstance(item["inclusion_reason"], str)
            or not item["inclusion_reason"].strip()
            or item["evidence_availability"] not in {"METADATA_ONLY", "METADATA_AND_ABSTRACT"}
        ):
            raise PackageValidationError("selected-paper decision is invalid")
        selected_ids.add(item["candidate_id"])
    excluded_ids: set[str] = set()
    for item in selected["exclusions"]:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "reason"}:
            raise PackageValidationError("exclusion entry fields mismatch")
        if (
            item["candidate_id"] not in candidate_ids
            or item["candidate_id"] in selected_ids
            or item["candidate_id"] in excluded_ids
            or not isinstance(item["reason"], str)
            or not item["reason"].strip()
        ):
            raise PackageValidationError("exclusion decision is invalid")
        excluded_ids.add(item["candidate_id"])
    if selected_ids | excluded_ids != set(candidate_ids):
        raise PackageValidationError("every candidate requires one screening disposition")

    report = report_path.read_text(encoding="utf-8")
    for heading in (
        "Executive summary", "Search coverage", "Main research themes",
        "Common methods", "Representative works", "Trends", "Limitations",
        "Potential research gaps", "Recommended next research action",
        "Selected-paper references",
    ):
        if heading.casefold() not in report.casefold():
            raise PackageValidationError(f"literature report is missing {heading}")
    folded_report = report.casefold()
    if not all(term in folded_report for term in ("metadata", "abstract", "full text")):
        raise PackageValidationError("literature report must disclose metadata/abstract-only evidence")
    if candidates["mode"] == "DEMO" and "fictional demo evidence" not in folded_report:
        raise PackageValidationError("demo report is missing the fictional evidence label")


def _progress_v2_identity(report: dict[str, Any]) -> dict[str, str]:
    content = {
        key: value
        for key, value in report.items()
        if key not in {"report_id", "report_content_checksum", "report_checksum"}
    }
    content_checksum = canonical_hash(content)
    report_id = "prv2-" + canonical_hash(
        {
            "package_id": report["package_id"],
            "workflow_id": report["workflow_id"],
            "workflow_version": report["workflow_version"],
            "execution_round": report["execution_round"],
            "previous_report_id": report["previous_report_id"],
            "report_content_checksum": content_checksum,
        }
    ).split(":", 1)[1]
    complete = {**report, "report_checksum": None}
    return {
        "report_content_checksum": content_checksum,
        "report_id": report_id,
        "report_checksum": canonical_hash(complete),
    }


def _validate_v1_report(
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    checksum = report.get("report_checksum")
    if not SHA256.fullmatch(str(checksum or "")):
        raise PackageValidationError("legacy Progress Report checksum is invalid")
    if checksum != canonical_hash({**report, "report_checksum": None}):
        raise PackageValidationError("legacy Progress Report checksum mismatch")
    if (
        report.get("package_id") != manifest["package_id"]
        or report.get("package_checksum") != manifest["package_checksum"]
    ):
        raise PackageValidationError("legacy Progress Report package identity mismatch")


def _validate_v2_report(
    report: dict[str, Any],
    manifest: dict[str, Any],
    package_root: Path,
) -> None:
    if set(report) != V2_FIELDS:
        raise PackageValidationError("v0.2 Progress Report fields mismatch")
    if not isinstance(report.get("execution_round"), int) or report["execution_round"] < 1:
        raise PackageValidationError("v0.2 execution round must be positive")
    if report.get("status") not in {"IN_PROGRESS", "COMPLETED", "BLOCKED", "FAILED", "CANCELLED"}:
        raise PackageValidationError("v0.2 Progress Report status is invalid")
    if report.get("experimental_declaration") != V2_EXPERIMENTAL:
        raise PackageValidationError("v0.2 experimental declaration is missing")
    for field in ("harness_type", "harness_session_id"):
        if not PORTABLE_IDENTIFIER.fullmatch(str(report.get(field, ""))):
            raise PackageValidationError(f"v0.2 {field} is invalid")
    for field in (
        "completed_work", "warnings", "errors", "unresolved_questions",
        "continuation_instructions",
    ):
        value = report.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise PackageValidationError(f"v0.2 {field} must be an array of strings")
    for field in ("current_state", "next_recommended_action"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            raise PackageValidationError(f"v0.2 {field} must be non-empty")
    if not REPORT_ID_V2.fullmatch(str(report.get("report_id", ""))):
        raise PackageValidationError("v0.2 report ID is invalid")
    for field in (
        "report_content_checksum", "report_checksum", "package_checksum",
        "workflow_checksum", "context_before_checksum", "context_after_checksum",
    ):
        if not SHA256.fullmatch(str(report.get(field, ""))):
            raise PackageValidationError(f"v0.2 {field} is invalid")
    if (report["previous_report_id"] is None) != (report["previous_report_checksum"] is None):
        raise PackageValidationError("v0.2 predecessor ID/checksum must be paired")
    if report["previous_report_id"] is not None and (
        not REPORT_ID_V2.fullmatch(report["previous_report_id"])
        or not SHA256.fullmatch(report["previous_report_checksum"])
    ):
        raise PackageValidationError("v0.2 predecessor identity is invalid")
    try:
        started = datetime.fromisoformat(report["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(report["completed_at"].replace("Z", "+00:00"))
        generated = datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise PackageValidationError("v0.2 timestamps must be ISO-8601") from error
    if any(value.tzinfo is None for value in (started, completed, generated)) or completed < started:
        raise PackageValidationError("v0.2 timestamps require timezones and monotonic order")
    expected = _progress_v2_identity(report)
    if any(report[field] != value for field, value in expected.items()):
        raise PackageValidationError("v0.2 Progress Report identity mismatch")
    if (
        report["package_id"] != manifest["package_id"]
        or report["package_schema_version"] != manifest["package_schema_version"]
        or report["package_checksum"] != manifest["package_checksum"]
        or report["project_id"] != manifest["experimental_project_identity"]
        or report["workflow_id"] != manifest["workflow_id"]
        or report["workflow_version"] != manifest["workflow_version"]
        or report["workflow_checksum"] != manifest["workflow_checksum"]
    ):
        raise PackageValidationError("v0.2 Progress Report package/workflow identity mismatch")
    if not isinstance(report["output_artifacts"], list):
        raise PackageValidationError("v0.2 output artifacts must be an array")
    for output in report["output_artifacts"]:
        if not isinstance(output, dict) or set(output) != {
            "relative_path", "artifact_kind", "media_type", "checksum", "size"
        }:
            raise PackageValidationError("v0.2 output artifact must be an object")
        relative = safe_relative_path(output.get("relative_path"))
        if not relative.startswith("outputs/"):
            raise PackageValidationError("v0.2 output escapes outputs/")
        path = package_root.joinpath(*relative.split("/"))
        if path.is_symlink() or not path.is_file():
            raise PackageValidationError(f"v0.2 output is missing: {relative}")
        content = path.read_bytes()
        if output.get("checksum") != sha256_bytes(content) or output.get("size") != len(content):
            raise PackageValidationError(f"v0.2 output integrity mismatch: {relative}")
    for field in ("skill_pins", "template_pins"):
        pins = report.get(field)
        if not isinstance(pins, list) or not pins:
            raise PackageValidationError(f"v0.2 {field} must be non-empty")
        if any(
            not isinstance(pin, dict)
            or set(pin) != {"pin_type", "identity", "version", "checksum"}
            or pin.get("pin_type") not in {"SKILL", "TEMPLATE"}
            or not SHA256.fullmatch(str(pin.get("checksum", "")))
            for pin in pins
        ):
            raise PackageValidationError(f"v0.2 {field} checksum is invalid")


def _validate_progress_reports(manifest: dict[str, Any], package_root: Path) -> None:
    declared_schema = manifest.get("progress_report_schema_version", PROGRESS_V1)
    reports: list[dict[str, Any]] = []
    reports_root = package_root / "memory/progress/reports"
    for path in sorted(reports_root.glob("*.json")):
        if path.is_symlink():
            raise PackageValidationError("Progress Report symbolic link rejected")
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageValidationError("Progress Report must be UTF-8 JSON") from error
        if not isinstance(report, dict):
            raise PackageValidationError("Progress Report must be a JSON object")
        schema = report.get("schema_version")
        if schema == PROGRESS_V1 and declared_schema == PROGRESS_V1:
            _validate_v1_report(report, manifest)
        elif schema == PROGRESS_V2 and declared_schema == PROGRESS_V2:
            _validate_v2_report(report, manifest, package_root)
        else:
            raise PackageValidationError("Progress Report schema does not match package declaration")
        if path.name != f"{report.get('report_id')}.json":
            raise PackageValidationError("Progress Report filename does not match report ID")
        reports.append(report)
    if declared_schema != PROGRESS_V2:
        return
    if not reports:
        _validate_progress_receipts(reports, package_root)
        return
    reports.sort(key=lambda item: (item["execution_round"], item["report_id"]))
    if len({item["execution_round"] for item in reports}) != len(reports):
        raise PackageValidationError("Progress Report history contains a branched round")
    if reports[0]["execution_round"] != 1 or reports[0]["previous_report_id"] is not None:
        raise PackageValidationError("Progress Report chain must begin at round 1")
    for previous, current in zip(reports, reports[1:]):
        if current["execution_round"] != previous["execution_round"] + 1:
            raise PackageValidationError("Progress Report chain has a missing round")
        if (
            current["previous_report_id"] != previous["report_id"]
            or current["previous_report_checksum"] != previous["report_checksum"]
        ):
            raise PackageValidationError("Progress Report predecessor does not resolve")
        if current["context_before_checksum"] != previous["context_after_checksum"]:
            raise PackageValidationError("Progress Report context continuity mismatch")
        if previous["status"] == "COMPLETED" and not (current["continuation_reason"] or "").strip():
            raise PackageValidationError("completed round continuation requires a reason")
    context_checksum = sha256_bytes((package_root / "memory/context.md").read_bytes())
    if reports[-1]["context_after_checksum"] != context_checksum:
        raise PackageValidationError("latest report context-after does not match local context")
    _validate_progress_receipts(reports, package_root)


def _validate_progress_receipts(
    reports: list[dict[str, Any]],
    package_root: Path,
) -> None:
    receipts_root = package_root / "memory/progress/receipts"
    receipt_paths = sorted(receipts_root.glob("*.json"))
    if len(receipt_paths) > 1:
        raise PackageValidationError("V0.1 permits only one local upload receipt")
    if not receipt_paths:
        return
    if len(reports) != 1:
        raise PackageValidationError("upload receipt requires exactly one Progress Report")
    receipt = _read_json_if_present(receipt_paths[0], "local upload receipt")
    assert receipt is not None
    required = {
        "schema_version", "report_id", "report_checksum", "receipt_id",
        "receipt_checksum", "validation_status", "chain_state",
        "accepted_for_projection", "idempotent_replay", "projection_checksum",
        "verified_at",
    }
    if set(receipt) != required:
        raise PackageValidationError("local upload receipt fields mismatch")
    report = reports[0]
    if (
        receipt["schema_version"] != "local-progress-upload-receipt/v0.1"
        or receipt["report_id"] != report["report_id"]
        or receipt["report_checksum"] != report["report_checksum"]
        or receipt["validation_status"] != "ACCEPTED"
        or receipt["accepted_for_projection"] is not True
        or not isinstance(receipt["idempotent_replay"], bool)
        or not isinstance(receipt["receipt_id"], str)
        or not receipt["receipt_id"].strip()
        or not SHA256.fullmatch(str(receipt["receipt_checksum"]))
        or not SHA256.fullmatch(str(receipt["projection_checksum"]))
    ):
        raise PackageValidationError("local upload receipt does not verify the report")
    try:
        verified = datetime.fromisoformat(
            receipt["verified_at"].replace("Z", "+00:00")
        )
    except (AttributeError, ValueError) as error:
        raise PackageValidationError("local upload receipt timestamp is invalid") from error
    if verified.tzinfo is None:
        raise PackageValidationError("local upload receipt timestamp requires a timezone")


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
