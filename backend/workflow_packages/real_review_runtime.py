#!/usr/bin/env python3
"""Self-contained runner for the first reviewed local Real Review Capsule."""

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


class RealReviewError(RuntimeError):
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
        raise RealReviewError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealReviewError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise RealReviewError(f"{label} must be an object")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise RealReviewError("output parent is unsafe")
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
        raise RealReviewError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise RealReviewError("Capsule validation failed closed")


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise RealReviewError("configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise RealReviewError("Codex CLI is unavailable")
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


def _scope_instruction() -> str:
    return """REAGENT REAL REVIEW — INPUT_REVIEW AND REVIEW_SCOPE

Read AGENT.md, workflow/prompts/real-review.md, workflow/real-review.json,
memory/input-provenance.json, memory/evidence-availability.json, and only the
exact materialized inputs declared by that contract. Do not inspect sibling
Capsules or use network.

This pass MUST NOT create issues or a review recommendation. Create only
memory/review-scope.json with exactly: manuscript_identity, available_evidence,
categories, known_evidence_limitations, owner_focus. Copy manuscript_identity
from input provenance role manuscript. Copy available_evidence in this exact
role order when present: research_idea, literature_library, experiment_record.
Each identity object MUST be copied verbatim and contain exactly artifact_id,
artifact_type, sha256; never add role or other fields. known_evidence_limitations
and owner_focus MUST each be arrays of non-empty strings (use [] when none),
never objects and never null. Use categories only from workflow/real-review.json.
Include all six defaults unless the controlled Owner focus explicitly narrows
them. Record absent or scope-limited evidence as concise strings in
known_evidence_limitations. Do not add novelty, venue fit, significance,
acceptance, rejection, or scoring. The runner—not chat—will obtain exact durable
Owner approval after this pass."""


def _audit_instruction() -> str:
    return """REAGENT REAL REVIEW — BOUNDED EVIDENCE AUDIT

Read the exact materialized manuscript and supporting evidence, the immutable
memory/review-scope.json and memory/scope-approval.json, and
memory/evidence-availability.json. Do not change those files.

Audit the manuscript's existing typed claims and citations. Distinguish process
success, evaluation validity, and represented scientific results. Preserve
metadata/abstract limitations, planned language, missing evidence, and exact
Experiment limitations. Audit method/result consistency and bounded
reproducibility only to the supplied evidence.

Create memory/review-result.json containing exactly assessment, summary, issues,
limitations. assessment is exactly NO_BLOCKING_ISSUES, REVISION_REQUIRED, or
INSUFFICIENT_EVIDENCE. Each issue contains exactly issue_id, category, severity,
target, summary, evidence_refs, recommended_action, blocking. target contains
exactly section and nullable claim_id. Use only declared categories and
MAJOR/MINOR. Evidence refs use exactly artifact_id, artifact_type, sha256,
evidence_item, location, availability, limitation and may identify only the
bound manuscript/supporting Artifacts. Their availability is exactly AVAILABLE,
LIMITED, or UNAVAILABLE; translate SCOPE_LIMITED source availability to LIMITED
while preserving its limitation. Anchor seeded inconsistencies to actual
claims/sections. recommended_action is revision guidance, not rewritten prose.
Also create a concise human rendering at outputs/review.md, but the typed JSON is
authority. Never invent external sources, say ACCEPT/REJECT/WEAK_ACCEPT, predict
publication, or emit a numeric scientific score. The runner will validate and
obtain exact Owner review before publication."""


def _run_harness(root: Path, executable: str, instruction: str) -> None:
    command = [
        executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C", str(root), instruction,
    ]
    try:
        completed = subprocess.run(command, cwd=root, env=_codex_environment(), check=False)
    except OSError as error:
        raise RealReviewError("Codex process could not be started") from error
    if completed.returncode != 0:
        raise RealReviewError("Codex exited before completing the current Review stage")


def _load_inputs(root: Path) -> tuple[dict[str, dict[str, str]], dict[str, Any], dict[str, Any]]:
    _, sources, values = _validator(root)["_input_state"](root)
    return sources, values["manuscript"], values


def _prepare_availability(root: Path, manuscript: dict[str, Any], sources: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    availability = _validator(root)["derive_evidence_availability"](manuscript, sources)
    _atomic_json(root / "memory/evidence-availability.json", availability)
    return availability


def _load_scope(root: Path, sources: dict[str, dict[str, str]]) -> tuple[dict[str, Any], str]:
    namespace = _validator(root)
    manuscript_ref = sources["manuscript"]
    support = namespace["supporting_refs"](sources)
    scope = namespace["validate_review_scope"](
        _object(root / "memory/review-scope.json", "Review Scope"),
        manuscript_ref, support,
    )
    return scope, canonical_hash(scope)


def _approve_scope(
    root: Path, scope: dict[str, Any], scope_sha: str,
    sources: dict[str, dict[str, str]], approval_input: Callable[[str], str],
) -> dict[str, Any]:
    path = root / "memory/scope-approval.json"
    if path.exists() or path.is_symlink():
        raise RealReviewError("a Review Scope approval already exists")
    print("\nReview Scope\n" + canonical_json(scope), flush=True)
    expected = f"approve {scope_sha}"
    if approval_input(f"Type `{expected}` to approve this exact Review Scope: ").strip() != expected:
        raise RealReviewError("Owner did not approve the exact Review Scope")
    support = _validator(root)["supporting_refs"](sources)
    payload = {
        "scope_sha256": scope_sha,
        "manuscript_sha256": sources["manuscript"]["sha256"],
        "bound_artifacts_sha256": canonical_hash(support),
        "approved_at": _timestamp(),
        "decision": "APPROVED",
    }
    approval = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, approval)
    return approval


def _verify_scope(
    root: Path, sources: dict[str, dict[str, str]], scope: dict[str, Any],
    approval: dict[str, Any],
) -> None:
    current_scope, scope_sha = _load_scope(root, sources)
    current = _object(root / "memory/scope-approval.json", "Review Scope approval")
    payload = dict(current); checksum = payload.pop("sha256", None)
    support = _validator(root)["supporting_refs"](sources)
    if current_scope != scope or current != approval or checksum != canonical_hash(payload) or any((
        current["scope_sha256"] != scope_sha,
        current["manuscript_sha256"] != sources["manuscript"]["sha256"],
        current["bound_artifacts_sha256"] != canonical_hash(support),
        current["decision"] != "APPROVED",
    )):
        raise RealReviewError("Review Scope approval or exact inputs drifted")


def _load_result(
    root: Path, sources: dict[str, dict[str, str]], manuscript: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    namespace = _validator(root)
    surface = namespace["manuscript_surface"](manuscript)
    support = namespace["supporting_refs"](sources)
    result = namespace["validate_review_result"](
        _object(root / "memory/review-result.json", "Review result"),
        manuscript_ref=sources["manuscript"], support=support, surface=surface,
    )
    rendered = root / "outputs/review.md"
    if rendered.is_symlink() or not rendered.is_file() or rendered.stat().st_nlink != 1 or not rendered.read_text(encoding="utf-8").strip():
        raise RealReviewError("human Review rendering must be one non-empty regular file")
    return result, canonical_hash(result)


def _owner_review(
    root: Path, result: dict[str, Any], result_sha: str,
    review_input: Callable[[str], str],
) -> dict[str, Any]:
    path = root / "memory/owner-review.json"
    if path.exists() or path.is_symlink():
        raise RealReviewError("an Owner Review approval already exists")
    print("\nStructured Review Result\n" + canonical_json(result), flush=True)
    expected = f"finalize {result_sha}"
    if review_input(f"Type `{expected}` after reviewing this exact issue set: ").strip() != expected:
        raise RealReviewError("Owner did not approve the exact Review result")
    payload = {"review_result_sha256": result_sha, "reviewed_at": _timestamp(), "decision": "APPROVED"}
    review = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, review)
    return review


def _publish(
    root: Path, workflow_instance_id: str, sources: dict[str, dict[str, str]],
    scope: dict[str, Any], approval: dict[str, Any],
    availability: list[dict[str, Any]], result: dict[str, Any],
    owner_review: dict[str, Any],
) -> dict[str, Any]:
    namespace = _validator(root)
    contract = _object(root / "workflow/real-review.json", "Real Review contract")
    support = namespace["supporting_refs"](sources)
    scope_wrapper = {"sha256": canonical_hash(scope), "value": scope}
    result_payload = {
        "source_manuscript": sources["manuscript"],
        "supporting_artifacts": support,
        "review_scope": scope_wrapper,
        "scope_approval": approval,
        "evidence_availability": availability,
        **result,
    }
    if owner_review["review_result_sha256"] != canonical_hash(result_payload):
        raise RealReviewError("Owner review does not bind the exact structured result")
    artifact = {
        "schema": "review-report/v2",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {
            "workflow_instance_id": workflow_instance_id,
            "capsule_id": contract["capsule_id"],
            "capsule_version": contract["capsule_version"],
            "execution_round": 1,
        },
        **result_payload,
        "owner_review": owner_review,
    }
    try:
        namespace["validate_review_report_v2"](artifact, root=root)
    except Exception as error:
        raise RealReviewError(f"review-report/v2 validation failed: {error}") from error
    content = canonical_json(artifact).encode()
    checksum = sha256_bytes(content)
    relative = "outputs/artifacts/review-report/sha256-" + checksum[7:] + ".json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content:
            raise RealReviewError("content-addressed Review Output conflicts")
    else:
        _atomic_bytes(target, content)
    current = {"relative_path": relative, "artifact_kind": "review-report/v2", "media_type": "application/json", "checksum": checksum, "size": len(content)}
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _finalize_progress(root: Path, current: dict[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    context = {
        "schema_version": "reagent.real-review-context/v0.1", "stage": "COMPLETED",
        "latest_output": current, "updated_at": _timestamp(),
    }
    _atomic_bytes(root / "memory/context.md", ("# Real Review Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode())
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
    now = _timestamp()
    draft.update({
        "started_at": draft.get("started_at") or now, "completed_at": now,
        "status": "COMPLETED",
        "completed_work": ["Approved one exact bounded Review Scope", "Produced and Owner-reviewed one structured review-report/v2"],
        "current_state": "COMPLETED",
        "next_recommended_action": "Use the exact structured issues as W2 revision input",
        "warnings": ["Review is bounded to supplied evidence and is not a publication decision"],
        "errors": [], "unresolved_questions": [],
        "continuation_instructions": ["Bind this exact review-report/v2 to W2; never infer latest Review"],
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
        raise RealReviewError("Real Review already has terminal Progress")
    sources, manuscript, values = _load_inputs(root)
    availability = _prepare_availability(root, manuscript, sources)
    executable = _codex_executable(codex_executable)
    _run_harness(root, executable, _scope_instruction())
    scope, scope_sha = _load_scope(root, sources)
    approval = _approve_scope(root, scope, scope_sha, sources, approval_input)
    _run_harness(root, executable, _audit_instruction())
    current_sources, current_manuscript, current_values = _load_inputs(root)
    _verify_scope(root, current_sources, scope, approval)
    if current_sources != sources or current_values != values or current_manuscript != manuscript:
        raise RealReviewError("exact Review inputs drifted after Scope approval")
    current_availability = _validator(root)["derive_evidence_availability"](manuscript, sources)
    if current_availability != availability or json.loads((root / "memory/evidence-availability.json").read_text()) != availability:
        raise RealReviewError("Review evidence availability drifted")
    result, _ = _load_result(root, sources, manuscript)
    result_payload = {
        "source_manuscript": sources["manuscript"],
        "supporting_artifacts": _validator(root)["supporting_refs"](sources),
        "review_scope": {"sha256": canonical_hash(scope), "value": scope},
        "scope_approval": approval,
        "evidence_availability": availability,
        **result,
    }
    owner_review = _owner_review(root, result, canonical_hash(result_payload), review_input)
    current = _publish(root, workflow_instance_id, sources, scope, approval, availability, result, owner_review)
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
    except (RealReviewError, OSError, ValueError) as error:
        print(f"Real Review stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
