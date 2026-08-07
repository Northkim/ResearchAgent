"""Destructive NIGHT-B6 migration qualification on an isolated database."""

from __future__ import annotations

import json
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_b6_empty_b5_populated_downgrade_reupgrade_and_preservation() -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B6_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B6 migration database URL is required")
    if "reagent_night_b6" not in database_url:
        pytest.fail("migration qualification refuses a non-NIGHT-B6 database")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    new_tables = {
        "local_artifact_references",
        "workflow_artifact_requirements",
        "project_artifact_dependency_bindings",
    }
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0012")
        assert _revision(engine) == "20260806_0012"
        assert new_tables <= set(inspect(engine).get_table_names())
        assert all(_count(engine, table) == 0 for table in new_tables)

        command.downgrade(config, "20260806_0007")
        first_project = "project-61616161616161616161616161616161"
        second_project = "project-62626262626262626262626262626262"
        checksum = "sha256:" + "6" * 64
        with engine.begin() as connection:
            _insert_project(connection, first_project, checksum)
            _insert_project(connection, second_project, checksum)
        command.upgrade(config, "20260806_0010")
        with engine.begin() as connection:
            _insert_progress(connection, first_project, checksum, "7")
            _insert_progress(connection, first_project, checksum, "8")
            _insert_progress(connection, second_project, checksum, "9")
        command.upgrade(config, "20260806_0011")
        progress_before = _progress_rows(engine)

        command.upgrade(config, "20260806_0012")
        assert _revision(engine) == "20260806_0012"
        assert _progress_rows(engine) == progress_before
        # B5 metadata has no ratified Artifact type/schema, so 0012 must not
        # guess a production type or promote historical rows.
        assert _count(engine, "local_artifact_references") == 0
        assert _count(engine, "workflow_artifact_requirements") == 0
        assert _count(engine, "project_artifact_dependency_bindings") == 0

        command.downgrade(config, "20260806_0011")
        assert _revision(engine) == "20260806_0011"
        assert new_tables.isdisjoint(inspect(engine).get_table_names())
        assert _progress_rows(engine) == progress_before
        command.upgrade(config, "20260806_0012")
        assert _revision(engine) == "20260806_0012"
        assert _progress_rows(engine) == progress_before
        assert all(_count(engine, table) == 0 for table in new_tables)
    finally:
        engine.dispose()


def _insert_project(connection, project_id: str, checksum: str) -> None:
    package_id = f"literature-search-{project_id}-v0.5"
    connection.execute(text(
        """
        INSERT INTO local_projects
          (project_id,name,research_topic,selected_workflow,created_at,updated_at,
           current_package_id,current_package_schema_version,current_package_checksum,
           current_manifest_checksum,current_zip_checksum,current_workflow_id,
           current_workflow_version,current_workflow_checksum,current_archive_storage_key,
           current_package_file_count,current_package_size_bytes,current_package_generated_at)
        VALUES
          (:project_id,'Legacy B6','Fictional topic','LITERATURE_SEARCH',
           '2026-08-06T00:00:00Z','2026-08-06T01:00:00Z',:package_id,
           'workflow-package/v0.1',:checksum,:checksum,:checksum,
           'literature-search-local-experimental','0.3.0',:checksum,
           'fictional/package.zip',29,1024,'2026-08-06T01:00:00Z')
        """
    ), {"project_id": project_id, "package_id": package_id, "checksum": checksum})


def _insert_progress(connection, project_id: str, checksum: str, digit: str) -> None:
    package_id = f"literature-search-{project_id}-v0.5"
    receipt_id = "progress-receipt-" + digit * 64
    normalized = {
        "project_id": project_id,
        "package_id": package_id,
        "package_checksum": checksum,
        "workflow_id": "literature-search-local-experimental",
        "workflow_version": "0.3.0",
        "output_artifacts": [{
            "relative_path": "outputs/selected_papers.json",
            "artifact_kind": "SELECTED_PAPER_LIBRARY",
            "media_type": "application/json",
            "checksum": checksum,
            "size": 128,
        }],
    }
    connection.execute(text(
        """
        INSERT INTO uploaded_progress_reports
          (receipt_id,project_id,package_id,package_checksum,report_id,
           report_checksum,report_schema_version,original_report_checksum,
           original_report_size,original_report_media_type,original_storage_key,
           envelope_checksum,uploaded_at,received_at,uploader_type,client_version,
           source_path_hint,validation_status,validation_errors_json,
           validation_warnings_json,chain_state,accepted_for_projection,
           normalized_record_json)
        VALUES
          (:receipt_id,:project_id,:package_id,:checksum,:report_id,:checksum,
           'progress-report/v0.2',:checksum,128,'application/json',
           'fictional/progress.json',:checksum,'2026-08-07T01:00:00Z',
           '2026-08-07T01:00:01Z','local-cli','fictional/1.0',
           'memory/progress/reports/fictional.json','ACCEPTED',CAST('[]' AS jsonb),
           CAST('[]' AS jsonb),'VALID_CHAIN',true,CAST(:normalized AS jsonb))
        """
    ), {
        "receipt_id": receipt_id,
        "project_id": project_id,
        "package_id": package_id,
        "checksum": checksum,
        "report_id": "prv2-" + digit * 64,
        "normalized": json.dumps(normalized),
    })


def _progress_rows(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(text(
            """
            SELECT receipt_id,project_id,workflow_instance_id,package_id,report_id,
                   report_checksum,original_report_checksum,uploaded_at,received_at,
                   normalized_record_json
            FROM uploaded_progress_reports ORDER BY receipt_id
            """
        )).tuples())


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _count(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
