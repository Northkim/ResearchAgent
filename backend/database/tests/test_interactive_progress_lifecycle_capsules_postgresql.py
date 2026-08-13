"""Migration and Registry identity for Progress-lifecycle repair Capsules."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork
from backend.project_workspaces.production_workflows import (
    EXPERIMENT_V0_4_CAPSULE_CHECKSUM,
    EXPERIMENT_V0_5_CAPSULE_CHECKSUM,
    EXPERIMENT_V0_5_CAPSULE_ID,
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    SCAFFOLD_V0_3_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_4_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_4_CAPSULE_IDS,
    WRITING_WORKFLOW_ID,
)
from backend.project_workspaces.service import ensure_production_workflow_foundation


def test_0021_seed_matches_registry_constants() -> None:
    migration = import_module(
        "backend.database.migrations.versions."
        "20260813_0021_interactive_progress_lifecycle_capsules"
    )
    assert migration.down_revision == "20260813_0020"
    by_workflow = {item["definition_id"]: item for item in migration.CAPSULES}
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID):
        item = by_workflow[workflow_id]
        assert item["old_checksum"] == SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id]
        assert item["new_id"] == SCAFFOLD_V0_4_CAPSULE_IDS[workflow_id]
        assert item["new_checksum"] == SCAFFOLD_V0_4_CAPSULE_CHECKSUMS[workflow_id]
        assert item["definition_version"] == "0.2.0"
    experiment = by_workflow[EXPERIMENT_WORKFLOW_ID]
    assert experiment["old_checksum"] == EXPERIMENT_V0_4_CAPSULE_CHECKSUM
    assert experiment["new_id"] == EXPERIMENT_V0_5_CAPSULE_ID
    assert experiment["new_checksum"] == EXPERIMENT_V0_5_CAPSULE_CHECKSUM
    assert experiment["definition_version"] == "0.3.0"


def test_0021_capsules_are_seeded_without_replacing_historical_pins(
    sql_uow_factory, postgres_engine,
) -> None:
    uow: SQLAlchemyUnitOfWork = sql_uow_factory()
    ensure_production_workflow_foundation(
        uow, now=datetime(2026, 8, 14, tzinfo=UTC)
    )
    uow.commit()
    uow.close()
    with postgres_engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT workflow_definition_id, capsule_id, capsule_version,
                   workflow_version, definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE (workflow_definition_id IN
                   ('writing-local-experimental', 'review-local-experimental')
                   AND capsule_version IN ('0.3.0', '0.4.0'))
               OR (workflow_definition_id =
                   'reproduction-experiment-local-experimental'
                   AND capsule_version IN ('0.4.0', '0.5.0'))
            ORDER BY workflow_definition_id, capsule_version
        """)).mappings().all()
    assert len(rows) == 6
    by_identity = {
        (row["workflow_definition_id"], row["capsule_version"]): dict(row)
        for row in rows
    }
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID):
        old = by_identity[(workflow_id, "0.3.0")]
        new = by_identity[(workflow_id, "0.4.0")]
        assert old["definition_checksum"] == SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id]
        assert "progress_lifecycle" not in old["compatibility"]
        assert new["capsule_id"] == SCAFFOLD_V0_4_CAPSULE_IDS[workflow_id]
        assert new["workflow_version"] == "0.2.0"
        assert new["definition_checksum"] == SCAFFOLD_V0_4_CAPSULE_CHECKSUMS[workflow_id]
        assert new["compatibility"]["progress_lifecycle"] == (
            "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE"
        )
    old = by_identity[(EXPERIMENT_WORKFLOW_ID, "0.4.0")]
    new = by_identity[(EXPERIMENT_WORKFLOW_ID, "0.5.0")]
    assert old["definition_checksum"] == EXPERIMENT_V0_4_CAPSULE_CHECKSUM
    assert "progress_lifecycle" not in old["compatibility"]
    assert new["capsule_id"] == EXPERIMENT_V0_5_CAPSULE_ID
    assert new["workflow_version"] == "0.3.0"
    assert new["definition_checksum"] == EXPERIMENT_V0_5_CAPSULE_CHECKSUM
