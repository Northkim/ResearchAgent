from __future__ import annotations

import json
import multiprocessing
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.local_projects.contracts import LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import LITERATURE_SEARCH_CAPSULE_ID, LITERATURE_SEARCH_DEFINITION_ID
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.workspace_cli import WorkspaceCLIError


@pytest.fixture
def sync_fixture(tmp_path: Path):
    database = InMemoryDatabase()
    package_root = tmp_path / "cloud-packages"
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(package_root),
    )))
    created = client.post("/projects", json={
        "name": "B4 fictional project",
        "research_topic": "Fictional local continuity",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert created.status_code == 201
    project_id = created.json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    return {
        "client": client,
        "database": database,
        "package_root": package_root,
        "project_id": project_id,
        "bootstrap": bootstrap,
        "workspace": workspace,
    }


class _ClientTransport:
    def __init__(self, client: TestClient, *, fail_ack: bool = False):
        self.client = client
        self.fail_ack = fail_ack
        self.downloads = 0
        self.acks = 0

    def create_plan(self, project_id, payload):
        response = self.client.post(f"/projects/{project_id}/workspace/sync-plan", json=payload)
        if response.status_code != 200:
            error = response.json()["error"]
            raise WorkspaceCLIError(error["code"], error["message"], workspace_cli.EXIT_CLOUD)
        return response.json()

    def download(self, path, expected=None):
        self.downloads += 1
        response = self.client.get(path)
        if response.status_code != 200:
            raise WorkspaceCLIError("CAPSULE_DOWNLOAD_FAILED", "download failed", workspace_cli.EXIT_CLOUD)
        return response.content

    def acknowledge(self, project_id, payload):
        self.acks += 1
        if self.fail_ack:
            raise WorkspaceCLIError("WORKSPACE_SYNC_NOT_AVAILABLE", "offline", workspace_cli.EXIT_CLOUD)
        response = self.client.post(f"/projects/{project_id}/workspace/sync-ack", json=payload)
        if response.status_code not in {200, 201}:
            error = response.json()["error"]
            raise WorkspaceCLIError(error["code"], error["message"], workspace_cli.EXIT_CLOUD)
        return response.json()


def test_cloud_sync_plan_artifact_download_and_acknowledgement_are_bound(sync_fixture):
    client = sync_fixture["client"]
    project_id = sync_fixture["project_id"]
    bootstrap = sync_fixture["bootstrap"]
    instance_id = bootstrap["workflow_capsules"][0]["workflow_instance_id"]
    request = {
        "workspace_id": bootstrap["workspace_id"],
        "installed_manifest_revision": 0,
        "installed_lock_checksum": None,
        "installed_capsules": [],
        "idempotency_key": "00000000-0000-4000-8000-000000000001",
        "dry_run": False,
    }
    response = client.post(f"/projects/{project_id}/workspace/sync-plan", json=request)
    assert response.status_code == 200
    plan = response.json()
    assert plan["target_manifest_revision"] == 1
    assert [item["workflow_instance_id"] for item in plan["actions"]] == [instance_id]
    action = plan["actions"][0]
    assert action["action_type"] == "INSTALL_CAPSULE"
    assert action["trust_classification"] == "TRUSTED_BUILT_IN_UNSIGNED"
    artifact = action["artifact"]
    assert artifact["package_checksum"].startswith("sha256:")
    downloaded = client.get(artifact["download_path"])
    assert downloaded.status_code == 200
    assert downloaded.headers["X-ReAgent-Workflow-Instance-ID"] == instance_id
    assert workspace_cli.sha256_bytes(downloaded.content) == artifact["archive_checksum"]

    installed = [{key: action[key] for key in (
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
    )}]
    acknowledgement = {
        "schema_version": workspace_cli.SYNC_ACK_SCHEMA,
        "installation_id": plan["installation_id"],
        "project_id": project_id,
        "workspace_id": bootstrap["workspace_id"],
        "manifest_revision": 1,
        "manifest_checksum": plan["target_manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "installed_lock_schema": workspace_cli.INSTALLED_LOCK_SCHEMA,
        "installed_lock_checksum": "sha256:" + "1" * 64,
        "idempotency_key": "00000000-0000-4000-8000-000000000002",
        "installed_capsules": installed,
        "installed_at": "2026-08-07T00:00:00Z",
    }
    accepted = client.post(f"/projects/{project_id}/workspace/sync-ack", json=acknowledgement)
    assert accepted.status_code == 201
    replay = client.post(f"/projects/{project_id}/workspace/sync-ack", json=acknowledgement)
    assert replay.status_code == 201
    assert replay.json() == accepted.json()
    changed = dict(acknowledgement)
    changed["installed_lock_checksum"] = "sha256:" + "2" * 64
    conflict = client.post(f"/projects/{project_id}/workspace/sync-ack", json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_additional_instance_gets_distinct_artifact_and_plan_order(sync_fixture):
    client = sync_fixture["client"]
    project_id = sync_fixture["project_id"]
    created = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert created.status_code == 201
    response = client.post(f"/projects/{project_id}/workspace/sync-plan", json={
        "workspace_id": sync_fixture["bootstrap"]["workspace_id"],
        "installed_manifest_revision": 0,
        "installed_lock_checksum": None,
        "installed_capsules": [],
        "idempotency_key": "00000000-0000-4000-8000-000000000003",
        "dry_run": False,
    })
    assert response.status_code == 200
    actions = response.json()["actions"]
    assert [item["workflow_instance_id"] for item in actions] == sorted(
        item["workflow_instance_id"] for item in actions
    )
    assert len({item["artifact"]["package_id"] for item in actions}) == 2
    assert len({item["artifact"]["capsule_artifact_id"] for item in actions}) == 2


def test_sync_installs_atomically_retries_ack_and_then_is_noop(sync_fixture):
    workspace = sync_fixture["workspace"]
    offline = _ClientTransport(sync_fixture["client"], fail_ack=True)
    first = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=offline,
        now=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )
    assert first.status == "ACK_PENDING"
    assert first.acknowledgement_status == "ACK_PENDING"
    assert offline.downloads == 1
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock = workspace_cli.validate_installed_lock(
        json.loads(lock_path.read_text()),
        workspace_cli.validate_workspace_descriptor(json.loads((workspace / "project.json").read_text())),
    )
    capsule = workspace / lock["installed_capsules"][0]["relative_path"]
    assert capsule.is_dir()
    output = capsule / "outputs/search_plan.md"
    output.write_text("preserve user output", encoding="utf-8")

    online = _ClientTransport(sync_fixture["client"])
    retried = workspace_cli.sync_workspace(workspace_root=workspace, transport=online)
    assert retried.status == "ACKNOWLEDGED"
    assert online.downloads == 0
    assert output.read_text() == "preserve user output"
    noop = workspace_cli.sync_workspace(workspace_root=workspace, transport=online)
    assert noop.status == "NO_CHANGE"
    assert online.downloads == 0
    assert output.read_text() == "preserve user output"


def test_cli_returns_distinct_ack_pending_exit(sync_fixture, monkeypatch, capsys):
    offline = _ClientTransport(sync_fixture["client"], fail_ack=True)
    monkeypatch.setattr(
        workspace_cli,
        "HTTPWorkspaceSyncTransport",
        lambda _url: offline,
    )
    result = workspace_cli.main([
        "sync",
        str(sync_fixture["workspace"]),
        "--api-url",
        "http://127.0.0.1:8000",
        "--json",
    ])
    assert result == workspace_cli.EXIT_ACK_PENDING
    assert json.loads(capsys.readouterr().out)["acknowledgement_status"] == "ACK_PENDING"


def test_b3_registry_migrates_without_download_or_mutable_rewrite(sync_fixture):
    client = sync_fixture["client"]
    project_id = "project-" + "c" * 32
    legacy = LocalProject(
        project_id=project_id,
        name="B3 retained fictional project",
        research_topic="Fictional retained adoption state",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-06T00:00:00Z",
        updated_at="2026-08-06T00:00:00Z",
    )
    seed = InMemoryUnitOfWork(sync_fixture["database"])
    seed.local_projects.add(legacy)
    ProjectWorkspaceApplicationService(
        unit_of_work=seed,
        clock=lambda: datetime(2026, 8, 6, tzinfo=timezone.utc),
    ).initialize_project(legacy)
    seed.commit()
    generated = client.post(f"/projects/{project_id}/packages")
    assert generated.status_code == 201
    updated_bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = sync_fixture["workspace"].parent / "legacy-workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=updated_bootstrap)
    source = (
        sync_fixture["package_root"] / project_id / "literature-search-v0.5" / "package"
    )
    mutable = source / "memory/search/operations/fictional.json"
    mutable.write_text('{"fictional":true}', encoding="utf-8")
    workspace_cli.adopt_legacy_package(
        source=source,
        workspace_root=workspace,
        bootstrap_descriptor=updated_bootstrap,
    )
    adopted_hash = workspace_cli._tree_checksum(source)
    transport = _ClientTransport(client)
    _, descriptor, cached = workspace_cli.load_workspace(workspace)
    migrated = workspace_cli._load_or_migrate_lock(
        workspace, descriptor, cached, now=datetime(2026, 8, 7, tzinfo=timezone.utc)
    )
    probe = transport.create_plan(project_id, {
        "workspace_id": descriptor["workspace_id"],
        "installed_manifest_revision": migrated["manifest_revision"],
        "installed_lock_checksum": migrated["lock_checksum"],
        "installed_capsules": [workspace_cli._installed_observation(migrated["installed_capsules"][0])],
        "idempotency_key": "00000000-0000-4000-8000-000000000005",
        "dry_run": True,
    })
    assert probe["actions"][0]["action_type"] == "NOOP", (migrated, probe)
    result = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert result.acknowledgement_status == "ACKNOWLEDGED"
    assert transport.downloads == 0
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    assert lock["installed_capsules"][0]["installation_source"] == "B3_LEGACY_ADOPTION"
    adopted = workspace / lock["installed_capsules"][0]["relative_path"]
    assert workspace_cli._tree_checksum(adopted) == adopted_hash
    assert json.loads((workspace / workspace_cli.CAPSULE_REGISTRY).read_text())["entries"]


def test_incremental_instance_install_and_retire_retain_local_capsule(sync_fixture):
    workspace = sync_fixture["workspace"]
    client = sync_fixture["client"]
    transport = _ClientTransport(client)
    first = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert first.installed_capsules == 1
    first_lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    legacy = first_lock["installed_capsules"][0]
    legacy_path = workspace / legacy["relative_path"]
    marker = legacy_path / "outputs/search_plan.md"
    marker.write_text("retain this fictional result", encoding="utf-8")

    created = client.post(f"/projects/{sync_fixture['project_id']}/workflow-instances", json={
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert created.status_code == 201
    second_id = created.json()["workflow_instance_id"]
    incremental = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert incremental.installed_capsules == 2
    assert marker.read_text() == "retain this fictional result"
    second_lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    assert {item["workflow_instance_id"] for item in second_lock["installed_capsules"]} == {
        legacy["workflow_instance_id"], second_id,
    }

    retired = client.post(
        f"/projects/{sync_fixture['project_id']}/workflow-instances/{legacy['workflow_instance_id']}/retire",
        json={"base_revision": 2},
    )
    assert retired.status_code == 200
    retained = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert retained.installed_capsules == 1
    assert retained.retained_capsules == 1
    assert legacy_path.is_dir()
    assert marker.read_text() == "retain this fictional result"
    final_lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    retired_local = next(
        item for item in final_lock["installed_capsules"]
        if item["workflow_instance_id"] == legacy["workflow_instance_id"]
    )
    assert retired_local["lifecycle"] == "RETAINED_NOT_DESIRED"


def test_drift_corrupt_lock_and_target_symlink_fail_closed(sync_fixture, tmp_path):
    workspace = sync_fixture["workspace"]
    transport = _ClientTransport(sync_fixture["client"])
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock = json.loads(lock_path.read_text())
    capsule = workspace / lock["installed_capsules"][0]["relative_path"]
    (capsule / "AGENT.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert error.value.code in {"LEGACY_PACKAGE_CHECKSUM_MISMATCH", "LOCAL_CAPSULE_DRIFT"}

    lock_path.write_text("{}", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert error.value.code == "INSTALLED_LOCK_INVALID"


def _hold_lock(workspace: str, ready: multiprocessing.Event) -> None:
    with workspace_cli._WorkspaceWriteLock(Path(workspace)):
        ready.set()
        time.sleep(1.0)


def test_workspace_sync_lock_is_cross_process_and_crash_safe(sync_fixture):
    workspace = sync_fixture["workspace"]
    ready = multiprocessing.Event()
    process = multiprocessing.Process(target=_hold_lock, args=(str(workspace), ready))
    process.start()
    assert ready.wait(5)
    with pytest.raises(WorkspaceCLIError) as error:
        with workspace_cli._WorkspaceWriteLock(workspace):
            pass
    assert error.value.code == "WORKSPACE_BUSY"
    process.terminate()
    process.join(5)
    with workspace_cli._WorkspaceWriteLock(workspace):
        pass


def test_published_before_lock_and_cloud_success_before_local_receipt_recover(
    sync_fixture,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = sync_fixture["workspace"]
    transport = _ClientTransport(sync_fixture["client"])
    original_write = workspace_cli._atomic_write_json
    failed = False

    def fail_first_lock(path, value):
        nonlocal failed
        if path == workspace / workspace_cli.INSTALLED_LOCK and not failed:
            failed = True
            raise OSError("injected lock write failure")
        original_write(path, value)

    monkeypatch.setattr(workspace_cli, "_atomic_write_json", fail_first_lock)
    with pytest.raises(OSError, match="injected lock"):
        workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert not (workspace / workspace_cli.INSTALLED_LOCK).exists()
    assert any((workspace / "capsules").rglob("package-manifest.json"))
    monkeypatch.setattr(workspace_cli, "_atomic_write_json", original_write)
    recovered = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert recovered.acknowledgement_status == "ACKNOWLEDGED"

    # Simulate Cloud accepting the exact acknowledgement before the local
    # receipt replace. The pending envelope retains the original idempotency key.
    ack_path = next((workspace / workspace_cli.ACKNOWLEDGEMENTS_ROOT).glob("*.json"))
    value = json.loads(ack_path.read_text())
    value["local_status"] = "ACK_PENDING"
    value.pop("cloud_receipt", None)
    original_store = workspace_cli._store_ack_receipt
    calls = 0

    def fail_local_receipt(path, envelope, receipt):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected local receipt failure")
        original_store(path, envelope, receipt)

    workspace_cli._atomic_write_json(ack_path, value)
    monkeypatch.setattr(workspace_cli, "_store_ack_receipt", fail_local_receipt)
    with pytest.raises(OSError, match="local receipt"):
        workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    replayed = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert replayed.status == "ACKNOWLEDGED"
    assert json.loads(ack_path.read_text())["local_status"] == "ACKNOWLEDGED"


def test_manifest_race_preserves_revision_n_install_then_syncs_n_plus_one(sync_fixture):
    workspace = sync_fixture["workspace"]
    client = sync_fixture["client"]

    class RaceTransport(_ClientTransport):
        def __init__(self, client):
            super().__init__(client)
            self.advanced = False

        def acknowledge(self, project_id, payload):
            if not self.advanced:
                self.advanced = True
                response = self.client.post(f"/projects/{project_id}/workflow-instances", json={
                    "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
                    "workflow_version": "0.3.0",
                    "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
                    "capsule_version": "0.5.0",
                    "base_revision": 1,
                })
                assert response.status_code == 201
            return super().acknowledge(project_id, payload)

    race = RaceTransport(client)
    revision_n = workspace_cli.sync_workspace(workspace_root=workspace, transport=race)
    assert revision_n.status == "ACK_PENDING"
    assert revision_n.manifest_revision == 1
    assert json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())["manifest_revision"] == 1
    current = workspace_cli.sync_workspace(workspace_root=workspace, transport=race)
    assert current.manifest_revision == 2
    assert current.installed_capsules == 2
    assert current.acknowledgement_status == "ACKNOWLEDGED"


def test_archive_attack_and_install_failure_do_not_write_lock(sync_fixture, tmp_path):
    workspace = sync_fixture["workspace"]
    client_transport = _ClientTransport(sync_fixture["client"])
    plan = client_transport.create_plan(sync_fixture["project_id"], {
        "workspace_id": sync_fixture["bootstrap"]["workspace_id"],
        "installed_manifest_revision": 0,
        "installed_lock_checksum": None,
        "installed_capsules": [],
        "idempotency_key": "00000000-0000-4000-8000-000000000004",
        "dry_run": False,
    })

    class Malicious(_ClientTransport):
        def download(self, path, expected=None):
            archive = tmp_path / "bad.zip"
            import zipfile
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape", b"unsafe")
            content = archive.read_bytes()
            # Preserve plan identity while forcing archive-level rejection.
            return content

    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(workspace_root=workspace, transport=Malicious(sync_fixture["client"]))
    assert error.value.code == "CAPSULE_CHECKSUM_MISMATCH"
    assert not (workspace / workspace_cli.INSTALLED_LOCK).exists()
    assert not (tmp_path / "escape").exists()


def test_h1_workflow_list_and_stable_selector_are_user_oriented_and_json_stable(
    sync_fixture, capsys
):
    workspace = sync_fixture["workspace"]
    transport = _ClientTransport(sync_fixture["client"])
    synced = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
    )

    listed = workspace_cli.workflow_list(workspace)
    assert listed["schema_version"] == workspace_cli.WORKFLOW_LIST_SCHEMA
    assert listed["status"] == "WORKFLOWS_LISTED"
    assert len(listed["workflows"]) == 1
    workflow = listed["workflows"][0]
    assert workflow["display_name"] == "Literature Search"
    assert workflow["local_readiness"] == "READY"
    assert workflow["next_action"] == "RUN"
    assert workflow["run_command"] == (
        "python reagent_local.py run . --workflow "
        + workflow["workflow_definition_id"]
    )
    assert workspace_cli.resolve_workflow_selector(
        workspace, workflow["workflow_definition_id"]
    ) == workflow["workflow_instance_id"]

    workspace_cli._print_result(listed, json_output=False)
    human = capsys.readouterr().out
    assert "Installed Workflows (1)" in human
    assert "Next: Run" in human
    assert workflow["workflow_instance_id"] not in human
    workspace_cli._print_result(synced, json_output=True)
    assert capsys.readouterr().out.strip() == workspace_cli.canonical_json(synced.as_dict())


def test_h1_stable_selector_fails_closed_when_same_type_is_ambiguous(sync_fixture):
    client = sync_fixture["client"]
    workspace = sync_fixture["workspace"]
    project_id = sync_fixture["project_id"]
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(client),
    )
    catalog = client.get("/workflow-definitions").json()["items"]
    literature = next(
        item for item in catalog
        if item["workflow_definition_id"] == "literature-search-local-experimental"
    )
    created = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": literature["workflow_definition_id"],
            "workflow_version": literature["recommended_version"]["version"],
            "capsule_id": literature["recommended_capsule"]["capsule_id"],
            "capsule_version": literature["recommended_capsule"]["capsule_version"],
            "base_revision": 1,
        },
    )
    assert created.status_code == 201
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(client),
    )

    with pytest.raises(workspace_cli.WorkspaceCLIError) as raised:
        workspace_cli.resolve_workflow_selector(
            workspace, "literature-search-local-experimental"
        )
    assert raised.value.code == "WORKFLOW_SELECTOR_AMBIGUOUS"
    commands = [item["run_command"] for item in workspace_cli.workflow_list(workspace)["workflows"]]
    assert all("--workflow-instance wfi-" in command for command in commands)


def test_h1_human_error_explains_what_why_and_next(capsys):
    code = workspace_cli.main([
        "run", ".", "--workflow", "unknown-workflow", "--preflight-only",
    ])
    assert code == workspace_cli.EXIT_IDENTITY
    error = capsys.readouterr().err
    assert "What happened:" in error
    assert "Why it matters:" in error
    assert "Next:" in error
    assert "Code: WORKSPACE_DESCRIPTOR_INVALID" in error
