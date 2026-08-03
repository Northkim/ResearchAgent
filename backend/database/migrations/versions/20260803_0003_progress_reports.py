"""Add immutable local Progress Report history and cloud projections.

Revision ID: 20260803_0003
Revises: 20260721_0002
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260803_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "uploaded_progress_reports",
        sa.Column("receipt_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("package_id", sa.String(length=255), nullable=False),
        sa.Column("package_checksum", sa.String(length=255), nullable=False),
        sa.Column("report_id", sa.String(length=255), nullable=False),
        sa.Column("report_checksum", sa.String(length=255), nullable=False),
        sa.Column("report_schema_version", sa.String(length=100), nullable=False),
        sa.Column("original_report_checksum", sa.String(length=255), nullable=False),
        sa.Column("original_report_size", sa.BigInteger(), nullable=False),
        sa.Column("original_report_media_type", sa.String(length=255), nullable=False),
        sa.Column("original_storage_key", sa.Text(), nullable=False),
        sa.Column("envelope_checksum", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploader_type", sa.String(length=100), nullable=False),
        sa.Column("client_version", sa.String(length=100), nullable=False),
        sa.Column("source_path_hint", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("validation_errors_json", postgresql.JSONB(), nullable=False),
        sa.Column("validation_warnings_json", postgresql.JSONB(), nullable=False),
        sa.Column("chain_state", sa.String(length=50), nullable=False),
        sa.Column("accepted_for_projection", sa.Boolean(), nullable=False),
        sa.Column("normalized_record_json", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "original_report_size > 0",
            name="ck_uploaded_progress_reports_progress_report_size_positive",
        ),
        sa.PrimaryKeyConstraint("receipt_id", name="pk_uploaded_progress_reports"),
        sa.UniqueConstraint(
            "project_id",
            "package_id",
            "package_checksum",
            "report_id",
            "report_checksum",
            "original_report_checksum",
            name="uq_progress_reports_exact_identity",
        ),
    )
    op.create_index(
        "ix_progress_reports_project_package_received",
        "uploaded_progress_reports",
        ["project_id", "package_id", "received_at"],
    )
    op.create_index(
        "ix_progress_reports_report_id",
        "uploaded_progress_reports",
        ["report_id"],
    )
    op.create_index(
        "ix_progress_reports_original_checksum",
        "uploaded_progress_reports",
        ["original_report_checksum"],
    )
    op.create_table(
        "project_progress_projections",
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("package_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("package_checksum", sa.String(length=255), nullable=False),
        sa.Column("latest_report_id", sa.String(length=255), nullable=False),
        sa.Column("latest_report_checksum", sa.String(length=255), nullable=False),
        sa.Column("latest_execution_round", sa.Integer(), nullable=False),
        sa.Column("latest_status", sa.String(length=50), nullable=False),
        sa.Column("chain_state", sa.String(length=50), nullable=False),
        sa.Column("projection_checksum", sa.String(length=255), nullable=False),
        sa.Column("projection_json", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "project_id",
            "package_id",
            "workflow_id",
            "workflow_version",
            name="pk_project_progress_projections",
        ),
    )


def downgrade() -> None:
    op.drop_table("project_progress_projections")
    op.drop_index(
        "ix_progress_reports_original_checksum",
        table_name="uploaded_progress_reports",
    )
    op.drop_index(
        "ix_progress_reports_report_id",
        table_name="uploaded_progress_reports",
    )
    op.drop_index(
        "ix_progress_reports_project_package_received",
        table_name="uploaded_progress_reports",
    )
    op.drop_table("uploaded_progress_reports")
