"""Migration and Registry identity for the first Real Experiment publication."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork
from backend.project_workspaces.production_workflows import (
    REAL_EXPERIMENT_CAPSULE_CHECKSUM,
    REAL_EXPERIMENT_CAPSULE_ID,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation
from backend.workflow_packages.production_workflows import real_experiment_contract_checksum


def test_real_experiment_migration_matches_runtime_authority() -> None:
    migration = import_module(
        "backend.database.migrations.versions.20260814_0022_real_experiment_narrow_slice"
    )
    assert migration.down_revision == "20260813_0021"
    assert migration.VERSION == "0.4.0"
    assert migration.CONTRACT_CHECKSUM == real_experiment_contract_checksum()
    assert migration.CAPSULE_ID == REAL_EXPERIMENT_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.6.0"
    assert migration.CAPSULE_CHECKSUM == REAL_EXPERIMENT_CAPSULE_CHECKSUM


def test_real_experiment_registry_is_narrow_and_preserves_v1_capsule(
    sql_uow_factory, postgres_engine,
) -> None:
    uow: SQLAlchemyUnitOfWork = sql_uow_factory()
    ensure_production_workflow_foundation(uow, now=datetime(2026, 8, 14, tzinfo=UTC))
    uow.commit()
    uow.close()
    with postgres_engine.connect() as connection:
        versions = connection.execute(text("""
            SELECT version, output_schema_id, core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
              AND version IN ('0.3.0', '0.4.0') ORDER BY version
        """)).mappings().all()
        capsule = connection.execute(text("""
            SELECT capsule_id, capsule_version, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :capsule_id AND capsule_version = '0.6.0'
        """), {"capsule_id": REAL_EXPERIMENT_CAPSULE_ID}).mappings().one()
        artifact_count = connection.scalar(text("""
            SELECT count(*) FROM workflow_artifact_requirements
            WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
              AND workflow_version = '0.4.0'
        """))
        resource = connection.execute(text("""
            SELECT requirement_key, resource_kind, cardinality_min,
                   cardinality_max, required, allowed_providers_json
            FROM workflow_resource_requirements
            WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
              AND workflow_version = '0.4.0'
        """)).mappings().one()
    assert [item["version"] for item in versions] == ["0.3.0", "0.4.0"]
    assert versions[0]["output_schema_id"] == "experiment-record/v1"
    assert dict(versions[1]) == {"version": "0.4.0", "output_schema_id": "experiment-record/v2", "core_capability_maturity": "REVIEWED_CORE"}
    assert dict(capsule) == {"capsule_id": REAL_EXPERIMENT_CAPSULE_ID, "capsule_version": "0.6.0", "workflow_version": "0.4.0", "definition_checksum": REAL_EXPERIMENT_CAPSULE_CHECKSUM}
    assert artifact_count == 1
    assert dict(resource) == {"requirement_key": "source_repository", "resource_kind": "SOURCE_REPOSITORY", "cardinality_min": 1, "cardinality_max": 1, "required": True, "allowed_providers_json": ["GITHUB"]}
