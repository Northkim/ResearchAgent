#!/usr/bin/env python3
"""Bounded real-Codex smoke for Writing/Review 0.3 interactive bootstrap."""

from __future__ import annotations

import argparse
import json
import runpy
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from backend.workflow_packages.production_workflows import (
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    build_review_scaffold_v0_3_package,
    build_writing_scaffold_v0_3_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def _materialize(capsule: Path, workflow_id: str) -> None:
    values = (
        {
            "research_idea": (
                "selected-research-idea/v1", "selected-research-idea.json",
                {"schema": "selected-research-idea/v1", "selected_idea": {
                    "title": "Synthetic bootstrap continuity",
                    "research_question": "Can a bounded first turn arrive automatically?",
                }},
            ),
            "literature_library": (
                "selected-paper-library/v1", "selected-paper-library.json",
                {"schema": "selected-paper-library/v1", "papers": []},
            ),
        }
        if workflow_id == WRITING_WORKFLOW_ID
        else {
            "manuscript": (
                "manuscript-draft/v1", "manuscript-draft.json",
                {"schema": "manuscript-draft/v1", "title": "Synthetic draft",
                 "content_markdown": "SCAFFOLD PLACEHOLDER — no substantive prose."},
            ),
        }
    )
    records = {}
    for index, (role, (artifact_type, filename, value)) in enumerate(values.items(), 1):
        content = (canonical_json(value) + "\n").encode()
        (capsule / "inputs" / filename).write_bytes(content)
        records[role] = {
            "artifact_id": "artifact-" + str(index) * 32,
            "artifact_type": artifact_type,
            "sha256": sha256_bytes(content),
            "relative_path": f"inputs/{filename}",
        }
    (capsule / "memory/input-provenance.json").write_text(
        canonical_json({
            "schema_version": "reagent.scaffold-input-provenance/v0.1",
            "workflow_instance_id": "wfi-" + "6" * 32,
            "artifacts": records,
        }) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", choices=("writing", "review"))
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args()
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        parser.error("real Codex qualification requires a controlling terminal")
    workflow_id, builder = (
        (WRITING_WORKFLOW_ID, build_writing_scaffold_v0_3_package)
        if args.workflow == "writing"
        else (REVIEW_WORKFLOW_ID, build_review_scaffold_v0_3_package)
    )
    with tempfile.TemporaryDirectory(
        prefix=f".reagent-real-{args.workflow}-codex-", dir=Path.cwd()
    ) as temporary:
        package = builder(
            project_id="project-" + "6" * 32,
            project_name=f"Synthetic {args.workflow.title()} Codex smoke",
            research_topic="Synthetic bounded bootstrap qualification",
            output_root=Path(temporary) / args.workflow,
            package_id=f"{args.workflow}-synthetic-real-codex-v0.3",
        )
        capsule = package.package_root
        _materialize(capsule, workflow_id)
        namespace = runpy.run_path(str(capsule / "reagent_local.py"))
        namespace["preflight"](capsule)
        try:
            namespace["_run_harness"](
                capsule, namespace["_codex_executable"](args.codex)
            )
        except Exception as error:
            if f"Owner interrupted the {args.workflow.title()} scaffold" not in str(error):
                raise
        print(json.dumps({
            "ok": True,
            "real_codex": True,
            "workflow": args.workflow,
            "result": "bounded INPUT_REVIEW observed and exited",
            "owner_data": False,
            "provider_calls": 0,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
