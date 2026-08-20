"""E4 publication evidence for Experiment 0.8 / Capsule 0.11."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.database.repositories.workflow_foundation import (
    _capsule_content,
    _definition_version_content,
    _workflow_skill_pin_content,
)
from backend.project_workspaces.generic_harness_foundation import (
    artifact_requirement,
    capsule_version,
    definition_version,
    skill_pin,
)
from backend.project_workspaces.service import (
    _requirement_content,
    ensure_production_workflow_foundation,
)
from backend.workflow_packages.generic_harness_publication import (
    GENERIC_HARNESS_CAPSULE_CHECKSUM,
    GENERIC_HARNESS_CAPSULE_ID,
    GENERIC_HARNESS_CAPSULE_VERSION,
    GENERIC_HARNESS_CONTRACT_CHECKSUM,
    GENERIC_HARNESS_WORKFLOW_VERSION,
)
from backend.workflow_packages.production_workflows import EXPERIMENT_WORKFLOW_ID
from backend.workflow_packages.serialization import to_json_value

MIGRATION = (
    "backend.database.migrations.versions."
    "20260820_0038_generic_harness_experiment"
)


def _head(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _counts(engine) -> tuple[int, int, int, int]:
    parameters = {"id": EXPERIMENT_WORKFLOW_ID, "version": "0.8.0"}
    with engine.connect() as connection:
        return (
            connection.scalar(text("""
                SELECT count(*) FROM local_workflow_definition_versions
                WHERE workflow_definition_id=:id AND version=:version
            """), parameters),
            connection.scalar(text("""
                SELECT count(*) FROM local_workflow_capsule_versions
                WHERE workflow_definition_id=:id AND workflow_version=:version
            """), parameters),
            connection.scalar(text("""
                SELECT count(*) FROM workflow_definition_version_skill_pins
                WHERE workflow_definition_id=:id AND workflow_version=:version
            """), parameters),
            connection.scalar(text("""
                SELECT count(*) FROM workflow_artifact_requirements
                WHERE workflow_definition_id=:id AND workflow_version=:version
            """), parameters),
        )


def test_migration_identity_matches_generic_harness_source_authority() -> None:
    migration = import_module(MIGRATION)
    assert migration.down_revision == "20260820_0037"
    assert (
        migration.VERSION,
        migration.CONTRACT_CHECKSUM,
        migration.CAPSULE_ID,
        migration.CAPSULE_VERSION,
        migration.CAPSULE_CHECKSUM,
    ) == (
        GENERIC_HARNESS_WORKFLOW_VERSION,
        GENERIC_HARNESS_CONTRACT_CHECKSUM,
        GENERIC_HARNESS_CAPSULE_ID,
        GENERIC_HARNESS_CAPSULE_VERSION,
        GENERIC_HARNESS_CAPSULE_CHECKSUM,
    )
    now = datetime(2026, 8, 20, tzinfo=UTC)
    assert migration._definition_compatibility() == to_json_value(
        definition_version(now).compatibility
    )
    assert migration._capsule_compatibility() == to_json_value(
        capsule_version(now).compatibility
    )
    assert tuple(migration._artifact_outputs()) == tuple(
        definition_version(now).compatibility["artifact_outputs"]
    )


def test_generic_harness_publication_is_exact_idempotent_and_reversible(
    postgres_engine,
) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (1, 1, 1, 1)
    now = datetime(2026, 8, 20, tzinfo=UTC)
    session_factory = create_session_factory(postgres_engine)
    uow = SQLAlchemyUnitOfWork(session_factory)
    try:
        published_definition = uow.workflow_foundation.get_definition_version(
            EXPERIMENT_WORKFLOW_ID, GENERIC_HARNESS_WORKFLOW_VERSION
        )
        published_capsule = uow.workflow_foundation.get_capsule_version(
            GENERIC_HARNESS_CAPSULE_ID, GENERIC_HARNESS_CAPSULE_VERSION
        )
        published_pins = uow.workflow_foundation.list_workflow_skill_pins(
            EXPERIMENT_WORKFLOW_ID, GENERIC_HARNESS_WORKFLOW_VERSION
        )
        published_requirement = uow.artifact_references.get_requirement(
            EXPERIMENT_WORKFLOW_ID,
            GENERIC_HARNESS_WORKFLOW_VERSION,
            "research_idea",
        )
        assert published_definition is not None
        assert published_capsule is not None
        assert published_requirement is not None
        assert _definition_version_content(published_definition) == (
            _definition_version_content(definition_version(now))
        )
        assert _capsule_content(published_capsule) == _capsule_content(
            capsule_version(now)
        )
        assert tuple(map(_workflow_skill_pin_content, published_pins)) == (
            _workflow_skill_pin_content(skill_pin(now)),
        )
        assert _requirement_content(published_requirement) == _requirement_content(
            artifact_requirement(now)
        )
        ensure_production_workflow_foundation(uow, now=now)
        ensure_production_workflow_foundation(uow, now=now)
        uow.commit()
    finally:
        uow.close()
    assert _counts(postgres_engine) == (1, 1, 1, 1)

    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(configuration, "20260820_0037")
    try:
        assert _head(postgres_engine) == "20260820_0037"
        assert _counts(postgres_engine) == (0, 0, 0, 0)
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("""
                SELECT definition_checksum FROM local_workflow_capsule_versions
                WHERE workflow_definition_id=:id AND workflow_version='0.7.0'
                  AND capsule_version='0.10.0'
            """), {"id": EXPERIMENT_WORKFLOW_ID}) == (
                "sha256:cd7ff18e9857b6d20fbe9ba2ccab7ba6"
                "9a0883b3164627dcd12d07e6eb634ad4"
            )
    finally:
        command.upgrade(configuration, "20260820_0039")
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (1, 1, 1, 1)
