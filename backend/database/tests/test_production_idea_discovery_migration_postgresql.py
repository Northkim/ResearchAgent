"""Destructive NIGHT-B7 seed qualification on an isolated PostgreSQL database."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.database.disposable import require_disposable_database

LS_ID = "literature-search-local-experimental"
IDEA_ID = "idea-discovery-local-experimental"


def test_b7_empty_b6_populated_downgrade_reupgrade_and_conflict_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B7_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B7 migration database URL is required")
    monkeypatch.setenv("REAGENT_DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    try:
        require_disposable_database(
            engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0013")
        assert _revision(engine) == "20260806_0013"
        assert _seed_identity(engine) == (
            (IDEA_ID, "0.1.0"),
            (LS_ID, "0.3.0"),
            (LS_ID, "0.4.0"),
        )
        assert _requirement_count(engine) == 1

        command.downgrade(config, "20260806_0012")
        assert _revision(engine) == "20260806_0012"
        assert _seed_identity(engine) == ((LS_ID, "0.3.0"),)
        assert _requirement_count(engine) == 0
        assert _count(engine, "local_artifact_references") == 0

        # A populated B6 database is preserved: the marker is outside the B7
        # seed rows and proves the data-only migration does not rewrite Projects.
        marker = "project-" + "7" * 32
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO local_projects
                  (project_id,name,research_topic,selected_workflow,created_at,updated_at)
                VALUES (:id,'Legacy B6','Fictional retained data','LITERATURE_SEARCH',
                        '2026-08-06T00:00:00Z','2026-08-06T00:00:00Z')
            """), {"id": marker})
        command.upgrade(config, "20260806_0013")
        assert _revision(engine) == "20260806_0013"
        assert _project_exists(engine, marker)
        first = _seed_identity(engine)
        command.upgrade(config, "20260806_0013")
        assert _seed_identity(engine) == first

        command.downgrade(config, "20260806_0012")
        assert _project_exists(engine, marker)
        # A conflicting owner-ratified stable identity must abort transactionally.
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO local_workflow_definitions
                  (workflow_definition_id,display_name,description,lifecycle,
                   allows_multiple_instances,created_at,updated_at)
                VALUES (:id,'Wrong identity','Conflict','AVAILABLE',true,
                        CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """), {"id": IDEA_ID})
        with pytest.raises(Exception):
            command.upgrade(config, "20260806_0013")
        assert _revision(engine) == "20260806_0012"
        with engine.begin() as connection:
            connection.execute(text(
                "DELETE FROM local_workflow_definitions WHERE workflow_definition_id = :id"
            ), {"id": IDEA_ID})
        command.upgrade(config, "20260806_0013")
        assert _revision(engine) == "20260806_0013"
        assert _project_exists(engine, marker)
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _seed_identity(engine) -> tuple[tuple[str, str], ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT workflow_definition_id, version
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id IN (:ls, :idea)
            ORDER BY workflow_definition_id, version
        """), {"ls": LS_ID, "idea": IDEA_ID}).tuples())


def _requirement_count(engine) -> int:
    with engine.connect() as connection:
        return connection.scalar(text("""
            SELECT count(*) FROM workflow_artifact_requirements
            WHERE workflow_definition_id = :id AND workflow_version = '0.1.0'
              AND requirement_key = 'paper_library'
        """), {"id": IDEA_ID})


def _count(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.scalar(text(f'SELECT count(*) FROM "{table}"'))


def _project_exists(engine, project_id: str) -> bool:
    with engine.connect() as connection:
        return bool(connection.scalar(text(
            "SELECT count(*) FROM local_projects WHERE project_id = :id"
        ), {"id": project_id}))
