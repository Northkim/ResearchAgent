#!/usr/bin/env python3
"""Local interactive runner bundled in the reviewed Idea Discovery Capsule."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_STAGES = {
    "INPUT_REVIEW",
    "LANDSCAPE_ANALYSIS",
    "GAP_EXPLORATION",
    "CANDIDATE_IDEAS",
    "USER_REVIEW",
    "REFINEMENT",
    "COMPLETED",
}
SHA256_PREFIX = "sha256:"


class IdeaDiscoveryError(RuntimeError):
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
    return SHA256_PREFIX + hashlib.sha256(content).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise IdeaDiscoveryError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IdeaDiscoveryError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise IdeaDiscoveryError(f"{label} must be a JSON object")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (canonical_json(value) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_package(root: Path) -> None:
    namespace = runpy.run_path(str(root / "validate_package.py"))
    try:
        result = namespace["validate"](root, pristine=False)
    except Exception as error:
        raise IdeaDiscoveryError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise IdeaDiscoveryError("Capsule validation failed closed")


def preflight(root: Path) -> dict[str, Any]:
    _validate_package(root)
    library_path = root / "inputs/selected-paper-library.json"
    library = _object(library_path, "materialized selected paper library")
    if library.get("schema") != "selected-paper-library/v1":
        raise IdeaDiscoveryError("Materialized input has the wrong Artifact schema")
    papers = library.get("papers")
    if not isinstance(papers, list) or not papers:
        raise IdeaDiscoveryError("Materialized input has no selected papers")
    checksum = sha256_bytes(library_path.read_bytes())
    return {
        "schema_version": "reagent.idea-discovery-preflight/v0.1",
        "ready": True,
        "artifact_type": "selected-paper-library/v1",
        "input_relative_path": "inputs/selected-paper-library.json",
        "input_checksum": checksum,
        "paper_count": len(papers),
    }


def _reports(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted((root / "memory/progress/reports").glob("prv2-*.json")):
        result.append(_object(path, "Progress Report"))
    result.sort(key=lambda item: (item["execution_round"], item["report_id"]))
    return result


def _prepare_draft(root: Path, *, stage: str) -> str:
    if stage not in ALLOWED_STAGES:
        raise IdeaDiscoveryError("Idea Discovery stage is invalid")
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    history = _reports(root)
    previous = history[-1] if history else None
    now = _timestamp()
    draft = {
        "execution_round": 1 if previous is None else previous["execution_round"] + 1,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": f"idea-discovery-round-{1 if previous is None else previous['execution_round'] + 1}",
        "previous_report_id": None if previous is None else previous["report_id"],
        "previous_report_checksum": None if previous is None else previous["report_checksum"],
        "started_at": now,
        "completed_at": now,
        "status": "COMPLETED" if stage == "COMPLETED" else "IN_PROGRESS",
        "completed_work": [],
        "current_state": stage,
        "next_recommended_action": "Continue the evidence-grounded Idea Discovery conversation",
        "continuation_reason": None,
        "warnings": [],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": [
            "Read AGENT.md, memory/context.md, and existing outputs before continuing."
        ],
    }
    if previous is not None and previous.get("status") == "COMPLETED":
        draft["continuation_reason"] = "Owner explicitly started another refinement round"
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    return snapshot["context_before_checksum"]


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise IdeaDiscoveryError("Configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise IdeaDiscoveryError("Codex CLI is unavailable")
    return resolved


def _run_harness(root: Path, executable: str) -> None:
    environment = dict(os.environ)
    for key in (
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        "REAGENT_DATABASE_URL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        environment.pop(key, None)
    result = subprocess.run([executable], cwd=root, env=environment, check=False)
    if result.returncode != 0:
        raise IdeaDiscoveryError("Codex exited before Idea Discovery finalization")


def _finalize(root: Path, context_before: str) -> Path:
    draft_path = root / "memory/progress/report-draft.json"
    draft = _object(draft_path, "Progress Report draft")
    draft["completed_at"] = _timestamp()
    _atomic_json(draft_path, draft)
    _validate_package(root)
    namespace = runpy.run_path(str(root / "progress_report.py"))
    try:
        result = namespace["finalize"](
            package_root=root,
            draft_path="memory/progress/report-draft.json",
            context_before_checksum=context_before,
        )
    except Exception as error:
        raise IdeaDiscoveryError(f"Progress finalization failed: {error}") from error
    return root / result["created"]


def _upload(
    *, root: Path, report_path: Path, workflow_instance_id: str, api_url: str
) -> dict[str, Any]:
    manifest = _object(root / "package-manifest.json", "package manifest")
    report = _object(report_path, "Progress Report")
    report_bytes = report_path.read_bytes()
    uploaded_at = _timestamp()
    payload = {
        "workflow_instance_id": workflow_instance_id,
        "upload_schema_version": "progress-report-upload/v0.1",
        "project_id": manifest["experimental_project_identity"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "report_schema_version": report["schema_version"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "original_report_media_type": "application/json",
        "original_report_base64": base64.b64encode(report_bytes).decode("ascii"),
        "original_report_checksum": sha256_bytes(report_bytes),
        "original_report_size": len(report_bytes),
        "uploaded_at": uploaded_at,
        "uploader_type": "local-cli",
        "client_version": "reagent-local-idea-discovery/0.1.0",
        "source_path_hint": report_path.relative_to(root).as_posix(),
        "context_snapshot_metadata": None,
        "artifact_declarations": [],
        "envelope_checksum": None,
    }
    envelope = dict(payload)
    envelope.pop("workflow_instance_id")
    envelope.pop("artifact_declarations")
    payload["envelope_checksum"] = sha256_bytes(canonical_json(envelope).encode("utf-8"))
    project_id = manifest["experimental_project_identity"]
    request = urllib.request.Request(
        api_url.rstrip("/") + f"/projects/{project_id}/progress-reports",
        data=(canonical_json(payload) + "\n").encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read(262_145).decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
        raise IdeaDiscoveryError("Progress upload failed; the finalized local report is retained") from error
    if not isinstance(value, dict) or not value.get("accepted_for_projection"):
        raise IdeaDiscoveryError("Cloud did not accept Idea Discovery Progress")
    receipt_path = root / "memory/progress/receipts" / f"{report['report_id']}.json"
    _atomic_json(receipt_path, value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Idea Discovery Workflow")
    commands = parser.add_subparsers(dest="command", required=True)
    preflight_parser = commands.add_parser("preflight")
    preflight_parser.add_argument("root", nargs="?", default=".", type=Path)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("root", nargs="?", default=".", type=Path)
    run_parser.add_argument("--workflow-instance", required=True)
    run_parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--stage", choices=sorted(ALLOWED_STAGES), default="INPUT_REVIEW")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        result = preflight(root)
        if args.command == "run" and not args.preflight_only:
            context_before = _prepare_draft(root, stage=args.stage)
            _run_harness(root, _codex_executable(args.codex_executable))
            report_path = _finalize(root, context_before)
            result = {
                **result,
                "progress": _upload(
                    root=root,
                    report_path=report_path,
                    workflow_instance_id=args.workflow_instance,
                    api_url=args.api_url,
                ),
            }
    except IdeaDiscoveryError as error:
        print(canonical_json({"ok": False, "error": str(error)}))
        return 1
    print(canonical_json({"ok": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
