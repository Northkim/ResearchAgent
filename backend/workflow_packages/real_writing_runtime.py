#!/usr/bin/env python3
"""Self-contained runner for the first reviewed local Real Writing Capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


class RealWritingError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise RealWritingError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealWritingError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise RealWritingError(f"{label} must be an object")
    return value


def _array(path: Path, label: str) -> list[Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise RealWritingError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealWritingError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, list):
        raise RealWritingError(f"{label} must be an array")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise RealWritingError("output parent is unsafe")
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content); handle.flush(); os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, (canonical_json(value) + "\n").encode())


def _validator(root: Path) -> dict[str, Any]:
    return runpy.run_path(str(root / "validate_package.py"))


def _validate_package(root: Path) -> None:
    try:
        result = _validator(root)["validate"](root, pristine=False)
    except Exception as error:
        raise RealWritingError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise RealWritingError("Capsule validation failed closed")


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise RealWritingError("configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise RealWritingError("Codex CLI is unavailable")
    return resolved


def _codex_environment() -> dict[str, str]:
    blocked = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY", "DATABASE_URL")
    environment = {
        key: value for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in blocked)
        and key in {"PATH", "TMPDIR", "LANG", "LC_ALL", "TERM", "SHELL"}
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _phase_one_instruction() -> str:
    return """REAGENT REAL WRITING — INPUT_REVIEW THROUGH OUTLINE

Read AGENT.md, workflow/prompts/real-writing.md, workflow/real-writing.json,
memory/input-provenance.json, and only the exact materialized inputs declared by
that contract. Do not inspect sibling Capsules or use network.

This first pass MUST NOT draft manuscript prose. Create only:
  memory/writing-brief.json
  memory/evidence-map.json
  memory/outline.json
using the exact shapes documented by workflow/real-writing.json.

The Writing Brief `target_words` value MUST be an object with integer `minimum`
and `maximum` fields. Every evidence reference MUST contain exactly:
`artifact_id`, `artifact_type`, `sha256`, `evidence_item`, `location`,
`availability`, and nullable `limitation`; copy the first three fields from one
exact record in memory/input-provenance.json. Use availability only from
AVAILABLE, LIMITED, UNAVAILABLE. Evidence Map items contain exactly `section`,
`support_status`, `evidence_refs`, `limitations`, where `limitations` MUST be a
JSON array of strings (use `[]`, never a single string). The Writing Brief
`requested_sections` and `owner_constraints` are also JSON arrays of strings.
Outline items contain exactly
`heading`, `support_status`. SUPPORTED items require at least one exact evidence
reference. UNAVAILABLE items MUST use an empty evidence_refs array; describe why
in limitations rather than citing evidence. Do not substitute a `locator` field.

The Evidence Map is mandatory. Use only SUPPORTED, PLANNED, UNAVAILABLE. An Idea
supports proposed questions/hypotheses/design, never executed results. Literature
is metadata/available-abstract evidence only unless its exact record says less;
never imply full text was read. Only a bound experiment-record/v2 with SUCCEEDED
execution, VALID evaluation, and SUCCEEDED result may support an observed result.
If no Experiment is bound, result evidence is UNAVAILABLE. Preserve exact
Artifact identity in every evidence reference. The runner—not chat—will present
the exact Outline and obtain durable owner approval after you exit."""


def _phase_two_instruction() -> str:
    return """REAGENT REAL WRITING — SECTION_DRAFTING AND CLAIM_CITATION_CHECK

Read AGENT.md, workflow/prompts/real-writing.md, the exact materialized inputs,
memory/writing-brief.json, memory/evidence-map.json, memory/outline.json, and
memory/outline-approval.json. The approval is immutable authority: do not change
the brief, Evidence Map, Outline, or inputs.

Produce a substantive evidence-bound initial draft at outputs/draft.md and typed
arrays at memory/claims.json and memory/citations.json using the exact shapes in
workflow/real-writing.json. A claim contains exactly `claim_id`, `claim_type`,
`section`, `claim_text`, `support_status`, `evidence_refs`, `citation_ids`, and
`limitations`; both `citation_ids` and `limitations` MUST be JSON arrays of
strings. claim_type is LITERATURE, PROPOSAL, or RESULT. A citation contains
exactly `citation_id`, `paper_id`, `source_artifact`, `evidence_scope`, and
`reference_markdown`; copy `source_artifact` exactly from the literature input
provenance and use evidence_scope METADATA_ONLY or ABSTRACT. Evidence references
use the same exact seven-field shape from the first pass; do not use `locator`.
SUPPORTED claims require evidence; UNAVAILABLE claims MUST have an empty
evidence_refs array. A supported LITERATURE claim also requires a selected-library
citation. A RESULT claim may be SUPPORTED only by a valid bound experiment.
SUPPORTED prose must stay within exact evidence;
PLANNED prose must use proposal/future language; UNAVAILABLE evidence must not
become fact. Never fabricate observed results. Literature citations must name
papers in the exact selected library and preserve METADATA_ONLY versus ABSTRACT
scope. Run a careful claim/citation consistency pass before exiting. Do not
finalize Progress or publish an Artifact. The runner will validate the bounded
truth/provenance contract, present the draft for owner review, and finalize only
after exact approval."""


def _run_harness(root: Path, executable: str, instruction: str) -> None:
    command = [
        executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C", str(root), instruction,
    ]
    try:
        completed = subprocess.run(command, cwd=root, env=_codex_environment(), check=False)
    except OSError as error:
        raise RealWritingError("Codex process could not be started") from error
    if completed.returncode != 0:
        raise RealWritingError("Codex exited before completing the current Writing stage")


def _load_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    _, sources, library, experiment = _validator(root)["_input_state"](root)
    return {
        "research_idea": sources["research_idea"],
        "literature_library": sources["literature_library"],
        "experiment_record": sources.get("experiment_record"),
    }, library, experiment


def _load_outline(root: Path, sources: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]], str]:
    namespace = _validator(root)
    brief = namespace["validate_writing_brief"](_object(root / "memory/writing-brief.json", "Writing Brief"))
    evidence_map = namespace["validate_evidence_map"](_array(root / "memory/evidence-map.json", "Evidence Map"), sources)
    outline = namespace["validate_outline"](_array(root / "memory/outline.json", "Outline"))
    return brief, evidence_map, outline, canonical_hash(outline)


def _approve_outline(
    root: Path, sources: dict[str, Any], brief: dict[str, Any],
    evidence_map: list[dict[str, Any]], outline: list[dict[str, str]],
    outline_sha: str, approval_input: Callable[[str], str],
) -> dict[str, Any]:
    path = root / "memory/outline-approval.json"
    if path.exists() or path.is_symlink():
        raise RealWritingError("an Outline approval already exists")
    print("\nWriting Brief\n" + canonical_json(brief), flush=True)
    print("\nEvidence Map\n" + canonical_json(evidence_map), flush=True)
    print("\nOutline\n" + canonical_json(outline), flush=True)
    expected = f"approve {outline_sha}"
    if approval_input(f"Type `{expected}` to approve this exact Outline: ").strip() != expected:
        raise RealWritingError("Owner did not approve the exact Outline")
    payload = {
        "outline_sha256": outline_sha,
        "brief_sha256": canonical_hash(brief),
        "evidence_map_sha256": canonical_hash(evidence_map),
        "source_artifacts_sha256": canonical_hash(sources),
        "approved_at": _timestamp(),
        "decision": "APPROVED",
    }
    approval = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, approval)
    return approval


def _verify_outline_approval(
    root: Path, sources: dict[str, Any], brief: dict[str, Any],
    evidence_map: list[dict[str, Any]], outline: list[dict[str, str]],
    approval: dict[str, Any],
) -> None:
    current = _object(root / "memory/outline-approval.json", "Outline approval")
    payload = dict(current); checksum = payload.pop("sha256", None)
    if current != approval or checksum != canonical_hash(payload) or any((
        current["outline_sha256"] != canonical_hash(outline),
        current["brief_sha256"] != canonical_hash(brief),
        current["evidence_map_sha256"] != canonical_hash(evidence_map),
        current["source_artifacts_sha256"] != canonical_hash(sources),
        current["decision"] != "APPROVED",
    )):
        raise RealWritingError("Outline approval or approved inputs drifted")


def _load_draft(
    root: Path, sources: dict[str, Any], library: dict[str, Any],
    experiment: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], str]:
    draft_path = root / "outputs/draft.md"
    if draft_path.is_symlink() or not draft_path.is_file() or draft_path.stat().st_nlink != 1:
        raise RealWritingError("substantive draft must be one regular unlinked Markdown file")
    content = draft_path.read_text(encoding="utf-8")
    if not content.strip():
        raise RealWritingError("substantive draft is empty")
    namespace = _validator(root)
    citations = namespace["validate_citations"](_array(root / "memory/citations.json", "citations"), sources, library)
    claims = namespace["validate_claims"](_array(root / "memory/claims.json", "claims"), sources, citations, experiment)
    draft_sha = canonical_hash({
        "title": _title(content), "content_markdown": content,
        "claims": claims, "citations": citations,
    })
    return content, claims, citations, draft_sha


def _title(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    raise RealWritingError("draft must begin with a level-one title")


def _owner_review(root: Path, content: str, draft_sha: str, review_input: Callable[[str], str]) -> dict[str, Any]:
    path = root / "memory/owner-review.json"
    if path.exists() or path.is_symlink():
        raise RealWritingError("an Owner draft review already exists")
    print("\nSubstantive Initial Draft\n" + content, flush=True)
    expected = f"finalize {draft_sha}"
    if review_input(f"Type `{expected}` after reviewing this exact draft: ").strip() != expected:
        raise RealWritingError("Owner did not approve the exact initial draft")
    payload = {"draft_sha256": draft_sha, "reviewed_at": _timestamp(), "decision": "APPROVED"}
    review = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, review)
    return review


def _publish(
    root: Path, workflow_instance_id: str, sources: dict[str, Any], brief: dict[str, Any],
    evidence_map: list[dict[str, Any]], outline: list[dict[str, str]],
    approval: dict[str, Any], content: str, claims: list[dict[str, Any]],
    citations: list[dict[str, Any]], review: dict[str, Any],
) -> dict[str, Any]:
    contract = _object(root / "workflow/real-writing.json", "Real Writing contract")
    artifact = {
        "schema": "manuscript-draft/v2",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {
            "workflow_instance_id": workflow_instance_id,
            "capsule_id": contract["capsule_id"],
            "capsule_version": contract["capsule_version"],
            "execution_round": 1,
        },
        "source_artifacts": {
            "research_idea": sources["research_idea"],
            "literature_library": sources["literature_library"],
            "experiment_record": sources.get("experiment_record"),
        },
        "writing_brief": brief,
        "evidence_map": evidence_map,
        "approved_outline": {"sha256": canonical_hash(outline), "value": outline},
        "outline_approval": approval,
        "title": _title(content),
        "content_markdown": content,
        "claims": claims,
        "citations": citations,
        "experiment_evidence_available": sources.get("experiment_record") is not None,
        "unsupported_areas": [item["section"] for item in evidence_map if item["support_status"] == "UNAVAILABLE"],
        "limitations": [
            "Writing is limited to exact bound Artifact content; no sibling private files or external retrieval were used.",
            "Mechanical claim/citation validation does not establish scientific correctness.",
        ],
        "owner_review": review,
    }
    try:
        _validator(root)["validate_manuscript_draft_v2"](artifact, root=root)
    except Exception as error:
        raise RealWritingError(f"manuscript-draft/v2 validation failed: {error}") from error
    content_bytes = canonical_json(artifact).encode()
    checksum = sha256_bytes(content_bytes)
    relative = "outputs/artifacts/manuscript-draft/sha256-" + checksum[7:] + ".json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content_bytes:
            raise RealWritingError("content-addressed Writing Output conflicts")
    else:
        _atomic_bytes(target, content_bytes)
    current = {"relative_path": relative, "artifact_kind": "manuscript-draft/v2", "media_type": "application/json", "checksum": checksum, "size": len(content_bytes)}
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _finalize_progress(root: Path, current: dict[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    context = {
        "schema_version": "reagent.real-writing-context/v0.1", "stage": "COMPLETED",
        "latest_output": current, "updated_at": _timestamp(),
    }
    _atomic_bytes(root / "memory/context.md", ("# Real Writing Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode())
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
    now = _timestamp()
    draft.update({
        "started_at": draft.get("started_at") or now, "completed_at": now,
        "status": "COMPLETED",
        "completed_work": ["Approved one exact evidence-aware Outline", "Produced and owner-reviewed one validated manuscript-draft/v2"],
        "current_state": "COMPLETED",
        "next_recommended_action": "Inspect the exact Writing Output and evidence limitations",
        "warnings": ["Scientific correctness remains subject to Real Review"],
        "errors": [], "unresolved_questions": [],
        "continuation_instructions": ["Use the exact manuscript-draft/v2 as the Real Review input"],
    })
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    report = namespace["finalize"](package_root=root, draft_path="memory/progress/report-draft.json", context_before_checksum=snapshot["context_before_checksum"])
    return "memory/progress/reports/" + report["report_id"] + ".json"


def run(
    root: Path, workflow_instance_id: str, *, codex_executable: str | None = None,
    approval_input: Callable[[str], str] = input,
    review_input: Callable[[str], str] = input,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_package(root)
    if list((root / "memory/progress/reports").glob("*.json")):
        raise RealWritingError("Real Writing already has terminal Progress")
    sources, library, experiment = _load_inputs(root)
    executable = _codex_executable(codex_executable)
    _run_harness(root, executable, _phase_one_instruction())
    brief, evidence_map, outline, outline_sha = _load_outline(root, sources)
    approval = _approve_outline(root, sources, brief, evidence_map, outline, outline_sha, approval_input)
    _run_harness(root, executable, _phase_two_instruction())
    current_sources, current_library, current_experiment = _load_inputs(root)
    current_brief, current_map, current_outline, _ = _load_outline(root, current_sources)
    _verify_outline_approval(root, current_sources, current_brief, current_map, current_outline, approval)
    if current_sources != sources or current_library != library or current_experiment != experiment:
        raise RealWritingError("exact Writing inputs drifted after Outline approval")
    content, claims, citations, draft_sha = _load_draft(root, sources, library, experiment)
    review = _owner_review(root, content, draft_sha, review_input)
    current = _publish(root, workflow_instance_id, sources, brief, evidence_map, outline, approval, content, claims, citations, review)
    report = _finalize_progress(root, current)
    _validate_package(root)
    return {"status": "COMPLETED", "artifact": current, "progress_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python reagent_local.py")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("root", type=Path)
    run_parser.add_argument("--workflow-instance", required=True)
    run_parser.add_argument("--api-url")
    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        _validate_package(root)
        if args.preflight_only:
            _load_inputs(root)
            print(canonical_json({"status": "PREFLIGHT_READY"}))
        else:
            print(canonical_json(run(root, args.workflow_instance, codex_executable=args.codex_executable)))
    except (RealWritingError, OSError, ValueError) as error:
        print(f"Real Writing stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
