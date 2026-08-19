from __future__ import annotations

import json
import multiprocessing
import os
import runpy
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.api.deployment import DeploymentSettings
from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.cloud_api_proxy.contracts import PaperSearchV01Request
from backend.cloud_api_proxy.composition import ProxyApplicationContainer
from backend.local_projects.contracts import LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import LITERATURE_SEARCH_CAPSULE_ID, LITERATURE_SEARCH_DEFINITION_ID
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.workspace_cli import WorkspaceCLIError
from backend.workflow_packages.tests.fake_codex_cli import plan as fixture_plan


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
        self.consents = 0

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

    def list_project_skills(self, project_id):
        response = self.client.get(f"/projects/{project_id}/user-skills")
        assert response.status_code == 200, response.text
        return response.json()

    def acknowledge_project_skills(self, project_id, installed_skills):
        response = self.client.post(
            f"/projects/{project_id}/user-skills/sync-ack",
            json={"installed_skills": installed_skills},
        )
        assert response.status_code in {200, 201}, response.text

    def list_artifacts(self, project_id, *, offset=0, limit=100):
        response = self.client.get(
            f"/projects/{project_id}/artifacts",
            params={"offset": offset, "limit": limit},
        )
        assert response.status_code == 200, response.text
        return response.json()

    def materialization_plan(self, project_id, consumer_workflow_instance_id):
        response = self.client.get(
            f"/projects/{project_id}/workflow-instances/"
            f"{consumer_workflow_instance_id}/artifact-materialization-plan"
        )
        assert response.status_code == 200, response.text
        return response.json()

    def literature_execution_mode(self, project_id, package_identity):
        del project_id
        return {**package_identity, "mode": "NORMAL"}

    def grant_real_provider_consent(
        self, project_id, package_identity, *, confirmation
    ):
        self.consents += 1
        assert confirmation == workspace_cli.REAL_PROVIDER_CONFIRMATION
        return {
            "project_id": project_id,
            **package_identity,
            "disclosure_version": workspace_cli.REAL_PROVIDER_DISCLOSURE_VERSION,
            "status": "CONSENT_RECORDED",
            "expires_at": "2026-08-11T12:02:00Z",
        }


class _ControlledClientTransport(_ClientTransport):
    def literature_execution_mode(self, project_id, package_identity):
        response = self.client.get(
            f"/projects/{project_id}/local-sessions/execution-mode",
            params=package_identity,
        )
        assert response.status_code == 200, response.text
        return response.json()


class _DemoClientTransport(_ClientTransport):
    def literature_execution_mode(self, project_id, package_identity):
        del project_id
        return {**package_identity, "mode": "DEMO"}


def _literature_capsule(workspace: Path) -> tuple[Path, dict]:
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = next(
        item
        for item in lock["installed_capsules"]
        if item["workflow_definition_id"]
        == "literature-search-local-experimental"
    )
    return workspace / installed["relative_path"], installed


def _reach_search_completed(capsule: Path) -> tuple[dict, int]:
    """Use the installed Capsule state-machine helpers to reach owner state."""

    namespace = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    manifest = json.loads((capsule / "package-manifest.json").read_text())
    namespace["_initialize_control"](
        root=capsule,
        manifest=manifest,
        mode="DEMO",
        execution_style="INTERACTIVE",
    )
    fixture_plan(capsule)
    namespace["_mark_plan_confirmed"](capsule)
    topic = json.loads((capsule / "inputs/research_request.json").read_text())["topic"]
    queries = namespace["_validate_query_plan"](capsule, topic)
    fake = DeterministicFakePaperSearchAdapter()
    for query in queries:
        provider_data = fake.search(
            PaperSearchV01Request(query=query["query"], max_results=5)
        )
        namespace["_write_atomic"](
            capsule
            / "memory/search/operations"
            / f"{query['query_id']}.result.json",
            {
                "schema_version": "literature-search-normalized-query-result/v0.1",
                "mode": "DEMO",
                "query_id": query["query_id"],
                "issued_query": query["query"],
                "operation_id": f"fixture-{query['query_id']}",
                "request_content_checksum": "sha256:" + "a" * 64,
                "provider_data_checksum": "sha256:" + "b" * 64,
                "response_content_checksum": "sha256:" + "c" * 64,
                "provider_adapter": {"adapter_id": fake.adapter_id},
                "usage": {"provider_calls": 1},
                "provider_data": provider_data,
            },
        )
    namespace["_mark_search_completed"](capsule)
    control = json.loads((capsule / "memory/round-control.json").read_text())
    assert control["state"] == "SEARCH_COMPLETED"
    return control, fake.invocation_count


def _synced_full_research_workspace(tmp_path: Path):
    database = InMemoryDatabase()
    from backend.project_workspaces.tests.test_generic_experiment_v5_workspace import (
        _seed_forward,
    )
    _seed_forward(database)
    package_root = tmp_path / "cloud-packages"
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(package_root),
    )))
    created = client.post("/projects", json={
        "name": "F1F relative launcher regression",
        "research_topic": "Synthetic fixture",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    })
    assert created.status_code == 201, created.text
    project_id = created.json()["project_id"]
    descriptor = client.get(
        f"/projects/{project_id}/workspace-bootstrap"
    ).json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _ClientTransport(client)
    synced = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
    )
    assert synced.status == "SYNCED"
    return workspace, descriptor, transport


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


def test_workflow_list_cleans_only_bounded_managed_macos_metadata(sync_fixture):
    workspace = sync_fixture["workspace"]
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(sync_fixture["client"]),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    capsule = workspace / lock["installed_capsules"][0]["relative_path"]
    metadata = capsule / ".DS_Store"
    metadata.write_bytes(
        b"/Users/researcher/controlled-env\x00"
        b"OPENAI_API_KEY=credential-shaped-metadata"
    )

    public = subprocess.run(
        [
            sys.executable,
            str(workspace / "reagent_local.py"),
            "workflow",
            "list",
            str(workspace),
            "--json",
        ],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    assert public.returncode == 0, public.stderr
    listed = json.loads(public.stdout)

    assert listed["status"] == "WORKFLOWS_LISTED"
    assert not metadata.exists()

    unknown = capsule / "unexpected.txt"
    unknown.write_text("ordinary undeclared content\n", encoding="utf-8")
    with pytest.raises(WorkspaceCLIError, match="undeclared"):
        workspace_cli.workflow_list(workspace)
    assert unknown.read_text(encoding="utf-8") == "ordinary undeclared content\n"


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


@pytest.mark.parametrize(
    ("workspace_form", "workspace_name"),
    [
        ("dot", None),
        ("absolute", None),
        ("relative", "named-workspace"),
        ("relative", "workspace with spaces"),
        ("relative", "研究工作区"),
    ],
)
def test_capsule_launcher_path_is_interpreted_once_for_supported_workspace_forms(
    sync_fixture,
    monkeypatch,
    workspace_form,
    workspace_name,
):
    workspace = sync_fixture["workspace"]
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(sync_fixture["client"]),
    )
    if workspace_name is not None:
        renamed = workspace.parent / workspace_name
        workspace.rename(renamed)
        workspace = renamed
    if workspace_form == "dot":
        monkeypatch.chdir(workspace)
        workspace_argument = Path(".")
    elif workspace_form == "absolute":
        monkeypatch.chdir(workspace.parent)
        workspace_argument = workspace.absolute()
    else:
        monkeypatch.chdir(workspace.parent)
        workspace_argument = Path(workspace.name)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = lock["installed_capsules"][0]
    captured = {}

    def launch(command, *, cwd, env, check):
        captured.update(command=command, cwd=Path(cwd), env=env, check=check)
        target = Path(cwd) / command[1]
        if not target.is_absolute():
            target = Path.cwd() / target
        assert target.is_file()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(workspace_cli.subprocess, "run", launch)
    sentinel = "synthetic-secret-sentinel"
    for key in workspace_cli.PROVIDER_CREDENTIAL_ENV_VARS:
        monkeypatch.setenv(key, sentinel)
    transport = _ClientTransport(sync_fixture["client"])
    result = workspace_cli.run_workflow(
        workspace_root=workspace_argument,
        workflow_instance_id=installed["workflow_instance_id"],
        transport=transport,
        api_url="http://127.0.0.1:8000",
        consent_input=lambda _: workspace_cli.REAL_PROVIDER_CONFIRMATION,
    )

    assert result.status == "RUN_COMPLETED"
    assert captured["command"][1:] == ["reagent_local.py", "run", "."]
    assert "capsules" not in captured["command"][1]
    assert captured["cwd"] == workspace_argument / installed["relative_path"]
    assert transport.consents == 1
    assert all(key not in captured["env"] for key in workspace_cli.PROVIDER_CREDENTIAL_ENV_VARS)
    assert "REAGENT_DATABASE_URL" not in captured["env"]


def test_normal_run_cancelled_consent_never_starts_capsule(sync_fixture, monkeypatch):
    workspace = sync_fixture["workspace"]
    transport = _ClientTransport(sync_fixture["client"])
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = lock["installed_capsules"][0]
    monkeypatch.setattr(
        workspace_cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("cancelled consent must not launch a Capsule")
        ),
    )

    with pytest.raises(WorkspaceCLIError) as raised:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=installed["workflow_instance_id"],
            transport=transport,
            api_url="http://127.0.0.1:8000",
            consent_input=lambda _: "cancel",
        )

    assert raised.value.code == "REAL_PROVIDER_CONSENT_CANCELLED"
    assert transport.consents == 0


def test_owner_copyable_dot_command_uses_downloaded_generic_launcher_once(
    tmp_path,
    monkeypatch,
    capsys,
):
    workspace, _, transport = _synced_full_research_workspace(tmp_path)
    listing = workspace_cli.workflow_list(workspace)
    assert len(listing["workflows"]) == 5
    literature = next(
        item for item in listing["workflows"]
        if item["workflow_definition_id"]
        == "literature-search-local-experimental"
    )
    assert literature["run_command"] == (
        "python reagent_local.py run . "
        "--workflow literature-search-local-experimental"
    )
    copied_cli = workspace / "reagent_local.py"
    namespace = runpy.run_path(str(copied_cli))
    namespace["main"].__globals__["HTTPWorkspaceSyncTransport"] = (
        lambda _api_url: transport
    )
    captured = {}

    def launch(command, *, cwd, env, check):
        target = Path(cwd) / command[1]
        if not target.is_absolute():
            target = Path.cwd() / target
        captured.update(command=command, cwd=Path(cwd), target=target)
        assert target.is_file()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", launch)
    namespace["continue_workflow"].__kwdefaults__["consent_input"] = (
        lambda _: workspace_cli.REAL_PROVIDER_CONFIRMATION
    )
    monkeypatch.chdir(workspace)
    exit_code = namespace["main"]([
        "run",
        ".",
        "--workflow",
        "literature-search-local-experimental",
    ])

    assert exit_code == workspace_cli.EXIT_SUCCESS
    assert captured["command"][1:] == ["reagent_local.py", "run", "."]
    assert captured["target"] == (
        Path.cwd() / captured["cwd"] / "reagent_local.py"
    )
    capsule_text = captured["cwd"].as_posix()
    assert captured["target"].as_posix().count(capsule_text) == 1
    assert "Local Workspace operation: Run Completed" in capsys.readouterr().out


def test_owner_dot_command_projects_controlled_demo_mode_from_real_server_route(
    tmp_path,
    monkeypatch,
):
    database = InMemoryDatabase()
    from backend.project_workspaces.tests.test_generic_experiment_v5_workspace import (
        _seed_forward,
    )
    _seed_forward(database)
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
    )
    proxy_database = InMemoryProxyDatabase()
    fake = DeterministicFakePaperSearchAdapter()
    proxy = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_database),
        adapter=fake,
    )
    app = create_app(
        container,
        proxy_container=ProxyApplicationContainer(service=proxy),
        enable_experimental_proxy=True,
        enable_local_workflow_sessions=True,
        deployment_settings=DeploymentSettings.isolated_test_defaults(),
    )
    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        created = client.post("/projects", json={
            "name": "Controlled owner route",
            "research_topic": "Deterministic fixture",
            "selected_workflow": "LITERATURE_SEARCH",
            "workflow_setup": "full-research",
        })
        assert created.status_code == 201, created.text
        project_id = created.json()["project_id"]
        descriptor = client.get(
            f"/projects/{project_id}/workspace-bootstrap"
        ).json()
        downloaded = client.get("/local-client/reagent_local.py")
        assert downloaded.status_code == 200
        workspace = tmp_path / "controlled workspace"
        workspace_cli.bootstrap_workspace(
            target=workspace,
            descriptor=descriptor,
            cli_source=downloaded.content,
        )
        transport = _ControlledClientTransport(client)
        workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
        namespace = runpy.run_path(str(workspace / "reagent_local.py"))
        namespace["main"].__globals__["HTTPWorkspaceSyncTransport"] = (
            lambda _api_url: transport
        )
        captured = {}

        def launch(command, *, cwd, env, check):
            captured.update(command=command, cwd=Path(cwd), env=env, check=check)
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(subprocess, "run", launch)
        monkeypatch.chdir(workspace)
        exit_code = namespace["main"]([
            "run", ".", "--workflow",
            "literature-search-local-experimental",
        ])

    assert exit_code == workspace_cli.EXIT_SUCCESS
    assert captured["command"][1:] == [
        "reagent_local.py", "run", ".", "--mode", "demo",
    ]
    assert captured["cwd"].name == "0.6.0"
    assert fake.invocation_count == 0


def test_owner_search_completed_state_projects_resume_and_generic_run_uses_it(
    tmp_path,
    monkeypatch,
    capsys,
):
    workspace, _, transport = _synced_full_research_workspace(tmp_path)
    capsule, installed = _literature_capsule(workspace)
    initial_control, initial_calls = _reach_search_completed(capsule)
    result_checksums = initial_control["search_result_checksums"]

    listed = workspace_cli.workflow_list(workspace)
    literature = next(
        item for item in listed["workflows"]
        if item["workflow_instance_id"] == installed["workflow_instance_id"]
    )
    assert literature["local_readiness"] == "FINALIZATION_PENDING"
    assert literature["next_action"] == "RESUME"
    assert literature["next_command"] == literature["run_command"]
    workspace_cli._print_result(listed, json_output=False)
    human = capsys.readouterr().out
    assert "Literature Search · Finalization Pending" in human
    assert "Next: Resume" in human

    captured = {}

    def launch(command, *, cwd, env, check):
        captured.update(command=command, cwd=Path(cwd), env=env, check=check)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(workspace_cli.subprocess, "run", launch)
    monkeypatch.chdir(workspace)
    result = workspace_cli.run_workflow(
        workspace_root=Path("."),
        workflow_instance_id=installed["workflow_instance_id"],
        transport=_DemoClientTransport(transport.client),
        api_url="http://127.0.0.1:8000",
    )
    assert result.status == "RUN_COMPLETED"
    assert captured["command"][1:] == [
        "reagent_local.py", "run", ".", "--mode", "demo", "--resume",
    ]
    current = json.loads((capsule / "memory/round-control.json").read_text())
    assert current["search_result_checksums"] == result_checksums
    assert initial_calls == 2


def test_failed_generic_harness_marks_valid_post_search_interruption(
    tmp_path,
    monkeypatch,
):
    workspace, _, transport = _synced_full_research_workspace(tmp_path)
    capsule, installed = _literature_capsule(workspace)
    initial_control, _ = _reach_search_completed(capsule)
    checksums = initial_control["search_result_checksums"]

    monkeypatch.setattr(
        workspace_cli.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 2),
    )
    with pytest.raises(WorkspaceCLIError) as raised:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=installed["workflow_instance_id"],
            transport=_DemoClientTransport(transport.client),
            api_url="http://127.0.0.1:8000",
        )
    assert raised.value.code == "WORKFLOW_RUN_FAILED"
    control = json.loads((capsule / "memory/round-control.json").read_text())
    assert control["state"] == "INTERRUPTED"
    assert control["last_completed_state"] == "SEARCH_COMPLETED"
    assert control["interrupted_stage"] == "POST_SEARCH_INTERACTION"
    assert control["failure_code"] == "HARNESS_SESSION_STOPPED"
    assert control["candidate_review_confirmed"] is False
    assert control["finalization_confirmed"] is False
    assert control["search_result_checksums"] == checksums

    literature = next(
        item
        for item in workspace_cli.workflow_list(workspace)["workflows"]
        if item["workflow_instance_id"] == installed["workflow_instance_id"]
    )
    assert literature["local_readiness"] == "INTERRUPTED"
    assert literature["next_action"] == "RESUME"


def test_tampered_search_result_blocks_continuity_projection_and_resume(
    tmp_path,
):
    workspace, _, _ = _synced_full_research_workspace(tmp_path)
    capsule, _ = _literature_capsule(workspace)
    _reach_search_completed(capsule)
    result = capsule / "memory/search/operations/query-1.result.json"
    result.write_text(result.read_text() + " ", encoding="utf-8")

    with pytest.raises(WorkspaceCLIError) as raised:
        workspace_cli.workflow_list(workspace)
    assert raised.value.code == "LOCAL_CAPSULE_DRIFT"


def test_all_f1f_capsule_types_share_capsule_relative_launcher_rule(tmp_path):
    workspace, _, _ = _synced_full_research_workspace(tmp_path)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    commands = {}
    for installed in lock["installed_capsules"]:
        capsule = workspace / installed["relative_path"]
        commands[installed["workflow_definition_id"]] = (
            workspace_cli._capsule_runner_command(capsule)
        )

    assert set(commands) == {
        "literature-search-local-experimental",
        "idea-discovery-local-experimental",
        "writing-local-experimental",
        "review-local-experimental",
        "reproduction-experiment-local-experimental",
    }
    assert all(command[1] == "reagent_local.py" for command in commands.values())


def test_dot_preflight_only_succeeds_without_starting_launcher(
    sync_fixture,
    monkeypatch,
):
    workspace = sync_fixture["workspace"]
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(sync_fixture["client"]),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = lock["installed_capsules"][0]
    monkeypatch.chdir(workspace)

    def unexpected_launch(*args, **kwargs):
        raise AssertionError("preflight-only must not start the Literature launcher")

    monkeypatch.setattr(workspace_cli.subprocess, "run", unexpected_launch)
    result = workspace_cli.run_workflow(
        workspace_root=Path("."),
        workflow_instance_id=installed["workflow_instance_id"],
        transport=_ClientTransport(sync_fixture["client"]),
        api_url="http://127.0.0.1:8000",
        preflight_only=True,
    )
    assert result.status == "PREFLIGHT_READY"


def test_tampered_capsule_fails_closed_before_launcher_start(
    sync_fixture,
    monkeypatch,
):
    workspace = sync_fixture["workspace"]
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=_ClientTransport(sync_fixture["client"]),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = lock["installed_capsules"][0]
    runner = workspace / installed["relative_path"] / "reagent_local.py"
    runner.write_text(runner.read_text() + "\n# local tamper\n")
    monkeypatch.chdir(workspace)

    def unexpected_launch(*args, **kwargs):
        raise AssertionError("tampered Capsule must fail before subprocess launch")

    monkeypatch.setattr(workspace_cli.subprocess, "run", unexpected_launch)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as raised:
        workspace_cli.run_workflow(
            workspace_root=Path("."),
            workflow_instance_id=installed["workflow_instance_id"],
            transport=_ClientTransport(sync_fixture["client"]),
            api_url="http://127.0.0.1:8000",
        )
    assert raised.value.code in {
        "LOCAL_CAPSULE_DRIFT",
        "LEGACY_PACKAGE_CHECKSUM_MISMATCH",
    }


def test_workflow_run_failure_guidance_stops_launcher_path_retry_loop(capsys):
    workspace_cli._print_human_error(
        "run",
        workspace_cli.WorkspaceCLIError(
            "WORKFLOW_RUN_FAILED",
            "Workflow local Harness did not complete successfully",
            workspace_cli.EXIT_VALIDATION,
        ),
    )
    error = capsys.readouterr().err
    assert "path/file error" in error
    assert "instead of repeatedly retrying" in error
    assert "report code WORKFLOW_RUN_FAILED" in error
