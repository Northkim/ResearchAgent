"""Publish the immutable Experiment scaffold interactive-bootstrap Capsule.

Revision ID: 20260813_0019
Revises: 20260811_0018
Create Date: 2026-08-13
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260813_0019"
down_revision: str | None = "20260811_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXPERIMENT_ID = "reproduction-experiment-local-experimental"
EXPERIMENT_VERSION = "0.3.0"
OLD_CAPSULE_ID = "capsule-4aa162608aafec3c67db316957f57349"
OLD_CAPSULE_VERSION = "0.3.0"
OLD_CAPSULE_CHECKSUM = (
    "sha256:4aa162608aafec3c67db316957f57349de3c35c8167bd24b9d008e6e0f1f0da7"
)
CAPSULE_ID = "capsule-be6448913e6c3d00512ecb2e8a5f00ae"
CAPSULE_VERSION = "0.4.0"
CAPSULE_CHECKSUM = (
    "sha256:be6448913e6c3d00512ecb2e8a5f00ae70e9746e7e79d71657c93e25d917c96a"
)

def upgrade() -> None:
    connection = op.get_bind()
    _assert_old_capsule_immutable(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    old = connection.execute(
        sa.text("""
            SELECT compatibility
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": OLD_CAPSULE_ID, "version": OLD_CAPSULE_VERSION},
    ).mappings().one()
    compatibility = dict(old["compatibility"])
    compatibility["harness_integration"] = (
        "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP"
    )
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
            "definition_id": EXPERIMENT_ID,
            "workflow_version": EXPERIMENT_VERSION,
            "checksum": CAPSULE_CHECKSUM,
            "mutable_roots": _json([
                "memory/context.md", "memory/progress",
                "memory/input-provenance.json", "memory/resource-provenance.json",
                "memory/current-artifact.json", "outputs", "inputs",
            ]),
            "capabilities": _json([
                "progress.upload/v0.2", "artifact.materialize/v0.1",
                "artifact.publish/v0.1", "resource.index.verify/v0.1",
            ]),
            "compatibility": _json(compatibility),
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
        "workflow_definition_id": EXPERIMENT_ID,
        "workflow_version": EXPERIMENT_VERSION,
        "definition_checksum": OLD_CAPSULE_CHECKSUM,
    }:
        raise RuntimeError("Experiment 0.3 Capsule immutable-content conflict")


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
        "workflow_definition_id": EXPERIMENT_ID,
        "workflow_version": EXPERIMENT_VERSION,
        "definition_checksum": CAPSULE_CHECKSUM,
    }:
        raise RuntimeError("Experiment 0.4 Capsule seed conflict")
