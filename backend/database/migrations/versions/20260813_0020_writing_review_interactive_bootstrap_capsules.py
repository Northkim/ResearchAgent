"""Publish immutable Writing and Review interactive-bootstrap Capsules.

Revision ID: 20260813_0020
Revises: 20260813_0019
Create Date: 2026-08-13
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260813_0020"
down_revision: str | None = "20260813_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFINITION_VERSION = "0.2.0"
OLD_CAPSULE_VERSION = "0.2.0"
CAPSULE_VERSION = "0.3.0"

CAPSULES = (
    {
        "definition_id": "writing-local-experimental",
        "old_capsule_id": "capsule-84896829db7ee1cb6b24a5e10bf6705b",
        "old_checksum": "sha256:84896829db7ee1cb6b24a5e10bf6705beac93fa42857d0dc08d4916e0243ee0c",
        "capsule_id": "capsule-38e6a3d9bb0938fd9f0723767bc7d471",
        "checksum": "sha256:38e6a3d9bb0938fd9f0723767bc7d471973f2ca4d515f9c4097c2ddf3743f377",
    },
    {
        "definition_id": "review-local-experimental",
        "old_capsule_id": "capsule-9c3e4e8f065914393f5dc786b36d07bb",
        "old_checksum": "sha256:9c3e4e8f065914393f5dc786b36d07bbbdc962f381ea70f125353429c48089f1",
        "capsule_id": "capsule-c497f21cc4876ae1aea19f56cb4491a4",
        "checksum": "sha256:c497f21cc4876ae1aea19f56cb4491a4f2baf74657e0590bab41fe3056616c25",
    },
)


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    for capsule in CAPSULES:
        old = _assert_old_capsule_immutable(connection, capsule)
        compatibility = dict(old["compatibility"])
        compatibility["harness_integration"] = (
            "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP"
        )
        connection.execute(
            sa.text("""
                INSERT INTO local_workflow_capsule_versions
                  (capsule_id, capsule_version, workflow_definition_id,
                   workflow_version, definition_checksum, archive_size_bytes,
                   archive_media_type, mutable_roots, capability_requirements,
                   compatibility, review_status, legacy_package_compatible,
                   created_at, updated_at)
                VALUES (:capsule_id, :capsule_version, :definition_id,
                        :workflow_version, :checksum, 0, 'application/zip',
                        CAST(:mutable_roots AS jsonb), CAST(:capabilities AS jsonb),
                        CAST(:compatibility AS jsonb), 'REVIEWED', false, :now, :now)
                ON CONFLICT (capsule_id, capsule_version) DO NOTHING
            """),
            {
                **capsule,
                "capsule_version": CAPSULE_VERSION,
                "workflow_version": DEFINITION_VERSION,
                "mutable_roots": _json([
                    "memory/context.md", "memory/progress",
                    "memory/input-provenance.json", "memory/current-artifact.json",
                    "outputs", "inputs",
                ]),
                "capabilities": _json([
                    "progress.upload/v0.2", "artifact.materialize/v0.1",
                    "artifact.publish/v0.1",
                ]),
                "compatibility": _json(compatibility),
                "now": now,
            },
        )
        _assert_new_capsule(connection, capsule)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM local_workflow_capsule_versions
            WHERE capsule_id IN :ids AND capsule_version = :version
        """).bindparams(sa.bindparam("ids", expanding=True)),
        {
            "ids": tuple(item["capsule_id"] for item in CAPSULES),
            "version": CAPSULE_VERSION,
        },
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_old_capsule_immutable(
    connection: sa.Connection, capsule: dict[str, str]
) -> dict[str, object]:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version,
                   definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": capsule["old_capsule_id"], "version": OLD_CAPSULE_VERSION},
    ).mappings().one_or_none()
    if row is None or {
        "workflow_definition_id": row["workflow_definition_id"],
        "workflow_version": row["workflow_version"],
        "definition_checksum": row["definition_checksum"],
    } != {
        "workflow_definition_id": capsule["definition_id"],
        "workflow_version": DEFINITION_VERSION,
        "definition_checksum": capsule["old_checksum"],
    }:
        raise RuntimeError("Writing/Review 0.2 Capsule immutable-content conflict")
    return dict(row)


def _assert_new_capsule(
    connection: sa.Connection, capsule: dict[str, str]
) -> None:
    row = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": capsule["capsule_id"], "version": CAPSULE_VERSION},
    ).mappings().one_or_none()
    if row is None or dict(row) != {
        "workflow_definition_id": capsule["definition_id"],
        "workflow_version": DEFINITION_VERSION,
        "definition_checksum": capsule["checksum"],
    }:
        raise RuntimeError("Writing/Review 0.3 Capsule seed conflict")
