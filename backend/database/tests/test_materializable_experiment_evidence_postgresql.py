"""E4 publication evidence for Experiment 0.7 / Capsule 0.10 / v5."""

from __future__ import annotations

from importlib import import_module
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text

from backend.database.disposable import require_disposable_database
from backend.workflow_packages.generic_experiment_v5_publication import (
    BOUNDED_EVIDENCE_SCHEMA, GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
    GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM, GENERIC_EXPERIMENT_V5_CAPSULE_ID,
    GENERIC_EXPERIMENT_V5_CAPSULE_VERSION, GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
    GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
)

MIGRATION = (
    "backend.database.migrations.versions."
    "20260818_0031_materializable_experiment_evidence"
)


def test_v5_migration_matches_compiler_authority() -> None:
    migration = import_module(MIGRATION)
    assert migration.down_revision == "20260817_0030"
    assert migration.VERSION == GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION
    assert migration.CONTRACT_CHECKSUM == GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM
    assert migration.CAPSULE_ID == GENERIC_EXPERIMENT_V5_CAPSULE_ID
    assert migration.CAPSULE_VERSION == GENERIC_EXPERIMENT_V5_CAPSULE_VERSION
    assert migration.CAPSULE_CHECKSUM == GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM
    assert migration.ARTIFACT_TYPE == GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE
    assert migration.EVIDENCE_SCHEMA == BOUNDED_EVIDENCE_SCHEMA


def test_v5_publication_downgrade_reupgrade_and_conflict(postgres_engine) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine, database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260820_0039"
    command.downgrade(config, "20260817_0030")
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260817_0030"
        assert connection.scalar(text("""
            SELECT count(*) FROM local_workflow_definition_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND version='0.7.0'
        """)) == 0
    command.upgrade(config, "20260820_0039")
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260820_0039"
        with pytest.raises(RuntimeError, match="already occupied"):
            import_module(MIGRATION)._assert_preconditions(connection)


def test_v5_registry_is_exact_and_does_not_advance_default(postgres_engine) -> None:
    with postgres_engine.connect() as connection:
        versions = connection.execute(text("""
            SELECT version, contract_checksum, output_schema_id,
                   compatibility->>'default_project_setup' AS is_default
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND version IN ('0.6.0','0.7.0') ORDER BY version
        """)).mappings().all()
        capsule = connection.execute(text("""
            SELECT capsule_id, capsule_version, definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.7.0'
        """)).mappings().one()
        requirement = connection.execute(text("""
            SELECT requirement_key, artifact_type, compatibility_mode,
                   materialization_mode, target_relative_path
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.7.0'
        """)).mappings().one()
    assert [dict(item) for item in versions] == [
        {
            "version": "0.6.0",
            "contract_checksum": "sha256:5e91401ee48979ff1e61453c8e304565c9c35ab317d511fdb458b82347dff517",
            "output_schema_id": "experiment-record/v4", "is_default": "true",
        },
        {
            "version": "0.7.0", "contract_checksum": GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
            "output_schema_id": "experiment-record/v5", "is_default": "false",
        },
    ]
    assert capsule["capsule_id"] == GENERIC_EXPERIMENT_V5_CAPSULE_ID
    assert capsule["capsule_version"] == "0.10.0"
    assert capsule["definition_checksum"] == GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM
    assert capsule["compatibility"]["evidence_authority"] == "LOCAL_FINAL_ARTIFACT"
    assert capsule["compatibility"]["presentation_companion_authoritative"] is False
    assert dict(requirement) == {
        "requirement_key": "research_idea",
        "artifact_type": "selected-research-idea/v1",
        "compatibility_mode": "EXACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": "inputs/selected-research-idea.json",
    }
