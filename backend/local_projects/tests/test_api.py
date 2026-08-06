from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.cloud_api_proxy.composition import ProxyApplicationContainer
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.tests.factories import native_report, upload_envelope
from backend.research.adapters import LocalFilesystemArtifactStorage


@pytest.fixture
def product_client(tmp_path) -> Iterator[tuple[TestClient, InMemoryDatabase]]:
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
        local_package_root=str(tmp_path / "packages"),
        clock=lambda: datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
        project_id_factory=lambda: "project-fedcba9876543210fedcba9876543210",
    )

    def forbidden_runtime_graph(_):
        raise AssertionError("local product action constructed Hosted Runtime services")

    container.build_services = forbidden_runtime_graph  # type: ignore[method-assign]
    with TestClient(create_app(container)) as client:
        yield client, database


@pytest.fixture
def session_client(tmp_path) -> Iterator[tuple[TestClient, InMemoryDatabase]]:
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
        local_package_root=str(tmp_path / "packages"),
        clock=lambda: datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
        project_id_factory=lambda: "project-fedcba9876543210fedcba9876543210",
    )
    proxy_database = InMemoryProxyDatabase()
    adapter = DeterministicFakePaperSearchAdapter()
    proxy_service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_database),
        adapter=adapter,
        clock=lambda: datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
    )
    proxy_container = ProxyApplicationContainer(service=proxy_service)
    app = create_app(
        container,
        proxy_container=proxy_container,
        enable_experimental_proxy=True,
        enable_local_workflow_sessions=True,
    )
    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        yield client, database


def _create(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={
            "name": "Fictional local project",
            "research_topic": "A fictional public topic about transparent handoff",
            "selected_workflow": "LITERATURE_SEARCH",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_project_create_list_get_without_execution(product_client) -> None:
    client, database = product_client
    project = _create(client)
    listed = client.get("/projects")
    fetched = client.get(f"/projects/{project['project_id']}")
    assert listed.status_code == fetched.status_code == 200
    assert listed.json() == [project]
    assert fetched.json() == project
    assert database.executions == {}
    assert database.execution_events == {}
    assert database.provider_operations == {}


def test_package_generate_latest_and_download(product_client) -> None:
    client, database = product_client
    project = _create(client)
    path = f"/projects/{project['project_id']}/packages"
    generated = client.post(path)
    replayed = client.post(path)
    assert generated.status_code == replayed.status_code == 201
    package = generated.json()
    assert replayed.json()["package_checksum"] == package["package_checksum"]
    assert len(package["package_checksum"]) == 71

    latest = client.get(f"/projects/{project['project_id']}/packages/latest")
    archive = client.get(package["download_url"])
    assert latest.status_code == archive.status_code == 200
    assert latest.json() == replayed.json()
    assert archive.headers["content-type"] == "application/zip"
    assert package["package_id"] in archive.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        names = bundle.namelist()
        assert "AGENT.md" in names
        assert "package-manifest.json" in names
        assert not any(name.endswith(".env") for name in names)
    assert database.executions == {}
    assert database.execution_events == {}
    assert database.provider_operations == {}


def test_project_response_aggregates_uploaded_progress(product_client) -> None:
    client, _ = product_client
    project = _create(client)
    package = client.post(
        f"/projects/{project['project_id']}/packages"
    ).json()
    report = native_report(
        project_id=project["project_id"],
        package_id=package["package_id"],
        package_checksum=package["package_checksum"],
    )
    upload = client.post(
        f"/projects/{project['project_id']}/progress-reports",
        json=upload_envelope(report).to_dict(),
    )
    assert upload.status_code == 201
    fetched = client.get(f"/projects/{project['project_id']}").json()
    assert fetched["progress"]["latest_execution_round"] == 1
    assert fetched["progress"]["current_state_summary"] == (
        "Fictional catalog screening is recorded."
    )


def test_project_and_package_not_found(product_client) -> None:
    client, _ = product_client
    assert client.get("/projects/project-00000000000000000000000000000000").status_code == 404
    project = _create(client)
    assert (
        client.get(f"/projects/{project['project_id']}/packages/latest").status_code
        == 404
    )


def test_local_session_is_exact_package_scoped_and_revokeable(session_client) -> None:
    client, database = session_client
    project = _create(client)
    package = client.post(f"/projects/{project['project_id']}/packages").json()
    response = client.post(
        f"/projects/{project['project_id']}/local-sessions",
        json={
            "package_id": package["package_id"],
            "package_checksum": package["package_checksum"],
            "workflow_id": package["workflow_id"],
            "workflow_version": package["workflow_version"],
            "workflow_checksum": package["workflow_checksum"],
            "mode": "DEMO",
        },
    )
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    session = response.json()
    assert session["maximum_query_variants"] == 3
    identity = {
        "package_id": package["package_id"],
        "package_checksum": package["package_checksum"],
        "workflow_id": package["workflow_id"],
        "workflow_version": package["workflow_version"],
        "workflow_checksum": package["workflow_checksum"],
    }
    missing_bearer = client.get(
        f"/projects/{project['project_id']}/local-sessions/{session['session_id']}/progress-reports",
        params=identity,
    )
    assert missing_bearer.status_code == 401
    wrong_project = client.get(
        f"/projects/project-00000000000000000000000000000000/local-sessions/{session['session_id']}/progress-reports",
        params=identity,
        headers={"Authorization": f"Bearer {session['session_token']}"},
    )
    assert wrong_project.status_code == 403
    closed = client.delete(
        f"/projects/{project['project_id']}/local-sessions/{session['session_id']}",
        params=identity,
        headers={"Authorization": f"Bearer {session['session_token']}"},
    )
    assert closed.status_code == 204
    assert database.executions == {}
    assert database.execution_events == {}
    assert database.provider_operations == {}
