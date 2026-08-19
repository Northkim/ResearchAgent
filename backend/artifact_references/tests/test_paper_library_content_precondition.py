"""Forward Idea content-readiness agreement for exact Literature Artifacts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.application.errors import ApplicationValidationError
from backend.artifact_references.contracts import (
    PAPER_LIBRARY_QUALIFICATION_SCHEMA,
    ArtifactReference,
    ArtifactState,
)
from backend.artifact_references.service import ArtifactReferenceService
from backend.local_projects.contracts import LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.contracts import (
    ProjectWorkflowInstance,
    WorkflowInstanceDesiredState,
)
from backend.project_workspaces.presets import FULL_RESEARCH
from backend.project_workspaces.tests.test_generic_experiment_v5_workspace import (
    _seed_forward,
)
from backend.workflow_packages.serialization import canonical_hash
from backend.progress_reports.aggregation import ProjectProgressAggregationService


PROJECT_ID = "project-36363636363636363636363636363636"
ZERO_ID = "artifact-00000000000000000000000000000036"
ONE_ID = "artifact-11111111111111111111111111111136"
ZERO_HASH = "sha256:" + "0" * 64
ONE_HASH = "sha256:" + "1" * 64
NOW = datetime(2026, 8, 20, 3, tzinfo=UTC)


def _seed() -> tuple[InMemoryDatabase, str, str]:
    database = InMemoryDatabase()
    _seed_forward(database)
    uow = InMemoryUnitOfWork(database)
    project = LocalProject(
        project_id=PROJECT_ID,
        name="Disposable Idea precondition",
        research_topic="Deterministic paper count qualification",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-20T03:00:00Z",
        updated_at="2026-08-20T03:00:00Z",
        current_package=None,
    )
    uow.local_projects.add(project)
    ProjectWorkspaceApplicationService(
        unit_of_work=uow,
        clock=lambda: NOW,
        instance_id_factory=_instance_id,
    ).initialize_project_setup(project, FULL_RESEARCH, ())
    instances = uow.workflow_foundation.list_workflow_instances(PROJECT_ID)
    literature = next(
        item for item in instances
        if item.workflow_definition_id == "literature-search-local-experimental"
    )
    idea = next(
        item for item in instances
        if item.workflow_definition_id == "idea-discovery-local-experimental"
    )
    assert (idea.workflow_version, idea.capsule_version) == ("0.3.0", "0.4.0")
    for artifact_id, checksum in ((ZERO_ID, ZERO_HASH), (ONE_ID, ONE_HASH)):
        uow.artifact_references.add_artifact(ArtifactReference(
            artifact_id=artifact_id,
            project_id=PROJECT_ID,
            producer_workflow_instance_id=literature.workflow_instance_id,
            producer_progress_receipt_id=f"progress-receipt-{checksum[7:]}",
            producer_progress_report_id=f"prv2-{checksum[7:]}",
            producer_execution_round=1,
            producer_capsule_id=literature.capsule_id,
            producer_capsule_version=literature.capsule_version,
            artifact_type="selected-paper-library/v1",
            artifact_schema_version="selected-paper-library/v1",
            media_type="application/json",
            state=ArtifactState.LOCAL_AVAILABLE,
            relative_path=(
                "outputs/artifacts/selected-paper-library/"
                f"sha256-{checksum[7:]}.json"
            ),
            content_checksum=checksum,
            size_bytes=256,
            cloud_metadata_available=True,
            produced_at=NOW,
            retired_at=None,
            created_at=NOW,
            updated_at=NOW,
        ))
    uow.commit()
    return database, literature.workflow_instance_id, idea.workflow_instance_id


def _qualification(artifact_id: str, checksum: str, count: int) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
        "artifact_id": artifact_id,
        "artifact_checksum": checksum,
        "selected_count": count,
    }
    return {**payload, "qualification_checksum": canonical_hash(payload)}


def test_zero_paper_is_valid_artifact_but_not_forward_idea_input() -> None:
    database, _, idea_id = _seed()
    service = ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    )
    zero = _qualification(ZERO_ID, ZERO_HASH, 0)
    one = _qualification(ONE_ID, ONE_HASH, 1)
    assert service.report_content_qualification(
        project_id=PROJECT_ID, artifact_id=ZERO_ID, payload=zero
    )["payload"]["selected_count"] == 0
    zero_projection = ProjectProgressAggregationService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    ).project_progress(project_id=PROJECT_ID)
    zero_idea = next(
        item for item in zero_projection.instances
        if item.workflow_instance_id == idea_id
    )
    assert zero_idea.compatible_input_counts == {"paper_library": 0}
    assert service.report_content_qualification(
        project_id=PROJECT_ID, artifact_id=ONE_ID, payload=one
    )["payload"]["selected_count"] == 1

    candidates = service.list_compatible_artifacts(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=idea_id,
        requirement_key="paper_library",
        offset=0,
        limit=100,
    )
    assert [item["artifact_id"] for item in candidates["artifacts"]] == [ONE_ID]
    one_projection = ProjectProgressAggregationService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    ).project_progress(project_id=PROJECT_ID)
    one_idea = next(
        item for item in one_projection.instances
        if item.workflow_instance_id == idea_id
    )
    assert one_idea.compatible_input_counts == {"paper_library": 1}
    with pytest.raises(ApplicationValidationError) as zero_error:
        service.bind_dependency(
            project_id=PROJECT_ID,
            consumer_workflow_instance_id=idea_id,
            requirement_key="paper_library",
            artifact_id=ZERO_ID,
            idempotency_key="00000000-0000-4000-8000-000000000036",
        )
    assert getattr(zero_error.value, "code", None) == (
        "ARTIFACT_CONTENT_PRECONDITION_UNSATISFIED"
    )
    binding = service.bind_dependency(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=idea_id,
        requirement_key="paper_library",
        artifact_id=ONE_ID,
        idempotency_key="00000000-0000-4000-8000-000000000037",
    )
    plan = service.materialization_plan(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=idea_id,
    )
    assert binding.artifact_id == ONE_ID
    assert plan["artifacts"][0]["expected_checksum"] == ONE_HASH


def test_qualification_is_exact_immutable_and_presentation_cannot_substitute() -> None:
    database, _, idea_id = _seed()
    service = ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    )
    with pytest.raises(ApplicationValidationError) as absent:
        service.bind_dependency(
            project_id=PROJECT_ID,
            consumer_workflow_instance_id=idea_id,
            requirement_key="paper_library",
            artifact_id=ONE_ID,
            idempotency_key="00000000-0000-4000-8000-000000000038",
        )
    assert getattr(absent.value, "code", None) == (
        "ARTIFACT_CONTENT_PRECONDITION_UNSATISFIED"
    )
    payload = _qualification(ONE_ID, ONE_HASH, 1)
    first = service.report_content_qualification(
        project_id=PROJECT_ID, artifact_id=ONE_ID, payload=payload
    )
    replay = ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    ).report_content_qualification(
        project_id=PROJECT_ID, artifact_id=ONE_ID, payload=payload
    )
    assert replay == first
    with pytest.raises(ApplicationValidationError):
        service.report_content_qualification(
            project_id=PROJECT_ID,
            artifact_id=ONE_ID,
            payload=_qualification(ONE_ID, ZERO_HASH, 1),
        )


def test_historical_idea_0_2_keeps_its_published_type_compatibility() -> None:
    database, _, forward_idea_id = _seed()
    uow = InMemoryUnitOfWork(database)
    forward = uow.workflow_foundation.get_workflow_instance(forward_idea_id)
    assert forward is not None
    historical_id = "wfi-99999999999999999999999999999936"
    historical = replace(
        forward,
        workflow_instance_id=historical_id,
        workflow_version="0.2.0",
        capsule_id="capsule-3976596c49e3df30e08774233055bcce",
        capsule_version="0.3.0",
        display_name="Historical Idea Discovery",
        desired_state=WorkflowInstanceDesiredState.ACTIVE,
    )
    uow.workflow_foundation.add_workflow_instance(historical)
    uow.commit()
    service = ArtifactReferenceService(
        unit_of_work=InMemoryUnitOfWork(database), clock=lambda: NOW
    )
    candidates = service.list_compatible_artifacts(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=historical_id,
        requirement_key="paper_library",
        offset=0,
        limit=100,
    )
    assert {item["artifact_id"] for item in candidates["artifacts"]} == {
        ZERO_ID, ONE_ID,
    }


def test_http_reports_exact_qualification_and_lists_only_eligible_candidates() -> None:
    database, _, idea_id = _seed()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database)
    )))
    for artifact_id, checksum, count in (
        (ZERO_ID, ZERO_HASH, 0),
        (ONE_ID, ONE_HASH, 1),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/artifacts/{artifact_id}/content-qualification",
            json=_qualification(artifact_id, checksum, count),
        )
        assert response.status_code == 200, response.text
    candidates = client.get(
        f"/projects/{PROJECT_ID}/workflow-instances/{idea_id}/"
        "artifact-requirements/paper_library/candidates"
    )
    assert candidates.status_code == 200, candidates.text
    assert [item["artifact_id"] for item in candidates.json()["artifacts"]] == [
        ONE_ID
    ]
    page = client.get(f"/projects/{PROJECT_ID}/artifacts")
    by_id = {item["artifact_id"]: item for item in page.json()["artifacts"]}
    assert by_id[ZERO_ID]["content_qualification"]["payload"]["selected_count"] == 0
    assert by_id[ONE_ID]["content_qualification"]["payload"]["selected_count"] == 1


def _instance_id() -> str:
    _instance_id.counter += 1
    return f"wfi-{_instance_id.counter:032x}"


_instance_id.counter = 0
