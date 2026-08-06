from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import (
    LITERATURE_SEARCH_CAPSULE_ID,
    LITERATURE_SEARCH_DEFINITION_ID,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
)


def _client(tmp_path):
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    )
    return TestClient(create_app(container)), database


def _create_project(client: TestClient, name: str = "Project") -> str:
    response = client.post(
        "/projects",
        json={
            "name": name,
            "research_topic": "Public fictional topic",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    )
    assert response.status_code == 201
    return response.json()["project_id"]


def _create_request(base_revision: int) -> dict[str, object]:
    return {
        "workflow_definition_id": LITERATURE_SEARCH_DEFINITION_ID,
        "workflow_version": "0.3.0",
        "capsule_id": LITERATURE_SEARCH_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "base_revision": base_revision,
    }


def test_catalog_is_repository_backed_ordered_and_planned_is_not_creatable(tmp_path):
    client, database = _client(tmp_path)
    _create_project(client)
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    database.workflow_definitions["idea-discovery-planned"] = WorkflowDefinition(
        workflow_definition_id="idea-discovery-planned",
        display_name="Idea Discovery",
        description="Planned",
        lifecycle=WorkflowDefinitionLifecycle.PLANNED,
        allows_multiple_instances=True,
        created_at=now,
        updated_at=now,
    )

    response = client.get("/workflow-definitions")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["workflow_definition_id"] for item in items] == [
        "idea-discovery-planned",
        LITERATURE_SEARCH_DEFINITION_ID,
    ]
    assert items[0]["lifecycle"] == "PLANNED"
    assert items[0]["creatable"] is False
    assert items[1]["creatable"] is True
    detail = client.get(f"/workflow-definitions/{LITERATURE_SEARCH_DEFINITION_ID}")
    assert detail.status_code == 200
    assert detail.json()["recommended_version"]["version"] == "0.3.0"
    assert detail.json()["recommended_capsule"]["capsule_version"] == "0.5.0"
    unknown = client.get("/workflow-definitions/unknown-workflow")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "WORKFLOW_DEFINITION_NOT_FOUND"


def test_project_bridge_instances_manifest_create_retire_and_stale_revision(tmp_path):
    client, _ = _client(tmp_path)
    project_id = _create_project(client)

    initial = client.get(f"/projects/{project_id}/workflow-instances")
    assert initial.status_code == 200
    assert initial.json()["total"] == 1
    assert initial.json()["manifest_revision"] == 1
    legacy_id = initial.json()["items"][0]["workflow_instance_id"]
    manifest = client.get(f"/projects/{project_id}/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["manifest_revision"] == 1
    assert len(manifest.json()["manifest"]["workflow_instances"]) == 1

    created = client.post(
        f"/projects/{project_id}/workflow-instances",
        json=_create_request(1),
    )
    assert created.status_code == 201
    second_id = created.json()["workflow_instance_id"]
    listed = client.get(f"/projects/{project_id}/workflow-instances").json()
    assert listed["total"] == 2
    assert listed["manifest_revision"] == 2

    stale = client.post(
        f"/projects/{project_id}/workflow-instances",
        json=_create_request(1),
    )
    assert stale.status_code == 409
    assert stale.json()["error"] == {
        "code": "MANIFEST_REVISION_CONFLICT",
        "message": "Desired Project Manifest revision conflict",
        "details": {"expected_revision": 1, "current_revision": 2},
    }
    assert client.get(f"/projects/{project_id}/workflow-instances").json()["total"] == 2

    retired = client.post(
        f"/projects/{project_id}/workflow-instances/{second_id}/retire",
        json={"base_revision": 2},
    )
    assert retired.status_code == 200
    assert retired.json()["desired_state"] == "RETIRED"
    assert retired.json()["in_current_manifest"] is False
    assert retired.json()["retired_manifest_revision"] == 3
    assert client.get(f"/projects/{project_id}/workflow-instances/{second_id}").status_code == 200
    repeated = client.post(
        f"/projects/{project_id}/workflow-instances/{second_id}/retire",
        json={"base_revision": 3},
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "WORKFLOW_INSTANCE_INVALID_STATE"
    assert client.get(f"/projects/{project_id}/workflow-instances/{legacy_id}").status_code == 200


def test_scope_version_capsule_and_planned_fail_closed_without_manifest_change(tmp_path):
    client, database = _client(tmp_path)
    first = _create_project(client, "First")
    second = _create_project(client, "Second")
    foreign_instance = client.get(
        f"/projects/{second}/workflow-instances"
    ).json()["items"][0]["workflow_instance_id"]
    scoped = client.get(f"/projects/{first}/workflow-instances/{foreign_instance}")
    assert scoped.status_code == 403
    assert scoped.json()["error"]["code"] == "PROJECT_SCOPE_MISMATCH"

    unknown_version = _create_request(1)
    unknown_version["workflow_version"] = "9.9.9"
    response = client.post(
        f"/projects/{first}/workflow-instances", json=unknown_version
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "WORKFLOW_VERSION_NOT_FOUND"
    unknown_capsule = _create_request(1)
    unknown_capsule["capsule_id"] = "capsule-" + "f" * 32
    response = client.post(
        f"/projects/{first}/workflow-instances", json=unknown_capsule
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CAPSULE_VERSION_NOT_FOUND"

    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    database.workflow_definitions["planned-workflow"] = WorkflowDefinition(
        workflow_definition_id="planned-workflow",
        display_name="Planned",
        description="",
        lifecycle=WorkflowDefinitionLifecycle.PLANNED,
        allows_multiple_instances=True,
        created_at=now,
        updated_at=now,
    )
    planned = _create_request(1)
    planned["workflow_definition_id"] = "planned-workflow"
    response = client.post(f"/projects/{first}/workflow-instances", json=planned)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WORKFLOW_UNAVAILABLE"
    final = client.get(f"/projects/{first}/workflow-instances").json()
    assert final["total"] == 1
    assert final["manifest_revision"] == 1
