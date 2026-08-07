from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.local_projects.contracts import LocalPackageMetadata, LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.contracts import CapsuleArtifactStatus, WorkflowCapsuleArtifact
from backend.project_workspaces.legacy import legacy_workflow_instance_id
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.workflow_packages.template import WORKFLOW_ID, WORKFLOW_VERSION

from .factories import HASH_A, HASH_B, HASH_C, native_report, upload_envelope

PROJECT_ID = "project-22222222222222222222222222222222"
LEGACY_PACKAGE_ID = "fictional-legacy-progress-package"
SECOND_PACKAGE_ID = "fictional-second-instance-package"
SECOND_PACKAGE_CHECKSUM = "sha256:" + "d" * 64


@pytest.fixture
def instance_progress_client(
    tmp_path,
) -> Iterator[tuple[TestClient, InMemoryDatabase, str]]:
    database = InMemoryDatabase()
    seed = InMemoryUnitOfWork(database)
    project = LocalProject(
        project_id=PROJECT_ID,
        name="Two independent searches",
        research_topic="Fictional public multi-instance topic",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-07T01:00:00Z",
        updated_at="2026-08-07T01:00:00Z",
        current_package=LocalPackageMetadata(
            package_id=LEGACY_PACKAGE_ID,
            package_schema_version="workflow-package/v0.1",
            package_checksum=HASH_C,
            manifest_checksum=HASH_A,
            zip_checksum=HASH_B,
            workflow_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            workflow_checksum=HASH_A,
            archive_storage_key="fictional/legacy.zip",
            file_count=1,
            package_size_bytes=1,
            generated_at="2026-08-07T01:00:00Z",
        ),
    )
    seed.local_projects.add(project)
    application = ProjectWorkspaceApplicationService(
        unit_of_work=seed,
        clock=lambda: datetime(2026, 8, 7, 1, 0, tzinfo=UTC),
        instance_id_factory=lambda: "wfi-22222222222222222222222222222222",
    )
    application.initialize_project(project)
    seed.commit()
    second = application.create_instance(
        project_id=PROJECT_ID,
        workflow_definition_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        capsule_id=next(iter(database.workflow_capsule_versions.values())).capsule_id,
        capsule_version="0.5.0",
        display_name="Literature Search B",
        base_revision=1,
    )
    artifact_uow = InMemoryUnitOfWork(database)
    artifact_uow.workspace_sync.add_capsule_artifact(
        WorkflowCapsuleArtifact(
            capsule_artifact_id="capsule-artifact-22222222222222222222222222222222",
            project_id=PROJECT_ID,
            workflow_instance_id=second.workflow_instance_id,
            capsule_id=second.capsule_id or "",
            capsule_version=second.capsule_version or "",
            package_id=SECOND_PACKAGE_ID,
            package_schema_version="workflow-package/v0.1",
            package_checksum=SECOND_PACKAGE_CHECKSUM,
            manifest_checksum=HASH_A,
            archive_checksum=HASH_B,
            archive_size_bytes=1,
            file_count=1,
            archive_storage_key="fictional/second.zip",
            status=CapsuleArtifactStatus.AVAILABLE,
            created_at=datetime(2026, 8, 7, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 8, 7, 1, 1, tzinfo=UTC),
        )
    )
    artifact_uow.commit()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "progress"),
        clock=lambda: datetime(2026, 8, 7, 2, 0, tzinfo=UTC),
    )
    with TestClient(create_app(container)) as client:
        yield client, database, second.workflow_instance_id


def test_two_same_definition_instances_keep_independent_progress(
    instance_progress_client,
) -> None:
    client, database, second_id = instance_progress_client
    legacy = native_report(
        project_id=PROJECT_ID,
        package_id=LEGACY_PACKAGE_ID,
        package_checksum=HASH_C,
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        current_state="Primary search remains independent.",
    )
    second = native_report(
        project_id=PROJECT_ID,
        package_id=SECOND_PACKAGE_ID,
        package_checksum=SECOND_PACKAGE_CHECKSUM,
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        current_state="Second search has separate evidence.",
    )
    first_response = client.post(
        f"/projects/{PROJECT_ID}/progress-reports",
        json=upload_envelope(legacy).to_dict(),
    )
    second_payload = upload_envelope(second).to_dict()
    second_payload["workflow_instance_id"] = second_id
    second_response = client.post(
        f"/projects/{PROJECT_ID}/progress-reports", json=second_payload
    )

    project = client.get(f"/projects/{PROJECT_ID}/progress").json()
    first_id = legacy_workflow_instance_id(PROJECT_ID)
    primary = client.get(
        f"/projects/{PROJECT_ID}/workflow-instances/{first_id}/progress"
    ).json()
    other = client.get(
        f"/projects/{PROJECT_ID}/workflow-instances/{second_id}/progress"
    ).json()

    assert first_response.status_code == second_response.status_code == 201
    assert len(database.progress_reports) == 2
    instance_ids = [item["workflow_instance_id"] for item in project["instances"]]
    assert set(instance_ids) == {first_id, second_id}
    assert instance_ids == [
        item["workflow_instance_id"]
        for item in client.get(f"/projects/{PROJECT_ID}/progress").json()["instances"]
    ]
    assert primary["history_total"] == other["history_total"] == 1
    assert primary["history"][0]["workflow_instance_id"] == first_id
    assert other["history"][0]["workflow_instance_id"] == second_id
    assert primary["projection"]["latest_summary"] != other["projection"]["latest_summary"]
    assert "percentage" not in project


def test_explicit_cross_instance_binding_fails_without_a_row(
    instance_progress_client,
) -> None:
    client, database, second_id = instance_progress_client
    report = native_report(
        project_id=PROJECT_ID,
        package_id=LEGACY_PACKAGE_ID,
        package_checksum=HASH_C,
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
    )
    payload = upload_envelope(report).to_dict()
    payload["workflow_instance_id"] = second_id

    response = client.post(f"/projects/{PROJECT_ID}/progress-reports", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROGRESS_WORKFLOW_IDENTITY_MISMATCH"
    assert database.progress_reports == {}


def test_project_progress_is_paginated_and_stably_ordered(
    instance_progress_client,
) -> None:
    client, _, second_id = instance_progress_client
    for round_number in (1, 2):
        previous = None
        if round_number == 2:
            # A separate Package/instance chain is sufficient for page-order proof.
            package_id = SECOND_PACKAGE_ID
            checksum = SECOND_PACKAGE_CHECKSUM
            instance_id = second_id
        else:
            package_id = LEGACY_PACKAGE_ID
            checksum = HASH_C
            instance_id = legacy_workflow_instance_id(PROJECT_ID)
        report = native_report(
            project_id=PROJECT_ID,
            package_id=package_id,
            package_checksum=checksum,
            workflow_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            previous=previous,
        )
        payload = upload_envelope(report).to_dict()
        payload["workflow_instance_id"] = instance_id
        assert client.post(f"/projects/{PROJECT_ID}/progress-reports", json=payload).status_code == 201
    page = client.get(
        f"/projects/{PROJECT_ID}/progress", params={"offset": 0, "limit": 1}
    ).json()
    assert page["history_total"] == 2
    assert len(page["history"]) == 1
    assert page["has_more_history"] is True
