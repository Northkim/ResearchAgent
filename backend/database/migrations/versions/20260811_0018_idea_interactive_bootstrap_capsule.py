"""Publish the immutable Idea Discovery interactive-bootstrap Capsule.

Revision ID: 20260811_0018
Revises: 20260806_0017
Create Date: 2026-08-11
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260811_0018"
down_revision: str | None = "20260806_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IDEA_ID = "idea-discovery-local-experimental"
IDEA_VERSION = "0.2.0"
OLD_CAPSULE_ID = "capsule-6b66289a38895ce0eba2f76cd7725176"
OLD_CAPSULE_VERSION = "0.2.0"
OLD_CAPSULE_CHECKSUM = (
    "sha256:6b66289a38895ce0eba2f76cd77251766711a6ec8ebf416cdd368695b5c727f5"
)
CAPSULE_ID = "capsule-3976596c49e3df30e08774233055bcce"
CAPSULE_VERSION = "0.3.0"
CAPSULE_CHECKSUM = (
    "sha256:3976596c49e3df30e08774233055bcce32745034e02a78c35970242cb22c772e"
)

LITERATURE_TYPE = "selected-paper-library/v1"
SELECTED_IDEA_TYPE = "selected-research-idea/v1"
SELECTED_IDEA_OUTPUT = {
    "artifact_type": SELECTED_IDEA_TYPE,
    "artifact_schema_version": SELECTED_IDEA_TYPE,
    "media_type": "application/json",
    "relative_path_prefix": "outputs/artifacts/selected-research-idea",
    "content_addressed_filename": "sha256-<content-sha256>.json",
    "progress_artifact_kind": SELECTED_IDEA_TYPE,
}


def upgrade() -> None:
    connection = op.get_bind()
    _assert_old_capsule_immutable(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id, workflow_version,
               definition_checksum, archive_size_bytes, archive_media_type,
               mutable_roots, capability_requirements, compatibility, review_status,
               legacy_package_compatible, created_at, updated_at)
            VALUES (:capsule_id, :capsule_version, :definition_id, :workflow_version,
                    :checksum, 0, 'application/zip', CAST(:mutable_roots AS jsonb),
                    CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                    'REVIEWED', false, :now, :now)
            ON CONFLICT (capsule_id, capsule_version) DO NOTHING
        """),
        {
            "capsule_id": CAPSULE_ID,
            "capsule_version": CAPSULE_VERSION,
            "definition_id": IDEA_ID,
            "workflow_version": IDEA_VERSION,
            "checksum": CAPSULE_CHECKSUM,
            "mutable_roots": _json([
                "memory/context.md", "memory/progress", "outputs", "inputs",
            ]),
            "capabilities": _json([
                "progress.upload/v0.2", "artifact.materialize/v0.1",
                "artifact.publish/v0.1",
            ]),
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "idea-discovery-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_requirements": [{
                    "requirement_key": "paper_library",
                    "artifact_type": LITERATURE_TYPE,
                    "artifact_schema_version": LITERATURE_TYPE,
                    "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                    "materialization_mode": "VERIFIED_COPY",
                    "target_relative_path": "inputs/selected-paper-library.json",
                }],
                "artifact_outputs": [SELECTED_IDEA_OUTPUT],
                "core_capability_maturity": "REVIEWED_CORE",
            }),
            "now": now,
        },
    )
    _assert_new_capsule(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": CAPSULE_ID, "version": CAPSULE_VERSION},
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_old_capsule_immutable(connection: sa.Connection) -> None:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": OLD_CAPSULE_ID, "version": OLD_CAPSULE_VERSION},
    ).mappings().one_or_none()
    if row is None or dict(row) != {
        "workflow_definition_id": IDEA_ID,
        "workflow_version": IDEA_VERSION,
        "definition_checksum": OLD_CAPSULE_CHECKSUM,
    }:
        raise RuntimeError("Idea Discovery 0.2 Capsule immutable-content conflict")


def _assert_new_capsule(connection: sa.Connection) -> None:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": CAPSULE_ID, "version": CAPSULE_VERSION},
    ).mappings().one_or_none()
    if row is None or dict(row) != {
        "workflow_definition_id": IDEA_ID,
        "workflow_version": IDEA_VERSION,
        "definition_checksum": CAPSULE_CHECKSUM,
    }:
        raise RuntimeError("Idea Discovery 0.3 Capsule seed conflict")
