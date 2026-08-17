"""Add exact bounded Artifact presentation companions.

Revision ID: 20260817_0029
Revises: 20260817_0028
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0029"
down_revision: str | None = "20260817_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "local_artifact_references",
        sa.Column("presentation_schema_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column("presentation_checksum", sa.String(length=71), nullable=True),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column("presentation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column("presentation_reported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "local_artifact_reference_presentation_all_or_none",
        "local_artifact_references",
        "(presentation_schema_id IS NULL AND presentation_checksum IS NULL "
        "AND presentation_json IS NULL AND presentation_reported_at IS NULL) OR "
        "(presentation_schema_id IS NOT NULL AND presentation_checksum IS NOT NULL "
        "AND presentation_json IS NOT NULL AND presentation_reported_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "local_artifact_reference_presentation_checksum",
        "local_artifact_references",
        "presentation_checksum IS NULL OR presentation_checksum ~ '^sha256:[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "local_artifact_reference_presentation_size",
        "local_artifact_references",
        "presentation_json IS NULL OR octet_length(presentation_json::text) <= 65536",
    )


def downgrade() -> None:
    op.drop_constraint(
        "local_artifact_reference_presentation_size",
        "local_artifact_references",
        type_="check",
    )
    op.drop_constraint(
        "local_artifact_reference_presentation_checksum",
        "local_artifact_references",
        type_="check",
    )
    op.drop_constraint(
        "local_artifact_reference_presentation_all_or_none",
        "local_artifact_references",
        type_="check",
    )
    op.drop_column("local_artifact_references", "presentation_reported_at")
    op.drop_column("local_artifact_references", "presentation_json")
    op.drop_column("local_artifact_references", "presentation_checksum")
    op.drop_column("local_artifact_references", "presentation_schema_id")
