"""E4 publication evidence for the exact Experiment-v5 downstream chain."""

from __future__ import annotations

from importlib import import_module
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text

from backend.database.disposable import require_disposable_database
from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_CHECKSUM, INITIAL_WRITING_CAPSULE_ID,
    REVIEW_CAPSULE_CHECKSUM, REVIEW_CAPSULE_ID,
    WRITING_REVISION_CAPSULE_CHECKSUM, WRITING_REVISION_CAPSULE_ID,
    workflow_checksum,
)

MIGRATION = "backend.database.migrations.versions.20260818_0032_forward_downstream_v5_chain"


def test_migration_identity_matches_forward_compiler_authority() -> None:
    migration = import_module(MIGRATION)
    assert migration.down_revision == "20260818_0031"
    expected = (
        ("initial-writing", "0.5.0", INITIAL_WRITING_CAPSULE_ID, INITIAL_WRITING_CAPSULE_CHECKSUM),
        ("review", "0.4.0", REVIEW_CAPSULE_ID, REVIEW_CAPSULE_CHECKSUM),
        ("revision", "0.6.0", WRITING_REVISION_CAPSULE_ID, WRITING_REVISION_CAPSULE_CHECKSUM),
    )
    assert [(item["role"], item["version"], item["capsule_id"], item["capsule"]) for item in migration.PUBLICATIONS] == list(expected)
    assert [item["contract"] for item in migration.PUBLICATIONS] == [workflow_checksum(role) for role, *_ in expected]


def test_forward_publication_is_exact_role_aware_and_reversible(postgres_engine) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(postgres_engine, database_url=database_url, expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"))
    config = Config("alembic.ini"); config.set_main_option("sqlalchemy.url", database_url)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260818_0032"
        rows = connection.execute(text("""
            SELECT workflow_definition_id, version, output_schema_id,
                   compatibility->>'writing_role' AS writing_role,
                   compatibility->>'default_project_setup' AS is_default
            FROM local_workflow_definition_versions
            WHERE (workflow_definition_id='writing-local-experimental' AND version IN ('0.5.0','0.6.0'))
               OR (workflow_definition_id='review-local-experimental' AND version='0.4.0')
            ORDER BY workflow_definition_id, version
        """)).mappings().all()
        requirements = connection.execute(text("""
            SELECT workflow_definition_id, workflow_version, requirement_key,
                   artifact_type, compatibility_mode, materialization_mode, required
            FROM workflow_artifact_requirements
            WHERE workflow_version IN ('0.5.0','0.6.0','0.4.0')
              AND artifact_type IN ('experiment-record/v5','manuscript-draft/v4','review-report/v3')
            ORDER BY workflow_definition_id, workflow_version, requirement_key
        """)).mappings().all()
    assert [dict(row) for row in rows] == [
        {"workflow_definition_id":"review-local-experimental","version":"0.4.0","output_schema_id":"review-report/v3","writing_role":None,"is_default":"true"},
        {"workflow_definition_id":"writing-local-experimental","version":"0.5.0","output_schema_id":"manuscript-draft/v4","writing_role":"INITIAL","is_default":"true"},
        {"workflow_definition_id":"writing-local-experimental","version":"0.6.0","output_schema_id":"manuscript-draft/v5","writing_role":"REVISION","is_default":"false"},
    ]
    assert all(row["compatibility_mode"] == "EXACT" and row["materialization_mode"] == "VERIFIED_COPY" for row in requirements)
    assert {(row["workflow_version"], row["artifact_type"], row["required"]) for row in requirements} >= {
        ("0.5.0", "experiment-record/v5", False), ("0.4.0", "manuscript-draft/v4", True),
        ("0.4.0", "experiment-record/v5", False), ("0.6.0", "manuscript-draft/v4", True),
        ("0.6.0", "review-report/v3", True), ("0.6.0", "experiment-record/v5", False),
    }
    command.downgrade(config, "20260818_0031")
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM local_workflow_definition_versions WHERE (workflow_definition_id='writing-local-experimental' AND version IN ('0.5.0','0.6.0')) OR (workflow_definition_id='review-local-experimental' AND version='0.4.0')")) == 0
    command.upgrade(config, "20260818_0032")
    with postgres_engine.connect() as connection:
        with pytest.raises(RuntimeError, match="already occupied"):
            import_module(MIGRATION)._assert_preconditions(connection)

