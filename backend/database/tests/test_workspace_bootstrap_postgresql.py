from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app


def test_workspace_bootstrap_descriptor_reloads_from_postgresql(
    sql_uow_factory,
    tmp_path: Path,
) -> None:
    container = ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "packages"),
    )
    client = TestClient(create_app(container))
    created = client.post(
        "/projects",
        json={
            "name": "PostgreSQL Workspace",
            "research_topic": "Fictional restart-safe Workspace metadata",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    )
    assert created.status_code == 201
    project_id = created.json()["project_id"]
    package = client.post(f"/projects/{project_id}/packages")
    assert package.status_code == 201

    first = client.get(f"/projects/{project_id}/workspace-bootstrap")
    assert first.status_code == 200
    assert first.json()["bootstrap_manifest_revision"] == 1
    assert first.json()["workflow_capsules"][0]["capsule_version"] == "0.8.0"
    assert first.json()["workflow_capsules"][0]["legacy_package"] is None
    assert client.get(package.json()["download_url"]).status_code == 200

    # Every request receives a fresh SQLAlchemy Unit of Work. This second read
    # therefore proves descriptor reconstruction from committed PostgreSQL rows,
    # not a router-local object or in-process cache.
    reloaded = client.get(f"/projects/{project_id}/workspace-bootstrap")
    assert reloaded.status_code == 200
    assert reloaded.json() == first.json()
