from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.api import ApplicationContainer, create_app
from backend.project_workspaces import LITERATURE_SEARCH_CAPSULE_ID, LITERATURE_SEARCH_DEFINITION_ID


def test_workspace_artifacts_acknowledgement_reload_and_concurrency(
    sql_uow_factory,
    postgres_engine,
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "packages"),
    )))
    created = client.post("/projects", json={
        "name": "B4 PostgreSQL",
        "research_topic": "Fictional synchronization persistence",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert created.status_code == 201
    project_id = created.json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    added = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert added.status_code == 201
    plan_response = client.post(f"/projects/{project_id}/workspace/sync-plan", json={
        "workspace_id": bootstrap["workspace_id"],
        "installed_manifest_revision": 0,
        "installed_lock_checksum": None,
        "installed_capsules": [],
        "idempotency_key": "00000000-0000-4000-8000-000000000010",
        "dry_run": False,
    })
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["target_manifest_revision"] == 2
    assert len(plan["actions"]) == 2
    assert len({item["artifact"]["package_id"] for item in plan["actions"]}) == 2
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM local_workflow_capsule_artifacts"
        )) == 2

    acknowledgement = {
        "schema_version": "reagent.capsule-installation-ack/v0.1",
        "installation_id": plan["installation_id"],
        "project_id": project_id,
        "workspace_id": bootstrap["workspace_id"],
        "manifest_revision": plan["target_manifest_revision"],
        "manifest_checksum": plan["target_manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
        "installed_lock_checksum": "sha256:" + "a" * 64,
        "idempotency_key": "00000000-0000-4000-8000-000000000011",
        "installed_capsules": [
            {key: item[key] for key in (
                "workflow_instance_id", "workflow_definition_id",
                "workflow_definition_version", "capsule_id", "capsule_version",
                "capsule_definition_checksum",
            )}
            for item in plan["actions"]
        ],
        "installed_at": "2026-08-07T00:00:00Z",
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(
            lambda _: client.post(
                f"/projects/{project_id}/workspace/sync-ack", json=acknowledgement
            ),
            range(2),
        ))
    assert {item.status_code for item in responses}.issubset({201, 409})
    assert any(item.status_code == 201 for item in responses)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_installation_acknowledgements"
        )) == 1
    replay = client.post(
        f"/projects/{project_id}/workspace/sync-ack", json=acknowledgement
    )
    assert replay.status_code == 201
    assert replay.json()["installed_lock_checksum"] == acknowledgement["installed_lock_checksum"]


def test_stale_manifest_acknowledgement_never_claims_current(
    sql_uow_factory,
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "packages"),
    )))
    created = client.post("/projects", json={
        "name": "B4 race",
        "research_topic": "Fictional manifest race",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    project_id = created.json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    plan = client.post(f"/projects/{project_id}/workspace/sync-plan", json={
        "workspace_id": bootstrap["workspace_id"],
        "installed_manifest_revision": 0,
        "installed_lock_checksum": None,
        "installed_capsules": [],
        "idempotency_key": "00000000-0000-4000-8000-000000000020",
        "dry_run": False,
    }).json()
    advanced = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert advanced.status_code == 201
    action = plan["actions"][0]
    stale = client.post(f"/projects/{project_id}/workspace/sync-ack", json={
        "schema_version": "reagent.capsule-installation-ack/v0.1",
        "installation_id": plan["installation_id"],
        "project_id": project_id,
        "workspace_id": bootstrap["workspace_id"],
        "manifest_revision": 1,
        "manifest_checksum": plan["target_manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
        "installed_lock_checksum": "sha256:" + "b" * 64,
        "idempotency_key": "00000000-0000-4000-8000-000000000021",
        "installed_capsules": [{key: action[key] for key in (
            "workflow_instance_id", "workflow_definition_id",
            "workflow_definition_version", "capsule_id", "capsule_version",
            "capsule_definition_checksum",
        )}],
        "installed_at": "2026-08-07T00:00:00Z",
    })
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ACKNOWLEDGEMENT_STALE"
