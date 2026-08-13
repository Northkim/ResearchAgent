#!/usr/bin/env python3
"""Bounded real-Codex smoke for Experiment 0.4 interactive bootstrap.

This operator-only helper creates synthetic local state, launches the real
Codex CLI in the caller's terminal, and makes no Provider or Resource call.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
import tempfile
from pathlib import Path

from backend.workflow_packages.production_workflows import (
    build_experiment_scaffold_v0_4_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args()
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        parser.error("real Codex qualification requires a controlling terminal")
    with tempfile.TemporaryDirectory(
        prefix="reagent-real-experiment-codex-"
    ) as temporary:
        root = Path(temporary)
        package = build_experiment_scaffold_v0_4_package(
            project_id="project-" + "9" * 32,
            project_name="Synthetic Experiment Codex bootstrap smoke",
            research_topic="Synthetic multi-agent stress testing",
            output_root=root / "experiment",
            package_id="experiment-synthetic-real-codex-v0.4",
        )
        capsule = package.package_root
        idea = {
            "schema": "selected-research-idea/v1",
            "selected_idea": {
                "idea_id": "idea-003",
                "title": "Stress-testing multi-agent control",
                "research_question": "How can multi-agent control be stress-tested?",
            },
        }
        content = (canonical_json(idea) + "\n").encode()
        (capsule / "inputs/selected-research-idea.json").write_bytes(content)
        (capsule / "memory/input-provenance.json").write_text(
            canonical_json({
                "schema_version": "reagent.scaffold-input-provenance/v0.1",
                "workflow_instance_id": "wfi-" + "9" * 32,
                "artifacts": {
                    "research_idea": {
                        "artifact_id": "artifact-" + "9" * 32,
                        "artifact_type": "selected-research-idea/v1",
                        "sha256": sha256_bytes(content),
                        "relative_path": "inputs/selected-research-idea.json",
                    }
                },
            }) + "\n",
            encoding="utf-8",
        )
        resources = json.loads(
            (capsule / "memory/resource-provenance.json").read_text()
        )
        resources["workflow_instance_id"] = "wfi-" + "9" * 32
        (capsule / "memory/resource-provenance.json").write_text(
            canonical_json(resources) + "\n", encoding="utf-8"
        )
        namespace = runpy.run_path(str(capsule / "reagent_local.py"))
        namespace["preflight"](capsule)
        try:
            namespace["_run_harness"](
                capsule, namespace["_codex_executable"](args.codex)
            )
        except Exception as error:
            if "Owner interrupted the Experiment scaffold" not in str(error):
                raise
        print(json.dumps({
            "ok": True,
            "real_codex": True,
            "result": "bounded Experiment INPUT_REVIEW observed and exited",
            "owner_data": False,
            "provider_calls": 0,
            "resource_execution": False,
        }, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
