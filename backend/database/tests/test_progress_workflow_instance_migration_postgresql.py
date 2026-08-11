"""Destructive NIGHT-B5 Progress identity migration qualification."""

from __future__ import annotations

import importlib
import json
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.database.disposable import require_disposable_database
from backend.project_workspaces.legacy import legacy_workflow_instance_id


def test_b5_empty_populated_downgrade_reupgrade_and_fail_closed() -> None:
    database_url = os.environ.get("REAGENT_NIGHT_B5_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-B5 migration database URL is required")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    migration = importlib.import_module(
        "backend.database.migrations.versions.20260806_0011_progress_workflow_instances"
    )
    project_id = "project-55555555555555555555555555555555"
    package_id = "literature-search-project-55555555555555555555555555555555-v0.5"
    checksum = "sha256:" + "5" * 64
    receipt_id = "progress-receipt-" + "5" * 64
    second_receipt = "progress-receipt-" + "7" * 64
    second_project = "project-88888888888888888888888888888888"
    second_package = "literature-search-project-88888888888888888888888888888888-v0.5"
    empty_project = "project-99999999999999999999999999999999"
    try:
        require_disposable_database(
            engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0011")
        assert _revision(engine) == "20260806_0011"
        assert _count(engine, "uploaded_progress_reports") == 0

        command.downgrade(config, "20260806_0007")
        with engine.begin() as connection:
            _insert_project(connection, project_id, package_id, checksum)
            _insert_project(connection, second_project, second_package, checksum)
            _insert_project_without_package(connection, empty_project)
        command.upgrade(config, "20260806_0010")
        with engine.begin() as connection:
            _insert_progress(connection, receipt_id, project_id, package_id, checksum)
            _insert_progress(
                connection,
                "progress-receipt-" + "8" * 64,
                project_id,
                package_id,
                checksum,
            )
            _insert_progress(
                connection,
                second_receipt,
                second_project,
                second_package,
                checksum,
            )
        before = _progress_without_instance(engine, receipt_id)

        command.upgrade(config, "20260806_0011")
        assert _revision(engine) == "20260806_0011"
        assert _progress_without_instance(engine, receipt_id) == before
        with engine.connect() as connection:
            bound = connection.scalar(text(
                "SELECT workflow_instance_id FROM uploaded_progress_reports "
                "WHERE receipt_id=:receipt_id"
            ), {"receipt_id": receipt_id})
        assert bound == legacy_workflow_instance_id(project_id)
        with engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT workflow_instance_id FROM uploaded_progress_reports "
                "WHERE receipt_id=:receipt_id"
            ), {"receipt_id": second_receipt}) == legacy_workflow_instance_id(second_project)
            assert connection.scalar(text(
                "SELECT count(*) FROM uploaded_progress_reports "
                "WHERE project_id=:project_id"
            ), {"project_id": empty_project}) == 0
        with engine.begin() as connection:
            migration._backfill_legacy_progress(connection)
        assert _count(engine, "uploaded_progress_reports") == 3

        command.downgrade(config, "20260806_0010")
        assert "workflow_instance_id" not in {
            column["name"]
            for column in inspect(engine).get_columns("uploaded_progress_reports")
        }
        assert _progress_without_instance(engine, receipt_id) == before
        command.upgrade(config, "20260806_0011")
        assert _progress_without_instance(engine, receipt_id) == before
        assert _revision(engine) == "20260806_0011"

        # An anomalous Project/report without the deterministic B1 Instance
        # aborts the whole migration and leaves 0010 intact.
        command.downgrade(config, "20260806_0010")
        broken_project = "project-66666666666666666666666666666666"
        with engine.begin() as connection:
            connection.execute(text(
                """
                INSERT INTO local_projects
                  (project_id,name,research_topic,selected_workflow,created_at,updated_at)
                VALUES (:project_id,'Broken history','Fictional topic',
                        'LITERATURE_SEARCH','2026-08-07T00:00:00Z',
                        '2026-08-07T00:00:00Z')
                """
            ), {"project_id": broken_project})
            _insert_progress(
                connection,
                "progress-receipt-" + "6" * 64,
                broken_project,
                "broken-legacy-package",
                "sha256:" + "6" * 64,
            )
        with pytest.raises(Exception, match="missing its deterministic Workflow Instance"):
            command.upgrade(config, "20260806_0011")
        assert _revision(engine) == "20260806_0010"
        assert "workflow_instance_id" not in {
            column["name"]
            for column in inspect(engine).get_columns("uploaded_progress_reports")
        }
    finally:
        engine.dispose()


def _insert_project(connection, project_id: str, package_id: str, checksum: str) -> None:
    connection.execute(text(
        """
        INSERT INTO local_projects
          (project_id,name,research_topic,selected_workflow,created_at,updated_at,
           current_package_id,current_package_schema_version,current_package_checksum,
           current_manifest_checksum,current_zip_checksum,current_workflow_id,
           current_workflow_version,current_workflow_checksum,current_archive_storage_key,
           current_package_file_count,current_package_size_bytes,current_package_generated_at)
        VALUES
          (:project_id,'Legacy B5','Fictional topic','LITERATURE_SEARCH',
           '2026-08-06T00:00:00Z','2026-08-06T01:00:00Z',:package_id,
           'workflow-package/v0.1',:checksum,:checksum,:checksum,
           'literature-search-local-experimental','0.3.0',:checksum,
           'fictional/package.zip',29,1024,'2026-08-06T01:00:00Z')
        """
    ), {"project_id": project_id, "package_id": package_id, "checksum": checksum})


def _insert_project_without_package(connection, project_id: str) -> None:
    connection.execute(text(
        """
        INSERT INTO local_projects
          (project_id,name,research_topic,selected_workflow,created_at,updated_at)
        VALUES (:project_id,'Legacy B5 without Progress','Fictional topic',
                'LITERATURE_SEARCH','2026-08-06T00:00:00Z','2026-08-06T01:00:00Z')
        """
    ), {"project_id": project_id})


def _insert_progress(
    connection,
    receipt_id: str,
    project_id: str,
    package_id: str,
    checksum: str,
) -> None:
    normalized = {
        "project_id": project_id,
        "package_id": package_id,
        "package_checksum": checksum,
        "workflow_id": "literature-search-local-experimental",
        "workflow_version": "0.3.0",
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
        "report_id": "prv2-" + receipt_id[-64:],
        "normalized": json.dumps(normalized),
    })


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _count(engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.scalar(text(f'SELECT count(*) FROM "{table}"'))


def _progress_without_instance(engine, receipt_id: str):
    with engine.connect() as connection:
        return connection.execute(text(
            """
            SELECT receipt_id,project_id,package_id,package_checksum,report_id,
                   report_checksum,report_schema_version,original_report_checksum,
                   original_report_size,original_report_media_type,
                   original_storage_key,envelope_checksum,uploaded_at,received_at,
                   uploader_type,client_version,source_path_hint,validation_status,
                   validation_errors_json,validation_warnings_json,chain_state,
                   accepted_for_projection,normalized_record_json
            FROM uploaded_progress_reports WHERE receipt_id=:receipt_id
            """
        ), {"receipt_id": receipt_id}).one()
