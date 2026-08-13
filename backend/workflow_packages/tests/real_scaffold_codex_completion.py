#!/usr/bin/env python3
"""Disposable real-Codex completion qualification for future scaffold runners."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    build_experiment_scaffold_v0_5_package,
    build_review_scaffold_v0_4_package,
    build_writing_scaffold_v0_4_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
from backend.workflow_packages.tests.test_experiment_interactive_bootstrap import (
    _materialize as _materialize_experiment,
)
from backend.workflow_packages.tests.test_writing_review_interactive_bootstrap import (
    _materialize as _materialize_writing_review,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", choices=("writing", "review", "experiment"))
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args()
    workflow_id, builder, version = {
        "writing": (WRITING_WORKFLOW_ID, build_writing_scaffold_v0_4_package, "0.4.0"),
        "review": (REVIEW_WORKFLOW_ID, build_review_scaffold_v0_4_package, "0.4.0"),
        "experiment": (EXPERIMENT_WORKFLOW_ID, build_experiment_scaffold_v0_5_package, "0.5.0"),
    }[args.workflow]
    with tempfile.TemporaryDirectory(prefix=f"reagent-real-{args.workflow}-complete-") as temp:
        package = builder(
            project_id="project-" + "7" * 32,
            project_name=f"Synthetic {args.workflow} completion",
            research_topic="Synthetic bounded completion qualification",
            output_root=Path(temp) / args.workflow,
            package_id=f"{args.workflow}-real-codex-completion-{version}",
        )
        root = package.package_root
        if workflow_id == EXPERIMENT_WORKFLOW_ID:
            _materialize_experiment(root)
        else:
            _materialize_writing_review(root, workflow_id)
        wrapper = Path(temp) / "codex-completion-wrapper"
        wrapper.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"--version\" ] || [ \"$1\" = \"--help\" ] || [ \"$1\" = \"login\" ]; then\n"
            f"  exec {args.codex!s} \"$@\"\n"
            "fi\n"
            "prompt=\"\"\n"
            "for arg in \"$@\"; do prompt=\"$arg\"; done\n"
            f"exec {args.codex!s} exec --sandbox workspace-write --skip-git-repo-check \"$prompt\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        namespace = runpy.run_path(str(root / "reagent_local.py"))
        uploads: list[dict] = []

        def upload(**kwargs):
            report = json.loads(kwargs["report_path"].read_text(encoding="utf-8"))
            uploads.append(report)
            return {"accepted_for_projection": True, "report_id": report["report_id"]}

        namespace["main"].__globals__["_upload"] = upload
        previous = Path.cwd()
        os.chdir(root)
        try:
            result = namespace["main"]([
                "run", ".", "--workflow-instance", "wfi-" + "8" * 32,
                "--api-url", "http://127.0.0.1:9",
                "--codex-executable", str(wrapper),
            ])
        finally:
            os.chdir(previous)
        reports = namespace["_report_chain_snapshot"](root)
        if result != 0 or len(reports) != 1 or len(uploads) != 1:
            raise RuntimeError("real Codex did not complete exactly one adopted Progress round")
        context_checksum = sha256_bytes((root / "memory/context.md").read_bytes())
        if reports[0]["context_after_checksum"] != context_checksum:
            raise RuntimeError("real Codex completion context does not match its report")
        print(canonical_json({
            "ok": True,
            "real_codex": True,
            "workflow": args.workflow,
            "capsule_version": version,
            "progress_rounds": 1,
            "runner_adopted_agent_finalization": True,
            "owner_data": False,
            "provider_calls": 0,
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
