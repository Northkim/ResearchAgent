#!/usr/bin/env python3
"""Bounded real-Codex smoke for the Idea interactive bootstrap.

This operator-only helper builds synthetic local state and launches the real
Codex CLI in the caller's controlling terminal for bounded observation. It
never uses owner research bytes or a Provider.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
import tempfile
from pathlib import Path

from backend.workflow_packages.production_workflows import (
    build_idea_discovery_v0_3_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
from backend.workflow_packages.tests.test_f1a_selected_idea import (
    _materialize_literature,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args()
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        parser.error("real Codex qualification requires a controlling terminal")
    with tempfile.TemporaryDirectory(prefix="reagent-real-idea-codex-") as temporary:
        root = Path(temporary)
        package = build_idea_discovery_v0_3_package(
            project_id="project-" + "9" * 32,
            project_name="Synthetic real Codex bootstrap smoke",
            research_topic="Durable local research continuity",
            output_root=root / "idea",
            package_id="idea-discovery-synthetic-real-codex-v0.3",
        )
        capsule = package.package_root
        _materialize_literature(root, capsule)
        input_path = capsule / "inputs/selected-paper-library.json"
        (capsule / "outputs/candidate_ideas.json").write_text(
            canonical_json({
                "schema": "candidate-ideas/v0.1",
                "source_artifact": {
                    "artifact_id": "artifact-" + "9" * 32,
                    "artifact_type": "selected-paper-library/v1",
                    "sha256": sha256_bytes(input_path.read_bytes()),
                },
                "ideas": [],
            }) + "\n",
            encoding="utf-8",
        )
        namespace = runpy.run_path(str(capsule / "reagent_local.py"))
        namespace["_prepare_draft"](capsule, stage="INPUT_REVIEW")

        try:
            namespace["_run_harness"](
                capsule, namespace["_codex_executable"](args.codex)
            )
        except Exception as error:
            if "Owner interrupted Idea Discovery" not in str(error):
                raise
        print(json.dumps({
            "ok": True,
            "real_codex": True,
            "result": "bounded session observed and exited",
            "owner_data": False,
            "provider_calls": 0,
        }, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
