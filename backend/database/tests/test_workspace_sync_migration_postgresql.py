"""Destructive NIGHT-B4 migration qualification on an isolated database."""

from __future__ import annotations

import importlib
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.database.disposable import require_disposable_database


def test_b4_empty_populated_idempotent_downgrade_reupgrade_and_fail_closed() -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B4_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B4 migration database URL is required")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    migration = importlib.import_module(
        "backend.database.migrations.versions.20260806_0010_workspace_sync_acknowledgements"
    )
    try:
        require_disposable_database(
            engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0010")
        assert _revision(engine) == "20260806_0010"
        assert _count(engine, "local_workflow_capsule_artifacts") == 0
        assert _count(engine, "workspace_installation_acknowledgements") == 0

        command.downgrade(config, "20260806_0007")
        project_id = "project-00000000000000000000000000000000"
        package_id = f"literature-search-{project_id}-v0.5"
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO local_projects
                  (project_id,name,research_topic,selected_workflow,created_at,updated_at,
                   current_package_id,current_package_schema_version,current_package_checksum,
                   current_manifest_checksum,current_zip_checksum,current_workflow_id,
                   current_workflow_version,current_workflow_checksum,current_archive_storage_key,
                   current_package_file_count,current_package_size_bytes,current_package_generated_at)
                VALUES
                  (:project_id,'B4 fictional','Fictional topic','LITERATURE_SEARCH',
                   '2026-08-06T00:00:00Z','2026-08-06T01:00:00Z',:package_id,
                   'workflow-package/v0.1',:checksum,:checksum,:checksum,
                   'literature-search-local-experimental','0.3.0',:checksum,
                   'fictional/package.zip',29,1024,'2026-08-06T01:00:00Z')
            """), {
                "project_id": project_id,
                "package_id": package_id,
                "checksum": "sha256:" + "1" * 64,
            })
        legacy_before = _legacy(engine)
        command.upgrade(config, "20260806_0010")
        assert _legacy(engine) == legacy_before
        assert _count(engine, "local_workflow_capsule_artifacts") == 1
        with engine.connect() as connection:
            artifact = connection.execute(text("""
                SELECT project_id,workflow_instance_id,package_id,archive_checksum
                FROM local_workflow_capsule_artifacts
            """)).mappings().one()
        assert artifact["project_id"] == project_id
        assert artifact["package_id"] == package_id
        assert artifact["workflow_instance_id"].startswith("wfi-")
        assert artifact["archive_checksum"] == "sha256:" + "1" * 64

        with engine.begin() as connection:
            migration._backfill_legacy_artifacts(connection)
        assert _count(engine, "local_workflow_capsule_artifacts") == 1

        command.downgrade(config, "20260806_0009")
        assert _legacy(engine) == legacy_before
        assert "local_workflow_capsule_artifacts" not in inspect(engine).get_table_names()
        assert "workspace_installation_acknowledgements" not in inspect(engine).get_table_names()
        command.upgrade(config, "20260806_0010")
        assert _count(engine, "local_workflow_capsule_artifacts") == 1
        assert _legacy(engine) == legacy_before

        # A broken legacy binding aborts 0010 without leaving either new table.
        command.downgrade(config, "20260806_0009")
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE project_workflow_instances SET legacy_package_id=NULL"
            ))
        with pytest.raises(Exception, match="missing its deterministic Workflow Instance"):
            command.upgrade(config, "20260806_0010")
        assert _revision(engine) == "20260806_0009"
        assert "local_workflow_capsule_artifacts" not in inspect(engine).get_table_names()
        command.downgrade(config, "20260806_0007")
        command.upgrade(config, "20260806_0010")
        assert _revision(engine) == "20260806_0010"
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _count(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.scalar(text(f'SELECT count(*) FROM "{table}"'))


def _legacy(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT project_id,name,research_topic,selected_workflow,current_package_id,
                   current_package_checksum,current_manifest_checksum,current_zip_checksum,
                   created_at,updated_at FROM local_projects ORDER BY project_id
        """)).tuples())
