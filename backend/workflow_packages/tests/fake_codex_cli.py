#!/usr/bin/env python3
"""Deterministic Codex-equivalent used only by the no-network LS1 E2E."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum(value) -> str:
    content = value if isinstance(value, bytes) else canonical(value).encode()
    return "sha256:" + hashlib.sha256(content).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(canonical(value) + "\n", encoding="utf-8")


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


def main() -> int:
    instruction = sys.argv[-1]
    root = Path.cwd()
    if "PLANNING_STAGE" in instruction:
        plan(root)
    elif "SYNTHESIS_STAGE" in instruction:
        synthesize(root)
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
