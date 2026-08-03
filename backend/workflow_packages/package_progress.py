#!/usr/bin/env python3
"""Self-contained Progress Report v0.2 helper copied into future packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "progress-report/v0.2"
EXPERIMENTAL_DECLARATION = "EXPERIMENTAL_PROGRESS_REPORT_V0_2"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
REPORT_ID = re.compile(r"^prv2-[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{1,255}$")
STATUSES = {"IN_PROGRESS", "COMPLETED", "BLOCKED", "FAILED", "CANCELLED"}
DRAFT_FIELDS = {
    "execution_round",
    "harness_type",
    "harness_version",
    "harness_session_id",
    "previous_report_id",
    "previous_report_checksum",
    "started_at",
    "completed_at",
    "status",
    "completed_work",
    "current_state",
    "next_recommended_action",
    "continuation_reason",
    "warnings",
    "errors",
    "unresolved_questions",
    "continuation_instructions",
}


class ProgressReportError(ValueError):
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


def safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ProgressReportError("path must be a clean relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ProgressReportError("path must be a clean relative POSIX path")
    return value


def compute_identity(report: dict[str, Any]) -> dict[str, Any]:
    content = {
        key: value
        for key, value in report.items()
        if key not in {"report_id", "report_content_checksum", "report_checksum"}
    }
    content_checksum = canonical_hash(content)
    report_id_digest = canonical_hash(
        {
            "package_id": report["package_id"],
            "workflow_id": report["workflow_id"],
            "workflow_version": report["workflow_version"],
            "execution_round": report["execution_round"],
            "previous_report_id": report["previous_report_id"],
            "report_content_checksum": content_checksum,
        }
    ).split(":", 1)[1]
    identified = {
        **report,
        "report_id": f"prv2-{report_id_digest}",
        "report_content_checksum": content_checksum,
        "report_checksum": None,
    }
    return {
        **identified,
        "report_checksum": canonical_hash(identified),
    }


def verify_identity(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ProgressReportError("unsupported Progress Report schema")
    if not REPORT_ID.fullmatch(str(report.get("report_id", ""))):
        raise ProgressReportError("invalid deterministic report ID")
    expected = compute_identity(report)
    for field in ("report_content_checksum", "report_id", "report_checksum"):
        if report.get(field) != expected[field]:
            raise ProgressReportError(f"Progress Report {field} mismatch")


def _load_object(path: Path, name: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProgressReportError(f"{name} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProgressReportError(f"{name} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ProgressReportError(f"{name} must be a JSON object")
    return value


def _root(value: str | Path) -> Path:
    supplied = Path(value)
    if supplied.is_symlink():
        raise ProgressReportError("package root must not be a symbolic link")
    root = supplied.resolve()
    if not root.is_dir():
        raise ProgressReportError("package root must be a directory")
    return root


def snapshot(package_root: str | Path) -> dict[str, Any]:
    root = _root(package_root)
    context = root / "memory/context.md"
    if context.is_symlink() or not context.is_file():
        raise ProgressReportError("local context must be a regular file")
    return {
        "schema_version": SCHEMA_VERSION,
        "context_before_checksum": sha256_bytes(context.read_bytes()),
        "instruction": "Retain this checksum and pass it to finalize after the round.",
    }


def _existing_reports(root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    reports_root = root / "memory/progress/reports"
    for path in sorted(reports_root.glob("*.json")):
        report = _load_object(path, "existing Progress Report")
        verify_identity(report)
        if path.name != f"{report['report_id']}.json":
            raise ProgressReportError("existing report filename does not match report ID")
        reports.append(report)
    return reports


def _validate_draft(draft: dict[str, Any]) -> None:
    if set(draft) != DRAFT_FIELDS:
        missing = sorted(DRAFT_FIELDS - set(draft))
        unknown = sorted(set(draft) - DRAFT_FIELDS)
        raise ProgressReportError(f"draft fields mismatch; missing={missing}; unknown={unknown}")
    if not isinstance(draft["execution_round"], int) or draft["execution_round"] < 1:
        raise ProgressReportError("execution_round must be positive")
    if draft["status"] not in STATUSES:
        raise ProgressReportError("invalid status")
    for field in (
        "completed_work",
        "warnings",
        "errors",
        "unresolved_questions",
        "continuation_instructions",
    ):
        if not isinstance(draft[field], list) or not all(
            isinstance(item, str) for item in draft[field]
        ):
            raise ProgressReportError(f"{field} must be an array of strings")
    for field in (
        "harness_type",
        "harness_session_id",
        "started_at",
        "completed_at",
        "current_state",
        "next_recommended_action",
    ):
        if not isinstance(draft[field], str) or not draft[field].strip():
            raise ProgressReportError(f"{field} must be a non-empty string")
    for field in ("harness_type", "harness_session_id"):
        if not IDENTIFIER.fullmatch(draft[field]):
            raise ProgressReportError(f"{field} must be a portable identifier")
    for field in (
        "harness_version",
        "previous_report_id",
        "previous_report_checksum",
        "continuation_reason",
    ):
        if draft[field] is not None and not isinstance(draft[field], str):
            raise ProgressReportError(f"{field} must be a string or null")
    if (draft["previous_report_id"] is None) != (
        draft["previous_report_checksum"] is None
    ):
        raise ProgressReportError("previous report ID and checksum must be paired")
    if draft["previous_report_id"] is not None:
        if not REPORT_ID.fullmatch(draft["previous_report_id"]):
            raise ProgressReportError("previous report ID is invalid")
        if not SHA256.fullmatch(draft["previous_report_checksum"]):
            raise ProgressReportError("previous report checksum is invalid")
    try:
        started = datetime.fromisoformat(draft["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(draft["completed_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ProgressReportError("round timestamps must be ISO-8601") from error
    if started.tzinfo is None or completed.tzinfo is None or completed < started:
        raise ProgressReportError("round timestamps require timezones and monotonic order")


def finalize(
    *,
    package_root: str | Path,
    draft_path: str,
    context_before_checksum: str,
) -> dict[str, Any]:
    root = _root(package_root)
    if not SHA256.fullmatch(context_before_checksum):
        raise ProgressReportError("context-before must be a sha256 checksum")
    relative_draft = safe_relative_path(draft_path)
    draft = _load_object(root.joinpath(*relative_draft.split("/")), "report draft")
    _validate_draft(draft)
    manifest = _load_object(root / "package-manifest.json", "package manifest")
    context = root / "memory/context.md"
    context_after_checksum = sha256_bytes(context.read_bytes())
    existing = _existing_reports(root)
    previous = max(existing, key=lambda item: item["execution_round"]) if existing else None
    if previous is None:
        if draft["execution_round"] != 1 or draft["previous_report_id"] is not None:
            raise ProgressReportError("round 1 must not name a predecessor")
    else:
        if draft["execution_round"] != previous["execution_round"] + 1:
            raise ProgressReportError("execution round must increment the latest round")
        if draft["previous_report_id"] != previous["report_id"]:
            raise ProgressReportError("draft does not name the latest report ID")
        if draft["previous_report_checksum"] != previous["report_checksum"]:
            raise ProgressReportError("draft does not name the latest report checksum")
        if previous["context_after_checksum"] != context_before_checksum:
            raise ProgressReportError("context-before does not continue the latest report")
        if previous["status"] == "COMPLETED" and not (
            draft["continuation_reason"] or ""
        ).strip():
            raise ProgressReportError("continuing a completed round requires a reason")
    outputs: list[dict[str, Any]] = []
    for contract in manifest.get("output_contracts", []):
        relative = safe_relative_path(contract["required_output_path"])
        path = root.joinpath(*relative.split("/"))
        if path.is_symlink() or not path.is_file():
            raise ProgressReportError(f"declared output is missing: {relative}")
        content = path.read_bytes()
        outputs.append(
            {
                "relative_path": relative,
                "artifact_kind": contract["artifact_kind"],
                "media_type": contract["media_type"],
                "checksum": sha256_bytes(content),
                "size": len(content),
            }
        )
    skill_pins = [
        {
            "pin_type": "SKILL",
            "identity": pin["name"],
            "version": pin["semantic_version"],
            "checksum": pin["checksum"],
        }
        for pin in manifest["skill_pins"]
    ]
    template_pins = [
        {
            "pin_type": "TEMPLATE",
            "identity": manifest["package_template_id"],
            "version": manifest["package_template_version"],
            "checksum": manifest["manifest_checksum"],
        }
    ]
    base = {
        "schema_version": SCHEMA_VERSION,
        "report_id": None,
        "report_content_checksum": None,
        "report_checksum": None,
        "package_id": manifest["package_id"],
        "package_schema_version": manifest["package_schema_version"],
        "package_checksum": manifest["package_checksum"],
        "project_id": manifest["experimental_project_identity"],
        "workflow_id": manifest["workflow_id"],
        "workflow_version": manifest["workflow_version"],
        "workflow_checksum": manifest["workflow_checksum"],
        **draft,
        "output_artifacts": outputs,
        "context_before_checksum": context_before_checksum,
        "context_after_checksum": context_after_checksum,
        "skill_pins": skill_pins,
        "template_pins": template_pins,
        "generated_at": draft["completed_at"],
        "experimental_declaration": EXPERIMENTAL_DECLARATION,
    }
    report = compute_identity(base)
    verify_identity(report)
    reports_root = root / "memory/progress/reports"
    target = reports_root / f"{report['report_id']}.json"
    if target.exists() or target.is_symlink():
        raise ProgressReportError("Progress Reports are append-only")
    target.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return {
        "created": target.relative_to(root).as_posix(),
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "context_before_checksum": context_before_checksum,
        "context_after_checksum": context_after_checksum,
        "upload_ready": True,
    }


def validate_report(*, package_root: str | Path, report_path: str) -> dict[str, Any]:
    root = _root(package_root)
    relative = safe_relative_path(report_path)
    report = _load_object(root.joinpath(*relative.split("/")), "Progress Report")
    verify_identity(report)
    return {
        "valid": True,
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "upload_ready": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate Progress Report v0.2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--root", default=".")
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--root", default=".")
    finalize_parser.add_argument("--draft", required=True)
    finalize_parser.add_argument("--context-before", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--root", default=".")
    validate_parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot(args.root)
        elif args.command == "finalize":
            result = finalize(
                package_root=args.root,
                draft_path=args.draft,
                context_before_checksum=args.context_before,
            )
        else:
            result = validate_report(
                package_root=args.root,
                report_path=args.report,
            )
    except ProgressReportError as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
