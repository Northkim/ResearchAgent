#!/usr/bin/env python3
"""Self-contained runner for one bounded Review-to-Writing revision round."""

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


class WritingRevisionError(RuntimeError):
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
        raise WritingRevisionError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WritingRevisionError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise WritingRevisionError(f"{label} must be an object")
    return value


def _array(path: Path, label: str) -> list[Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise WritingRevisionError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WritingRevisionError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, list):
        raise WritingRevisionError(f"{label} must be an array")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise WritingRevisionError("output parent is unsafe")
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name); handle.write(content); handle.flush(); os.fsync(handle.fileno())
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
        raise WritingRevisionError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise WritingRevisionError("Capsule validation failed closed")


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise WritingRevisionError("configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise WritingRevisionError("Codex CLI is unavailable")
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
    return """REAGENT WRITING REVISION — ISSUE RECONCILIATION AND REVISION PLAN

Read AGENT.md, workflow/prompts/writing-revision.md,
workflow/writing-revision.json, memory/input-provenance.json, and only the exact
materialized inputs declared there. Do not inspect sibling Capsules or use network.

Verify that review-report/v2 names the exact prior manuscript-draft/v2. This pass
MUST NOT revise prose. Create only memory/revision-plan.json as a JSON array using
the exact descriptor fields. Include every causal Review issue exactly once and no
invented issue. Use only ADDRESSED, PARTIALLY_ADDRESSED, NOT_ADDRESSED. A Review
request creates no evidence; use evidence_to_use only from exact supporting input
provenance, in the seven-field evidence-reference shape. Partial/unaddressed plans
must state known_limitation. The runner will show this exact plan and obtain durable
Owner approval after you exit."""


def _phase_two_instruction() -> str:
    return """REAGENT WRITING REVISION — DRAFT REVISION AND EVIDENCE RECHECK

Read the exact prior Draft, causal Review, supporting inputs,
memory/revision-plan.json, and immutable memory/revision-plan-approval.json. Do
not alter the plan or inputs. Revise the prior manuscript rather than generating
an unrelated paper. Write outputs/revised-draft.md, memory/claims.json,
memory/citations.json, and memory/issue-accounting.json using exact descriptor
shapes. Account for every Review issue exactly once. PARTIALLY_ADDRESSED and
NOT_ADDRESSED require remaining_limitation. Do not call an issue resolved.

Preserve the prior Writing Brief, supported content, exact source identities, and
W1 truth rules. SUPPORTED claims require exact bound evidence; PLANNED stays
proposal/future language; UNAVAILABLE never becomes fact. A Review request does
not create evidence. Citations stay within the exact selected paper library and
observed results still require valid experiment-record/v2. Revise only within the
approved plan, recheck claims/citations, and leave finalization to the runner."""


def _run_harness(root: Path, executable: str, instruction: str) -> None:
    command = [
        executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C", str(root), instruction,
    ]
    try:
        completed = subprocess.run(command, cwd=root, env=_codex_environment(), check=False)
    except OSError as error:
        raise WritingRevisionError("Codex process could not be started") from error
    if completed.returncode != 0:
        raise WritingRevisionError("Codex exited before completing the revision stage")


def _load_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    _, inputs, prior, review, library, experiment = _validator(root)["_input_state"](root)
    sources = {key: inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in inputs}
    return inputs, prior, review, library, experiment


def _load_plan(root: Path, review: dict[str, Any], sources: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    namespace = _validator(root)
    plan = namespace["validate_revision_plan"](
        _array(root / "memory/revision-plan.json", "Revision Plan"), review["issues"], sources,
    )
    return plan, canonical_hash(plan)


def _approve_plan(
    root: Path, inputs: dict[str, Any], review: dict[str, Any], sources: dict[str, Any],
    plan: list[dict[str, Any]], plan_sha: str, approval_input: Callable[[str], str],
) -> dict[str, Any]:
    path = root / "memory/revision-plan-approval.json"
    if path.exists() or path.is_symlink():
        raise WritingRevisionError("a Revision Plan approval already exists")
    print("\nRevision Plan\n" + canonical_json(plan), flush=True)
    expected = f"approve {plan_sha}"
    if approval_input(f"Type `{expected}` to approve this exact Revision Plan: ").strip() != expected:
        raise WritingRevisionError("Owner did not approve the exact Revision Plan")
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if key in sources]
    payload = {
        "prior_manuscript_sha256": inputs["prior_manuscript"]["sha256"],
        "causal_review_sha256": inputs["causal_review"]["sha256"],
        "issue_set_sha256": canonical_hash(review["issues"]),
        "revision_plan_sha256": plan_sha,
        "supporting_artifacts_sha256": canonical_hash(support),
        "approved_at": _timestamp(), "decision": "APPROVED",
    }
    approval = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, approval)
    return approval


def _verify_plan_approval(
    root: Path, inputs: dict[str, Any], review: dict[str, Any], sources: dict[str, Any],
    plan: list[dict[str, Any]], approval: dict[str, Any],
) -> None:
    current = _object(root / "memory/revision-plan-approval.json", "Revision Plan approval")
    payload = dict(current); checksum = payload.pop("sha256", None)
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if key in sources]
    if current != approval or checksum != canonical_hash(payload) or any((
        current["prior_manuscript_sha256"] != inputs["prior_manuscript"]["sha256"],
        current["causal_review_sha256"] != inputs["causal_review"]["sha256"],
        current["issue_set_sha256"] != canonical_hash(review["issues"]),
        current["revision_plan_sha256"] != canonical_hash(plan),
        current["supporting_artifacts_sha256"] != canonical_hash(support),
        current["decision"] != "APPROVED",
    )):
        raise WritingRevisionError("Revision Plan approval or exact inputs drifted")


def _title(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    raise WritingRevisionError("revised draft must begin with a level-one title")


def _load_revision(
    root: Path, review: dict[str, Any], sources: dict[str, Any],
    library: dict[str, Any], experiment: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    path = root / "outputs/revised-draft.md"
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise WritingRevisionError("revised draft must be one regular unlinked Markdown file")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise WritingRevisionError("revised draft is empty")
    namespace = _validator(root)
    citations = namespace["validate_citations"](_array(root / "memory/citations.json", "citations"), sources, library)
    claims = namespace["validate_claims"](_array(root / "memory/claims.json", "claims"), sources, citations, experiment)
    accounting = namespace["validate_issue_accounting"](
        _array(root / "memory/issue-accounting.json", "issue accounting"),
        review["issues"], {item["claim_id"] for item in claims},
    )
    draft_sha = canonical_hash({
        "title": _title(content), "content_markdown": content,
        "claims": claims, "citations": citations,
    })
    return content, claims, citations, accounting, draft_sha


def _owner_review(
    root: Path, content: str, accounting: list[dict[str, Any]], draft_sha: str,
    review_input: Callable[[str], str],
) -> dict[str, Any]:
    path = root / "memory/owner-review.json"
    if path.exists() or path.is_symlink():
        raise WritingRevisionError("an Owner revision review already exists")
    print("\nRevised Manuscript\n" + content, flush=True)
    print("\nIssue Accounting\n" + canonical_json(accounting), flush=True)
    expected = f"finalize {draft_sha}"
    if review_input(f"Type `{expected}` after reviewing this exact revision: ").strip() != expected:
        raise WritingRevisionError("Owner did not approve the exact revised draft")
    payload = {
        "revised_draft_sha256": draft_sha,
        "issue_accounting_sha256": canonical_hash(accounting),
        "reviewed_at": _timestamp(), "decision": "APPROVED",
    }
    review = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(path, review)
    return review


def _publish(
    root: Path, workflow_instance_id: str, inputs: dict[str, Any],
    prior: dict[str, Any], review_report: dict[str, Any], sources: dict[str, Any],
    plan: list[dict[str, Any]], approval: dict[str, Any], content: str,
    claims: list[dict[str, Any]], citations: list[dict[str, Any]],
    accounting: list[dict[str, Any]], owner_review: dict[str, Any],
) -> dict[str, Any]:
    contract = _object(root / "workflow/writing-revision.json", "Writing Revision contract")
    disposition = {item["issue_id"]: item["disposition"] for item in accounting}
    remaining = [
        issue["issue_id"] for issue in review_report["issues"]
        if issue["blocking"] and disposition[issue["issue_id"]] != "ADDRESSED"
    ]
    support = [sources[key] for key in ("research_idea", "literature_library", "experiment_record") if key in sources]
    artifact = {
        "schema": "manuscript-draft/v3", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {
            "workflow_instance_id": workflow_instance_id,
            "capsule_id": contract["capsule_id"], "capsule_version": contract["capsule_version"],
            "execution_round": 1,
        },
        "prior_manuscript": inputs["prior_manuscript"],
        "causal_review": inputs["causal_review"], "supporting_artifacts": support,
        "revision_round": 1, "writing_brief": prior["writing_brief"],
        "title": _title(content), "content_markdown": content,
        "claims": claims, "citations": citations,
        "experiment_evidence_available": "experiment_record" in sources,
        "unsupported_areas": sorted({item["section"] for item in claims if item["support_status"] == "UNAVAILABLE"}),
        "limitations": list(prior.get("limitations", [])) + [
            "Revision used only exact bound Artifacts; no new evidence was acquired.",
            "Mechanical revision validation does not establish scientific correctness.",
        ],
        "revision_plan": {"sha256": canonical_hash(plan), "value": plan},
        "revision_plan_approval": approval, "issue_accounting": accounting,
        "remaining_blocking_issue_ids": remaining,
        "remaining_blocking_issue_count": len(remaining),
        "revision_limitations": [item["remaining_limitation"] for item in accounting if item["remaining_limitation"] is not None],
        "owner_review": owner_review,
    }
    try:
        _validator(root)["validate_manuscript_draft_v3"](artifact, root=root)
    except Exception as error:
        raise WritingRevisionError(f"manuscript-draft/v3 validation failed: {error}") from error
    content_bytes = canonical_json(artifact).encode(); checksum = sha256_bytes(content_bytes)
    relative = "outputs/artifacts/manuscript-draft/sha256-" + checksum[7:] + ".json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content_bytes:
            raise WritingRevisionError("content-addressed revision Output conflicts")
    else:
        _atomic_bytes(target, content_bytes)
    current = {"relative_path": relative, "artifact_kind": "manuscript-draft/v3", "media_type": "application/json", "checksum": checksum, "size": len(content_bytes)}
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _finalize_progress(root: Path, current: dict[str, Any], remaining_count: int) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py")); snapshot = namespace["snapshot"](root)
    context = {"schema_version": "reagent.writing-revision-context/v0.1", "stage": "COMPLETED", "latest_output": current, "updated_at": _timestamp()}
    _atomic_bytes(root / "memory/context.md", ("# Writing Revision Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode())
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft"); now = _timestamp()
    draft.update({
        "started_at": draft.get("started_at") or now, "completed_at": now,
        "status": "COMPLETED", "completed_work": [
            "Approved one exact issue-complete Revision Plan",
            "Produced and Owner-reviewed one validated manuscript-draft/v3",
        ], "current_state": "COMPLETED",
        "next_recommended_action": "Inspect remaining blocking issues before any future Review round",
        "warnings": [f"{remaining_count} blocking Review issue(s) remain after this completed revision pass"],
        "errors": [], "unresolved_questions": [],
        "continuation_instructions": ["Use exact v3 lineage; do not treat Writing disposition as Review resolution"],
    })
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    report = namespace["finalize"](package_root=root, draft_path="memory/progress/report-draft.json", context_before_checksum=snapshot["context_before_checksum"])
    return "memory/progress/reports/" + report["report_id"] + ".json"


def run(
    root: Path, workflow_instance_id: str, *, codex_executable: str | None = None,
    approval_input: Callable[[str], str] = input,
    review_input: Callable[[str], str] = input,
) -> dict[str, Any]:
    root = root.resolve(); _validate_package(root)
    if list((root / "memory/progress/reports").glob("*.json")):
        raise WritingRevisionError("Writing Revision already has terminal Progress")
    inputs, prior, review, library, experiment = _load_inputs(root)
    sources = {key: inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in inputs}
    executable = _codex_executable(codex_executable)
    _run_harness(root, executable, _phase_one_instruction())
    plan, plan_sha = _load_plan(root, review, sources)
    approval = _approve_plan(root, inputs, review, sources, plan, plan_sha, approval_input)
    _run_harness(root, executable, _phase_two_instruction())
    current_inputs, current_prior, current_review, current_library, current_experiment = _load_inputs(root)
    current_sources = {key: current_inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in current_inputs}
    current_plan, _ = _load_plan(root, current_review, current_sources)
    _verify_plan_approval(root, current_inputs, current_review, current_sources, current_plan, approval)
    if (current_inputs, current_prior, current_review, current_library, current_experiment) != (inputs, prior, review, library, experiment):
        raise WritingRevisionError("exact revision inputs drifted after plan approval")
    content, claims, citations, accounting, draft_sha = _load_revision(root, review, sources, library, experiment)
    owner = _owner_review(root, content, accounting, draft_sha, review_input)
    current = _publish(root, workflow_instance_id, inputs, prior, review, sources, plan, approval, content, claims, citations, accounting, owner)
    remaining_count = sum(1 for issue in review["issues"] if issue["blocking"] and next(item for item in accounting if item["issue_id"] == issue["issue_id"])["disposition"] != "ADDRESSED")
    report = _finalize_progress(root, current, remaining_count); _validate_package(root)
    return {"status": "COMPLETED", "artifact": current, "progress_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python reagent_local.py")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run"); run_parser.add_argument("root", type=Path)
    run_parser.add_argument("--workflow-instance", required=True); run_parser.add_argument("--api-url")
    run_parser.add_argument("--codex-executable"); run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(); _validate_package(root)
        if args.preflight_only:
            _load_inputs(root); print(canonical_json({"status": "PREFLIGHT_READY"}))
        else:
            print(canonical_json(run(root, args.workflow_instance, codex_executable=args.codex_executable)))
    except (WritingRevisionError, OSError, ValueError) as error:
        print(f"Writing Revision stopped: {error}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
