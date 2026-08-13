from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    build_experiment_scaffold_v0_4_package,
    build_writing_scaffold_v0_3_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json
from backend.workflow_packages.tests.test_experiment_interactive_bootstrap import (
    _materialize as _materialize_experiment,
)
from backend.workflow_packages.tests.test_writing_review_interactive_bootstrap import (
    _materialize as _materialize_writing_review,
)
from backend.project_workspaces.tests import test_progress_backlog_recovery as backlog

PROJECT_ID = "project-" + "7" * 32
WORKSPACE_ID = "workspace-" + "6" * 32
INSTANCE_ID = "wfi-" + "8" * 32
OTHER_INSTANCE_ID = "wfi-" + "9" * 32


def _legacy_state(tmp_path: Path, workflow_id: str):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    relative = f"capsules/{INSTANCE_ID}"
    builder = (
        build_writing_scaffold_v0_3_package
        if workflow_id == WRITING_WORKFLOW_ID
        else build_experiment_scaffold_v0_4_package
    )
    package = builder(
        project_id=PROJECT_ID,
        project_name="Legacy recovery fixture",
        research_topic="Synthetic bounded recovery",
        output_root=workspace / relative,
        package_id=f"legacy-{workflow_id}",
    )
    root = package.package_root
    relative = root.relative_to(workspace).as_posix()
    if workflow_id == WRITING_WORKFLOW_ID:
        _materialize_writing_review(root, workflow_id)
        definition_version, capsule_version = "0.2.0", "0.3.0"
    else:
        _materialize_experiment(root)
        definition_version, capsule_version = "0.3.0", "0.4.0"
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": workflow_id,
        "workflow_definition_version": definition_version,
        "capsule_version": capsule_version,
        "relative_path": root.relative_to(workspace).as_posix(),
    }
    receipts = workspace / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT
    receipts.mkdir(parents=True)
    provenance = json.loads((root / "memory/input-provenance.json").read_text())
    for index, (key, record) in enumerate(provenance["artifacts"].items(), 1):
        payload = {
            "schema_version": workspace_cli.MATERIALIZATION_RECEIPT_SCHEMA,
            "project_id": PROJECT_ID,
            "workspace_id": WORKSPACE_ID,
            "consumer_workflow_instance_id": INSTANCE_ID,
            "requirement_key": key,
            "binding_id": "artifact-binding-" + f"{index:032x}",
            "artifact_id": record["artifact_id"],
            "producer_workflow_instance_id": "wfi-" + f"{index:032x}",
            "artifact_type": record["artifact_type"],
            "artifact_schema_version": record["artifact_type"],
            "source_checksum": record["sha256"],
            "target_relative_path": f"{relative}/{record['relative_path']}",
            "target_checksum": record["sha256"],
            "materialized_at": "2026-08-13T00:00:00Z",
            "materialization_version": "0.1.0",
            "plan_checksum": "sha256:" + f"{index:064x}",
        }
        value = {**payload, "receipt_checksum": canonical_hash(payload)}
        (receipts / f"{value['binding_id']}.json").write_text(
            canonical_json(value) + "\n", encoding="utf-8"
        )
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    config = json.loads((root / "workflow/scaffold.json").read_text())
    context_before = runtime["_prepare_draft"](root, config)
    artifact = runtime["_publish"](root, config)
    runtime["_update_context"](root, config, artifact)
    report_path = runtime["_finalize"](root, context_before)
    # Reproduce the exact historical second runner update after report N.
    runtime["_publish"](root, config)
    runtime["_update_context"](root, config, artifact)
    manifest = json.loads((root / "package-manifest.json").read_text())
    report = json.loads(report_path.read_text())
    return workspace, descriptor, installed, root, manifest, report


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_exact_historical_scaffold_drift_is_recoverable_and_tamper_fails_closed(
    tmp_path: Path, workflow_id: str,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, workflow_id
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    assert [item["report_id"] for item in readiness.reports] == [report["report_id"]]

    current = json.loads((root / "memory/current-artifact.json").read_text())
    artifact = root / current["relative_path"]
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    rejected = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert rejected.state == "INVALID"


def test_arbitrary_context_mismatch_is_not_a_legacy_recovery_fingerprint(
    tmp_path: Path,
) -> None:
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path, WRITING_WORKFLOW_ID
    )
    context = root / "memory/context.md"
    context.write_text(context.read_text().replace("N+1", "arbitrary"), encoding="utf-8")
    # The literal may not exist; add an unexpected semantic field either way.
    raw = context.read_text()
    value = json.loads(raw.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
    value["unexpected"] = True
    context.write_text(
        "# Scaffold Workflow Context\n\n```json\n" + canonical_json(value) + "\n```\n",
        encoding="utf-8",
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "INVALID"


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_historical_scaffold_drift_uploads_exact_report_without_local_mutation(
    tmp_path: Path, workflow_id: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, workflow_id
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    transport = backlog._ProgressTransport()
    context_before = (root / "memory/context.md").read_bytes()
    output_before = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "outputs").rglob("*")) if path.is_file()
    }

    assert workspace_cli._recover_progress_backlog(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
        reports=list(readiness.reports),
        transport=transport,
    ) == 1
    assert transport.uploaded_rounds == [1]
    assert transport.accepted[0]["report_id"] == report["report_id"]
    assert (root / "memory/context.md").read_bytes() == context_before
    assert {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "outputs").rglob("*")) if path.is_file()
    } == output_before
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    acknowledged = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert acknowledged.state == "ACKNOWLEDGED"


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_list_continue_and_run_share_legacy_readiness_without_harness(
    tmp_path: Path, workflow_id: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, _manifest, _ = _legacy_state(
        tmp_path, workflow_id
    )
    active = {
        **installed,
        "capsule_id": "capsule-" + "a" * 32,
        "lifecycle": "ACTIVE",
    }
    lock = {"installed_capsules": [active]}
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        workspace_cli, "load_workspace",
        lambda _root: (workspace, descriptor, {}),
    )
    monkeypatch.setattr(workspace_cli, "_require_installed_lock", lambda *_: lock)
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_: None)
    harness_calls: list[list[str]] = []

    def forbidden_harness(*args, **kwargs):
        harness_calls.append(list(args[0]))
        raise AssertionError("upload-only recovery must not launch a Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", forbidden_harness)
    listing = workspace_cli.workflow_list(workspace)
    listed = listing["workflows"][0]
    assert listed["local_readiness"] == "PROGRESS_UPLOAD_PENDING"
    assert listed["next_action"] == "CONTINUE"
    assert listed["next_command"] == listed["run_command"]

    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    result = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=backlog._ProgressTransport(),
        api_url="http://127.0.0.1:9",
    )
    assert result.status == "PROGRESS_SYNCHRONIZED"
    assert harness_calls == []


@pytest.mark.parametrize(
    "case",
    ("A", "B", "C", "D", "E", "F", "G", "H"),
)
def test_pending_completion_survives_unrelated_workspace_context_changes(
    tmp_path: Path, case: str,
) -> None:
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path, WRITING_WORKFLOW_ID
    )
    if case == "B":
        # A read-only status projection must not consume or mutate readiness.
        assert workspace_cli._evaluate_local_progress_readiness(
            workspace=workspace, descriptor=descriptor, installed=installed,
            capsule=root, manifest=manifest,
        ).state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    elif case == "C":
        (workspace / workspace_cli.ARTIFACT_INDEX).parent.mkdir(parents=True, exist_ok=True)
        (workspace / workspace_cli.ARTIFACT_INDEX).write_text("artifact refresh\n")
    elif case == "D":
        (workspace / workspace_cli.DESIRED_MANIFEST_CACHE).parent.mkdir(parents=True, exist_ok=True)
        (workspace / workspace_cli.DESIRED_MANIFEST_CACHE).write_text("semantic noop sync\n")
    elif case == "E":
        (workspace / "capsules" / OTHER_INSTANCE_ID).mkdir(parents=True)
    elif case == "F":
        payload = {
            "schema_version": workspace_cli.MATERIALIZATION_RECEIPT_SCHEMA,
            "project_id": PROJECT_ID,
            "workspace_id": WORKSPACE_ID,
            "consumer_workflow_instance_id": OTHER_INSTANCE_ID,
            "requirement_key": "unrelated",
            "binding_id": "artifact-binding-" + "f" * 32,
            "artifact_id": "artifact-" + "e" * 32,
            "producer_workflow_instance_id": "wfi-" + "d" * 32,
            "artifact_type": "selected-paper-library/v1",
            "artifact_schema_version": "selected-paper-library/v1",
            "source_checksum": "sha256:" + "c" * 64,
            "target_relative_path": "capsules/unrelated/input.json",
            "target_checksum": "sha256:" + "c" * 64,
            "materialized_at": "2026-08-14T00:00:00Z",
            "materialization_version": "0.1.0",
            "plan_checksum": "sha256:" + "b" * 64,
        }
        receipt = {**payload, "receipt_checksum": canonical_hash(payload)}
        receipts = workspace / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT
        (receipts / f"{receipt['binding_id']}.json").write_text(
            canonical_json(receipt) + "\n", encoding="utf-8"
        )
    elif case == "G":
        unrelated = workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / OTHER_INSTANCE_ID
        unrelated.mkdir(parents=True)
        (unrelated / "receipt.json").write_text("{}\n", encoding="utf-8")
    elif case == "H":
        # A new evaluator invocation represents process/backend restart: all
        # authority is reloaded from durable local bytes.
        manifest = json.loads((root / "package-manifest.json").read_text())

    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
