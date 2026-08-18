from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import (
    LITERATURE_SEARCH_CAPSULE_ID,
    LITERATURE_SEARCH_DEFINITION_ID,
)
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.workspace_cli import WorkspaceCLIError

ARTIFACT_ID = "artifact-" + "a" * 32
BINDING_ID = "artifact-binding-" + "b" * 32
ARTIFACT_TYPE = "test.paper-library"
ARTIFACT_SCHEMA = "reagent.artifact.test-paper-library/v1.0"


@pytest.fixture
def artifact_workspace(tmp_path: Path):
    database = InMemoryDatabase()
    package_root = tmp_path / "cloud-packages"
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(package_root),
    )))
    created = client.post("/projects", json={
        "name": "B6 fictional project",
        "research_topic": "Fictional Artifact handoff",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert created.status_code == 201
    project_id = created.json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    sync_transport = _Transport(client)
    first = workspace_cli.sync_workspace(workspace_root=workspace, transport=sync_transport)
    assert first.installed_capsules == 1
    second = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert second.status_code == 201
    workspace_cli.sync_workspace(workspace_root=workspace, transport=sync_transport)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    entries = sorted(lock["installed_capsules"], key=lambda item: item["workflow_instance_id"])
    producer, consumer = entries
    source = workspace / producer["relative_path"] / "outputs/fictional-paper-library.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'{"fictional":["paper-1"]}\n')
    checksum = workspace_cli._hash_file(source)
    transport = _Transport(
        client,
        artifact=_artifact_document(
            project_id=project_id,
            producer=producer,
            checksum=checksum,
            size=source.stat().st_size,
        ),
        materialization=_plan(
            project_id=project_id,
            workspace_id=bootstrap["workspace_id"],
            producer=producer,
            consumer=consumer,
            checksum=checksum,
            size=source.stat().st_size,
        ),
    )
    return {
        "client": client,
        "workspace": workspace,
        "descriptor": bootstrap,
        "producer": producer,
        "consumer": consumer,
        "source": source,
        "checksum": checksum,
        "transport": transport,
    }


class _Transport:
    def __init__(self, client, *, artifact=None, materialization=None):
        self.client = client
        self.artifact = artifact
        self.materialization = materialization
        self.reported_presentations = []

    def create_plan(self, project_id, payload):
        response = self.client.post(f"/projects/{project_id}/workspace/sync-plan", json=payload)
        if response.status_code != 200:
            error = response.json()["error"]
            raise WorkspaceCLIError(error["code"], error["message"], workspace_cli.EXIT_CLOUD)
        return response.json()

    def download(self, path, expected=None):
        response = self.client.get(path)
        assert response.status_code == 200
        return response.content

    def acknowledge(self, project_id, payload):
        response = self.client.post(f"/projects/{project_id}/workspace/sync-ack", json=payload)
        if response.status_code not in {200, 201}:
            error = response.json()["error"]
            raise WorkspaceCLIError(error["code"], error["message"], workspace_cli.EXIT_CLOUD)
        return response.json()

    def list_artifacts(self, project_id, *, offset=0, limit=100):
        artifacts = [] if self.artifact is None else [self.artifact]
        return {
            "schema_version": workspace_cli.ARTIFACT_PAGE_SCHEMA,
            "project_id": project_id,
            "artifacts": artifacts[offset:offset + limit],
            "offset": offset,
            "limit": limit,
            "total": len(artifacts),
            "has_more": offset + limit < len(artifacts),
        }

    def materialization_plan(self, project_id, consumer_workflow_instance_id):
        assert self.materialization is not None
        assert self.materialization["project_id"] == project_id
        assert (
            self.materialization["consumer_workflow_instance_id"]
            == consumer_workflow_instance_id
        )
        return self.materialization

    def report_artifact_presentation(self, project_id, artifact_id, payload):
        assert self.artifact is not None
        assert self.artifact["project_id"] == project_id
        assert self.artifact["artifact_id"] == artifact_id
        self.reported_presentations.append(payload)
        self.artifact["presentation"] = {"payload": payload}
        return {"payload": payload}


def _artifact_document(*, project_id, producer, checksum, size):
    return {
        "schema_version": "reagent.artifact-reference/v0.1",
        "artifact_id": ARTIFACT_ID,
        "project_id": project_id,
        "producer_workflow_instance_id": producer["workflow_instance_id"],
        "producer_progress_receipt_id": "progress-receipt-" + "c" * 64,
        "producer_progress_report_id": "prv2-" + "d" * 64,
        "producer_execution_round": 1,
        "producer_capsule_id": producer["capsule_id"],
        "producer_capsule_version": producer["capsule_version"],
        "producer_core_capability_maturity": "REVIEWED_CORE",
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": ARTIFACT_SCHEMA,
        "media_type": "application/json",
        "state": "LOCAL_AVAILABLE",
        "relative_path": "outputs/fictional-paper-library.json",
        "content_checksum": checksum,
        "size_bytes": size,
        "cloud_metadata_available": True,
        "produced_at": "2026-08-07T12:00:00Z",
        "retired_at": None,
        "created_at": "2026-08-07T12:00:01Z",
        "updated_at": "2026-08-07T12:00:01Z",
    }


def _plan(*, project_id, workspace_id, producer, consumer, checksum, size):
    payload = {
        "schema_version": workspace_cli.MATERIALIZATION_PLAN_SCHEMA,
        "project_id": project_id,
        "workspace_id": workspace_id,
        "consumer_workflow_instance_id": consumer["workflow_instance_id"],
        "artifacts": [{
            "binding_id": BINDING_ID,
            "requirement_key": "paper-library",
            "consumer_workflow_instance_id": consumer["workflow_instance_id"],
            "producer_workflow_instance_id": producer["workflow_instance_id"],
            "artifact_id": ARTIFACT_ID,
            "artifact_type": ARTIFACT_TYPE,
            "artifact_schema_version": ARTIFACT_SCHEMA,
            "expected_checksum": checksum,
            "expected_size_bytes": size,
            "source_capsule_relative_path": producer["relative_path"],
            "source_relative_path": "outputs/fictional-paper-library.json",
            "target_capsule_relative_path": consumer["relative_path"],
            "target_relative_path": "inputs/paper-library/fictional-paper-library.json",
            "materialization_mode": "VERIFIED_COPY",
        }],
        "created_at": "2026-08-07T12:00:02Z",
    }
    return {**payload, "plan_checksum": workspace_cli.canonical_hash(payload)}


def test_artifact_index_refresh_and_materialization_are_verified_and_idempotent(
    artifact_workspace,
) -> None:
    workspace = artifact_workspace["workspace"]
    source = artifact_workspace["source"]
    source_before = source.read_bytes()
    refreshed = workspace_cli.refresh_artifact_index(
        workspace_root=workspace,
        transport=artifact_workspace["transport"],
        now=datetime(2026, 8, 7, 12, 1, tzinfo=UTC),
    )
    status = workspace_cli.artifact_status(workspace)
    first = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
        transport=artifact_workspace["transport"],
        now=datetime(2026, 8, 7, 12, 3, tzinfo=UTC),
    )
    repeated = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
        transport=artifact_workspace["transport"],
        now=datetime(2026, 8, 7, 12, 2, tzinfo=UTC),
    )
    target = (
        workspace
        / artifact_workspace["consumer"]["relative_path"]
        / "inputs/paper-library/fictional-paper-library.json"
    )

    assert refreshed.artifact_count == 1
    assert status["status"] == "VERIFIED"
    assert first.status == repeated.status == "MATERIALIZED"
    assert target.read_bytes() == source_before
    assert source.read_bytes() == source_before
    assert not target.is_symlink()
    assert target.stat().st_nlink == 1
    receipt = workspace / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT / f"{BINDING_ID}.json"
    assert workspace_cli._validate_materialization_receipt(
        json.loads(receipt.read_text()),
        workspace_cli.validate_workspace_descriptor(
            json.loads((workspace / "project.json").read_text())
        ),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    assert lock["materialized_artifacts"] == []


def test_publish_before_receipt_recovers_without_overwrite(
    artifact_workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = artifact_workspace["workspace"]
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    original = workspace_cli._atomic_write_json
    failed = False

    def fail_receipt(path, value):
        nonlocal failed
        if "materializations" in str(path) and not failed:
            failed = True
            raise OSError("injected receipt failure")
        original(path, value)

    monkeypatch.setattr(workspace_cli, "_atomic_write_json", fail_receipt)
    with pytest.raises(OSError, match="receipt failure"):
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    target = (
        workspace
        / artifact_workspace["consumer"]["relative_path"]
        / "inputs/paper-library/fictional-paper-library.json"
    )
    assert workspace_cli._hash_file(target) == artifact_workspace["checksum"]
    monkeypatch.setattr(workspace_cli, "_atomic_write_json", original)
    recovered = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
        transport=artifact_workspace["transport"],
    )
    assert recovered.materialized_count == 1
    assert target.read_bytes() == artifact_workspace["source"].read_bytes()


def test_source_drift_target_conflict_and_symlink_escape_fail_closed(
    artifact_workspace,
    tmp_path: Path,
) -> None:
    workspace = artifact_workspace["workspace"]
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    artifact_workspace["source"].write_bytes(b"drift")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert error.value.code == "LOCAL_ARTIFACT_DRIFT"

    artifact_workspace["source"].write_bytes(b'{"fictional":["paper-1"]}\n')
    target = (
        workspace
        / artifact_workspace["consumer"]["relative_path"]
        / "inputs/paper-library/fictional-paper-library.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"consumer-owned different bytes")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert error.value.code == "MATERIALIZATION_CONFLICT"

    target.unlink()
    target.parent.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert error.value.code in {"UNSAFE_PACKAGE_PATH", "UNSAFE_ARTIFACT_PATH"}
    assert list(outside.iterdir()) == []


def _hold_workspace_lock(path: str, ready: multiprocessing.Event) -> None:
    with workspace_cli._WorkspaceWriteLock(Path(path)):
        ready.set()
        time.sleep(1.0)


def test_artifact_writes_reuse_cross_process_workspace_lock(artifact_workspace) -> None:
    workspace = artifact_workspace["workspace"]
    ready = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_hold_workspace_lock, args=(str(workspace), ready)
    )
    process.start()
    assert ready.wait(5)
    try:
        with pytest.raises(WorkspaceCLIError) as error:
            workspace_cli.refresh_artifact_index(
                workspace_root=workspace,
                transport=artifact_workspace["transport"],
            )
        assert error.value.code == "WORKSPACE_BUSY"
    finally:
        process.terminate()
        process.join(5)
    refreshed = workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    assert refreshed.status == "INDEX_REFRESHED"


def test_index_refresh_rejects_symlink_hardlink_special_file_and_escape(
    artifact_workspace,
    tmp_path: Path,
) -> None:
    workspace = artifact_workspace["workspace"]
    source = artifact_workspace["source"]
    original = source.read_bytes()
    outside = tmp_path / "outside-artifact"
    outside.write_bytes(original)

    source.unlink()
    source.symlink_to(outside)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=artifact_workspace["transport"]
        )
    assert error.value.code in {"UNSAFE_ARTIFACT_PATH", "UNSAFE_PACKAGE_PATH"}
    source.unlink()
    source.write_bytes(original)

    hardlink = tmp_path / "artifact-hardlink"
    os.link(source, hardlink)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=artifact_workspace["transport"]
        )
    assert error.value.code == "UNSAFE_ARTIFACT_PATH"
    hardlink.unlink()

    source.unlink()
    os.mkfifo(source)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=artifact_workspace["transport"]
        )
    assert error.value.code == "UNSAFE_ARTIFACT_PATH"
    source.unlink()
    source.write_bytes(original)

    unsafe_artifact = {
        **artifact_workspace["transport"].artifact,
        "relative_path": "outputs/../outside-artifact",
    }
    unsafe_transport = _Transport(
        artifact_workspace["client"], artifact=unsafe_artifact
    )
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=unsafe_transport
        )
    assert error.value.code == "UNSAFE_ARTIFACT_PATH"


def test_corrupt_or_symlink_index_and_receipt_fail_closed(
    artifact_workspace,
    tmp_path: Path,
) -> None:
    workspace = artifact_workspace["workspace"]
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    index_path = workspace / workspace_cli.ARTIFACT_INDEX
    valid_index = index_path.read_bytes()
    index_path.write_text('{"corrupt":true}\n')
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.artifact_status(workspace)
    assert error.value.code == "ARTIFACT_INDEX_INVALID"
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=artifact_workspace["transport"]
        )
    assert error.value.code == "ARTIFACT_INDEX_INVALID"

    index_path.write_bytes(valid_index)
    outside = tmp_path / "outside-index"
    outside.write_bytes(valid_index)
    index_path.unlink()
    index_path.symlink_to(outside)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=artifact_workspace["transport"]
        )
    assert error.value.code == "ARTIFACT_INDEX_INVALID"
    index_path.unlink()
    index_path.write_bytes(valid_index)

    receipt = (
        workspace
        / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT
        / f"{BINDING_ID}.json"
    )
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.symlink_to(outside)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert error.value.code == "MATERIALIZED_ARTIFACT_DRIFT"


def test_copy_and_fsync_failures_leave_no_target_or_staging(
    artifact_workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = artifact_workspace["workspace"]
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    target = (
        workspace
        / artifact_workspace["consumer"]["relative_path"]
        / "inputs/paper-library/fictional-paper-library.json"
    )
    original_copy = workspace_cli._copy_verified_artifact

    def interrupted_copy(*_args, **_kwargs):
        raise OSError("injected copy interruption")

    monkeypatch.setattr(workspace_cli, "_copy_verified_artifact", interrupted_copy)
    with pytest.raises(OSError, match="copy interruption"):
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert not target.exists()
    assert list(target.parent.glob(f".{ARTIFACT_ID}.*")) == []

    monkeypatch.setattr(workspace_cli, "_copy_verified_artifact", original_copy)
    original_fsync = workspace_cli.os.fsync
    failed = False

    def interrupted_fsync(descriptor):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected fsync failure")
        return original_fsync(descriptor)

    monkeypatch.setattr(workspace_cli.os, "fsync", interrupted_fsync)
    with pytest.raises(OSError, match="fsync failure"):
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=artifact_workspace["consumer"]["workflow_instance_id"],
            transport=artifact_workspace["transport"],
        )
    assert not target.exists()
    assert list(target.parent.glob(f".{ARTIFACT_ID}.*")) == []


def test_materialization_plan_rejects_absolute_traversal_and_case_collision(
    artifact_workspace,
) -> None:
    descriptor = artifact_workspace["descriptor"]
    base = artifact_workspace["transport"].materialization
    for target in ("/absolute.json", "inputs/../escape.json"):
        payload = dict(base)
        entries = [dict(item) for item in base["artifacts"]]
        entries[0]["target_relative_path"] = target
        payload["artifacts"] = entries
        unsigned = dict(payload)
        unsigned.pop("plan_checksum")
        payload["plan_checksum"] = workspace_cli.canonical_hash(unsigned)
        with pytest.raises(WorkspaceCLIError) as error:
            workspace_cli.validate_materialization_plan(payload, descriptor)
        assert error.value.code == "UNSAFE_ARTIFACT_PATH"

    payload = dict(base)
    first = dict(base["artifacts"][0])
    second = {
        **first,
        "binding_id": "artifact-binding-" + "c" * 32,
        "requirement_key": "paper-library-two",
        "artifact_id": "artifact-" + "d" * 32,
        "target_relative_path": "inputs/paper-library/FICTIONAL-PAPER-LIBRARY.JSON",
    }
    payload["artifacts"] = [first, second]
    unsigned = dict(payload)
    unsigned.pop("plan_checksum")
    payload["plan_checksum"] = workspace_cli.canonical_hash(unsigned)
    with pytest.raises(WorkspaceCLIError):
        workspace_cli.validate_materialization_plan(payload, descriptor)


def test_artifact_cli_status_has_stable_json_and_exit_code(
    artifact_workspace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = artifact_workspace["workspace"]
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=artifact_workspace["transport"]
    )
    exit_code = workspace_cli.main([
        "artifact", "status", str(workspace), "--json",
    ])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == workspace_cli.EXIT_SUCCESS
    assert output["status"] == "VERIFIED"
    assert output["artifact_count"] == 1
    copied_cli = subprocess.run(
        [
            sys.executable,
            str(workspace / "reagent_local.py"),
            "artifact",
            "--help",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert copied_cli.returncode == 0
    assert "materialize" in copied_cli.stdout


def test_public_artifact_refresh_backfills_upstream_preview_without_research_rerun(
    artifact_workspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = artifact_workspace["workspace"]
    source = artifact_workspace["source"]
    value = {
        "schema": "selected-paper-library/v1",
        "source_schemas": {
            "candidate_papers": "candidate-papers/v0.2",
            "selected_papers": "selected-papers/v0.2",
        },
        "source_checksums": {
            "candidate_papers_sha256": "sha256:" + "1" * 64,
            "selected_papers_sha256": "sha256:" + "2" * 64,
        },
        "papers": [{
            "candidate_id": "candidate-0000000000000001",
            "paper": {
                "title": "Public refresh fixture",
                "authors": ["Fictional Author"],
                "publication_year": 2026,
                "doi": None,
                "provider_id": "stable-public-record",
            },
            "selection": {
                "inclusion_reason": "Exercises the supported public refresh command.",
                "evidence_availability": "METADATA_ONLY",
            },
        }],
    }
    source.write_text(workspace_cli.canonical_json(value), encoding="utf-8")
    transport = artifact_workspace["transport"]
    transport.artifact.update({
        "artifact_type": "selected-paper-library/v1",
        "artifact_schema_version": "selected-paper-library/v1",
        "content_checksum": workspace_cli._hash_file(source),
        "size_bytes": source.stat().st_size,
        "presentation": None,
    })
    monkeypatch.setattr(workspace_cli, "HTTPWorkspaceSyncTransport", lambda _url: transport)

    first = workspace_cli.main([
        "artifact", "refresh", str(workspace), "--api-url", "http://127.0.0.1:8000", "--json",
    ])
    first_output = json.loads(capsys.readouterr().out)
    second = workspace_cli.main([
        "artifact", "refresh", str(workspace), "--api-url", "http://127.0.0.1:8000", "--json",
    ])
    second_output = json.loads(capsys.readouterr().out)

    assert first == second == workspace_cli.EXIT_SUCCESS
    assert first_output["presentation_count"] == 1
    assert "presentation_count" not in second_output
    assert len(transport.reported_presentations) == 1


def test_selected_idea_preview_projection_is_deterministic_and_artifact_derived() -> None:
    value = {
        "schema": "selected-research-idea/v1",
        "core_capability_maturity": "REVIEWED_CORE",
        "source_candidate_ideas": {
            "schema": "candidate-ideas/v0.1", "relative_path": "outputs/candidate_ideas.json",
            "sha256": "sha256:" + "3" * 64,
        },
        "source_literature_artifact": {
            "artifact_id": "artifact-" + "4" * 32,
            "artifact_type": "selected-paper-library/v1", "sha256": "sha256:" + "5" * 64,
        },
        "selected_idea": {
            "idea_id": "idea-001", "title": "Compare archival practices",
            "research_question": "Where do the categories diverge?",
            "motivation": "The selected literature reports inconsistent categories.",
            "literature_basis": ["candidate-0000000000000001"],
            "observed_gap": "No direct comparison is reported.",
            "proposed_direction": "Apply a bounded comparison protocol.",
            "assumptions": ["Metadata is consistent."], "risks": ["Full text is unavailable."],
            "validation_needed": ["Confirm archival access."], "status": "selected",
        },
    }
    content = workspace_cli.canonical_json(value).encode()
    artifact = {
        "artifact_id": "artifact-" + "6" * 32,
        "artifact_type": "selected-research-idea/v1",
        "content_checksum": workspace_cli.sha256_bytes(content),
    }
    first = workspace_cli._project_upstream_presentation(artifact=artifact, content=content)
    second = workspace_cli._project_upstream_presentation(artifact=artifact, content=content)
    assert first == second
    assert first["title"] == "Compare archival practices"
    assert first["literature_basis_count"] == 1
