from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.application.errors import ApplicationConflictError, ApplicationValidationError
from backend.artifact_references.contracts import (
    ArtifactDeclaration,
    ArtifactState,
    CompatibilityMode,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from backend.artifact_references.service import ArtifactReferenceService
from backend.local_projects.contracts import LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.service import ProgressReportService
from backend.progress_reports.tests.factories import (
    HASH_A,
    HASH_B,
    native_report,
    upload_envelope,
)
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.contracts import (
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
)
from backend.research.adapters import LocalFilesystemArtifactStorage

PROJECT_ID = "project-11111111111111111111111111111111"
PRODUCER_ID = "wfi-22222222222222222222222222222222"
CONSUMER_ID = "wfi-33333333333333333333333333333333"
PRODUCER_DEFINITION = "test-producer"
CONSUMER_DEFINITION = "test-consumer"
PRODUCER_CAPSULE = "capsule-" + "2" * 32
CONSUMER_CAPSULE = "capsule-" + "3" * 32
ARTIFACT_ID = "artifact-" + "4" * 32
ARTIFACT_TYPE = "test.paper-library"
ARTIFACT_SCHEMA = "reagent.artifact.test-paper-library/v1.0"
NOW = datetime(2026, 8, 7, 12, tzinfo=UTC)


def _seed(database: InMemoryDatabase) -> InMemoryUnitOfWork:
    uow = InMemoryUnitOfWork(database)
    project = LocalProject(
        project_id=PROJECT_ID,
        name="Fictional Artifact Project",
        research_topic="Fictional typed handoff",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-07T10:00:00Z",
        updated_at="2026-08-07T10:00:00Z",
        current_package=None,
    )
    uow.local_projects.add(project)
    ProjectWorkspaceApplicationService(
        unit_of_work=uow, clock=lambda: NOW
    ).initialize_project(project)
    for definition_id, name in (
        (PRODUCER_DEFINITION, "Test Producer"),
        (CONSUMER_DEFINITION, "Test Consumer"),
    ):
        uow.workflow_foundation.add_definition(WorkflowDefinition(
            workflow_definition_id=definition_id,
            display_name=name,
            description="Test-only fixture",
            lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
            allows_multiple_instances=True,
            created_at=NOW,
            updated_at=NOW,
        ))
        uow.workflow_foundation.add_definition_version(WorkflowDefinitionVersion(
            workflow_definition_id=definition_id,
            version="1.0.0",
            contract_checksum=(HASH_A if definition_id == PRODUCER_DEFINITION else HASH_B),
            input_schema_id="test-input/v1",
            output_schema_id="test-output/v1",
            compatibility={},
            review_status=WorkflowReviewStatus.REVIEWED,
            published_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        ))
    uow.workflow_foundation.add_capsule_version(WorkflowCapsuleVersion(
        capsule_id=PRODUCER_CAPSULE,
        capsule_version="1.0.0",
        workflow_definition_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        definition_checksum="sha256:" + "2" * 64,
        archive_size_bytes=1,
        archive_media_type="application/zip",
        mutable_roots=("outputs",),
        capability_requirements=(),
        compatibility={
            "artifact_outputs": [{
                "artifact_type": ARTIFACT_TYPE,
                "artifact_schema_version": ARTIFACT_SCHEMA,
                "media_type": "text/markdown",
                "relative_path": "outputs/fictional_report.md",
                "progress_artifact_kind": "FICTIONAL_REPORT",
            }]
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=NOW,
        updated_at=NOW,
    ))
    uow.workflow_foundation.add_capsule_version(WorkflowCapsuleVersion(
        capsule_id=CONSUMER_CAPSULE,
        capsule_version="1.0.0",
        workflow_definition_id=CONSUMER_DEFINITION,
        workflow_version="1.0.0",
        definition_checksum="sha256:" + "3" * 64,
        archive_size_bytes=1,
        archive_media_type="application/zip",
        mutable_roots=("inputs",),
        capability_requirements=(),
        compatibility={},
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=NOW,
        updated_at=NOW,
    ))
    for instance_id, definition_id, capsule_id, name in (
        (PRODUCER_ID, PRODUCER_DEFINITION, PRODUCER_CAPSULE, "Producer"),
        (CONSUMER_ID, CONSUMER_DEFINITION, CONSUMER_CAPSULE, "Consumer"),
    ):
        uow.workflow_foundation.add_workflow_instance(ProjectWorkflowInstance(
            workflow_instance_id=instance_id,
            project_id=PROJECT_ID,
            workflow_definition_id=definition_id,
            workflow_version="1.0.0",
            capsule_id=capsule_id,
            capsule_version="1.0.0",
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name=name,
            created_manifest_revision=1,
            retired_manifest_revision=None,
            legacy_package_id=None,
            created_at=NOW,
            updated_at=NOW,
        ))
    uow.artifact_references.add_requirement(WorkflowArtifactRequirement(
        workflow_definition_id=CONSUMER_DEFINITION,
        workflow_version="1.0.0",
        requirement_key="paper-library",
        artifact_type=ARTIFACT_TYPE,
        compatibility_mode=CompatibilityMode.EXACT,
        schema_constraint=ARTIFACT_SCHEMA,
        cardinality_min=1,
        cardinality_max=1,
        required=True,
        materialization_mode=MaterializationMode.VERIFIED_COPY,
        target_relative_path="inputs/paper-library/fictional_report.md",
        created_at=NOW,
        updated_at=NOW,
    ))
    uow.commit()
    return InMemoryUnitOfWork(database)


def _progress_service(uow, tmp_path):
    artifacts = ArtifactReferenceService(unit_of_work=uow, clock=lambda: NOW)
    return ProgressReportService(
        repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(tmp_path / "progress"),
        commit_callback=uow.commit,
        workflow_identity_resolver=lambda envelope, normalized, requested: requested or PRODUCER_ID,
        artifact_reference_service=artifacts,
        clock=lambda: NOW,
    ), artifacts


def _declaration(**changes) -> ArtifactDeclaration:
    values = {
        "artifact_id": ARTIFACT_ID,
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": ARTIFACT_SCHEMA,
        "media_type": "text/markdown",
        "relative_path": "outputs/fictional_report.md",
        "content_checksum": HASH_B,
        "size_bytes": 42,
        "produced_at": datetime(2026, 8, 3, 1, 10, tzinfo=UTC),
    }
    values.update(changes)
    return ArtifactDeclaration(**values)


def test_progress_promotes_exact_artifact_and_retry_is_idempotent(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    service, artifacts = _progress_service(uow, tmp_path)
    report = native_report(
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        project_id=PROJECT_ID,
    )

    first = service.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    replay_uow = InMemoryUnitOfWork(database)
    replay, replay_artifacts = _progress_service(replay_uow, tmp_path)
    second = replay.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )

    page = replay_artifacts.list_artifacts(
        project_id=PROJECT_ID,
        producer_workflow_instance_id=PRODUCER_ID,
        artifact_type=ARTIFACT_TYPE,
        state=None,
        offset=0,
        limit=25,
    )
    assert first.receipt_id == second.receipt_id
    assert second.idempotent_replay
    assert page["total"] == 1
    artifact = page["artifacts"][0]
    assert artifact["producer_progress_receipt_id"] == first.receipt_id
    assert artifact["producer_workflow_instance_id"] == PRODUCER_ID
    assert artifact["content_checksum"] == HASH_B
    assert len(database.local_artifact_references) == 1


def test_progress_artifact_mutation_unknown_type_and_cross_instance_fail_closed(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    service, _ = _progress_service(uow, tmp_path)
    report = native_report(
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        project_id=PROJECT_ID,
    )
    service.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    replay, _ = _progress_service(InMemoryUnitOfWork(database), tmp_path)
    with pytest.raises(ApplicationConflictError):
        replay.upload(
            upload_envelope(report),
            workflow_instance_id=PRODUCER_ID,
            artifact_declarations=(_declaration(content_checksum=HASH_A),),
        )

    other_database = InMemoryDatabase()
    other_uow = _seed(other_database)
    other, _ = _progress_service(other_uow, tmp_path / "other")
    with pytest.raises(ApplicationValidationError, match="type"):
        other.upload(
            upload_envelope(report),
            workflow_instance_id=PRODUCER_ID,
            artifact_declarations=(_declaration(artifact_type="test.unknown"),),
        )
    assert other_database.progress_reports == {}
    assert other_database.local_artifact_references == {}


def test_exact_dependency_binding_plan_and_explicit_rebind(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    progress, service = _progress_service(uow, tmp_path)
    report = native_report(
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        project_id=PROJECT_ID,
    )
    progress.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    binding = service.bind_dependency(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
        requirement_key="paper-library",
        artifact_id=ARTIFACT_ID,
        idempotency_key="00000000-0000-4000-8000-000000000006",
    )
    replay = service.bind_dependency(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
        requirement_key="paper-library",
        artifact_id=ARTIFACT_ID,
        idempotency_key="00000000-0000-4000-8000-000000000006",
    )
    plan = service.materialization_plan(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
    )

    assert replay == binding
    assert plan["artifacts"][0]["artifact_id"] == ARTIFACT_ID
    assert plan["artifacts"][0]["expected_checksum"] == HASH_B
    assert plan["artifacts"][0]["target_relative_path"].startswith("inputs/")
    dependency_page = service.list_dependencies(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
    )
    assert dependency_page["total"] == 1
    assert len(dependency_page["dependencies"]) == 1


def test_no_production_artifact_type_is_inferred_from_literature_metadata(tmp_path) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    legacy_instance = next(
        item
        for item in uow.workflow_foundation.list_workflow_instances(PROJECT_ID)
        if item.workflow_definition_id == "literature-search-local-experimental"
    )
    service, _ = _progress_service(uow, tmp_path)
    report = native_report(project_id=PROJECT_ID)
    with pytest.raises(ApplicationValidationError) as error:
        service.upload(
            upload_envelope(report),
            workflow_instance_id=legacy_instance.workflow_instance_id,
            artifact_declarations=(_declaration(),),
        )
    assert getattr(error.value, "code", None) == "ARTIFACT_TYPE_UNKNOWN"
    assert database.local_artifact_references == {}


def test_dependency_is_exact_not_latest_and_retired_producer_history_is_preserved(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    uow = _seed(database)
    progress, service = _progress_service(uow, tmp_path)
    report = native_report(
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        project_id=PROJECT_ID,
    )
    progress.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    first = uow.artifact_references.get_artifact(ARTIFACT_ID)
    assert first is not None
    second = replace(
        first,
        artifact_id="artifact-" + "5" * 32,
        producer_progress_receipt_id="test-only-second-progress",
        producer_progress_report_id="test-only-second-report",
        relative_path="outputs/fictional_report_second.md",
        content_checksum=HASH_A,
    )
    uow.artifact_references.add_artifact(second)
    uow.workflow_foundation.save_workflow_instance(replace(
        uow.workflow_foundation.get_workflow_instance(PRODUCER_ID),
        desired_state=WorkflowInstanceDesiredState.RETIRED,
        retired_manifest_revision=2,
        updated_at=NOW,
    ))
    uow.commit()
    binding = service.bind_dependency(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
        requirement_key="paper-library",
        artifact_id=ARTIFACT_ID,
        idempotency_key="00000000-0000-4000-8000-000000000009",
    )
    plan = service.materialization_plan(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
    )
    assert binding.artifact_id == ARTIFACT_ID
    assert plan["artifacts"][0]["artifact_id"] == ARTIFACT_ID
    assert plan["artifacts"][0]["artifact_id"] != second.artifact_id

    other_database = InMemoryDatabase()
    other_uow = _seed(other_database)
    other_progress, _ = _progress_service(other_uow, tmp_path / "stale")
    other_progress.upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    stale = other_uow.artifact_references.get_artifact(ARTIFACT_ID)
    assert stale is not None
    other_database.local_artifact_references[ARTIFACT_ID] = replace(
        stale, state=ArtifactState.STALE
    )
    stale_uow = InMemoryUnitOfWork(other_database)
    other_service = ArtifactReferenceService(unit_of_work=stale_uow, clock=lambda: NOW)
    with pytest.raises(ApplicationValidationError) as error:
        other_service.bind_dependency(
            project_id=PROJECT_ID,
            consumer_workflow_instance_id=CONSUMER_ID,
            requirement_key="paper-library",
            artifact_id=ARTIFACT_ID,
            idempotency_key="00000000-0000-4000-8000-000000000010",
        )
    assert getattr(error.value, "code", None) == "DEPENDENCY_UNRESOLVED"
