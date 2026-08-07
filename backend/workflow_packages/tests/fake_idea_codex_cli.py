#!/usr/bin/env python3
"""Deterministic no-provider Harness fixture for H1 Idea Discovery E2E."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def main() -> int:
    root = Path.cwd()
    input_path = root / "inputs/selected-paper-library.json"
    library = json.loads(input_path.read_text(encoding="utf-8"))
    output_path = root / "outputs/candidate_ideas.json"
    output = json.loads(output_path.read_text(encoding="utf-8"))
    reports = sorted((root / "memory/progress/reports").glob("prv2-*.json"))
    round_number = len(reports) + 1
    candidate_id = library["papers"][0]["candidate_id"]
    output["ideas"] = [
        {
            "idea_id": "idea-001",
            "title": "Transparent continuation for local research agents",
            "research_question": (
                "How can local research agents preserve evidence-grounded "
                "decisions across interrupted sessions?"
            ),
            "motivation": (
                "The supplied bounded literature set motivates testing durable "
                "continuation state."
            ),
            "literature_basis": [candidate_id],
            "observed_gap": (
                "The supplied papers leave a potential gap around independently "
                "verifiable session continuation."
            ),
            "proposed_direction": (
                "Evaluate checksum-bound local memory and explicit user decisions."
            ),
            "assumptions": ["The supplied metadata is sufficient for this candidate direction."],
            "risks": ["Global novelty is not established by the supplied set."],
            "validation_needed": ["Broader literature and empirical validation are required."],
            "status": "candidate" if round_number == 1 else "shortlisted",
        }
    ]
    output_path.write_text(canonical(output) + "\n", encoding="utf-8")

    (root / "outputs/idea_discovery_report.md").write_text(
        "# Idea Discovery report\n\n"
        "## Literature landscape\nThe supplied fictional records describe local research continuity.\n\n"
        "## Observed patterns\nEvidence records favor explicit, inspectable state.\n\n"
        "## Gaps / tensions\nA potential gap remains in independently verified session continuation.\n\n"
        "## Candidate research directions\nTest checksum-bound local memory with user-confirmed decisions.\n\n"
        f"## User choices\n{'Candidate retained for review.' if round_number == 1 else 'Candidate shortlisted after a new session.'}\n\n"
        "## Uncertainties\nGlobal novelty is not proven; this is a bounded inference.\n\n"
        "## Next validation needs\nBroader literature search and empirical evaluation.\n",
        encoding="utf-8",
    )

    context_path = root / "memory/context.md"
    previous = context_path.read_text(encoding="utf-8")
    marker = hashlib.sha256(previous.encode("utf-8")).hexdigest()[:12]
    context_path.write_text(
        previous.rstrip()
        + f"\n\n## H1 deterministic session {round_number}\n"
        + f"Continued from local memory marker `{marker}`. "
        + ("User review remains next.\n" if round_number == 1 else "The candidate was shortlisted.\n"),
        encoding="utf-8",
    )
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft.update(
        {
            "current_state": "CANDIDATE_IDEAS" if round_number == 1 else "USER_REVIEW",
            "completed_work": [
                "Reviewed the materialized paper library",
                "Recorded one evidence-grounded candidate direction",
            ],
            "next_recommended_action": (
                "Review the candidate direction with the user"
                if round_number == 1
                else "Refine the shortlisted direction with broader validation"
            ),
            "continuation_instructions": [
                "Read AGENT.md, memory/context.md, and existing outputs before continuing."
            ],
        }
    )
    draft_path.write_text(canonical(draft) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
