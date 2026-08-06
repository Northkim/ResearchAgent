"""Destructive migration qualification on a dedicated NIGHT-B1 database."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.project_workspaces import legacy_workflow_instance_id


def test_empty_populated_downgrade_and_reupgrade() -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B1_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B1 migration database URL is required")
    if "reagent_night_b1" not in database_url:
        pytest.fail("migration qualification refuses a non-NIGHT-B1 database")

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0008")
        assert _revision(engine) == "20260806_0008"
        assert _count(engine, "local_workflow_definitions") == 1
        assert _count(engine, "local_workflow_definition_versions") == 1
        assert _count(engine, "local_workflow_capsule_versions") == 1
        assert _count(engine, "project_workflow_instances") == 0

        command.downgrade(config, "20260806_0007")
        project_rows = (
            {
                "project_id": "project-00000000000000000000000000000000",
                "name": "Unicode 项目",
                "topic": "Topic α",
                "package_id": "literature-search-project-00000000000000000000000000000000-v0.5",
            },
            {
                "project_id": "project-ffffffffffffffffffffffffffffffff",
                "name": "No Package",
                "topic": "Topic beta",
                "package_id": None,
            },
        )
        with engine.begin() as connection:
            for row in project_rows:
                connection.execute(
                    text("""
                        INSERT INTO local_projects
                          (project_id, name, research_topic, selected_workflow,
                           created_at, updated_at, current_package_id)
                        VALUES (:project_id, :name, :topic, 'LITERATURE_SEARCH',
                                '2026-08-06T00:00:00Z', '2026-08-06T01:00:00Z',
                                :package_id)
                    """),
                    row,
                )
        before = _legacy_projects(engine)
        command.upgrade(config, "20260806_0008")
        assert _legacy_projects(engine) == before
        with engine.connect() as connection:
            instances = connection.execute(
                text("""
                    SELECT workflow_instance_id, project_id, capsule_id,
                           legacy_package_id
                    FROM project_workflow_instances ORDER BY project_id
                """)
            ).mappings().all()
        assert [row["workflow_instance_id"] for row in instances] == [
            legacy_workflow_instance_id(item["project_id"]) for item in project_rows
        ]
        assert instances[0]["capsule_id"] is not None
        assert instances[1]["capsule_id"] is None

        command.downgrade(config, "20260806_0007")
        assert _legacy_projects(engine) == before
        assert "project_workflow_instances" not in inspect(engine).get_table_names()
        command.upgrade(config, "20260806_0008")
        assert _legacy_projects(engine) == before
        assert _count(engine, "project_workflow_instances") == 2
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _count(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.scalar(text(f'SELECT count(*) FROM "{table}"'))


def _legacy_projects(engine):
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text("""
                    SELECT project_id, name, research_topic, selected_workflow,
                           current_package_id, created_at, updated_at
                    FROM local_projects ORDER BY project_id
                """)
            ).tuples()
        )
