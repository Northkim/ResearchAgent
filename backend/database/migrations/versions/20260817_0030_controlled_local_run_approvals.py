"""Add exact controlled-local Run Approval handshake persistence.

Revision ID: 20260817_0030
Revises: 20260817_0029
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0030"
down_revision: str | None = "20260817_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controlled_local_run_approvals",
        sa.Column("request_id", sa.String(length=37), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_instance_id", sa.String(length=36), nullable=False),
        sa.Column("schema", sa.String(length=100), nullable=False),
        sa.Column("research_objective_checksum", sa.String(length=71), nullable=False),
        sa.Column("execution_plan_checksum", sa.String(length=71), nullable=False),
        sa.Column("validated_package_checksum", sa.String(length=71), nullable=False),
        sa.Column("runtime_compatibility_checksum", sa.String(length=71), nullable=True),
        sa.Column("capability_checksum", sa.String(length=71), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_checksum", sa.String(length=71), nullable=False),
        sa.Column("request_checksum", sa.String(length=71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner_actor", sa.String(length=120), nullable=True),
        sa.Column("decision_reason", sa.String(length=500), nullable=True),
        sa.Column("decision_idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_checksum", sa.String(length=71), nullable=True),
        sa.Column("consumed_attempt_id", sa.String(length=40), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumption_checksum", sa.String(length=71), nullable=True),
        sa.Column("persistence_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('REQUESTED','APPROVED','REJECTED','CONSUMED','SUPERSEDED')",
            name="controlled_local_approval_status",
        ),
        sa.CheckConstraint(
            "(status = 'REQUESTED' AND owner_actor IS NULL AND decided_at IS NULL "
            "AND approval_checksum IS NULL AND decision_idempotency_key IS NULL "
            "AND consumed_attempt_id IS NULL AND consumed_at IS NULL "
            "AND consumption_checksum IS NULL) OR "
            "(status IN ('APPROVED','REJECTED') AND owner_actor IS NOT NULL "
            "AND decided_at IS NOT NULL AND approval_checksum IS NOT NULL "
            "AND decision_idempotency_key IS NOT NULL AND consumed_attempt_id IS NULL "
            "AND consumed_at IS NULL AND consumption_checksum IS NULL) OR "
            "(status = 'CONSUMED' AND owner_actor IS NOT NULL AND decided_at IS NOT NULL "
            "AND approval_checksum IS NOT NULL AND consumed_attempt_id IS NOT NULL "
            "AND consumed_at IS NOT NULL AND consumption_checksum IS NOT NULL) OR "
            "(status = 'SUPERSEDED' AND consumed_attempt_id IS NULL "
            "AND consumed_at IS NULL AND consumption_checksum IS NULL)",
            name="controlled_local_approval_state_fields",
        ),
        sa.CheckConstraint(
            "persistence_version > 0",
            name="controlled_local_approval_persistence_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_controlled_local_approvals_instance_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("request_id", name="pk_controlled_local_run_approvals"),
        sa.UniqueConstraint(
            "request_checksum", name="uq_controlled_local_approvals_request_checksum"
        ),
        sa.UniqueConstraint(
            "project_id", "workflow_instance_id", "execution_plan_checksum",
            "request_checksum", name="uq_controlled_local_approvals_exact_request",
        ),
    )
    op.create_index(
        "uq_controlled_local_approvals_active_instance",
        "controlled_local_run_approvals",
        ["project_id", "workflow_instance_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('REQUESTED','APPROVED')"),
    )
    op.create_index(
        "ix_controlled_local_approvals_instance_created",
        "controlled_local_run_approvals",
        ["project_id", "workflow_instance_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_controlled_local_approvals_instance_created",
        table_name="controlled_local_run_approvals",
    )
    op.drop_index(
        "uq_controlled_local_approvals_active_instance",
        table_name="controlled_local_run_approvals",
    )
    op.drop_table("controlled_local_run_approvals")
