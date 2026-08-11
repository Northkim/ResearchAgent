"""Destructive F1B migration cycle qualification on an isolated database."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import bindparam, create_engine, text

from backend.api import ApplicationContainer, create_app
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.database.orm import Base
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import (
    qualify_full_scaffold_chain,
)
from backend.research.adapters import LocalFilesystemArtifactStorage

F1B_IDS = (
    "writing-local-experimental",
    "review-local-experimental",
    "reproduction-experiment-local-experimental",
)


def test_f1b_empty_populated_downgrade_reupgrade_is_deterministic(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    database_url = os.environ.get("REAGENT_NIGHT_F1B_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-F1B migration database URL is required")
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
        _truncate_qualification_database(engine)
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0014")
        baseline = _f1a_identity(engine)
        command.upgrade(config, "20260806_0015")
        first = _f1b_identity(engine)
        assert _revision(engine) == "20260806_0015"
        assert len(first) == 3
        assert all(row[3:] == ("AVAILABLE", True, "SCAFFOLD_CORE", "REVIEWED") for row in first)
        assert _requirement_counts(engine) == {
            "writing-local-experimental": 5,
            "review-local-experimental": 3,
            "reproduction-experiment-local-experimental": 2,
        }
        assert _f1a_identity(engine) == baseline

        command.downgrade(config, "20260806_0014")
        assert _revision(engine) == "20260806_0014"
        assert _f1b_identity(engine) == ()
        assert _f1a_identity(engine) == baseline

        command.upgrade(config, "20260806_0015")
        assert _f1b_identity(engine) == first
        assert _f1a_identity(engine) == baseline
        command.upgrade(config, "20260806_0015")
        assert _f1b_identity(engine) == first

        session_factory = create_session_factory(engine)
        uow_factory = lambda: SQLAlchemyUnitOfWork(session_factory)
        client = TestClient(create_app(ApplicationContainer(
            unit_of_work_factory=uow_factory,
            artifact_storage=LocalFilesystemArtifactStorage(
                tmp_path / "artifact-metadata-originals"
            ),
            local_package_root=str(tmp_path / "cloud-packages"),
        )))
        qualify_full_scaffold_chain(
            client,
            tmp_path / "sql-chain",
            uow_factory,
            seed_progress_parent=lambda artifact: _seed_progress_parent(
                engine, artifact
            ),
        )
    finally:
        engine.dispose()


def _truncate_qualification_database(engine) -> None:
    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    with engine.begin() as connection:
        connection.execute(text(
            f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"
        ))


def _seed_progress_parent(engine, artifact) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO uploaded_progress_reports
              (receipt_id, project_id, workflow_instance_id, package_id,
               package_checksum, report_id, report_checksum,
               report_schema_version, original_report_checksum,
               original_report_size, original_report_media_type,
               original_storage_key, envelope_checksum, uploaded_at,
               received_at, uploader_type, client_version, source_path_hint,
               validation_status, validation_errors_json,
               validation_warnings_json, chain_state,
               accepted_for_projection, normalized_record_json)
            VALUES
              (:receipt_id, :project_id, :instance_id, :package_id,
               :checksum, :report_id, :checksum, 'progress-report/v0.2',
               :checksum, 2, 'application/json', :storage_key, :checksum,
               :created_at, :created_at, 'f1b-synthetic-fixture',
               'f1b-test/0.1.0', :source_path, 'ACCEPTED',
               CAST('[]' AS jsonb), CAST('[]' AS jsonb), 'VALID_CHAIN', true, NULL)
        """), {
            "receipt_id": artifact.producer_progress_receipt_id,
            "project_id": artifact.project_id,
            "instance_id": artifact.producer_workflow_instance_id,
            "package_id": "f1b-synthetic-upstream-" + artifact.artifact_id[-1],
            "checksum": "sha256:" + artifact.artifact_id[-1] * 64,
            "report_id": artifact.producer_progress_report_id,
            "storage_key": "f1b/synthetic/" + artifact.artifact_id + ".json",
            "created_at": artifact.created_at,
            "source_path": "memory/progress/f1b-synthetic.json",
        })


def _revision(engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def _f1b_identity(engine) -> tuple[tuple, ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT d.workflow_definition_id, v.contract_checksum,
                   c.definition_checksum, d.lifecycle,
                   d.allows_multiple_instances, v.core_capability_maturity,
                   v.review_status
            FROM local_workflow_definitions d
            JOIN local_workflow_definition_versions v
              ON v.workflow_definition_id = d.workflow_definition_id
            JOIN local_workflow_capsule_versions c
              ON c.workflow_definition_id = d.workflow_definition_id
             AND c.workflow_version = v.version
            WHERE d.workflow_definition_id IN :ids
            ORDER BY d.workflow_definition_id
        """).bindparams(bindparam("ids", expanding=True)), {
            "ids": F1B_IDS
        }).tuples())


def _requirement_counts(engine) -> dict[str, int]:
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT workflow_definition_id, count(*)
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id IN :ids
            GROUP BY workflow_definition_id
        """).bindparams(bindparam("ids", expanding=True)), {
            "ids": F1B_IDS
        }).tuples().all()
        return dict(rows)


def _f1a_identity(engine) -> tuple[tuple, ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT workflow_definition_id, version, contract_checksum,
                   core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id IN (
              'literature-search-local-experimental',
              'idea-discovery-local-experimental'
            )
            ORDER BY workflow_definition_id, version
        """)).tuples())
