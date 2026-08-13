from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path

import pytest

from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    _experiment_v0_4_files,
    _scaffold_v0_3_files,
    build_experiment_scaffold_v0_5_package,
    build_review_scaffold_v0_4_package,
    build_writing_scaffold_v0_4_package,
)
from backend.workflow_packages.tests.test_experiment_interactive_bootstrap import (
    _materialize as _materialize_experiment,
)
from backend.workflow_packages.tests.test_writing_review_interactive_bootstrap import (
    _materialize as _materialize_writing_review,
)

PROJECT_ID = "project-" + "7" * 32
INSTANCE_ID = "wfi-" + "8" * 32


def _fake(tmp_path: Path) -> Path:
    source = Path(__file__).with_name("fake_completing_scaffold_codex_cli.py")
    target = tmp_path / "codex-completing-scaffold-fixture"
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


@pytest.mark.parametrize(
    ("workflow_id", "builder", "version"),
    (
        (WRITING_WORKFLOW_ID, build_writing_scaffold_v0_4_package, "0.4.0"),
        (REVIEW_WORKFLOW_ID, build_review_scaffold_v0_4_package, "0.4.0"),
        (EXPERIMENT_WORKFLOW_ID, build_experiment_scaffold_v0_5_package, "0.5.0"),
    ),
)
def test_future_runner_adopts_exact_agent_finalization_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    workflow_id: str, builder, version: str,
) -> None:
    package = builder(
        project_id=PROJECT_ID,
        project_name="Agent finalization fixture",
        research_topic="Synthetic bounded research",
        output_root=tmp_path / workflow_id,
        package_id=f"{workflow_id}-completion-{version}",
    )
    root = package.package_root
    if workflow_id == EXPERIMENT_WORKFLOW_ID:
        _materialize_experiment(root)
    else:
        _materialize_writing_review(root, workflow_id)
    namespace = runpy.run_path(str(root / "reagent_local.py"))
    uploads: list[dict] = []

    def upload(**kwargs):
        report = json.loads(kwargs["report_path"].read_text(encoding="utf-8"))
        uploads.append(report)
        return {"accepted_for_projection": True, "report_id": report["report_id"]}

    namespace["main"].__globals__["_upload"] = upload
    monkeypatch.chdir(root)
    result = namespace["main"]([
        "run", ".", "--workflow-instance", INSTANCE_ID,
        "--api-url", "http://127.0.0.1:9",
        "--codex-executable", str(_fake(tmp_path)),
    ])
    assert result == 0
    reports = namespace["_report_chain_snapshot"](root)
    assert len(reports) == 1
    assert reports[0]["execution_round"] == 1
    assert reports[0]["status"] == reports[0]["current_state"] == "COMPLETED"
    assert len(uploads) == 1
    context_checksum = namespace["sha256_bytes"](
        (root / "memory/context.md").read_bytes()
    )
    assert reports[0]["context_after_checksum"] == context_checksum
    assert json.loads((root / "memory/current-artifact.json").read_text()) in (
        reports[0]["output_artifacts"]
    )


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID))
def test_historical_writing_review_0_3_rendered_bytes_do_not_change(
    workflow_id: str,
) -> None:
    common = {
        "project_id": PROJECT_ID,
        "project_name": "Immutable interactive scaffold",
        "package_id": "immutable-interactive-v0.3",
        "package_checksum": "sha256:" + "0" * 64,
    }
    files = _scaffold_v0_3_files(workflow_id=workflow_id, **common)
    assert "_adopt_agent_finalization" not in files["reagent_local.py"].content.decode()


def test_historical_experiment_0_4_rendered_bytes_do_not_change() -> None:
    files = _experiment_v0_4_files(
        project_id=PROJECT_ID,
        project_name="Immutable Experiment",
        package_id="immutable-interactive-v0.4",
        package_checksum="sha256:" + "0" * 64,
    )
    assert "_adopt_agent_finalization" not in files["reagent_local.py"].content.decode()


@pytest.mark.parametrize(
    ("workflow_id", "builder"),
    (
        (WRITING_WORKFLOW_ID, build_writing_scaffold_v0_4_package),
        (REVIEW_WORKFLOW_ID, build_review_scaffold_v0_4_package),
        (EXPERIMENT_WORKFLOW_ID, build_experiment_scaffold_v0_5_package),
    ),
)
def test_public_agent_finalizer_replays_terminal_report_without_new_round(
    tmp_path: Path, workflow_id: str, builder,
) -> None:
    package = builder(
        project_id=PROJECT_ID,
        project_name="Atomic finalizer replay fixture",
        research_topic="Synthetic bounded completion",
        output_root=tmp_path / workflow_id,
        package_id=f"atomic-{workflow_id}",
    )
    root = package.package_root
    if workflow_id == EXPERIMENT_WORKFLOW_ID:
        _materialize_experiment(root)
    else:
        _materialize_writing_review(root, workflow_id)
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    config = json.loads((root / "workflow/scaffold.json").read_text())
    runtime["_prepare_draft"](root, config)

    first = runtime["_agent_finalize"](root)
    second = runtime["_agent_finalize"](root)

    assert "idempotent_replay" not in first
    assert second["idempotent_replay"] is True
    assert second["progress_report"] == first["progress_report"]
    assert len(runtime["_report_chain_snapshot"](root)) == 1
