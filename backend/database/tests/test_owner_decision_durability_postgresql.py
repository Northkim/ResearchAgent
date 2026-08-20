"""PostgreSQL qualification for forward durable Owner decisions."""

from __future__ import annotations

from datetime import UTC, datetime
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.project_workspaces.service import ensure_production_workflow_foundation


def _head(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _counts(engine) -> tuple[int, int, int]:
    with engine.connect() as connection:
        versions = connection.scalar(text("""
            SELECT count(*) FROM local_workflow_definition_versions
            WHERE (workflow_definition_id='literature-search-local-experimental'
                   AND version='0.5.0')
               OR (workflow_definition_id='idea-discovery-local-experimental'
                   AND version='0.4.0')
        """))
        capsules = connection.scalar(text("""
            SELECT count(*) FROM local_workflow_capsule_versions
            WHERE (capsule_id='capsule-5600c6c42c85d3a2ab8beb8e112216df'
                   AND capsule_version='0.7.0')
               OR (capsule_id='capsule-db831c40287135691c7c1c41a2a16934'
                   AND capsule_version='0.5.0')
        """))
        requirements = connection.scalar(text("""
            SELECT count(*) FROM workflow_artifact_requirements
            WHERE workflow_definition_id='idea-discovery-local-experimental'
              AND workflow_version='0.4.0' AND requirement_key='paper_library'
        """))
    return versions, capsules, requirements


def test_owner_decision_publication_is_exact_idempotent_and_reversible(
    postgres_engine,
) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (2, 2, 1)

    uow = SQLAlchemyUnitOfWork(create_session_factory(postgres_engine))
    try:
        timestamp = datetime(2026, 8, 20, tzinfo=UTC)
        ensure_production_workflow_foundation(uow, now=timestamp)
        ensure_production_workflow_foundation(uow, now=timestamp)
        uow.commit()
    finally:
        uow.close()
    assert _counts(postgres_engine) == (2, 2, 1)

    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(configuration, "20260820_0036")
    try:
        assert _head(postgres_engine) == "20260820_0036"
        assert _counts(postgres_engine) == (0, 0, 0)
    finally:
        command.upgrade(configuration, "20260820_0039")
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (2, 2, 1)
