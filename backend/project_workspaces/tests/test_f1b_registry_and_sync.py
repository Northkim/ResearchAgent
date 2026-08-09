from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    SCAFFOLD_CAPSULE_CHECKSUMS,
    SCAFFOLD_CAPSULE_IDS,
    SCAFFOLD_WORKFLOWS,
)
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)

from backend.project_workspaces.tests.test_b7_multi_workflow import _Transport


def _client(tmp_path):
    database = InMemoryDatabase()
    return TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    ))), database


def test_production_registry_has_exactly_five_real_workflow_types(tmp_path) -> None:
    client, _ = _client(tmp_path)
    client.post("/projects", json={
        "name": "F1B registry", "research_topic": "Synthetic",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    items = client.get("/workflow-definitions").json()["items"]
    assert {item["workflow_definition_id"] for item in items} == {
        "literature-search-local-experimental",
        "idea-discovery-local-experimental",
        WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
    }
    assert len(items) == 5
    for workflow_id in SCAFFOLD_WORKFLOWS:
        detail = client.get(f"/workflow-definitions/{workflow_id}").json()
        assert detail["lifecycle"] == "AVAILABLE"
        assert detail["creatable"] is True
        assert detail["allows_multiple_instances"] is True
        assert detail["recommended_version"]["version"] == "0.1.0"
        assert detail["recommended_version"]["core_capability_maturity"] == "SCAFFOLD_CORE"
        assert detail["recommended_capsule"]["capsule_id"] == SCAFFOLD_CAPSULE_IDS[workflow_id]
        assert detail["recommended_capsule"]["definition_checksum"] == SCAFFOLD_CAPSULE_CHECKSUMS[workflow_id]
        assert detail["recommended_capsule"]["trust_classification"] == "TRUSTED_BUILT_IN_UNSIGNED"


def test_each_scaffold_syncs_independently_and_repeat_is_noop(tmp_path) -> None:
    client, _ = _client(tmp_path)
    project = client.post("/projects", json={
        "name": "F1B independent sync", "research_topic": "Synthetic",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    transport = _Transport(client)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport, now=now)
    downloads = len(transport.downloads)
    revision = 1
    installed_ids = set()
    for offset, workflow_id in enumerate((
        WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
    ), start=1):
        detail = client.get(f"/workflow-definitions/{workflow_id}").json()
        created = client.post(f"/projects/{project_id}/workflow-instances", json={
            "workflow_definition_id": workflow_id,
            "workflow_version": "0.1.0",
            "capsule_id": detail["recommended_capsule"]["capsule_id"],
            "capsule_version": "0.1.0",
            "base_revision": revision,
        })
        assert created.status_code == 201, created.text
        revision += 1
        result = workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport,
            now=now + timedelta(minutes=offset),
        )
        assert result.status == "SYNCED"
        assert len(transport.downloads) == downloads + offset
        installed_ids.add(created.json()["workflow_instance_id"])
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        assert installed_ids <= {
            item["workflow_instance_id"] for item in lock["installed_capsules"]
        }
    before = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    noop = workspace_cli.sync_workspace(
        workspace_root=workspace, transport=transport, now=now + timedelta(hours=1)
    )
    after = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    assert noop.status == "NO_CHANGE"
    assert before == after
    assert len(transport.downloads) == downloads + 3
