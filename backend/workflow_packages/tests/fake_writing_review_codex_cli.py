#!/usr/bin/env python3
"""Prompt-enforcing Harness for Writing/Review interactive qualification."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


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
    prohibited = (
        "REAGENT_OPENALEX_API_KEY", "OPENALEX_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL",
    )
    if any(key in os.environ for key in prohibited):
        print("Scaffold fixture received a prohibited secret", file=sys.stderr)
        return 9
    if not arguments or arguments[-1].startswith("-"):
        print("Scaffold fixture requires a ReAgent initial prompt", file=sys.stderr)
        return 10
    for option in (
        "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C",
    ):
        if option not in arguments:
            print("Scaffold fixture received an unsafe invocation", file=sys.stderr)
            return 12

    prompt = arguments[-1]
    root = Path.cwd()
    provenance = json.loads((root / "memory/input-provenance.json").read_text())
    records = provenance["artifacts"]
    if "REAGENT WRITING — INPUT_REVIEW" in prompt:
        required = (
            "Writing Workflow", "INPUT_REVIEW", "SCAFFOLD_CORE",
            "workflow/prompts/writing.md", "inputs/selected-research-idea.json",
            "inputs/selected-paper-library.json", "Artifact ID and checksum",
            "publication-quality", "manuscript-draft/v1",
        )
        if any(term not in prompt for term in required):
            print("Writing fixture received an incomplete prompt", file=sys.stderr)
            return 11
        print("REAGENT WRITING — INPUT_REVIEW", flush=True)
        print("Current capability: SCAFFOLD_CORE", flush=True)
        print("Loaded evidence:", flush=True)
        for role, value in sorted(records.items()):
            print(f"- {role}: {value['artifact_id']} {value['sha256']}", flush=True)
        revision = {"prior_manuscript", "review_feedback"}.issubset(records)
        print(f"Revision round: {'yes' if revision else 'no'}", flush=True)
        print(
            "This version will not create a substantive publication-ready manuscript.",
            flush=True,
        )
        print("It will publish only the bounded SCAFFOLD PLACEHOLDER.", flush=True)
        return 0
    if "REAGENT REVIEW — INPUT_REVIEW" in prompt:
        required = (
            "Review Workflow", "INPUT_REVIEW", "SCAFFOLD_CORE",
            "workflow/prompts/review.md", "inputs/manuscript-draft.json",
            "Artifact ID", "peer review", "acceptance/rejection judgment",
            "INSUFFICIENT_EVIDENCE",
        )
        if any(term not in prompt for term in required):
            print("Review fixture received an incomplete prompt", file=sys.stderr)
            return 11
        manuscript = records["manuscript"]
        print("REAGENT REVIEW — INPUT_REVIEW", flush=True)
        print("Current capability: SCAFFOLD_CORE", flush=True)
        print(
            f"Loaded manuscript: {manuscript['artifact_id']} {manuscript['sha256']}",
            flush=True,
        )
        supporting = sorted(set(records) - {"manuscript"})
        print(
            f"Supporting evidence: {', '.join(supporting) if supporting else 'none'}",
            flush=True,
        )
        print("No substantive peer review or acceptance judgment will occur.", flush=True)
        print(
            "The bounded SCAFFOLD REVIEW PLACEHOLDER uses INSUFFICIENT_EVIDENCE.",
            flush=True,
        )
        return 0
    print("Scaffold fixture did not receive a supported ReAgent prompt", file=sys.stderr)
    return 11


if __name__ == "__main__":
    raise SystemExit(main())
