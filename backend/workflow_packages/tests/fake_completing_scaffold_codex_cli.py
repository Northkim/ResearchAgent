#!/usr/bin/env python3
"""Codex-compatible fixture that performs the bundled Agent finalization."""

from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if args == ["--version"]:
        print("codex 0.0.0-scaffold-completion-fixture")
        return 0
    if args == ["--help"]:
        print("--sandbox --ask-for-approval --no-alt-screen --cd")
        return 0
    if args == ["login", "status"]:
        print("Logged in")
        return 0
    prompt = args[-1] if args else ""
    if "INPUT_REVIEW" not in prompt or "SCAFFOLD_CORE" not in prompt:
        print("fixture requires the bounded ReAgent positional prompt", file=sys.stderr)
        return 10
    root = Path.cwd()
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    finalized = subprocess.run(
        [sys.executable, "reagent_local.py", "finalize-scaffold", "."],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if finalized.returncode != 0:
        print(finalized.stdout, file=sys.stderr)
        print(finalized.stderr, file=sys.stderr)
        return 11
    config = json.loads(
        (root / "workflow/scaffold.json").read_text(encoding="utf-8")
    )
    print(prompt.splitlines()[0])
    print("Current capability: SCAFFOLD_CORE")
    if config["workflow_kind"] == "WRITING":
        provenance = json.loads(
            (root / "memory/input-provenance.json").read_text(encoding="utf-8")
        )
        print(
            "Revision round: "
            + ("yes" if "prior_manuscript" in provenance["artifacts"] else "no")
        )
    if config["workflow_kind"] == "EXPERIMENT":
        print("Paper reproduction: NOT_YET_ENABLED")
    print("Fixture completed one Agent-owned Progress round")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
