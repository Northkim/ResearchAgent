from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase
from backend.progress_reports.tests.factories import native_report, upload_envelope
from backend.project_workspaces.contracts import (
    CapsuleArtifactStatus,
    WorkflowCapsuleArtifact,
)

from .test_service import (
    ARTIFACT_ID,
    ARTIFACT_TYPE,
    CONSUMER_ID,
    PRODUCER_DEFINITION,
    PRODUCER_ID,
    PROJECT_ID,
    _declaration,
    _progress_service,
    _seed,
)


def test_project_artifact_api_is_scoped_paginated_and_repository_driven(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    progress, _ = _progress_service(uow, tmp_path)
    report = native_report(
        project_id=PROJECT_ID,
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
    )
    progress.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: _seedless_scope(database),
        artifact_storage=progress._storage,
    )))

    page = client.get(
        f"/projects/{PROJECT_ID}/artifacts",
        params={"workflow_instance_id": PRODUCER_ID, "artifact_type": ARTIFACT_TYPE},
    )
    instance_page = client.get(
        f"/projects/{PROJECT_ID}/workflow-instances/{PRODUCER_ID}/artifacts"
    )
    unknown = client.get(
        "/projects/project-99999999999999999999999999999999/artifacts"
    )

    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["artifacts"][0]["artifact_id"] == ARTIFACT_ID
    assert instance_page.json()["artifacts"] == page.json()["artifacts"]
    assert unknown.status_code == 404


def test_dependency_api_requires_specific_artifact_and_returns_plan(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    progress, _ = _progress_service(uow, tmp_path)
    report = native_report(
        project_id=PROJECT_ID,
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
    )
    progress.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: _seedless_scope(database),
        artifact_storage=progress._storage,
    )))
    payload = {
        "requirement_key": "paper-library",
        "artifact_id": ARTIFACT_ID,
        "idempotency_key": "00000000-0000-4000-8000-000000000007",
    }
    created = client.post(
        f"/projects/{PROJECT_ID}/workflow-instances/{CONSUMER_ID}/artifact-dependencies",
        json=payload,
    )
    replay = client.post(
        f"/projects/{PROJECT_ID}/workflow-instances/{CONSUMER_ID}/artifact-dependencies",
        json=payload,
    )
    plan = client.get(
        f"/projects/{PROJECT_ID}/workflow-instances/{CONSUMER_ID}/artifact-materialization-plan"
    )
    wrong_project = client.post(
        "/projects/project-99999999999999999999999999999999/"
        f"workflow-instances/{CONSUMER_ID}/artifact-dependencies",
        json={**payload, "idempotency_key": "00000000-0000-4000-8000-000000000008"},
    )

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == created.json()
    assert plan.status_code == 200
    assert plan.json()["artifacts"][0]["artifact_id"] == ARTIFACT_ID
    assert wrong_project.status_code == 404


def test_progress_http_promotion_is_additive_idempotent_and_conflict_detecting(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    seeded = _seed(database)
    progress, _ = _progress_service(seeded, tmp_path)
    report = native_report(
        project_id=PROJECT_ID,
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
    )
    seeded.workspace_sync.add_capsule_artifact(WorkflowCapsuleArtifact(
        capsule_artifact_id="capsule-artifact-" + "a" * 32,
        project_id=PROJECT_ID,
        workflow_instance_id=PRODUCER_ID,
        capsule_id="capsule-" + "2" * 32,
        capsule_version="1.0.0",
        package_id=report.package_id,
        package_schema_version="workflow-package/v0.1",
        package_checksum=report.package_checksum,
        manifest_checksum="sha256:" + "c" * 64,
        archive_checksum="sha256:" + "d" * 64,
        archive_size_bytes=1,
        file_count=1,
        archive_storage_key="test-only/b6-package.zip",
        status=CapsuleArtifactStatus.AVAILABLE,
        created_at=_declaration().produced_at,
        updated_at=_declaration().produced_at,
    ))
    seeded.commit()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: _seedless_scope(database),
        artifact_storage=progress._storage,
    )))
    path = f"/projects/{PROJECT_ID}/progress-reports"
    payload = {
        **upload_envelope(report).to_dict(),
        "workflow_instance_id": PRODUCER_ID,
        "artifact_declarations": [_declaration().canonical_payload()],
    }

    first = client.post(path, json=payload)
    replay = client.post(path, json=payload)
    changed = {
        **payload,
        "artifact_declarations": [{
            **payload["artifact_declarations"][0],
            "content_checksum": "sha256:" + "a" * 64,
        }],
    }
    conflict = client.post(path, json=changed)
    artifacts = client.get(f"/projects/{PROJECT_ID}/artifacts")

    assert first.status_code == 201, first.text
    assert replay.status_code == 200
    assert conflict.status_code == 409
    assert artifacts.json()["total"] == 1
    assert artifacts.json()["artifacts"][0]["artifact_id"] == ARTIFACT_ID


def _seedless_scope(database):
    from backend.persistence.adapters import InMemoryUnitOfWork

    return InMemoryUnitOfWork(database)
