"""Persistence-only SQLAlchemy mappings for the Phase 6 PostgreSQL schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WorkflowDefinitionORM(Base):
    __tablename__ = "workflow_definitions"

    workflow_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowRunORM(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_id", "workflow_version"],
            [
                "workflow_definitions.workflow_id",
                "workflow_definitions.version",
            ],
            name="fk_workflow_runs_definition",
        ),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_workflow_runs_project_idempotency",
        ),
        UniqueConstraint(
            "project_id",
            "id",
            name="uq_workflow_runs_project_id",
        ),
        CheckConstraint(
            "row_version >= 0",
            name="workflow_run_row_version_nonnegative",
        ),
        CheckConstraint(
            "persistence_version > 0",
            name="workflow_run_persistence_version_positive",
        ),
        Index("ix_workflow_runs_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(500), nullable=False)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    outputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    wait_reason: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(255))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    persistence_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __mapper_args__ = {
        "version_id_col": persistence_version,
        "version_id_generator": False,
    }


class AgentSessionORM(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_agent_sessions_run_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "role",
            name="uq_agent_sessions_run_role",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_agent_sessions_run_id",
        ),
        CheckConstraint(
            "row_version >= 0",
            name="agent_session_row_version_nonnegative",
        ),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_profile_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StepRunORM(Base):
    __tablename__ = "workflow_step_runs"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "step_id",
            "attempt",
            name="uq_step_runs_run_step_attempt",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "idempotency_key",
            name="uq_step_runs_run_idempotency",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "ordinal",
            name="uq_step_runs_run_ordinal",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_step_runs_run_id",
        ),
        CheckConstraint("attempt > 0", name="step_run_attempt_positive"),
        CheckConstraint("ordinal > 0", name="step_run_ordinal_positive"),
        CheckConstraint(
            "row_version >= 0",
            name="step_run_row_version_nonnegative",
        ),
        Index("ix_step_runs_run_status", "workflow_run_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(500), nullable=False)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    outputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(255))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CheckpointORM(Base):
    __tablename__ = "checkpoints"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_run_id", "agent_session_id"],
            ["agent_sessions.workflow_run_id", "agent_sessions.id"],
            name="fk_checkpoints_agent_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "sequence",
            name="uq_checkpoints_run_sequence",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "id",
            name="uq_checkpoints_run_id",
        ),
        CheckConstraint("sequence > 0", name="checkpoint_sequence_positive"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("checkpoints.id"),
    )


class CheckpointRecordORM(Base):
    __tablename__ = "checkpoint_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_run_id", "checkpoint_id"],
            ["checkpoints.workflow_run_id", "checkpoints.id"],
            name="fk_checkpoint_records_checkpoint_scope",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "record_sequence > 0",
            name="checkpoint_record_sequence_positive",
        ),
        Index(
            "uq_checkpoint_records_boundary_identity",
            "workflow_run_id",
            "boundary",
            "checkpoint_id",
            "step_id",
            "attempt",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    record_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    boundary: Mapped[str] = mapped_column(String(50), nullable=False)
    step_id: Mapped[str | None] = mapped_column(String(255))
    attempt: Mapped[int | None] = mapped_column(Integer)


class MemoryRevisionORM(Base):
    __tablename__ = "memory_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_memory_revisions_run_scope",
            ondelete="CASCADE",
        ),
        CheckConstraint("revision > 0", name="memory_revision_positive"),
    )

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    producer: Mapped[str] = mapped_column(String(255), nullable=False)
    source_references_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class ArtifactORM(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "producer_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_artifacts_run_scope",
        ),
        ForeignKeyConstraint(
            ["producer_run_id", "producer_step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_artifacts_step_scope",
        ),
        UniqueConstraint(
            "project_id",
            "logical_artifact_id",
            "version",
            name="uq_artifacts_project_logical_version",
        ),
        CheckConstraint("version > 0", name="artifact_version_positive"),
        CheckConstraint("size >= 0", name="artifact_size_nonnegative"),
        Index(
            "ix_artifacts_project_logical",
            "project_id",
            "logical_artifact_id",
        ),
        Index(
            "ix_artifacts_run_kind_created",
            "producer_run_id",
            "kind",
            "created_at",
        ),
        Index("ix_artifacts_project_checksum", "project_id", "checksum"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    logical_artifact_id: Mapped[str] = mapped_column(String(255), nullable=False)
    logical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_ref: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    producer_run_id: Mapped[str | None] = mapped_column(String(255))
    producer_step_run_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalRequestORM(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_approval_requests_run_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_approval_requests_step_scope",
        ),
        CheckConstraint(
            "row_version >= 0",
            name="approval_row_version_nonnegative",
        ),
        CheckConstraint(
            "persistence_version > 0",
            name="approval_persistence_version_positive",
        ),
        Index(
            "ix_approval_requests_pending",
            "project_id",
            "workflow_run_id",
            "status",
        ),
        Index(
            "ix_approval_requests_fingerprint",
            "project_id",
            "workflow_run_id",
            "request_fingerprint",
        ),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    step_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    requested_action_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    permitted_approver_role: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decision_idempotency_key: Mapped[str | None] = mapped_column(String(500))
    decision_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    persistence_version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {
        "version_id_col": persistence_version,
        "version_id_generator": False,
    }


class ExecutionEventORM(Base):
    __tablename__ = "execution_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_execution_events_run_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workflow_run_id", "agent_session_id"],
            ["agent_sessions.workflow_run_id", "agent_sessions.id"],
            name="fk_execution_events_agent_scope",
        ),
        ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_execution_events_step_scope",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "sequence",
            name="uq_execution_events_run_sequence",
        ),
        CheckConstraint("sequence > 0", name="execution_event_sequence_positive"),
        CheckConstraint(
            "payload_schema_version > 0",
            name="execution_event_schema_version_positive",
        ),
        Index(
            "ix_execution_events_project_run_time",
            "project_id",
            "workflow_run_id",
            "occurred_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agent_session_id: Mapped[str | None] = mapped_column(String(255))
    step_run_id: Mapped[str | None] = mapped_column(String(255))
    correlation_id: Mapped[str | None] = mapped_column(String(255))
    causation_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("execution_events.id"),
    )


class ProviderOperationORM(Base):
    __tablename__ = "provider_operations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_run_id"],
            ["workflow_runs.project_id", "workflow_runs.id"],
            name="fk_provider_operations_run_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workflow_run_id", "step_run_id"],
            ["workflow_step_runs.workflow_run_id", "workflow_step_runs.id"],
            name="fk_provider_operations_step_scope",
        ),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_provider_operations_project_idempotency",
        ),
        CheckConstraint(
            "status IN ('RESERVED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')",
            name="provider_operation_status_valid",
        ),
        CheckConstraint(
            "settlement_state IN ('UNSETTLED', 'SETTLED', 'RELEASED')",
            name="provider_operation_settlement_valid",
        ),
        CheckConstraint("row_version >= 0", name="provider_operation_row_version_nonnegative"),
        CheckConstraint(
            "persistence_version > 0",
            name="provider_operation_persistence_version_positive",
        ),
        CheckConstraint(
            "reserved_request_count >= 0 AND reserved_input_tokens >= 0 "
            "AND reserved_output_tokens >= 0 AND reserved_cost_minor_units >= 0",
            name="provider_operation_reservation_nonnegative",
        ),
        CheckConstraint("retry_count >= 0", name="provider_operation_retry_nonnegative"),
        Index(
            "ix_provider_operations_run_created",
            "workflow_run_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_provider_operations_status_updated",
            "status",
            "updated_at",
        ),
        Index(
            "ix_provider_operations_provider_failure_created",
            "provider_identity",
            "failure_category",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    logical_step_id: Mapped[str] = mapped_column(String(255), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(String(255))
    provider_category: Mapped[str] = mapped_column(String(50), nullable=False)
    operation_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_or_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(500), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    reserved_request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_cost_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    is_live_provider: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    settlement_state: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failure_category: Mapped[str | None] = mapped_column(String(100))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    diagnostic_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    persistence_version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {
        "version_id_col": persistence_version,
        "version_id_generator": False,
    }


class UploadedProgressReportORM(Base):
    __tablename__ = "uploaded_progress_reports"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "package_id",
            "package_checksum",
            "report_id",
            "report_checksum",
            "original_report_checksum",
            name="uq_progress_reports_exact_identity",
        ),
        CheckConstraint("original_report_size > 0", name="progress_report_size_positive"),
        Index(
            "ix_progress_reports_project_package_received",
            "project_id",
            "package_id",
            "received_at",
        ),
        Index("ix_progress_reports_report_id", "report_id"),
        Index("ix_progress_reports_original_checksum", "original_report_checksum"),
    )

    receipt_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    report_id: Mapped[str] = mapped_column(String(255), nullable=False)
    report_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    report_schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    original_report_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    original_report_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_report_media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    original_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    envelope_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    uploader_type: Mapped[str] = mapped_column(String(100), nullable=False)
    client_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_path_hint: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    validation_errors_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    validation_warnings_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    chain_state: Mapped[str] = mapped_column(String(50), nullable=False)
    accepted_for_projection: Mapped[bool] = mapped_column(Boolean, nullable=False)
    normalized_record_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ProjectProgressProjectionORM(Base):
    __tablename__ = "project_progress_projections"

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    package_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workflow_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    package_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_report_id: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_report_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_execution_round: Mapped[int] = mapped_column(Integer, nullable=False)
    latest_status: Mapped[str] = mapped_column(String(50), nullable=False)
    chain_state: Mapped[str] = mapped_column(String(50), nullable=False)
    projection_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    projection_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
