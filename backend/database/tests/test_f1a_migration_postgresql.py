"""Destructive F1A upgrade/downgrade qualification on an isolated database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.api import ApplicationContainer, create_app
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.project_workspaces.tests.test_b7_multi_workflow import (
    qualify_real_multi_workflow_artifact_handoff,
)
from backend.research.adapters.local_artifact_storage import (
    LocalFilesystemArtifactStorage,
)

IDEA_ID = "idea-discovery-local-experimental"
OLD_IDEA_CAPSULE = "capsule-f07330db6f0d87f3fd482b698223ea75"
OLD_IDEA_CHECKSUM = "sha256:f07330db6f0d87f3fd482b698223ea75414ce087fac193de80f8e8522e9e6452"
NEW_IDEA_CAPSULE = "capsule-6b66289a38895ce0eba2f76cd7725176"
LS_CAPSULE = "capsule-e9e6a2e0aa46146818fb6123e03877f3"
LS_CHECKSUM = "sha256:e9e6a2e0aa46146818fb6123e03877f32abaa8745f9c0b3139572530ccd1b80d"


def test_f1a_empty_populated_downgrade_reupgrade_and_identity_stability(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_url = os.environ.get("REAGENT_NIGHT_F1A_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-F1A migration database URL is required")
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
        command.upgrade(config, "20260806_0014")
        assert _revision(engine) == "20260806_0014"
        assert _idea_versions(engine) == ("0.1.0", "0.2.0")
        assert _maturities(engine) == {"REVIEWED_CORE"}
        assert _capsule_checksum(engine, OLD_IDEA_CAPSULE) == OLD_IDEA_CHECKSUM
        assert _capsule_checksum(engine, LS_CAPSULE) == LS_CHECKSUM
        assert _capsule_checksum(engine, NEW_IDEA_CAPSULE).startswith("sha256:")
        assert _future_workflow_count(engine) == 0

        session_factory = create_session_factory(engine)
        container = ApplicationContainer(
            unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
            local_package_root=str(tmp_path / "cloud-packages"),
            artifact_storage=LocalFilesystemArtifactStorage(
                tmp_path / "progress-artifacts"
            ),
        )
        product_state = tmp_path / "product-state"
        product_state.mkdir()
        with TestClient(create_app(container)) as client:
            project_id = qualify_real_multi_workflow_artifact_handoff(
                client, product_state
            )
        preserved_state = _preserved_product_state(engine, project_id)
        assert {(item[1], item[3]) for item in preserved_state[0]} == {
            ("0.4.0", "0.6.0"),
            ("0.1.0", "0.1.0"),
        }
        assert len(preserved_state[1]) == 2
        assert len(preserved_state[2]) == 1

        command.downgrade(config, "20260806_0013")
        assert _revision(engine) == "20260806_0013"
        assert _idea_versions(engine) == ("0.1.0",)
        assert not _column_exists(engine, "core_capability_maturity")
        assert _capsule_checksum(engine, OLD_IDEA_CAPSULE) == OLD_IDEA_CHECKSUM
        assert _preserved_product_state(engine, project_id) == preserved_state

        command.upgrade(config, "20260806_0014")
        first_identity = _new_identity(engine)
        assert _project_exists(engine, project_id)
        assert _preserved_product_state(engine, project_id) == preserved_state
        command.upgrade(config, "20260806_0014")
        assert _new_identity(engine) == first_identity

        command.downgrade(config, "20260806_0013")
        assert _project_exists(engine, project_id)
        assert _preserved_product_state(engine, project_id) == preserved_state
        command.upgrade(config, "20260806_0014")
        assert _new_identity(engine) == first_identity
        assert _capsule_checksum(engine, OLD_IDEA_CAPSULE) == OLD_IDEA_CHECKSUM
        assert _preserved_product_state(engine, project_id) == preserved_state
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _idea_versions(engine) -> tuple[str, ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT version FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id ORDER BY version
        """), {"id": IDEA_ID}).scalars())


def _maturities(engine) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(text(
            "SELECT core_capability_maturity FROM local_workflow_definition_versions"
        )).scalars())


def _capsule_checksum(engine, capsule_id: str) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(text("""
            SELECT definition_checksum FROM local_workflow_capsule_versions
            WHERE capsule_id = :id
        """), {"id": capsule_id})


def _future_workflow_count(engine) -> int:
    with engine.connect() as connection:
        return connection.scalar(text("""
            SELECT count(*) FROM local_workflow_definitions
            WHERE workflow_definition_id IN (
              'writing-local-experimental', 'review-local-experimental',
              'experiment-local-experimental'
            )
        """))


def _column_exists(engine, column: str) -> bool:
    with engine.connect() as connection:
        return bool(connection.scalar(text("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name = 'local_workflow_definition_versions'
              AND column_name = :column
        """), {"column": column}))


def _new_identity(engine) -> tuple[str, str, str]:
    with engine.connect() as connection:
        version = connection.execute(text("""
            SELECT contract_checksum, core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id AND version = '0.2.0'
        """), {"id": IDEA_ID}).one()
        capsule = _capsule_checksum(engine, NEW_IDEA_CAPSULE)
        return version[0], version[1], str(capsule)


def _project_exists(engine, project_id: str) -> bool:
    with engine.connect() as connection:
        return bool(connection.scalar(text(
            "SELECT count(*) FROM local_projects WHERE project_id = :id"
        ), {"id": project_id}))


def _preserved_product_state(engine, project_id: str) -> tuple[tuple, tuple, tuple]:
    with engine.connect() as connection:
        instances = tuple(connection.execute(text("""
            SELECT workflow_instance_id, workflow_version, capsule_id,
                   capsule_version, desired_state
            FROM project_workflow_instances
            WHERE project_id = :project_id
            ORDER BY workflow_instance_id
        """), {"project_id": project_id}).tuples())
        progress = tuple(connection.execute(text("""
            SELECT receipt_id, workflow_instance_id, report_id, report_checksum,
                   original_report_checksum, accepted_for_projection
            FROM uploaded_progress_reports
            WHERE project_id = :project_id
            ORDER BY receipt_id
        """), {"project_id": project_id}).tuples())
        artifacts = tuple(connection.execute(text("""
            SELECT artifact_id, producer_workflow_instance_id,
                   producer_progress_report_id, producer_capsule_id,
                   producer_capsule_version, artifact_type,
                   artifact_schema_version, content_checksum, relative_path, state
            FROM local_artifact_references
            WHERE project_id = :project_id
            ORDER BY artifact_id
        """), {"project_id": project_id}).tuples())
    return instances, progress, artifacts
