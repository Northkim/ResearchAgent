#!/usr/bin/env python3
"""Deterministic prompt-enforcing Harness for Experiment 0.4 qualification."""

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
        print("Experiment fixture received a prohibited secret environment", file=sys.stderr)
        return 9
    if not arguments or arguments[-1].startswith("-"):
        print("Experiment fixture requires a ReAgent initial prompt", file=sys.stderr)
        return 10
    prompt = arguments[-1]
    required = (
        "Reproduction & Experiment", "INPUT_REVIEW", "SCAFFOLD_CORE",
        "IDEA_EXPERIMENT", "PAPER_REPRODUCTION", "PLACEHOLDER_NOT_EXECUTED",
        "actual_results null", "workflow/prompts/reproduction-experiment.md",
        "inputs/selected-research-idea.json", "memory/resource-provenance.json",
    )
    if any(term not in prompt for term in required):
        print("Experiment fixture received an incomplete initial prompt", file=sys.stderr)
        return 11
    options = (
        "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C",
    )
    if any(option not in arguments for option in options):
        print("Experiment fixture received an unsafe interactive invocation", file=sys.stderr)
        return 12

    root = Path.cwd()
    idea = json.loads((root / "inputs/selected-research-idea.json").read_text())
    resources = json.loads((root / "memory/resource-provenance.json").read_text())
    selected = idea["selected_idea"]
    configured = [
        item["requirement_key"]
        for item in resources["requirements"] if item["configured"]
    ]
    missing = [
        item["requirement_key"]
        for item in resources["requirements"] if not item["configured"]
    ]
    print("REAGENT REPRODUCTION & EXPERIMENT — INPUT_REVIEW", flush=True)
    print("Current capability: SCAFFOLD_CORE", flush=True)
    print(f"Loaded research idea: {selected['title']}", flush=True)
    print(f"Configured Resources: {', '.join(configured) if configured else 'none'}", flush=True)
    print(f"Unconfigured Resources: {', '.join(missing)}", flush=True)
    print("Supported mode: IDEA_EXPERIMENT", flush=True)
    print("Paper reproduction: NOT_YET_ENABLED", flush=True)
    print(
        "No Resource bytes, simulation, model training, metrics, or scientific "
        "results will be executed or fabricated.",
        flush=True,
    )
    print(
        "The final experiment-record/v1 remains PLACEHOLDER_NOT_EXECUTED with "
        "actual_results null.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
