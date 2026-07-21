"""Create the initial production persistence schema.

Revision ID: 20260721_0001
Revises: None
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("definition_json", postgresql.JSONB(), nullable=False),
        sa.Column("definition_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "workflow_id",
            "version",
            name="pk_workflow_definitions",
        ),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("actor_user_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=500), nullable=False),
        sa.Column("inputs_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("outputs_json", postgresql.JSONB(), nullable=False),
        sa.Column("wait_reason", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("persistence_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "persistence_version > 0",
            name="ck_workflow_runs_workflow_run_persistence_version_positive",
        ),
        sa.CheckConstraint(
            "row_version >= 0",
            name="ck_workflow_runs_workflow_run_row_version_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id", "workflow_version"],
            ["workflow_definitions.workflow_id", "workflow_definitions.version"],
            name="fk_workflow_runs_definition",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_runs"),
        sa.UniqueConstraint(
            "project_id",
            "id",
            name="uq_workflow_runs_project_id",
        ),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_workflow_runs_project_idempotency",
        ),
    )
    op.create_index(
        "ix_workflow_runs_project_status",
        "workflow_runs",
        ["project_id", "status"],
    )

    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("agent_profile_ref", sa.String(length=500), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("state_json", postgresql.JSONB(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "row_version >= 0",
            name="ck_agent_sessions_agent_session_row_version_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_agent_sessions_run_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_sessions"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_agent_sessions_run_id",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "role",
            name="uq_agent_sessions_run_role",
        ),
    )

    op.create_table(
        "workflow_step_runs",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=255), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=500), nullable=False),
        sa.Column("inputs_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("outputs_json", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt > 0",
            name="ck_workflow_step_runs_step_run_attempt_positive",
        ),
        sa.CheckConstraint(
            "ordinal > 0",
            name="ck_workflow_step_runs_step_run_ordinal_positive",
        ),
        sa.CheckConstraint(
            "row_version >= 0",
            name="ck_workflow_step_runs_step_run_row_version_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name="fk_workflow_step_runs_workflow_run_id_workflow_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_step_runs"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_step_runs_run_id",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "idempotency_key",
            name="uq_step_runs_run_idempotency",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "ordinal",
            name="uq_step_runs_run_ordinal",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "step_id",
            "attempt",
            name="uq_step_runs_run_step_attempt",
        ),
    )
    op.create_index(
        "ix_step_runs_run_status",
        "workflow_step_runs",
        ["workflow_run_id", "status"],
    )

    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("agent_session_id", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parent_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_checkpoints_checkpoint_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "agent_session_id"],
            ["agent_sessions.workflow_run_id", "agent_sessions.id"],
            name="fk_checkpoints_agent_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["checkpoints.id"],
            name="fk_checkpoints_parent_id_checkpoints",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name="fk_checkpoints_workflow_run_id_workflow_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_checkpoints"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_checkpoints_run_id",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "sequence",
            name="uq_checkpoints_run_sequence",
        ),
    )

    op.create_table(
        "checkpoint_records",
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("record_sequence", sa.Integer(), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=255), nullable=False),
        sa.Column("boundary", sa.String(length=50), nullable=False),
        sa.Column("step_id", sa.String(length=255), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "record_sequence > 0",
            name="ck_checkpoint_records_checkpoint_record_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "checkpoint_id"],
            ["checkpoints.workflow_run_id", "checkpoints.id"],
            name="fk_checkpoint_records_checkpoint_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "workflow_run_id",
            "record_sequence",
            name="pk_checkpoint_records",
        ),
    )
    op.create_index(
        "uq_checkpoint_records_boundary_identity",
        "checkpoint_records",
        ["workflow_run_id", "boundary", "checkpoint_id", "step_id", "attempt"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    op.create_table(
        "memory_revisions",
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("context_json", postgresql.JSONB(), nullable=False),
        sa.Column("producer", sa.String(length=255), nullable=False),
        sa.Column("source_references_json", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "revision > 0",
            name="ck_memory_revisions_memory_revision_positive",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_memory_revisions_run_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "workflow_run_id",
            "revision",
            name="pk_memory_revisions",
        ),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("logical_artifact_id", sa.String(length=255), nullable=False),
        sa.Column("logical_name", sa.String(length=500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("storage_ref", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("producer_run_id", sa.String(length=255), nullable=True),
        sa.Column("producer_step_run_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "size >= 0",
            name="ck_artifacts_artifact_size_nonnegative",
        ),
        sa.CheckConstraint(
            "version > 0",
            name="ck_artifacts_artifact_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "producer_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_artifacts_run_scope",
        ),
        sa.ForeignKeyConstraint(
            ["producer_run_id", "producer_step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_artifacts_step_scope",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifacts"),
        sa.UniqueConstraint(
            "project_id",
            "logical_artifact_id",
            "version",
            name="uq_artifacts_project_logical_version",
        ),
    )
    op.create_index(
        "ix_artifacts_project_logical",
        "artifacts",
        ["project_id", "logical_artifact_id"],
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("step_run_id", sa.String(length=255), nullable=False),
        sa.Column("policy_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("requested_action_json", postgresql.JSONB(), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("permitted_approver_role", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decision_idempotency_key", sa.String(length=500), nullable=True),
        sa.Column("decision_metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("persistence_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "persistence_version > 0",
            name="ck_approval_requests_approval_persistence_version_positive",
        ),
        sa.CheckConstraint(
            "row_version >= 0",
            name="ck_approval_requests_approval_row_version_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_approval_requests_run_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_approval_requests_step_scope",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_approval_requests"),
    )
    op.create_index(
        "ix_approval_requests_fingerprint",
        "approval_requests",
        ["project_id", "workflow_run_id", "request_fingerprint"],
    )
    op.create_index(
        "ix_approval_requests_pending",
        "approval_requests",
        ["project_id", "workflow_run_id", "status"],
    )

    op.create_table(
        "execution_events",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("payload_schema_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_session_id", sa.String(length=255), nullable=True),
        sa.Column("step_run_id", sa.String(length=255), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("causation_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "payload_schema_version > 0",
            name="ck_execution_events_execution_event_schema_version_positive",
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_execution_events_execution_event_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "agent_session_id"],
            ["agent_sessions.workflow_run_id", "agent_sessions.id"],
            name="fk_execution_events_agent_scope",
        ),
        sa.ForeignKeyConstraint(
            ["causation_id"],
            ["execution_events.id"],
            name="fk_execution_events_causation_id_execution_events",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_execution_events_run_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_execution_events_step_scope",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_events"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "sequence",
            name="uq_execution_events_run_sequence",
        ),
    )
    op.create_index(
        "ix_execution_events_project_run_time",
        "execution_events",
        ["project_id", "workflow_run_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_table("execution_events")
    op.drop_table("approval_requests")
    op.drop_table("artifacts")
    op.drop_table("memory_revisions")
    op.drop_table("checkpoint_records")
    op.drop_table("checkpoints")
    op.drop_table("workflow_step_runs")
    op.drop_table("agent_sessions")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_definitions")
