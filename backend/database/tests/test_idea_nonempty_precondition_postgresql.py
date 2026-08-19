"""PostgreSQL publication qualification for the forward Idea precondition."""

from __future__ import annotations

from datetime import UTC, datetime
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.artifact_references.service import ArtifactReferenceService
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.local_projects.contracts import LocalProject
from backend.progress_reports.contracts import (
    ChainState,
    UploadedProgressReport,
    ValidationStatus,
)
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.presets import FULL_RESEARCH
from backend.project_workspaces.production_workflows import (
    IDEA_DISCOVERY_V0_4_CAPSULE_CHECKSUM,
    IDEA_DISCOVERY_V0_4_CAPSULE_ID,
    idea_discovery_v0_3_definition_version,
    idea_discovery_v0_3_requirement,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation
from backend.workflow_packages.serialization import canonical_hash


WORKFLOW_ID = "idea-discovery-local-experimental"
PROJECT_ID = "project-36363636363636363636363636363636"


def test_forward_idea_publication_is_exact_and_reversible(postgres_engine) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    _assert_head(postgres_engine, "20260820_0037")
    _assert_publication(postgres_engine)
    uow = SQLAlchemyUnitOfWork(create_session_factory(postgres_engine))
    try:
        ensure_production_workflow_foundation(
            uow, now=datetime(2026, 8, 20, tzinfo=UTC)
        )
        ensure_production_workflow_foundation(
            uow, now=datetime(2026, 8, 20, tzinfo=UTC)
        )
        uow.commit()
    finally:
        uow.close()
    columns = {
        item["name"]
        for item in inspect(postgres_engine).get_columns(
            "local_artifact_references"
        )
    }
    assert {
        "qualification_schema_id", "qualification_checksum",
        "qualification_json", "qualification_reported_at",
    } <= columns
    assert "content_precondition" in {
        item["name"]
        for item in inspect(postgres_engine).get_columns(
            "workflow_artifact_requirements"
        )
    }

    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(configuration, "20260820_0035")
    try:
        _assert_head(postgres_engine, "20260820_0035")
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("""
                SELECT count(*) FROM local_workflow_definition_versions
                WHERE workflow_definition_id=:workflow AND version='0.3.0'
            """), {"workflow": WORKFLOW_ID}) == 0
        assert "content_precondition" not in {
            item["name"]
            for item in inspect(postgres_engine).get_columns(
                "workflow_artifact_requirements"
            )
        }
    finally:
        command.upgrade(configuration, "20260820_0037")
    _assert_head(postgres_engine, "20260820_0037")
    _assert_publication(postgres_engine)


def test_postgresql_qualification_roundtrip_enforces_forward_candidates(
    postgres_engine,
) -> None:
    now = datetime(2026, 8, 20, 3, tzinfo=UTC)
    session_factory = create_session_factory(postgres_engine)
    uow = SQLAlchemyUnitOfWork(session_factory)
    project = LocalProject(
        project_id=PROJECT_ID,
        name="Disposable PostgreSQL Idea qualification",
        research_topic="Deterministic paper count",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-20T03:00:00Z",
        updated_at="2026-08-20T03:00:00Z",
        current_package=None,
    )
    uow.local_projects.add(project)
    ProjectWorkspaceApplicationService(
        unit_of_work=uow, clock=lambda: now, instance_id_factory=_instance_id,
    ).initialize_project_setup(project, FULL_RESEARCH, ())
    instances = uow.workflow_foundation.list_workflow_instances(PROJECT_ID)
    literature = next(
        item for item in instances
        if item.workflow_definition_id == "literature-search-local-experimental"
    )
    idea = next(
        item for item in instances if item.workflow_definition_id == WORKFLOW_ID
    )
    artifact_id = "artifact-36363636363636363636363636363636"
    checksum = "sha256:" + "3" * 64
    receipt_id = "progress-receipt-" + "3" * 64
    report_id = "prv2-" + "3" * 64
    uow.progress_reports.append(UploadedProgressReport(
        receipt_id=receipt_id,
        project_id=PROJECT_ID,
        workflow_instance_id=literature.workflow_instance_id,
        package_id="test-r1b2-literature-package",
        package_checksum=checksum,
        report_id=report_id,
        report_checksum=checksum,
        report_schema_version="progress-report/v0.2",
        original_report_checksum=checksum,
        original_report_size=1,
        original_report_media_type="application/json",
        original_storage_key="test/r1b2/literature-progress.json",
        envelope_checksum=checksum,
        uploaded_at=now.isoformat(),
        received_at=now.isoformat(),
        uploader_type="test-only",
        client_version="test-only/1.0",
        source_path_hint="memory/progress/reports/test.json",
        validation_status=ValidationStatus.ACCEPTED,
        validation_errors=(),
        validation_warnings=(),
        chain_state=ChainState.VALID_CHAIN,
        accepted_for_projection=True,
        normalized_record=None,
    ))
    uow.artifact_references.add_artifact(ArtifactReference(
        artifact_id=artifact_id,
        project_id=PROJECT_ID,
        producer_workflow_instance_id=literature.workflow_instance_id,
        producer_progress_receipt_id=receipt_id,
        producer_progress_report_id=report_id,
        producer_execution_round=1,
        producer_capsule_id=literature.capsule_id,
        producer_capsule_version=literature.capsule_version,
        artifact_type="selected-paper-library/v1",
        artifact_schema_version="selected-paper-library/v1",
        media_type="application/json",
        state=ArtifactState.LOCAL_AVAILABLE,
        relative_path="outputs/artifacts/selected-paper-library/sha256-" + "3" * 64 + ".json",
        content_checksum=checksum,
        size_bytes=256,
        cloud_metadata_available=True,
        produced_at=now,
        retired_at=None,
        created_at=now,
        updated_at=now,
    ))
    uow.commit()
    uow.close()

    payload = {
        "schema": "reagent.artifact-qualification.selected-paper-library/v0.1",
        "artifact_id": artifact_id,
        "artifact_checksum": checksum,
        "selected_count": 1,
    }
    payload["qualification_checksum"] = canonical_hash(payload)
    service_uow = SQLAlchemyUnitOfWork(session_factory)
    service = ArtifactReferenceService(unit_of_work=service_uow, clock=lambda: now)
    try:
        service.report_content_qualification(
            project_id=PROJECT_ID, artifact_id=artifact_id, payload=payload
        )
        candidates = service.list_compatible_artifacts(
            project_id=PROJECT_ID,
            consumer_workflow_instance_id=idea.workflow_instance_id,
            requirement_key="paper_library",
            offset=0,
            limit=100,
        )
    finally:
        service_uow.close()
    assert [item["artifact_id"] for item in candidates["artifacts"]] == [artifact_id]
    replay_uow = SQLAlchemyUnitOfWork(session_factory)
    try:
        stored = replay_uow.artifact_references.get_content_qualification(artifact_id)
        assert stored is not None
        assert stored.payload["selected_count"] == 1
        assert stored.artifact_checksum == checksum
    finally:
        replay_uow.close()


def _assert_head(engine, expected: str) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == expected


def _assert_publication(engine) -> None:
    now = datetime(2026, 8, 20, tzinfo=UTC)
    source_definition = idea_discovery_v0_3_definition_version(now)
    source_requirement = idea_discovery_v0_3_requirement(now)
    with engine.connect() as connection:
        row = connection.execute(text("""
            SELECT v.contract_checksum, c.capsule_id, c.capsule_version,
                   c.definition_checksum, r.content_precondition
            FROM local_workflow_definition_versions v
            JOIN local_workflow_capsule_versions c
              ON c.workflow_definition_id=v.workflow_definition_id
             AND c.workflow_version=v.version
            JOIN workflow_artifact_requirements r
              ON r.workflow_definition_id=v.workflow_definition_id
             AND r.workflow_version=v.version
            WHERE v.workflow_definition_id=:workflow AND v.version='0.3.0'
              AND r.requirement_key='paper_library'
        """), {"workflow": WORKFLOW_ID}).mappings().one()
    assert row["contract_checksum"] == source_definition.contract_checksum
    assert row["capsule_id"] == IDEA_DISCOVERY_V0_4_CAPSULE_ID
    assert row["capsule_version"] == "0.4.0"
    assert row["definition_checksum"] == IDEA_DISCOVERY_V0_4_CAPSULE_CHECKSUM
    assert row["content_precondition"] == dict(source_requirement.content_precondition)


def _instance_id() -> str:
    _instance_id.counter += 1
    return f"wfi-{_instance_id.counter:032x}"


_instance_id.counter = 0
