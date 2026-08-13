"""Migration/registry identity for the Experiment interactive Capsule."""

from __future__ import annotations

from importlib import import_module
from datetime import UTC, datetime

from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork
from backend.project_workspaces.production_workflows import (
    EXPERIMENT_V0_3_CAPSULE_CHECKSUM,
    EXPERIMENT_V0_4_CAPSULE_CHECKSUM,
    EXPERIMENT_V0_4_CAPSULE_ID,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation


def test_experiment_bootstrap_migration_matches_registry_and_preserves_old_pin() -> None:
    migration = import_module(
        "backend.database.migrations.versions."
        "20260813_0019_experiment_interactive_bootstrap_capsule"
    )
    assert migration.down_revision == "20260811_0018"
    assert migration.EXPERIMENT_VERSION == "0.3.0"
    assert migration.OLD_CAPSULE_VERSION == "0.3.0"
    assert migration.OLD_CAPSULE_CHECKSUM == EXPERIMENT_V0_3_CAPSULE_CHECKSUM
    assert migration.CAPSULE_ID == EXPERIMENT_V0_4_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.4.0"
    assert migration.CAPSULE_CHECKSUM == EXPERIMENT_V0_4_CAPSULE_CHECKSUM


def test_experiment_bootstrap_capsule_is_seeded_without_replacing_0_3(
    sql_uow_factory, postgres_engine,
) -> None:
    uow: SQLAlchemyUnitOfWork = sql_uow_factory()
    ensure_production_workflow_foundation(
        uow, now=datetime(2026, 8, 13, tzinfo=UTC)
    )
    uow.commit()
    uow.close()
    with postgres_engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT capsule_id, capsule_version, workflow_version,
                   definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id =
                  'reproduction-experiment-local-experimental'
              AND capsule_version IN ('0.3.0', '0.4.0')
            ORDER BY capsule_version
        """)).mappings().all()
    assert len(rows) == 2
    old, current = (dict(row) for row in rows)
    assert old["capsule_version"] == "0.3.0"
    assert old["definition_checksum"] == EXPERIMENT_V0_3_CAPSULE_CHECKSUM
    assert "harness_integration" not in old["compatibility"]
    assert current["capsule_id"] == EXPERIMENT_V0_4_CAPSULE_ID
    assert current["capsule_version"] == "0.4.0"
    assert current["workflow_version"] == "0.3.0"
    assert current["definition_checksum"] == EXPERIMENT_V0_4_CAPSULE_CHECKSUM
    assert current["compatibility"]["harness_integration"] == (
        "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP"
    )
