"""PostgreSQL persistence and concurrency evidence for typed Artifacts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import os
from threading import Barrier

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.application.errors import ApplicationNotFoundError
from backend.artifact_references.contracts import (
    ArtifactDeclaration,
    ArtifactPresentation,
    CompatibilityMode,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from backend.artifact_references.errors import ArtifactReferenceConflictError
from backend.artifact_references.service import ArtifactReferenceService
from backend.local_projects.contracts import LocalProject
from backend.database.orm import LocalArtifactReferenceORM, UploadedProgressReportORM
from backend.database.disposable import require_disposable_database
from backend.progress_reports.service import ProgressReportService
from backend.progress_reports.tests.factories import HASH_A, HASH_B, native_report, upload_envelope
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.contracts import (
    CoreCapabilityMaturity,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
)
from backend.research.adapters import LocalFilesystemArtifactStorage

PROJECT_ID = "project-71717171717171717171717171717171"
OTHER_PROJECT_ID = "project-72727272727272727272727272727272"
PRODUCER_ID = "wfi-73737373737373737373737373737373"
CONSUMER_ID = "wfi-74747474747474747474747474747474"
PRODUCER_DEFINITION = "test-b6-producer"
CONSUMER_DEFINITION = "test-b6-consumer"
PRODUCER_CAPSULE = "capsule-" + "7" * 32
CONSUMER_CAPSULE = "capsule-" + "8" * 32
ARTIFACT_ID = "artifact-" + "9" * 32
ARTIFACT_TYPE = "test.paper-library"
ARTIFACT_SCHEMA = "reagent.artifact.test-paper-library/v1.0"
NOW = datetime(2026, 8, 7, 12, tzinfo=UTC)


def test_gen_d_presentation_migration_downgrade_and_reupgrade() -> None:
    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL")
    identity = os.environ.get("REAGENT_TEST_DATABASE_IDENTITY")
    if not database_url or not identity:
        pytest.skip("dedicated disposable PostgreSQL database is required")
    engine = create_engine(database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    presentation_columns = {
        "presentation_schema_id", "presentation_checksum",
        "presentation_json", "presentation_reported_at",
    }
    try:
        require_disposable_database(
            engine, database_url=database_url, expected_identity=identity
        )
        assert _migration_revision(engine) == "20260817_0029"
        assert presentation_columns <= _artifact_columns(engine)
        command.downgrade(config, "20260817_0028")
        assert _migration_revision(engine) == "20260817_0028"
        assert presentation_columns.isdisjoint(_artifact_columns(engine))
        command.upgrade(config, "20260817_0029")
        assert _migration_revision(engine) == "20260817_0029"
        assert presentation_columns <= _artifact_columns(engine)
        checks = inspect(engine).get_check_constraints("local_artifact_references")
        presentation_checks = [
            item for item in checks
            if "presentation_" in str(item.get("sqltext", ""))
        ]
        assert len(presentation_checks) == 3
        assert any("octet_length" in item["sqltext"] for item in presentation_checks)
        assert any("sha256" in item["sqltext"] for item in presentation_checks)
    finally:
        engine.dispose()


def _artifact_columns(engine) -> set[str]:
    return {
        item["name"]
        for item in inspect(engine).get_columns("local_artifact_references")
    }


def _migration_revision(engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def test_postgresql_artifact_presentation_roundtrip_and_all_or_none_constraint(
    sql_uow_factory, tmp_path,
) -> None:
    _seed(sql_uow_factory)
    scope = sql_uow_factory()
    _progress_service(scope, tmp_path / "presentation-progress").upload(
        upload_envelope(_report()),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    scope.close()

    scope = sql_uow_factory()
    presentation = ArtifactPresentation(
        artifact_id=ARTIFACT_ID,
        artifact_checksum=HASH_B,
        schema_identity="reagent.artifact-presentation.experiment-record/v0.2",
        presentation_checksum=HASH_A,
        payload={"schema": "reagent.artifact-presentation.experiment-record/v0.2"},
        reported_at=NOW,
    )
    scope.artifact_references.add_presentation(presentation)
    scope.commit()
    scope.close()

    reloaded = sql_uow_factory()
    assert reloaded.artifact_references.get_presentation(ARTIFACT_ID) == presentation
    with pytest.raises(IntegrityError):
        reloaded.session.execute(text(
            "UPDATE local_artifact_references "
            "SET presentation_json = NULL WHERE artifact_id = :artifact_id"
        ), {"artifact_id": ARTIFACT_ID})
        reloaded.commit()
    reloaded.rollback()
    reloaded.close()


def test_postgresql_artifact_promotion_reload_immutability_and_rollback(
    sql_uow_factory, tmp_path,
) -> None:
    _seed(sql_uow_factory)
    report = _report()
    scope = sql_uow_factory()
    receipt = _progress_service(scope, tmp_path / "progress").upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    scope.close()

    reloaded = sql_uow_factory()
    artifact = reloaded.artifact_references.get_artifact(ARTIFACT_ID)
    assert artifact is not None
    assert artifact.producer_progress_receipt_id == receipt.receipt_id
    assert artifact.producer_workflow_instance_id == PRODUCER_ID
    assert artifact.content_checksum == HASH_B
    with pytest.raises(ArtifactReferenceConflictError):
        reloaded.artifact_references.add_artifact(
            replace(artifact, content_checksum=HASH_A)
        )
    rollback_artifact = replace(
        artifact,
        artifact_id="artifact-" + "a" * 32,
        relative_path="outputs/rollback-only.md",
    )
    reloaded.artifact_references.add_artifact(rollback_artifact)
    reloaded.rollback()
    reloaded.close()

    after_rollback = sql_uow_factory()
    assert after_rollback.artifact_references.get_artifact(
        rollback_artifact.artifact_id
    ) is None
    page = ArtifactReferenceService(
        unit_of_work=after_rollback, clock=lambda: NOW
    ).list_artifacts(
        project_id=PROJECT_ID,
        producer_workflow_instance_id=PRODUCER_ID,
        artifact_type=ARTIFACT_TYPE,
        state="LOCAL_AVAILABLE",
        offset=0,
        limit=25,
    )
    assert page["total"] == 1
    after_rollback.close()


def test_postgresql_concurrent_progress_retry_creates_one_artifact(
    sql_uow_factory, tmp_path,
) -> None:
    _seed(sql_uow_factory)
    report = _report()
    barrier = Barrier(2)
    storage_root = tmp_path / "concurrent-progress"

    def upload_once():
        scope = sql_uow_factory()
        try:
            barrier.wait(timeout=5)
            return _progress_service(scope, storage_root).upload(
                upload_envelope(report),
                workflow_instance_id=PRODUCER_ID,
                artifact_declarations=(_declaration(),),
            )
        finally:
            scope.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(executor.map(lambda _: upload_once(), range(2)))
    scope = sql_uow_factory()
    artifacts = scope.artifact_references.list_for_progress(receipts[0].receipt_id)
    reports = scope.progress_reports.list_for_project(
        PROJECT_ID, workflow_instance_id=PRODUCER_ID
    )
    scope.close()
    assert len(reports) == 1
    assert len(artifacts) == 1
    assert {item.receipt_id for item in receipts} == {reports[0].receipt_id}
    assert sorted(item.idempotent_replay for item in receipts) == [False, True]


def test_postgresql_dependency_binding_is_exact_idempotent_and_concurrent_safe(
    sql_uow_factory, tmp_path,
) -> None:
    _seed(sql_uow_factory)
    report = _report()
    producer_scope = sql_uow_factory()
    _progress_service(producer_scope, tmp_path / "dependency-progress").upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    producer_scope.close()

    barrier = Barrier(2)
    keys = (
        "00000000-0000-4000-8000-000000000061",
        "00000000-0000-4000-8000-000000000062",
    )

    def bind_once(key: str):
        scope = sql_uow_factory()
        try:
            service = ArtifactReferenceService(unit_of_work=scope, clock=lambda: NOW)
            barrier.wait(timeout=5)
            binding = service.bind_dependency(
                project_id=PROJECT_ID,
                consumer_workflow_instance_id=CONSUMER_ID,
                requirement_key="paper-library",
                artifact_id=ARTIFACT_ID,
                idempotency_key=key,
            )
            return ("accepted", binding.binding_id)
        except Exception as error:  # the losing unique race is the evidence
            return ("conflict", type(error).__name__)
        finally:
            scope.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(bind_once, keys))
    assert sorted(item[0] for item in outcomes) == ["accepted", "conflict"]

    scope = sql_uow_factory()
    service = ArtifactReferenceService(unit_of_work=scope, clock=lambda: NOW)
    page = service.list_dependencies(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
    )
    assert page["total"] == 1
    canonical = page["dependencies"][0]
    replay = service.bind_dependency(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
        requirement_key="paper-library",
        artifact_id=ARTIFACT_ID,
        idempotency_key=canonical["idempotency_key"],
    )
    assert replay.binding_id == canonical["binding_id"]
    plan = service.materialization_plan(
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=CONSUMER_ID,
    )
    assert plan["artifacts"][0]["artifact_id"] == ARTIFACT_ID
    assert plan["artifacts"][0]["expected_checksum"] == HASH_B
    scope.close()


def test_postgresql_cross_project_artifact_binding_fails_closed(
    sql_uow_factory, tmp_path,
) -> None:
    _seed(sql_uow_factory, include_other_project=True)
    report = _report()
    scope = sql_uow_factory()
    _progress_service(scope, tmp_path / "cross-project").upload(
        upload_envelope(report),
        workflow_instance_id=PRODUCER_ID,
        artifact_declarations=(_declaration(),),
    )
    scope.close()


def test_postgresql_artifact_page_scales_without_producer_or_progress_n_plus_one(
    sql_uow_factory,
) -> None:
    _seed(sql_uow_factory)
    scope = sql_uow_factory()
    producer_ids = [PRODUCER_ID]
    for index in range(1, 20):
        instance_id = "wfi-" + f"{0x8000 + index:032x}"
        producer_ids.append(instance_id)
        scope.workflow_foundation.add_workflow_instance(ProjectWorkflowInstance(
            workflow_instance_id=instance_id,
            project_id=PROJECT_ID,
            workflow_definition_id=PRODUCER_DEFINITION,
            workflow_version="1.0.0",
            capsule_id=PRODUCER_CAPSULE,
            capsule_version="1.0.0",
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name=f"Performance Producer {index + 1}",
            created_manifest_revision=1,
            retired_manifest_revision=None,
            legacy_package_id=None,
            created_at=NOW,
            updated_at=NOW,
        ))
    scope.session.flush()
    reports: list[UploadedProgressReportORM] = []
    artifacts: list[LocalArtifactReferenceORM] = []
    artifact_number = 0
    for producer_number, instance_id in enumerate(producer_ids, start=1):
        receipt_id = "progress-receipt-" + f"{producer_number:064x}"
        report_id = "prv2-" + f"{producer_number:064x}"
        checksum = "sha256:" + f"{producer_number:064x}"
        reports.append(UploadedProgressReportORM(
            receipt_id=receipt_id,
            project_id=PROJECT_ID,
            workflow_instance_id=instance_id,
            package_id=f"test-performance-package-{producer_number}",
            package_checksum=checksum,
            report_id=report_id,
            report_checksum=checksum,
            report_schema_version="progress-report/v0.2",
            original_report_checksum=checksum,
            original_report_size=1,
            original_report_media_type="application/json",
            original_storage_key=f"test/performance/{producer_number}.json",
            envelope_checksum=checksum,
            uploaded_at=NOW,
            received_at=NOW,
            uploader_type="test-only",
            client_version="test-only/1.0",
            source_path_hint="memory/progress/reports/test.json",
            validation_status="ACCEPTED",
            validation_errors_json=[],
            validation_warnings_json=[],
            chain_state="VALID_CHAIN",
            accepted_for_projection=True,
            normalized_record_json=None,
        ))
        for artifact_index in range(50):
            artifact_number += 1
            artifact_checksum = "sha256:" + f"{artifact_number:064x}"
            artifacts.append(LocalArtifactReferenceORM(
                artifact_id="artifact-" + f"{artifact_number:032x}",
                project_id=PROJECT_ID,
                producer_workflow_instance_id=instance_id,
                producer_progress_receipt_id=receipt_id,
                producer_progress_report_id=report_id,
                producer_execution_round=1,
                producer_capsule_id=PRODUCER_CAPSULE,
                producer_capsule_version="1.0.0",
                artifact_type=ARTIFACT_TYPE,
                artifact_schema_version=ARTIFACT_SCHEMA,
                media_type="application/json",
                state="LOCAL_AVAILABLE",
                relative_path=f"outputs/performance-{artifact_index:02d}.json",
                content_checksum=artifact_checksum,
                size_bytes=artifact_index,
                cloud_metadata_available=True,
                produced_at=NOW + timedelta(seconds=producer_number),
                retired_at=None,
                created_at=NOW,
                updated_at=NOW,
            ))
    scope.session.add_all(reports)
    scope.session.add_all(artifacts)
    scope.commit()

    statements: list[str] = []
    engine = scope.session.get_bind()

    def record_query(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        page = ArtifactReferenceService(
            unit_of_work=scope, clock=lambda: NOW
        ).list_artifacts(
            project_id=PROJECT_ID,
            producer_workflow_instance_id=producer_ids[-1],
            artifact_type=ARTIFACT_TYPE,
            state="LOCAL_AVAILABLE",
            offset=10,
            limit=25,
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_query)
        scope.close()
    assert page["total"] == 50
    assert len(page["artifacts"]) == 25
    assert all(
        item["producer_workflow_instance_id"] == producer_ids[-1]
        for item in page["artifacts"]
    )
    assert len(statements) <= 4

    scope = sql_uow_factory()
    service = ArtifactReferenceService(unit_of_work=scope, clock=lambda: NOW)
    with pytest.raises(ApplicationNotFoundError) as error:
        service.bind_dependency(
            project_id=OTHER_PROJECT_ID,
            consumer_workflow_instance_id=CONSUMER_ID,
            requirement_key="paper-library",
            artifact_id=ARTIFACT_ID,
            idempotency_key="00000000-0000-4000-8000-000000000063",
        )
    assert getattr(error.value, "code", None) == "WORKFLOW_INSTANCE_NOT_FOUND"
    scope.rollback()
    scope.close()


def _seed(sql_uow_factory, *, include_other_project: bool = False) -> None:
    scope = sql_uow_factory()
    projects = [
        LocalProject(
            project_id=PROJECT_ID,
            name="Fictional PostgreSQL Artifact Project",
            research_topic="Fictional typed handoff",
            selected_workflow="LITERATURE_SEARCH",
            created_at="2026-08-07T10:00:00Z",
            updated_at="2026-08-07T10:00:00Z",
            current_package=None,
        )
    ]
    if include_other_project:
        projects.append(LocalProject(
            project_id=OTHER_PROJECT_ID,
            name="Other fictional Project",
            research_topic="Cross-Project rejection",
            selected_workflow="LITERATURE_SEARCH",
            created_at="2026-08-07T10:00:00Z",
            updated_at="2026-08-07T10:00:00Z",
            current_package=None,
        ))
    for project in projects:
        scope.local_projects.add(project)
        ProjectWorkspaceApplicationService(
            unit_of_work=scope, clock=lambda: NOW
        ).initialize_project(project)
    for definition_id, name, checksum in (
        (PRODUCER_DEFINITION, "Test B6 Producer", HASH_A),
        (CONSUMER_DEFINITION, "Test B6 Consumer", HASH_B),
    ):
        scope.workflow_foundation.add_definition(WorkflowDefinition(
            workflow_definition_id=definition_id,
            display_name=name,
            description="Test-only B6 fixture",
            lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
            allows_multiple_instances=True,
            created_at=NOW,
            updated_at=NOW,
        ))
        scope.workflow_foundation.add_definition_version(WorkflowDefinitionVersion(
            workflow_definition_id=definition_id,
            version="1.0.0",
            contract_checksum=checksum,
            input_schema_id="test-input/v1",
            output_schema_id="test-output/v1",
            compatibility={},
            review_status=WorkflowReviewStatus.REVIEWED,
            core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
            published_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        ))
    scope.workflow_foundation.add_capsule_version(WorkflowCapsuleVersion(
        capsule_id=PRODUCER_CAPSULE,
        capsule_version="1.0.0",
        workflow_definition_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        definition_checksum="sha256:" + "7" * 64,
        archive_size_bytes=1,
        archive_media_type="application/zip",
        mutable_roots=("outputs",),
        capability_requirements=(),
        compatibility={"artifact_outputs": [{
            "artifact_type": ARTIFACT_TYPE,
            "artifact_schema_version": ARTIFACT_SCHEMA,
            "media_type": "text/markdown",
            "relative_path": "outputs/fictional_report.md",
            "progress_artifact_kind": "FICTIONAL_REPORT",
        }]},
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=NOW,
        updated_at=NOW,
    ))
    scope.workflow_foundation.add_capsule_version(WorkflowCapsuleVersion(
        capsule_id=CONSUMER_CAPSULE,
        capsule_version="1.0.0",
        workflow_definition_id=CONSUMER_DEFINITION,
        workflow_version="1.0.0",
        definition_checksum="sha256:" + "8" * 64,
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
        scope.workflow_foundation.add_workflow_instance(ProjectWorkflowInstance(
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
    scope.artifact_references.add_requirement(WorkflowArtifactRequirement(
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
    scope.commit()
    scope.close()


def _report():
    return native_report(
        workflow_id=PRODUCER_DEFINITION,
        workflow_version="1.0.0",
        project_id=PROJECT_ID,
    )


def _declaration() -> ArtifactDeclaration:
    return ArtifactDeclaration(
        artifact_id=ARTIFACT_ID,
        artifact_type=ARTIFACT_TYPE,
        artifact_schema_version=ARTIFACT_SCHEMA,
        media_type="text/markdown",
        relative_path="outputs/fictional_report.md",
        content_checksum=HASH_B,
        size_bytes=42,
        produced_at=datetime(2026, 8, 3, 1, 10, tzinfo=UTC),
    )


def _progress_service(scope, storage_root) -> ProgressReportService:
    artifacts = ArtifactReferenceService(unit_of_work=scope, clock=lambda: NOW)
    return ProgressReportService(
        repository=scope.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(storage_root),
        commit_callback=scope.commit,
        workflow_identity_resolver=lambda envelope, normalized, requested: (
            requested or PRODUCER_ID
        ),
        artifact_reference_service=artifacts,
        clock=lambda: NOW,
    )
