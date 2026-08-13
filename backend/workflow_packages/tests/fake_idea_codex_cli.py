#!/usr/bin/env python3
"""Deterministic no-provider Harness fixture for H1 Idea Discovery E2E."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import sys
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
    arguments = sys.argv[1:]
    if arguments == ["--version"]:
        print("codex-cli 0.100.0")
        return 0
    if arguments == ["--help"]:
        print("--sandbox --ask-for-approval --no-alt-screen --cd")
        return 0
    if arguments == ["login", "status"]:
        print("Logged in")
        return 0
    if any(
        key in os.environ
        for key in (
            "REAGENT_OPENALEX_API_KEY",
            "OPENALEX_API_KEY",
            "REAGENT_PROXY_TOKEN",
            "REAGENT_LOCAL_SESSION_TOKEN",
            "REAGENT_DATABASE_URL",
        )
    ):
        print("Idea fixture received a prohibited secret environment", file=sys.stderr)
        return 9
    if not arguments or arguments[-1].startswith("-"):
        print("Idea fixture requires a ReAgent initial prompt", file=sys.stderr)
        return 10
    prompt = arguments[-1]
    required_prompt_terms = (
        "Idea Discovery", "INPUT_REVIEW", "workflow/prompts/idea-discovery.md",
        "inputs/selected-paper-library.json", "priorities", "no full",
    )
    if any(term not in prompt for term in required_prompt_terms):
        print("Idea fixture received an incomplete initial prompt", file=sys.stderr)
        return 11
    required_options = (
        "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C",
    )
    if any(option not in arguments for option in required_options):
        print("Idea fixture received an unsafe interactive invocation", file=sys.stderr)
        return 12
    print("ReAgent Idea Discovery — INPUT_REVIEW", flush=True)
    print(
        "Reviewing the exact materialized Literature evidence before asking "
        "for owner priorities; metadata/abstract evidence only, no full text.",
        flush=True,
    )
    root = Path.cwd()
    input_path = root / "inputs/selected-paper-library.json"
    library = json.loads(input_path.read_text(encoding="utf-8"))
    output_path = root / "outputs/candidate_ideas.json"
    output = json.loads(output_path.read_text(encoding="utf-8"))
    reports = sorted((root / "memory/progress/reports").glob("prv2-*.json"))
    round_number = len(reports) + 1
    explicit_selection = os.environ.get("REAGENT_FAKE_IDEA_EXPLICIT_SELECTION") == "1"
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
            "status": (
                "selected"
                if explicit_selection
                else ("candidate" if round_number == 1 else "shortlisted")
            ),
        }
    ]
    output_path.write_text(canonical(output) + "\n", encoding="utf-8")

    (root / "outputs/idea_discovery_report.md").write_text(
        "# Idea Discovery report\n\n"
        "## Literature landscape\nThe supplied bounded records describe local research continuity.\n\n"
        "## Observed patterns\nEvidence records favor explicit, inspectable state.\n\n"
        "## Gaps / tensions\nA potential gap remains in independently verified session continuation.\n\n"
        "## Candidate research directions\nTest checksum-bound local memory with user-confirmed decisions.\n\n"
        f"## User choices\n{('The owner explicitly selected idea-001.' if explicit_selection else ('Candidate retained for review.' if round_number == 1 else 'Candidate shortlisted after a new session.'))}\n\n"
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
            "status": "COMPLETED" if explicit_selection else "IN_PROGRESS",
            "current_state": (
                "COMPLETED"
                if explicit_selection
                else ("CANDIDATE_IDEAS" if round_number == 1 else "USER_REVIEW")
            ),
            "completed_work": [
                "Reviewed the materialized paper library",
                "Recorded one evidence-grounded candidate direction",
            ],
            "next_recommended_action": (
                "Validate novelty and feasibility beyond the bounded supplied evidence"
                if explicit_selection
                else (
                    "Review the candidate direction with the user"
                    if round_number == 1
                    else "Refine the shortlisted direction with broader validation"
                )
            ),
            "continuation_instructions": [
                "Read AGENT.md, memory/context.md, and existing outputs before continuing."
            ],
        }
    )
    draft_path.write_text(canonical(draft) + "\n", encoding="utf-8")
    if os.environ.get("REAGENT_FAKE_IDEA_FINALIZE_PROGRESS") == "1":
        progress = runpy.run_path(str(root / "progress_report.py"))
        progress["finalize"](
            package_root=root,
            draft_path="memory/progress/report-draft.json",
            context_before_checksum="sha256:" + hashlib.sha256(
                previous.encode("utf-8")
            ).hexdigest(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
