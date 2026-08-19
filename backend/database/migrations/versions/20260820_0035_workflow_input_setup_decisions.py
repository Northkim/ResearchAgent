"""Persist exact Owner decisions for unresolved optional Workflow inputs.

Revision ID: 20260820_0035
Revises: 20260819_0034
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260820_0035"
down_revision: str | None = "20260819_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_workflow_input_setup_decisions",
        sa.Column("decision_id", sa.String(length=47), primary_key=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("consumer_workflow_instance_id", sa.String(length=36), nullable=False),
        sa.Column("consumer_workflow_definition_id", sa.String(length=128), nullable=False),
        sa.Column("consumer_workflow_version", sa.String(length=100), nullable=False),
        sa.Column("binding_set_checksum", sa.String(length=71), nullable=False),
        sa.Column(
            "omitted_optional_requirement_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column(
            "idempotency_key",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("decision_checksum", sa.String(length=71), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "consumer_workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_input_setup_decisions_consumer_instance",
        ),
        sa.UniqueConstraint(
            "project_id",
            "consumer_workflow_instance_id",
            "idempotency_key",
            name="uq_input_setup_decisions_idempotency",
        ),
        sa.CheckConstraint(
            "decision = 'CONTINUE_WITHOUT_OPTIONAL_EVIDENCE'",
            name="input_setup_decision_supported",
        ),
        sa.CheckConstraint(
            "binding_set_checksum ~ '^sha256:[0-9a-f]{64}$'",
            name="input_setup_binding_set_checksum",
        ),
        sa.CheckConstraint(
            "decision_checksum ~ '^sha256:[0-9a-f]{64}$'",
            name="input_setup_decision_checksum",
        ),
    )
    op.create_index(
        "ix_input_setup_decisions_current",
        "project_workflow_input_setup_decisions",
        ["project_id", "consumer_workflow_instance_id", "decided_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_input_setup_decisions_current",
        table_name="project_workflow_input_setup_decisions",
    )
    op.drop_table("project_workflow_input_setup_decisions")
