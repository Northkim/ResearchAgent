"""Bind immutable Progress Report rows to Project Workflow Instances.

Revision ID: 20260806_0011
Revises: 20260806_0010
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0011"
down_revision: str | None = "20260806_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")
_WORKFLOW_DEFINITION_ID = "literature-search-local-experimental"
_WORKFLOW_VERSION = "0.3.0"


def upgrade() -> None:
    op.add_column(
        "uploaded_progress_reports",
        sa.Column("workflow_instance_id", sa.String(36), nullable=True),
    )
    _backfill_legacy_progress(op.get_bind())
    op.alter_column(
        "uploaded_progress_reports",
        "workflow_instance_id",
        existing_type=sa.String(36),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_uploaded_progress_reports_project_workflow_instance",
        "uploaded_progress_reports",
        "project_workflow_instances",
        ["project_id", "workflow_instance_id"],
        ["project_id", "workflow_instance_id"],
    )
    op.create_index(
        "ix_progress_reports_project_instance_received",
        "uploaded_progress_reports",
        ["project_id", "workflow_instance_id", "received_at", "receipt_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_progress_reports_project_instance_received",
        table_name="uploaded_progress_reports",
    )
    op.drop_constraint(
        "fk_uploaded_progress_reports_project_workflow_instance",
        "uploaded_progress_reports",
        type_="foreignkey",
    )
    op.drop_column("uploaded_progress_reports", "workflow_instance_id")


def _backfill_legacy_progress(connection: sa.Connection) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT receipt_id, project_id, package_id, package_checksum,
                   normalized_record_json
            FROM uploaded_progress_reports
            ORDER BY receipt_id
            """
        )
    ).mappings()
    for row in rows:
        project_id = row["project_id"]
        identity_name = (
            f"legacy-workflow-instance/v1|project={project_id}|"
            "workflow=LITERATURE_SEARCH"
        )
        instance_id = "wfi-" + uuid5(_LEGACY_NAMESPACE, identity_name).hex
        instance = connection.execute(
            sa.text(
                """
                SELECT project_id, workflow_definition_id, workflow_version
                FROM project_workflow_instances
                WHERE workflow_instance_id = :instance_id
                """
            ),
            {"instance_id": instance_id},
        ).mappings().one_or_none()
        if instance is None or dict(instance) != {
            "project_id": project_id,
            "workflow_definition_id": _WORKFLOW_DEFINITION_ID,
            "workflow_version": _WORKFLOW_VERSION,
        }:
            raise RuntimeError(
                "legacy Progress Report is missing its deterministic Workflow "
                "Instance binding"
            )
        project = connection.execute(
            sa.text(
                "SELECT selected_workflow FROM local_projects "
                "WHERE project_id = :project_id"
            ),
            {"project_id": project_id},
        ).mappings().one_or_none()
        if project is None or project["selected_workflow"] != "LITERATURE_SEARCH":
            raise RuntimeError(
                "legacy Progress Report Project is not a supported Literature Search Project"
            )
        normalized = row["normalized_record_json"]
        if normalized is not None and any(
            normalized.get(key) != value
            for key, value in {
                "project_id": project_id,
                "package_id": row["package_id"],
                "package_checksum": row["package_checksum"],
            }.items()
        ):
            raise RuntimeError(
                "legacy Progress Report normalized Package identity cannot be mapped safely"
            )
        connection.execute(
            sa.text(
                """
                UPDATE uploaded_progress_reports
                SET workflow_instance_id = :instance_id
                WHERE receipt_id = :receipt_id
                  AND workflow_instance_id IS NULL
                """
            ),
            {"instance_id": instance_id, "receipt_id": row["receipt_id"]},
        )
    missing = connection.scalar(
        sa.text(
            "SELECT count(*) FROM uploaded_progress_reports "
            "WHERE workflow_instance_id IS NULL"
        )
    )
    if missing:
        raise RuntimeError("Progress Workflow Instance backfill was incomplete")
