"""Deterministic helpers for experimental local context and Progress Reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import LocalContext, OutputFileReference, ProgressReport
from .security import require_relative_path
from .serialization import canonical_json, sha256_bytes


def render_context(context: LocalContext) -> str:
    if not context.verify_checksum():
        raise ValueError("local context checksum is invalid")
    return (
        "# Local Task Context\n\n"
        "> Human-readable state; update this file at the declared boundary.\n\n"
        "```json\n"
        + canonical_json(context)
        + "\n```\n"
    )


def parse_context(content: str) -> LocalContext:
    marker = "```json\n"
    if marker not in content or "\n```" not in content:
        raise ValueError("local context must contain one JSON state block")
    payload_text = content.split(marker, 1)[1].split("\n```", 1)[0]
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError("local context payload must be an object")
    context = LocalContext(
        **{
            **payload,
            "completed_outputs": tuple(payload.get("completed_outputs", [])),
            "relevant_decisions": tuple(payload.get("relevant_decisions", [])),
            "unresolved_issues": tuple(payload.get("unresolved_issues", [])),
        }
    )
    if not context.verify_checksum():
        raise ValueError("local context checksum mismatch")
    return context


def write_context(package_root: str | Path, context: LocalContext) -> str:
    root = Path(package_root)
    target = root / "memory/context.md"
    if target.is_symlink():
        raise ValueError("local context must not be a symbolic link")
    content = render_context(context).encode("utf-8")
    target.write_bytes(content)
    return sha256_bytes(content)


def progress_report_from_dict(payload: dict[str, Any]) -> ProgressReport:
    output_files = tuple(OutputFileReference(**item) for item in payload.get("output_files", []))
    report = ProgressReport(
        **{
            **payload,
            "skill_versions": tuple(payload.get("skill_versions", [])),
            "completed_work": tuple(payload.get("completed_work", [])),
            "output_files": output_files,
            "warnings": tuple(payload.get("warnings", [])),
            "errors": tuple(payload.get("errors", [])),
            "unresolved_questions": tuple(payload.get("unresolved_questions", [])),
            "continuation_instructions": tuple(payload.get("continuation_instructions", [])),
        }
    )
    if not report.verify_checksum():
        raise ValueError("Progress Report checksum mismatch")
    return report


def append_progress_report(package_root: str | Path, report: ProgressReport) -> Path:
    if not report.verify_checksum():
        raise ValueError("Progress Report checksum is invalid")
    root = Path(package_root)
    manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
    if report.package_id != manifest.get("package_id") or report.package_checksum != manifest.get("package_checksum"):
        raise ValueError("Progress Report package identity mismatch")
    context_bytes = (root / "memory/context.md").read_bytes()
    if report.context_checksum != sha256_bytes(context_bytes):
        raise ValueError("Progress Report context checksum does not match local context file")
    for output in report.output_files:
        relative_path = require_relative_path(output.relative_path)
        output_path = root.joinpath(*relative_path.split("/"))
        if output_path.is_symlink() or not output_path.is_file():
            raise ValueError(f"Progress Report output does not exist: {relative_path}")
        if sha256_bytes(output_path.read_bytes()) != output.checksum:
            raise ValueError(f"Progress Report output checksum mismatch: {relative_path}")
    reports_root = root / "memory/progress/reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    target = reports_root / f"{report.report_id}.json"
    if target.exists() or target.is_symlink():
        raise FileExistsError("Progress Reports are append-only and cannot be overwritten")
    target.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return target
