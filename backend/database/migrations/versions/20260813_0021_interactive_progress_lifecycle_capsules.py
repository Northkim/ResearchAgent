"""Publish immutable interactive Progress-lifecycle repair Capsules.

Revision ID: 20260813_0021
Revises: 20260813_0020
Create Date: 2026-08-14
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260813_0021"
down_revision: str | None = "20260813_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CAPSULES = (
    {
        "definition_id": "writing-local-experimental",
        "definition_version": "0.2.0",
        "old_version": "0.3.0",
        "old_id": "capsule-38e6a3d9bb0938fd9f0723767bc7d471",
        "old_checksum": "sha256:38e6a3d9bb0938fd9f0723767bc7d471973f2ca4d515f9c4097c2ddf3743f377",
        "new_version": "0.4.0",
        "new_id": "capsule-f7c206e79a3fe8a1831138a43ee46f1b",
        "new_checksum": "sha256:f7c206e79a3fe8a1831138a43ee46f1b44c5c3d193646382db5c25dbd9542269",
    },
    {
        "definition_id": "review-local-experimental",
        "definition_version": "0.2.0",
        "old_version": "0.3.0",
        "old_id": "capsule-c497f21cc4876ae1aea19f56cb4491a4",
        "old_checksum": "sha256:c497f21cc4876ae1aea19f56cb4491a4f2baf74657e0590bab41fe3056616c25",
        "new_version": "0.4.0",
        "new_id": "capsule-cad9d7eaaca0a0f879e9cb2600257882",
        "new_checksum": "sha256:cad9d7eaaca0a0f879e9cb2600257882e89648fb2a77d9805ed180e0d9492aeb",
    },
    {
        "definition_id": "reproduction-experiment-local-experimental",
        "definition_version": "0.3.0",
        "old_version": "0.4.0",
        "old_id": "capsule-be6448913e6c3d00512ecb2e8a5f00ae",
        "old_checksum": "sha256:be6448913e6c3d00512ecb2e8a5f00ae70e9746e7e79d71657c93e25d917c96a",
        "new_version": "0.5.0",
        "new_id": "capsule-396f09bf03486ce53113611e2c9614dd",
        "new_checksum": "sha256:396f09bf03486ce53113611e2c9614dd6a86166f44415f9350fd02803ac04b3f",
    },
)


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    for item in CAPSULES:
        old = _assert_old_capsule(connection, item)
        compatibility = dict(old["compatibility"])
        compatibility["progress_lifecycle"] = (
            "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE"
        )
        connection.execute(
            sa.text("""
                INSERT INTO local_workflow_capsule_versions
                  (capsule_id, capsule_version, workflow_definition_id,
                   workflow_version, definition_checksum, archive_size_bytes,
                   archive_media_type, mutable_roots, capability_requirements,
                   compatibility, review_status, legacy_package_compatible,
                   created_at, updated_at)
                VALUES (:new_id, :new_version, :definition_id,
                        :definition_version, :new_checksum, 0, 'application/zip',
                        CAST(:mutable_roots AS jsonb), CAST(:capabilities AS jsonb),
                        CAST(:compatibility AS jsonb), 'REVIEWED', false, :now, :now)
                ON CONFLICT (capsule_id, capsule_version) DO NOTHING
            """),
            {
                **item,
                "mutable_roots": _json(old["mutable_roots"]),
                "capabilities": _json(old["capability_requirements"]),
                "compatibility": _json(compatibility),
                "now": now,
            },
        )
        _assert_new_capsule(connection, item)


def downgrade() -> None:
    connection = op.get_bind()
    for item in CAPSULES:
        connection.execute(
            sa.text("""
                DELETE FROM local_workflow_capsule_versions
                WHERE capsule_id = :new_id AND capsule_version = :new_version
            """),
            item,
        )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_old_capsule(
    connection: sa.Connection, item: dict[str, str]
) -> dict[str, object]:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version,
                   definition_checksum, mutable_roots,
                   capability_requirements, compatibility
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :old_id AND capsule_version = :old_version
        """),
        item,
    ).mappings().one_or_none()
    if row is None or {
        "workflow_definition_id": row["workflow_definition_id"],
        "workflow_version": row["workflow_version"],
        "definition_checksum": row["definition_checksum"],
    } != {
        "workflow_definition_id": item["definition_id"],
        "workflow_version": item["definition_version"],
        "definition_checksum": item["old_checksum"],
    }:
        raise RuntimeError("historical interactive Capsule immutable-content conflict")
    return dict(row)


def _assert_new_capsule(
    connection: sa.Connection, item: dict[str, str]
) -> None:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :new_id AND capsule_version = :new_version
        """),
        item,
    ).mappings().one_or_none()
    if row is None or dict(row) != {
        "workflow_definition_id": item["definition_id"],
        "workflow_version": item["definition_version"],
        "definition_checksum": item["new_checksum"],
    }:
        raise RuntimeError("interactive Progress lifecycle Capsule seed conflict")
