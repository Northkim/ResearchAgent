"""Migration and Registry identity for Writing/Review interactive Capsules."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork
from backend.project_workspaces.production_workflows import (
    REVIEW_WORKFLOW_ID,
    SCAFFOLD_V0_2_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_3_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_3_CAPSULE_IDS,
    WRITING_WORKFLOW_ID,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation


def test_writing_review_bootstrap_migration_matches_registry() -> None:
    migration = import_module(
        "backend.database.migrations.versions."
        "20260813_0020_writing_review_interactive_bootstrap_capsules"
    )
    assert migration.down_revision == "20260813_0019"
    assert migration.DEFINITION_VERSION == "0.2.0"
    assert migration.OLD_CAPSULE_VERSION == "0.2.0"
    assert migration.CAPSULE_VERSION == "0.3.0"
    by_workflow = {item["definition_id"]: item for item in migration.CAPSULES}
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID):
        assert by_workflow[workflow_id]["old_checksum"] == (
            SCAFFOLD_V0_2_CAPSULE_CHECKSUMS[workflow_id]
        )
        assert by_workflow[workflow_id]["capsule_id"] == (
            SCAFFOLD_V0_3_CAPSULE_IDS[workflow_id]
        )
        assert by_workflow[workflow_id]["checksum"] == (
            SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id]
        )


def test_writing_review_0_3_seed_preserves_0_2_and_is_recommended(
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
            SELECT workflow_definition_id, capsule_id, capsule_version,
                   workflow_version, definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id IN
                  ('writing-local-experimental', 'review-local-experimental')
              AND capsule_version IN ('0.2.0', '0.3.0')
            ORDER BY workflow_definition_id, capsule_version
        """)).mappings().all()
    assert len(rows) == 4
    by_identity = {
        (row["workflow_definition_id"], row["capsule_version"]): dict(row)
        for row in rows
    }
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID):
        old = by_identity[(workflow_id, "0.2.0")]
        current = by_identity[(workflow_id, "0.3.0")]
        assert old["definition_checksum"] == SCAFFOLD_V0_2_CAPSULE_CHECKSUMS[workflow_id]
        assert "harness_integration" not in old["compatibility"]
        assert current["capsule_id"] == SCAFFOLD_V0_3_CAPSULE_IDS[workflow_id]
        assert current["workflow_version"] == "0.2.0"
        assert current["definition_checksum"] == SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id]
        assert current["compatibility"]["harness_integration"] == (
            "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP"
        )
        assert current["compatibility"]["skill_pins"] == old["compatibility"]["skill_pins"]
