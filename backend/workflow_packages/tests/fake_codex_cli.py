#!/usr/bin/env python3
"""Deterministic terminal-attached Codex fixture for no-network LS2 tests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum(value) -> str:
    content = value if isinstance(value, bytes) else canonical(value).encode()
    return "sha256:" + hashlib.sha256(content).hexdigest()


def file_checksum(path: Path) -> str:
    return checksum(path.read_bytes())


def write_json(path: Path, value) -> None:
    temporary = path.with_name(f".{path.name}.fixture.tmp")
    temporary.write_text(canonical(value) + "\n", encoding="utf-8")
    temporary.replace(path)


def event_log(message: str) -> None:
    path = os.environ.get("REAGENT_FAKE_CODEX_EVENT_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")


def update_control(root: Path, **changes) -> None:
    path = root / "memory/round-control.json"
    control = json.loads(path.read_text())
    control.update(changes)
    control["updated_at"] = "2026-08-06T02:01:00Z"
    write_json(path, control)


def execution_mode(root: Path) -> str:
    control = json.loads((root / "memory/round-control.json").read_text())
    return control.get("mode") or "DEMO"


def plan(root: Path) -> None:
    topic = json.loads((root / "inputs/research_request.json").read_text())["topic"]
    mode = execution_mode(root)
    evidence_label = (
        "FICTIONAL DEMO EVIDENCE"
        if mode == "DEMO"
        else "REAL PROVIDER METADATA"
    )
    evidence_limit = (
        "Fictional metadata and available abstracts only; no full text."
        if mode == "DEMO"
        else "OpenAlex metadata and available abstracts only; no full text or PDFs."
    )
    query_description = (
        "Two bounded fictional variants."
        if mode == "DEMO"
        else "Two bounded OpenAlex search variants."
    )
    (root / "outputs/search_plan.md").write_text(
        f"""# Search plan — {evidence_label}

## Interpreted topic
{topic}
## Concepts and synonyms
transparent continuity; portable local state
## Query variants
{query_description}
## Search bounds
Two calls; five results per call; fifteen retained maximum.
## Screening rules
Include direct topical connection; record every exclusion.
## Evidence limitations
{evidence_limit}
""",
        encoding="utf-8",
    )
    write_json(
        root / "memory/search/query_plan.json",
        {
            "schema_version": "literature-search-query-plan/v0.1",
            "status": "READY",
            "original_topic": topic,
            "queries": [
                {"query_id": "query-1", "query": topic},
                {"query_id": "query-2", "query": f"{topic} transparent evidence"},
            ],
        },
    )


def synthesize(root: Path) -> None:
    mode = execution_mode(root)
    sources = [
        json.loads(path.read_text())
        for path in sorted((root / "memory/search/operations").glob("*.result.json"))
    ]
    merged: dict[str, dict] = {}
    for source in sources:
        for paper in source["provider_data"]["papers"]:
            provider_id = paper["provider_id"]
            item = merged.setdefault(
                provider_id,
                {
                    "candidate_id": "candidate-" + hashlib.sha256(provider_id.encode()).hexdigest()[:16],
                    "provider_id": provider_id,
                    "openalex_id": (
                        paper["provider_id"] if mode == "NORMAL" else None
                    ),
                    "title": paper["title"],
                    "authors": [author["name"] for author in paper["authors"]],
                    "publication_year": paper["publication_year"],
                    "doi": paper["doi"],
                    "source": paper["publication_venue"],
                    "language": paper["language"],
                    "abstract": paper["abstract"],
                    "source_query_ids": [],
                    "provenance_checksum": paper["raw_metadata_hash"],
                    "deduplication_status": "UNIQUE",
                },
            )
            item["source_query_ids"].append(source["query_id"])
            if len(item["source_query_ids"]) > 1:
                item["deduplication_status"] = "MERGED"
    candidates = list(merged.values())
    write_json(
        root / "outputs/candidate_papers.json",
        {"schema_version": "candidate-papers/v0.2", "mode": mode, "candidates": candidates},
    )
    selected = candidates[:3]
    write_json(
        root / "outputs/selected_papers.json",
        {
            "schema_version": "selected-papers/v0.2",
            "mode": mode,
            "selection_status": "SUFFICIENT",
            "selected": [
                {
                    "candidate_id": item["candidate_id"],
                    "relevance_decision": "INCLUDE",
                    "inclusion_reason": (
                        "Normalized OpenAlex metadata directly matches the research topic."
                        if mode == "NORMAL"
                        else "Fictional metadata directly matches the demonstration topic."
                    ),
                    "evidence_availability": "METADATA_ONLY",
                }
                for item in selected
            ],
            "exclusions": [
                {"candidate_id": item["candidate_id"], "reason": "Outside the bounded representative set."}
                for item in candidates[3:]
            ],
            "exclusion_summary": "Records outside the bounded representative set were excluded.",
        },
    )
    write_json(
        root / "memory/owner-decisions.json",
        {
            "schema_version": "reagent.owner-decision-snapshot.literature/v0.1",
            "candidate_set_checksum": file_checksum(
                root / "outputs/candidate_papers.json"
            ),
            "decision_revision": 1,
            "decisions": [
                {
                    "candidate_id": item["candidate_id"],
                    "disposition": (
                        "SELECTED" if index < 3 else
                        "UNCERTAIN" if index == 3 else "EXCLUDED"
                    ),
                    "reason": (
                        "Owner retained this bounded record."
                        if index < 3 else
                        "Owner withheld this record from the selected evidence set."
                    ),
                }
                for index, item in enumerate(candidates)
            ],
        },
    )
    evidence_heading = (
        "REAL PROVIDER METADATA"
        if mode == "NORMAL"
        else "FICTIONAL DEMO EVIDENCE"
    )
    evidence_summary = (
        "Three normalized OpenAlex records support the bounded local analysis."
        if mode == "NORMAL"
        else "Three fictional records illustrate the completed local flow."
    )
    (root / "outputs/literature_search_report.md").write_text(
        f"""# {evidence_heading} — Literature search report

## Executive summary
{evidence_summary}
## Search coverage
Two bounded queries returned normalized, deduplicated candidates.
## Main research themes
Transparent continuity and portable research state.
## Common methods
Metadata-only comparison.
## Representative works
Three bounded representative records.
## Trends
Local-first research handoffs.
## Limitations
Metadata and available-abstract evidence only; no full text or PDFs were read.
## Potential research gaps
Real topical evidence remains necessary in normal mode.
## Recommended next research action
Validate novelty and feasibility with broader evidence and full-paper review.
## Selected-paper references
The first three bounded candidate identities in selected_papers.json.
""",
        encoding="utf-8",
    )
    context_path = root / "memory/context.md"
    context = json.loads(
        context_path.read_text().split("```json\n", 1)[1].split("\n```", 1)[0]
    )
    context.update(
        {
            "current_workflow_state": "COMPLETED",
            "completed_outputs": [
                "outputs/search_plan.md",
                "outputs/candidate_papers.json",
                "outputs/selected_papers.json",
                "outputs/literature_search_report.md",
            ],
            "next_action": "Review the bounded metadata outputs.",
            "updated_at": "2026-08-06T02:02:00Z",
            "context_checksum": None,
        }
    )
    context["context_checksum"] = checksum(context)
    context_path.write_text(
        "# Local Task Context\n\n```json\n" + canonical(context) + "\n```\n",
        encoding="utf-8",
    )
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text())
    draft.update(
        {
            "started_at": "2026-08-06T02:00:00Z",
            "completed_at": "2026-08-06T02:02:00Z",
            "status": "COMPLETED",
            "completed_work": [
                "Queries performed: 2",
                "Candidates retained: 5",
                "Papers selected: 3",
                "Outputs generated: 4",
            ],
            "current_state": f"{evidence_heading}: three representative records selected.",
            "next_recommended_action": "Review local outputs and validate the bounded evidence.",
            "warnings": [
                f"{evidence_heading}; metadata and available-abstract scope; no full text or PDFs."
            ],
        }
    )
    write_json(draft_path, draft)


def mark_plan_confirmed(root: Path) -> None:
    control = json.loads((root / "memory/round-control.json").read_text())
    update_control(
        root,
        state="PLAN_CONFIRMED",
        last_completed_state="PLAN_CONFIRMED",
        plan_confirmation_count=control["plan_confirmation_count"] + 1,
        query_plan_checksum=file_checksum(root / "memory/search/query_plan.json"),
        candidate_review_confirmed=False,
        finalization_confirmed=False,
        failure_code=None,
    )


def mark_finalized(root: Path) -> None:
    outputs = {
        relative: file_checksum(root / relative)
        for relative in (
            "outputs/search_plan.md",
            "outputs/candidate_papers.json",
            "outputs/selected_papers.json",
            "outputs/literature_search_report.md",
        )
    }
    update_control(
        root,
        state="FINALIZED",
        last_completed_state="FINALIZED",
        candidate_review_confirmed=True,
        finalization_confirmed=True,
        output_checksums=outputs,
        context_checksum=file_checksum(root / "memory/context.md"),
        report_draft_checksum=file_checksum(root / "memory/progress/report-draft.json"),
        failure_code=None,
    )


def read_until(expected: str) -> None:
    if os.environ.get("REAGENT_FAKE_CODEX_AUTO_CONFIRM") == "1":
        print(f"Owner input received: {expected}", flush=True)
        return
    while True:
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("interactive input closed before finalization")
        print(f"Owner input received: {line.strip()}", flush=True)
        if line.strip().casefold() == expected:
            return


def wait_for_state(root: Path, expected: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        control = json.loads((root / "memory/round-control.json").read_text())
        if control["state"] == expected:
            return
        if control["state"] == "FAILED":
            raise RuntimeError("launcher Provider controller failed")
        time.sleep(0.05)
    raise RuntimeError("launcher state transition timed out")


def wait_for_state_or_failure(root: Path, expected: str) -> str:
    """Return the observed terminal state; surfaces FAILED/INTERRUPTED without
    requiring any Owner input, mirroring the automatic-continuation contract."""

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        control = json.loads((root / "memory/round-control.json").read_text())
        if control["state"] == expected:
            return "COMPLETED"
        if control["state"] == "FAILED":
            return "FAILED"
        if control["state"] == "INTERRUPTED":
            return "INTERRUPTED"
        time.sleep(0.05)
    raise RuntimeError("launcher state transition timed out")


def interactive(root: Path) -> None:
    delay = float(os.environ.get("REAGENT_FAKE_CODEX_DELAY_SECONDS", "0"))
    control = json.loads((root / "memory/round-control.json").read_text())
    if os.environ.get("REAGENT_FAKE_CODEX_ABORT") == "1":
        update_control(
            root,
            state="INTERRUPTED",
            last_completed_state="NOT_STARTED",
            interrupted_stage="SEARCH_PLAN",
            failure_code=None,
        )
        print("Codex fixture aborted by owner before plan confirmation.", flush=True)
        return
    state = (
        control["last_completed_state"]
        if control["state"] in {"INTERRUPTED", "FAILED"}
        else control["state"]
    )
    if state == "NOT_STARTED":
        print("CHECKPOINT: SEARCH PLAN", flush=True)
        print("Interpretation, two bounded queries, screening rules, metadata/abstract-only.", flush=True)
        print("Type proceed, request a revision, or abort safely.", flush=True)
        read_until("proceed")
        if delay:
            time.sleep(delay)
        plan(root)
        mark_plan_confirmed(root)
        print("Search plan confirmed; waiting for bounded Provider metadata.", flush=True)
    elif state == "PLAN_CONFIRMED":
        print("RESUME: confirmed plan preserved; waiting for bounded Provider metadata.", flush=True)
    elif state == "SEARCH_COMPLETED":
        print("RESUME: persisted search plan and Provider results loaded without chat history.", flush=True)
    else:
        raise RuntimeError(f"fixture cannot resume from {state}")
    outcome = wait_for_state_or_failure(root, "SEARCH_COMPLETED")
    if outcome == "FAILED":
        event_log("PROVIDER_FAILURE_SURFACED")
        print(
            "Provider search failed; the bounded search did not complete. "
            "No Owner input was required to see this failure.",
            flush=True,
        )
        return
    if outcome == "INTERRUPTED":
        return
    event_log("CANDIDATE_PRESENTED_AFTER_SEARCH")
    print("CHECKPOINT: CANDIDATE SCREENING", flush=True)
    print(
        "Candidate screening complete: 10 retrieved · 5 unique · "
        "3 recommended · 1 needs review · 1 excluded",
        flush=True,
    )
    print(
        "Recommended evidence: transparent continuity (one-line reason); "
        "portable local state (one-line reason); durable checkpoints (one-line reason).",
        flush=True,
    )
    print(
        "Needs your attention: one paper with uncertain relevance to the topic.",
        flush=True,
    )
    print(
        "Coverage gap: no retrieved record directly addresses the bounded question.",
        flush=True,
    )
    print(
        "You can accept the recommendations, inspect an uncertain paper, "
        "change a decision, show excluded papers, or abort. "
        "No confirmation input is required before the finalization checkpoint.",
        flush=True,
    )
    print("CHECKPOINT: FINALIZATION", flush=True)
    print("Four local outputs; three selected; bounded summary uploads; libraries stay local.", flush=True)
    print("Type finish to finalize the round.", flush=True)
    if os.environ.get("REAGENT_FAKE_CODEX_REFUSE_FINISH") == "1":
        raise RuntimeError("fixture refused finish; no finalization may occur")
    read_until("finish")
    if os.environ.get("REAGENT_FAKE_CODEX_NONZERO") == "1":
        raise RuntimeError("fixture requested a nonzero Codex exit")
    synthesize(root)
    if os.environ.get("REAGENT_FAKE_CODEX_INVALID_ARTIFACTS") == "1":
        (root / "outputs/selected_papers.json").unlink()
    mark_finalized(root)
    print("Codex fixture finalized exactly one local round.", flush=True)


def compatibility_command(arguments: list[str]) -> int | None:
    if arguments == ["--version"]:
        print("codex-cli 0.146.0")
        return 0
    if arguments == ["login", "status"]:
        print("Logged in (deterministic test fixture)")
        return 0
    if arguments in (["--help"], ["exec", "--help"]):
        print("--sandbox --ask-for-approval --no-alt-screen --cd -C --ephemeral --skip-git-repo-check")
        return 0
    return None


def mark_plan_confirmed(root: Path) -> None:
    control = json.loads((root / "memory/round-control.json").read_text())
    control.update(
        {
            "state": "PLAN_CONFIRMED",
            "last_completed_state": "PLAN_CONFIRMED",
            "plan_confirmation_count": int(control.get("plan_confirmation_count") or 0) + 1,
            "query_plan_checksum": file_checksum(root / "memory/search/query_plan.json"),
        }
    )
    write_json(root / "memory/round-control.json", control)


def main() -> int:
    compatibility = compatibility_command(sys.argv[1:])
    if compatibility is not None:
        return compatibility
    if any(
        key in os.environ
        for key in (
            "REAGENT_PROXY_TOKEN",
            "REAGENT_LOCAL_SESSION_TOKEN",
            "REAGENT_OPENALEX_API_KEY",
            "REAGENT_DATABASE_URL",
        )
    ):
        print("Codex fixture received a prohibited secret environment", file=sys.stderr)
        return 9
    instruction = sys.argv[-1]
    root = Path.cwd()
    if "PLANNING_STAGE" in instruction:
        plan(root)
    elif "SYNTHESIS_STAGE" in instruction:
        synthesize(root)
    elif "INTERACTIVE_ONE_ROUND" in instruction:
        try:
            interactive(root)
        except KeyboardInterrupt:
            print("Codex fixture interrupted safely.", file=sys.stderr, flush=True)
            return 130
    elif "LITERATURE CHECKPOINT SYNTHESIS" in instruction:
        synthesize(root)
        owner = json.loads((root / "memory/owner-decisions.json").read_text())
        write_json(
            root / "memory/proposed-screening.json",
            {
                "schema_version": "reagent.literature-screening-proposal/v0.1",
                "decisions": owner["decisions"],
            },
        )
        (root / "memory/owner-decisions.json").unlink()
    elif "LITERATURE PLANNING - INTERACTIVE" in instruction:
        plan(root)
        mark_plan_confirmed(root)
    elif "LITERATURE SCREENING - INTERACTIVE" in instruction:
        synthesize(root)
        owner = json.loads((root / "memory/owner-decisions.json").read_text())
        write_json(
            root / "memory/proposed-screening.json",
            {
                "schema_version": "reagent.literature-screening-proposal/v0.1",
                "decisions": owner["decisions"],
            },
        )
        (root / "memory/owner-decisions.json").unlink()
    elif "LITERATURE FINALIZATION - INTERACTIVE" in instruction:
        return 0
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
