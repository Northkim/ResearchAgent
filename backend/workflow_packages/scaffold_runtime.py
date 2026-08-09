#!/usr/bin/env python3
"""Shared local-Harness runner for production SCAFFOLD_CORE Capsules."""

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
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ScaffoldRuntimeError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ScaffoldRuntimeError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScaffoldRuntimeError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ScaffoldRuntimeError(f"{label} must be a JSON object")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ScaffoldRuntimeError("output parent must not be a symbolic link")
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, (canonical_json(value) + "\n").encode("utf-8"))


def _validate_package(root: Path) -> dict[str, Any]:
    namespace = runpy.run_path(str(root / "validate_package.py"))
    try:
        result = namespace["validate"](root, pristine=False)
    except Exception as error:
        raise ScaffoldRuntimeError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise ScaffoldRuntimeError("Capsule validation failed closed")
    return result


def preflight(root: Path) -> dict[str, Any]:
    _validate_package(root)
    config = _object(root / "workflow/scaffold.json", "scaffold contract")
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    if provenance.get("schema_version") != "reagent.scaffold-input-provenance/v0.1":
        raise ScaffoldRuntimeError("input provenance schema mismatch")
    records = provenance.get("artifacts")
    if not isinstance(records, dict):
        raise ScaffoldRuntimeError("input provenance records are invalid")
    verified: dict[str, str] = {}
    for requirement in config["input_requirements"]:
        key = requirement["requirement_key"]
        record = records.get(key)
        if record is None:
            if requirement["required"]:
                raise ScaffoldRuntimeError(
                    f"required input {key} is not explicitly bound and materialized"
                )
            continue
        if not isinstance(record, dict) or set(record) != {
            "artifact_id", "artifact_type", "sha256", "relative_path"
        }:
            raise ScaffoldRuntimeError(f"input provenance for {key} is invalid")
        if record["artifact_type"] != requirement["artifact_type"]:
            raise ScaffoldRuntimeError(f"input Artifact type mismatch for {key}")
        path = root.joinpath(*requirement["target_relative_path"].split("/"))
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ScaffoldRuntimeError(f"materialized input {key} is unavailable")
        checksum = sha256_bytes(path.read_bytes())
        if checksum != record["sha256"]:
            raise ScaffoldRuntimeError(f"materialized input checksum drift for {key}")
        value = _object(path, f"materialized input {key}")
        if value.get("schema") != requirement["artifact_type"]:
            raise ScaffoldRuntimeError(f"materialized input schema mismatch for {key}")
        verified[key] = checksum
    return {
        "schema_version": "reagent.scaffold-preflight/v0.1",
        "ready": True,
        "workflow_id": config["workflow_id"],
        "core_capability_maturity": "SCAFFOLD_CORE",
        "verified_inputs": verified,
    }


def _reports(root: Path) -> list[dict[str, Any]]:
    values = [
        _object(path, "Progress Report")
        for path in sorted((root / "memory/progress/reports").glob("prv2-*.json"))
    ]
    values.sort(key=lambda item: (item["execution_round"], item["report_id"]))
    return values


def _prepare_draft(root: Path, config: dict[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    history = _reports(root)
    previous = history[-1] if history else None
    round_number = 1 if previous is None else previous["execution_round"] + 1
    now = _timestamp()
    draft = {
        "execution_round": round_number,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": f"{config['workflow_slug']}-round-{round_number}",
        "previous_report_id": None if previous is None else previous["report_id"],
        "previous_report_checksum": None if previous is None else previous["report_checksum"],
        "started_at": now,
        "completed_at": now,
        "status": "COMPLETED",
        "completed_work": [
            "Validated exact materialized inputs",
            "Published a visibly marked scaffold placeholder Artifact",
        ],
        "current_state": "COMPLETED",
        "next_recommended_action": config["completed_next_action"],
        "continuation_reason": (
            None if previous is None
            else "Owner explicitly started another scaffold continuity round"
        ),
        "warnings": [
            "SCAFFOLD_CORE: product flow is functional; research capability is placeholder"
        ],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": [
            "Read AGENT.md, memory/context.md, exact inputs, and prior Progress Reports."
        ],
    }
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    return snapshot["context_before_checksum"]


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise ScaffoldRuntimeError("Configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise ScaffoldRuntimeError("Codex CLI is unavailable")
    return resolved


def _run_harness(root: Path, executable: str) -> None:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }
    result = subprocess.run([executable], cwd=root, env=environment, check=False)
    if result.returncode != 0:
        raise ScaffoldRuntimeError("Codex exited before scaffold finalization")


def _ref(records: dict[str, Any], key: str) -> dict[str, str] | None:
    value = records.get(key)
    if value is None:
        return None
    return {
        "artifact_id": value["artifact_id"],
        "artifact_type": value["artifact_type"],
        "sha256": value["sha256"],
    }


def _scaffold_payload(
    config: dict[str, Any], records: dict[str, Any], root: Path
) -> tuple[dict[str, Any], bytes]:
    workflow = config["workflow_kind"]
    if workflow == "WRITING":
        idea = _object(
            root / "inputs/selected-research-idea.json", "selected research idea"
        )
        title = str(idea["selected_idea"]["title"]).strip()
        revision = records.get("prior_manuscript") is not None
        content = (
            "# SCAFFOLD PLACEHOLDER\n\n"
            "No substantive academic manuscript was generated by this version.\n\n"
            f"# {title}\n\n"
            "## Introduction\n\n[Scaffold placeholder — substantive writing core not implemented.]\n\n"
            "## Related Work\n\n[Scaffold placeholder.]\n\n"
            "## Method\n\n[Scaffold placeholder.]\n\n"
            "## Results\n\n[Not generated. No experiment or scientific result is claimed.]\n\n"
            "## Conclusion\n\n[Scaffold placeholder.]\n"
        )
        if revision:
            content += (
                "\nScaffold revision generated to validate Writing ↔ Review provenance.\n"
                "No substantive revision core was executed.\n"
            )
        artifact = {
            "schema": "manuscript-draft/v1",
            "core_capability_maturity": "SCAFFOLD_CORE",
            "source_artifacts": {
                "research_idea": _ref(records, "research_idea"),
                "literature_library": _ref(records, "literature_library"),
                "experiment_record": _ref(records, "experiment_record"),
                "review_feedback": _ref(records, "review_feedback"),
                "prior_manuscript": _ref(records, "prior_manuscript"),
            },
            "title": f"SCAFFOLD PLACEHOLDER — {title}",
            "content_markdown": content,
        }
        return artifact, content.encode("utf-8")
    if workflow == "REVIEW":
        content = (
            "# SCAFFOLD REVIEW PLACEHOLDER\n\n"
            "This scaffold review does not perform substantive academic review.\n"
            "It does not assess novelty, correctness, acceptance, or publication quality.\n"
        )
        artifact = {
            "schema": "review-report/v1",
            "core_capability_maturity": "SCAFFOLD_CORE",
            "source_manuscript": _ref(records, "manuscript"),
            "supporting_artifacts": [
                item for item in (
                    _ref(records, "literature_library"),
                    _ref(records, "experiment_record"),
                ) if item is not None
            ],
            "summary": (
                "SCAFFOLD REVIEW PLACEHOLDER: no substantive academic review was performed."
            ),
            "major_issues": [],
            "minor_issues": [],
            "requested_revisions": [{
                "revision_id": "revision-scaffold-core-required",
                "priority": "MAJOR",
                "description": (
                    "This scaffold review does not perform substantive academic review. "
                    "Replace the scaffold core before using review feedback for research decisions."
                ),
            }],
            "recommendation": "INSUFFICIENT_EVIDENCE",
        }
        return artifact, content.encode("utf-8")
    idea = _object(
        root / "inputs/selected-research-idea.json", "selected research idea"
    )
    question = str(idea["selected_idea"]["research_question"]).strip()
    content = (
        "# SCAFFOLD EXPERIMENT PLACEHOLDER\n\n"
        "Current supported mode: Idea Experiment Skeleton.\n\n"
        "Paper Reproduction: NOT YET ENABLED.\n\n"
        f"Objective context: {question}\n\n"
        "No real experiment or reproduction was executed by this scaffold version.\n"
        "No metrics, benchmark results, runtimes, p-values, or success claims were generated.\n"
    )
    artifact = {
        "schema": "experiment-record/v1",
        "core_capability_maturity": "SCAFFOLD_CORE",
        "mode": "IDEA_EXPERIMENT",
        "source_artifacts": [
            item for item in (
                _ref(records, "research_idea"),
                _ref(records, "literature_library"),
            ) if item is not None
        ],
        "execution_status": "PLACEHOLDER_NOT_EXECUTED",
        "plan": {
            "objective": question,
            "hypothesis": None,
            "method": "No real experiment or reproduction was executed by this scaffold version.",
            "metrics": [],
            "baselines": [],
        },
        "actual_results": None,
        "limitations": [
            "SCAFFOLD_CORE placeholder only",
            "Paper reproduction and external Resource resolution are not enabled",
        ],
    }
    return artifact, content.encode("utf-8")


def _publish(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    artifact, human = _scaffold_payload(config, provenance["artifacts"], root)
    namespace = runpy.run_path(str(root / "validate_package.py"))
    namespace["validate_scaffold_artifact"](artifact)
    human_path = root.joinpath(*config["human_output_path"].split("/"))
    _atomic_bytes(human_path, human)
    content = canonical_json(artifact).encode("utf-8")
    checksum = sha256_bytes(content)
    relative = (
        config["artifact_path_prefix"] + "/sha256-" + checksum[7:] + ".json"
    )
    target = root.joinpath(*relative.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink():
        raise ScaffoldRuntimeError("Artifact parent is unsafe")
    if target.exists() or target.is_symlink():
        if (
            target.is_symlink() or not target.is_file()
            or target.stat().st_nlink != 1 or target.read_bytes() != content
        ):
            raise ScaffoldRuntimeError("content-addressed scaffold Artifact conflicts")
    else:
        _atomic_bytes(target, content)
    current = {
        "relative_path": relative,
        "artifact_kind": config["output_artifact_type"],
        "media_type": "application/json",
        "checksum": checksum,
        "size": len(content),
    }
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _update_context(root: Path, config: dict[str, Any], artifact: dict[str, Any]) -> None:
    history = _reports(root)
    payload = {
        "schema_version": "reagent.scaffold-context/v0.1",
        "workflow_id": config["workflow_id"],
        "core_capability_maturity": "SCAFFOLD_CORE",
        "completed_rounds": len(history) + 1,
        "latest_artifact": artifact,
        "continuation": "Read local files; prior chat history is not required.",
        "updated_at": _timestamp(),
    }
    _atomic_bytes(
        root / "memory/context.md",
        ("# Scaffold Workflow Context\n\n```json\n" + canonical_json(payload) + "\n```\n").encode("utf-8"),
    )


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
        raise ScaffoldRuntimeError(f"Progress finalization failed: {error}") from error
    return root / result["created"]


def _upload(
    *, root: Path, report_path: Path, workflow_instance_id: str, api_url: str
) -> dict[str, Any]:
    manifest = _object(root / "package-manifest.json", "package manifest")
    report = _object(report_path, "Progress Report")
    report_bytes = report_path.read_bytes()
    current = _object(root / "memory/current-artifact.json", "current Artifact")
    artifact_id = "artifact-" + uuid.uuid5(
        uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966"),
        "production-artifact/v1|package=" + manifest["package_id"]
        + "|report=" + report["report_id"] + "|path=" + current["relative_path"]
        + "|checksum=" + current["checksum"],
    ).hex
    declaration = {
        "artifact_id": artifact_id,
        "artifact_type": current["artifact_kind"],
        "artifact_schema_version": current["artifact_kind"],
        "media_type": current["media_type"],
        "relative_path": current["relative_path"],
        "content_checksum": current["checksum"],
        "size_bytes": current["size"],
        "produced_at": report["completed_at"],
    }
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
        "uploaded_at": _timestamp(),
        "uploader_type": "local-cli",
        "client_version": "reagent-local-scaffold/0.1.0",
        "source_path_hint": report_path.relative_to(root).as_posix(),
        "context_snapshot_metadata": None,
        "artifact_declarations": [declaration],
        "envelope_checksum": None,
    }
    envelope = dict(payload)
    envelope.pop("workflow_instance_id")
    envelope.pop("artifact_declarations")
    payload["envelope_checksum"] = sha256_bytes(
        canonical_json(envelope).encode("utf-8")
    )
    request = urllib.request.Request(
        api_url.rstrip("/") + f"/projects/{manifest['experimental_project_identity']}/progress-reports",
        data=(canonical_json(payload) + "\n").encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read(262_145).decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
        raise ScaffoldRuntimeError(
            "Progress upload failed; finalized local files are retained"
        ) from error
    if not isinstance(value, dict) or not value.get("accepted_for_projection"):
        raise ScaffoldRuntimeError("Cloud did not accept scaffold Progress")
    _atomic_json(
        root / "memory/progress/receipts" / f"{report['report_id']}.json", value
    )
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a local ReAgent scaffold Workflow")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("root", nargs="?", default=".", type=Path)
    run_parser.add_argument("--workflow-instance", required=True)
    run_parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        result = preflight(root)
        if not args.preflight_only:
            config = _object(root / "workflow/scaffold.json", "scaffold contract")
            context_before = _prepare_draft(root, config)
            _run_harness(root, _codex_executable(args.codex_executable))
            # The Harness is untrusted with respect to immutable input bytes and
            # scaffold safety. Re-run the exact preflight before publication.
            preflight(root)
            artifact = _publish(root, config)
            _update_context(root, config, artifact)
            report_path = _finalize(root, context_before)
            result = {
                **result,
                "artifact": artifact,
                "progress": _upload(
                    root=root, report_path=report_path,
                    workflow_instance_id=args.workflow_instance, api_url=args.api_url,
                ),
            }
    except ScaffoldRuntimeError as error:
        print(canonical_json({"ok": False, "error": str(error)}))
        return 1
    print(canonical_json({"ok": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
