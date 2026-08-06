"""Destructive NIGHT-B2 migration qualification on a dedicated database."""

from __future__ import annotations

import importlib
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.project_workspaces import legacy_workflow_instance_id


def test_b2_empty_populated_idempotent_downgrade_reupgrade_and_rollback() -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B2_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B2 migration database URL is required")
    if "reagent_night_b2" not in database_url:
        pytest.fail("migration qualification refuses a non-NIGHT-B2 database")

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0009")
        assert _revision(engine) == "20260806_0009"
        assert _count(engine, "projects") == 0
        assert _count(engine, "project_desired_manifests") == 0

        command.downgrade(config, "20260806_0008")
        rows = (
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
            for row in rows:
                connection.execute(text("""
                    INSERT INTO local_projects
                      (project_id,name,research_topic,selected_workflow,
                       created_at,updated_at,current_package_id)
                    VALUES (:project_id,:name,:topic,'LITERATURE_SEARCH',
                            '2026-08-06T00:00:00Z','2026-08-06T01:00:00Z',:package_id)
                """), row)
        # Re-run 0008 against populated state to obtain canonical B1 instances.
        command.downgrade(config, "20260806_0007")
        command.upgrade(config, "20260806_0008")
        legacy_before = _legacy_projects(engine)
        instance_ids = tuple(legacy_workflow_instance_id(row["project_id"]) for row in rows)

        command.upgrade(config, "20260806_0009")
        assert _legacy_projects(engine) == legacy_before
        assert _count(engine, "projects") == 2
        assert _count(engine, "project_desired_manifests") == 2
        assert _count(engine, "project_manifest_entries") == 2
        with engine.connect() as connection:
            manifests = connection.execute(text("""
                SELECT p.project_id,p.current_manifest_revision,
                       m.base_revision,e.workflow_instance_id
                FROM projects p
                JOIN project_desired_manifests m ON m.project_id=p.project_id
                  AND m.manifest_revision=p.current_manifest_revision
                JOIN project_manifest_entries e ON e.project_id=m.project_id
                  AND e.manifest_revision=m.manifest_revision
                ORDER BY p.project_id
            """)).mappings().all()
        assert [row["workflow_instance_id"] for row in manifests] == list(instance_ids)
        assert all(row["current_manifest_revision"] == 1 for row in manifests)
        assert all(row["base_revision"] == 0 for row in manifests)

        migration = importlib.import_module(
            "backend.database.migrations.versions.20260806_0009_desired_project_manifests"
        )
        with engine.begin() as connection:
            migration._backfill(connection)
        assert _count(engine, "projects") == 2
        assert _count(engine, "project_desired_manifests") == 2
        assert _count(engine, "project_manifest_entries") == 2

        command.downgrade(config, "20260806_0008")
        assert _legacy_projects(engine) == legacy_before
        assert "projects" not in inspect(engine).get_table_names()
        assert _instance_ids(engine) == instance_ids
        with engine.connect() as connection:
            restored_capsule = connection.execute(text("""
                SELECT capsule_id,capsule_version FROM project_workflow_instances
                WHERE project_id='project-ffffffffffffffffffffffffffffffff'
            """)).one()
        assert restored_capsule == (None, None)
        command.upgrade(config, "20260806_0009")
        assert _instance_ids(engine) == instance_ids
        assert _count(engine, "project_desired_manifests") == 2

        # A missing B1 instance aborts the entire transactional B2 migration.
        command.downgrade(config, "20260806_0008")
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM project_workflow_instances WHERE workflow_instance_id=:id"),
                {"id": instance_ids[0]},
            )
        with pytest.raises(Exception, match="legacy Workflow Instance missing"):
            command.upgrade(config, "20260806_0009")
        assert _revision(engine) == "20260806_0008"
        assert "projects" not in inspect(engine).get_table_names()
        command.downgrade(config, "20260806_0007")
        command.upgrade(config, "20260806_0009")
        assert _revision(engine) == "20260806_0009"
        assert _count(engine, "project_desired_manifests") == 2
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
        return tuple(connection.execute(text("""
            SELECT project_id,name,research_topic,selected_workflow,current_package_id,
                   created_at,updated_at FROM local_projects ORDER BY project_id
        """)).tuples())


def _instance_ids(engine):
    with engine.connect() as connection:
        return tuple(connection.scalars(text(
            "SELECT workflow_instance_id FROM project_workflow_instances ORDER BY project_id"
        )))
