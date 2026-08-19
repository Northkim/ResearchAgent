"""PostgreSQL qualification for exact Workflow input-setup decisions."""

from __future__ import annotations

from datetime import UTC, datetime
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.artifact_references.contracts import WorkflowInputSetupDecision
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.local_projects.contracts import LocalProject
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.presets import FULL_RESEARCH


PROJECT_ID = "project-35353535353535353535353535353535"
NOW = datetime(2026, 8, 20, 2, tzinfo=UTC)


def test_input_setup_decision_roundtrip_and_migration_reversibility(
    postgres_engine,
) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    session_factory = create_session_factory(postgres_engine)
    uow = SQLAlchemyUnitOfWork(session_factory)
    project = LocalProject(
        project_id=PROJECT_ID,
        name="Disposable optional evidence decision",
        research_topic="Deterministic test-only topic",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-20T02:00:00Z",
        updated_at="2026-08-20T02:00:00Z",
        current_package=None,
    )
    uow.local_projects.add(project)
    ProjectWorkspaceApplicationService(
        unit_of_work=uow,
        clock=lambda: NOW,
        instance_id_factory=_instance_id,
    ).initialize_project_setup(project, FULL_RESEARCH, ())
    review = next(
        item
        for item in uow.workflow_foundation.list_workflow_instances(PROJECT_ID)
        if item.workflow_definition_id == "review-local-experimental"
    )
    decision = WorkflowInputSetupDecision(
        decision_id="input-decision-" + "4" * 32,
        project_id=PROJECT_ID,
        consumer_workflow_instance_id=review.workflow_instance_id,
        consumer_workflow_definition_id=review.workflow_definition_id,
        consumer_workflow_version=review.workflow_version,
        binding_set_checksum="sha256:" + "5" * 64,
        omitted_optional_requirement_keys=("experiment_record", "research_idea"),
        decision="CONTINUE_WITHOUT_OPTIONAL_EVIDENCE",
        idempotency_key="00000000-0000-4000-8000-000000000035",
        decision_checksum="sha256:" + "6" * 64,
        decided_at=NOW,
    )
    uow.artifact_references.add_input_setup_decision(decision)
    uow.commit()
    uow.close()

    replay = SQLAlchemyUnitOfWork(session_factory)
    assert replay.artifact_references.list_input_setup_decisions(
        PROJECT_ID, review.workflow_instance_id
    ) == (decision,)
    replay.close()

    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(configuration, "20260819_0034")
    try:
        assert not inspect(postgres_engine).has_table(
            "project_workflow_input_setup_decisions"
        )
    finally:
        command.upgrade(configuration, "20260820_0035")
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260820_0035"
        )
    assert inspect(postgres_engine).has_table(
        "project_workflow_input_setup_decisions"
    )


def _instance_id() -> str:
    _instance_id.counter += 1
    return f"wfi-{_instance_id.counter:032x}"


_instance_id.counter = 0
