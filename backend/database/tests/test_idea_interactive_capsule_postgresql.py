"""Migration/registry identity check for the immutable Idea bootstrap Capsule."""

from __future__ import annotations

from importlib import import_module

from backend.project_workspaces.production_workflows import (
    IDEA_DISCOVERY_V0_2_CAPSULE_CHECKSUM,
    IDEA_DISCOVERY_V0_3_CAPSULE_CHECKSUM,
    IDEA_DISCOVERY_V0_3_CAPSULE_ID,
)


def test_idea_bootstrap_migration_matches_registry_and_preserves_old_pin() -> None:
    migration = import_module(
        "backend.database.migrations.versions."
        "20260811_0018_idea_interactive_bootstrap_capsule"
    )
    assert migration.down_revision == "20260806_0017"
    assert migration.IDEA_VERSION == "0.2.0"
    assert migration.OLD_CAPSULE_VERSION == "0.2.0"
    assert migration.OLD_CAPSULE_CHECKSUM == IDEA_DISCOVERY_V0_2_CAPSULE_CHECKSUM
    assert migration.CAPSULE_ID == IDEA_DISCOVERY_V0_3_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.3.0"
    assert migration.CAPSULE_CHECKSUM == IDEA_DISCOVERY_V0_3_CAPSULE_CHECKSUM
