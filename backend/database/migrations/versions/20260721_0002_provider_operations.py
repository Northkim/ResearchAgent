"""Add auditable provider operations and artifact lookup indexes.

Revision ID: 20260721_0002
Revises: 20260721_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_operations",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("logical_step_id", sa.String(length=255), nullable=False),
        sa.Column("step_run_id", sa.String(length=255), nullable=True),
        sa.Column("provider_category", sa.String(length=50), nullable=False),
        sa.Column("operation_kind", sa.String(length=50), nullable=False),
        sa.Column("provider_identity", sa.String(length=255), nullable=False),
        sa.Column("adapter_version", sa.String(length=100), nullable=False),
        sa.Column("model_or_endpoint", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=500), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("reserved_request_count", sa.Integer(), nullable=False),
        sa.Column("reserved_input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("reserved_output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("reserved_cost_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("cost_currency", sa.String(length=10), nullable=False),
        sa.Column("is_live_provider", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("settlement_state", sa.String(length=50), nullable=False),
        sa.Column("actual_usage_json", postgresql.JSONB(), nullable=True),
        sa.Column("failure_category", sa.String(length=100), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("diagnostic_metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("persistence_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('RESERVED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')",
            name="ck_provider_operations_provider_operation_status_valid",
        ),
        sa.CheckConstraint(
            "settlement_state IN ('UNSETTLED', 'SETTLED', 'RELEASED')",
            name="ck_provider_operations_provider_operation_settlement_valid",
        ),
        sa.CheckConstraint(
            "row_version >= 0",
            name="ck_provider_operations_provider_operation_row_version_nonnegative",
        ),
        sa.CheckConstraint(
            "persistence_version > 0",
            name="ck_provider_operations_provider_operation_persistence_version_positive",
        ),
        sa.CheckConstraint(
            "reserved_request_count >= 0 AND reserved_input_tokens >= 0 "
            "AND reserved_output_tokens >= 0 AND reserved_cost_minor_units >= 0",
            name="ck_provider_operations_provider_operation_reservation_nonnegative",
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_provider_operations_provider_operation_retry_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_provider_operations_run_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_provider_operations_step_scope",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_operations"),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_provider_operations_project_idempotency",
        ),
    )
    op.create_index(
        "ix_provider_operations_run_created",
        "provider_operations",
        ["workflow_run_id", "created_at", "id"],
    )
    op.create_index(
        "ix_provider_operations_status_updated",
        "provider_operations",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_provider_operations_provider_failure_created",
        "provider_operations",
        ["provider_identity", "failure_category", "created_at"],
    )
    op.create_index(
        "ix_artifacts_run_kind_created",
        "artifacts",
        ["producer_run_id", "kind", "created_at"],
    )
    op.create_index(
        "ix_artifacts_project_checksum",
        "artifacts",
        ["project_id", "checksum"],
    )


def downgrade() -> None:
    op.drop_index("ix_artifacts_project_checksum", table_name="artifacts")
    op.drop_index("ix_artifacts_run_kind_created", table_name="artifacts")
    op.drop_table("provider_operations")
