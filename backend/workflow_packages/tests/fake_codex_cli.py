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


def update_control(root: Path, **changes) -> None:
    path = root / "memory/round-control.json"
    control = json.loads(path.read_text())
    control.update(changes)
    control["updated_at"] = "2026-08-06T02:01:00Z"
    write_json(path, control)


def plan(root: Path) -> None:
    topic = json.loads((root / "inputs/research_request.json").read_text())["topic"]
    (root / "outputs/search_plan.md").write_text(
        f"""# Search plan — FICTIONAL DEMO EVIDENCE

## Interpreted topic
{topic}
## Concepts and synonyms
transparent continuity; portable local state
## Query variants
Two bounded fictional variants.
## Search bounds
Two calls; five results per call; fifteen retained maximum.
## Screening rules
Include direct topical connection; record every exclusion.
## Evidence limitations
Fictional metadata and available abstracts only; no full text.
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
                    "openalex_id": None,
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
        {"schema_version": "candidate-papers/v0.2", "mode": "DEMO", "candidates": candidates},
    )
    selected = candidates[:3]
    write_json(
        root / "outputs/selected_papers.json",
        {
            "schema_version": "selected-papers/v0.2",
            "mode": "DEMO",
            "selection_status": "SUFFICIENT",
            "selected": [
                {
                    "candidate_id": item["candidate_id"],
                    "relevance_decision": "INCLUDE",
                    "inclusion_reason": "Fictional metadata directly matches the demonstration topic.",
                    "evidence_availability": "METADATA_ONLY",
                }
                for item in selected
            ],
            "exclusions": [
                {"candidate_id": item["candidate_id"], "reason": "Outside the bounded representative set."}
                for item in candidates[3:]
            ],
            "exclusion_summary": "Two fictional duplicates were screened outside the representative set.",
        },
    )
    (root / "outputs/literature_search_report.md").write_text(
        """# FICTIONAL DEMO EVIDENCE — Literature search report

## Executive summary
Three fictional records illustrate the completed local flow.
## Search coverage
Two bounded fictional queries returned five deduplicated candidates.
## Main research themes
Transparent continuity and portable research state.
## Common methods
Metadata-only comparison.
## Representative works
Three fictional demonstration records.
## Trends
Local-first research handoffs.
## Limitations
Fictional metadata and abstract-only scope; no full text was read.
## Potential research gaps
Real topical evidence remains necessary in normal mode.
## Recommended next research action
Run a separately authorized normal OpenAlex round.
## Selected-paper references
The first three fictional candidate identities in selected_papers.json.
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
            "next_action": "Review fictional demo outputs.",
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
            "current_state": "FICTIONAL DEMO EVIDENCE: three representative records selected.",
            "next_recommended_action": "Review local outputs; use normal mode only with explicit authorization.",
            "warnings": ["FICTIONAL DEMO EVIDENCE; metadata and abstract-only scope; no full text."],
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


def interactive(root: Path) -> None:
    delay = float(os.environ.get("REAGENT_FAKE_CODEX_DELAY_SECONDS", "0"))
    print("CHECKPOINT: SEARCH PLAN", flush=True)
    print("Interpretation, two bounded queries, screening rules, metadata/abstract-only.", flush=True)
    print("Type proceed, request a revision, or abort safely.", flush=True)
    read_until("proceed")
    if delay:
        time.sleep(delay)
    plan(root)
    mark_plan_confirmed(root)
    print("Search plan confirmed; waiting for bounded Provider metadata.", flush=True)
    wait_for_state(root, "SEARCH_COMPLETED")
    print("CHECKPOINT: CANDIDATE SCREENING", flush=True)
    print("Retrieved 10; deduplicated 5; likely relevant 3; uncertain 1; excluded 1.", flush=True)
    print("Themes: transparent continuity and portable local state. Type continue.", flush=True)
    read_until("continue")
    print("CHECKPOINT: FINALIZATION", flush=True)
    print("Four local outputs; three selected; bounded summary uploads; libraries stay local.", flush=True)
    print("Type finish to finalize the round.", flush=True)
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
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
