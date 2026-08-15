"""Migration and Registry identity for the first Real Review publication."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork
from backend.project_workspaces.production_workflows import (
    REAL_REVIEW_CAPSULE_CHECKSUM,
    REAL_REVIEW_CAPSULE_ID,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation
from backend.workflow_packages.production_workflows import real_review_contract_checksum


def test_real_review_migration_matches_runtime_authority() -> None:
    migration = import_module(
        "backend.database.migrations.versions.20260815_0025_real_review_evidence_audit"
    )
    assert migration.down_revision == "20260815_0024"
    assert migration.VERSION == "0.3.0"
    assert migration.CONTRACT_CHECKSUM == real_review_contract_checksum()
    assert migration.CAPSULE_ID == REAL_REVIEW_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.5.0"
    assert migration.CAPSULE_CHECKSUM == REAL_REVIEW_CAPSULE_CHECKSUM


def test_real_review_registry_is_narrow_and_preserves_v1(
    sql_uow_factory, postgres_engine,
) -> None:
    uow: SQLAlchemyUnitOfWork = sql_uow_factory()
    ensure_production_workflow_foundation(
        uow, now=datetime(2026, 8, 15, tzinfo=UTC)
    )
    uow.commit()
    uow.close()
    with postgres_engine.connect() as connection:
        versions = connection.execute(text("""
            SELECT version, output_schema_id, core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = 'review-local-experimental'
              AND version IN ('0.2.0', '0.3.0') ORDER BY version
        """)).mappings().all()
        capsule = connection.execute(text("""
            SELECT capsule_id, capsule_version, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :capsule_id AND capsule_version = '0.5.0'
        """), {"capsule_id": REAL_REVIEW_CAPSULE_ID}).mappings().one()
        requirements = connection.execute(text("""
            SELECT requirement_key, artifact_type, required, target_relative_path
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id = 'review-local-experimental'
              AND workflow_version = '0.3.0' ORDER BY requirement_key
        """)).mappings().all()
    assert [item["version"] for item in versions] == ["0.2.0", "0.3.0"]
    assert versions[0]["output_schema_id"] == "review-report/v1"
    assert dict(versions[1]) == {
        "version": "0.3.0",
        "output_schema_id": "review-report/v2",
        "core_capability_maturity": "REVIEWED_CORE",
    }
    assert dict(capsule) == {
        "capsule_id": REAL_REVIEW_CAPSULE_ID,
        "capsule_version": "0.5.0",
        "workflow_version": "0.3.0",
        "definition_checksum": REAL_REVIEW_CAPSULE_CHECKSUM,
    }
    assert [
        (item["requirement_key"], item["artifact_type"], item["required"])
        for item in requirements
    ] == [
        ("experiment_record", "experiment-record/v2", False),
        ("literature_library", "selected-paper-library/v1", False),
        ("manuscript", "manuscript-draft/v2", True),
        ("research_idea", "selected-research-idea/v1", False),
    ]
