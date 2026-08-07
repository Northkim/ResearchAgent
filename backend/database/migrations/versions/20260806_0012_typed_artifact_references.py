"""Add typed local-product Artifact References and dependency bindings.

Revision ID: 20260806_0012
Revises: 20260806_0011
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0012"
down_revision: str | None = "20260806_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_progress_reports_artifact_producer_identity",
        "uploaded_progress_reports",
        ["receipt_id", "project_id", "workflow_instance_id", "report_id"],
    )
    op.create_table(
        "local_artifact_references",
        sa.Column("artifact_id", sa.String(41), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("producer_workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("producer_progress_receipt_id", sa.String(255), nullable=False),
        sa.Column("producer_progress_report_id", sa.String(255), nullable=False),
        sa.Column("producer_execution_round", sa.Integer(), nullable=False),
        sa.Column("producer_capsule_id", sa.String(40), nullable=False),
        sa.Column("producer_capsule_version", sa.String(100), nullable=False),
        sa.Column("artifact_type", sa.String(160), nullable=False),
        sa.Column("artifact_schema_version", sa.String(200), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("relative_path", sa.String(1024), nullable=False),
        sa.Column("content_checksum", sa.String(71), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("cloud_metadata_available", sa.Boolean(), nullable=False),
        sa.Column("produced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "producer_workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_local_artifact_references_producer_instance",
        ),
        sa.ForeignKeyConstraint(
            [
                "producer_progress_receipt_id",
                "project_id",
                "producer_workflow_instance_id",
                "producer_progress_report_id",
            ],
            [
                "uploaded_progress_reports.receipt_id",
                "uploaded_progress_reports.project_id",
                "uploaded_progress_reports.workflow_instance_id",
                "uploaded_progress_reports.report_id",
            ],
            name="fk_local_artifact_references_progress_producer",
        ),
        sa.ForeignKeyConstraint(
            ["producer_capsule_id", "producer_capsule_version"],
            [
                "local_workflow_capsule_versions.capsule_id",
                "local_workflow_capsule_versions.capsule_version",
            ],
            name="fk_local_artifact_references_capsule_version",
        ),
        sa.UniqueConstraint(
            "project_id", "artifact_id", name="uq_local_artifact_references_project_identity"
        ),
        sa.UniqueConstraint(
            "producer_progress_receipt_id",
            "relative_path",
            name="uq_local_artifact_references_progress_path",
        ),
        sa.CheckConstraint(
            "state IN ('DECLARED','LOCAL_AVAILABLE','EXTERNAL_AVAILABLE','METADATA_ONLY',"
            "'MISSING','STALE','INCOMPATIBLE','RETIRED')",
            name="local_artifact_reference_state",
        ),
        sa.CheckConstraint(
            "producer_execution_round > 0", name="local_artifact_reference_round_positive"
        ),
        sa.CheckConstraint(
            "size_bytes BETWEEN 0 AND 1099511627776",
            name="local_artifact_reference_size",
        ),
        sa.CheckConstraint(
            "cloud_metadata_available", name="local_artifact_reference_cloud_metadata"
        ),
    )
    op.create_index(
        "ix_local_artifact_references_project_produced",
        "local_artifact_references",
        ["project_id", "produced_at", "artifact_id"],
    )
    op.create_index(
        "ix_local_artifact_references_producer",
        "local_artifact_references",
        ["project_id", "producer_workflow_instance_id", "produced_at"],
    )
    op.create_index(
        "ix_local_artifact_references_type_state",
        "local_artifact_references",
        ["project_id", "artifact_type", "state"],
    )
    op.create_index(
        "ix_local_artifact_references_checksum",
        "local_artifact_references",
        ["content_checksum"],
    )

    op.create_table(
        "workflow_artifact_requirements",
        sa.Column("workflow_definition_id", sa.String(128), primary_key=True),
        sa.Column("workflow_version", sa.String(100), primary_key=True),
        sa.Column("requirement_key", sa.String(128), primary_key=True),
        sa.Column("artifact_type", sa.String(160), nullable=False),
        sa.Column("compatibility_mode", sa.String(24), nullable=False),
        sa.Column("schema_constraint", sa.String(200), nullable=False),
        sa.Column("cardinality_min", sa.Integer(), nullable=False),
        sa.Column("cardinality_max", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("materialization_mode", sa.String(24), nullable=False),
        sa.Column("target_relative_path", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_workflow_artifact_requirements_definition_version",
        ),
        sa.CheckConstraint(
            "compatibility_mode IN ('EXACT','COMPATIBLE_RANGE','CONVERTER_REQUIRED')",
            name="workflow_artifact_requirement_compatibility",
        ),
        sa.CheckConstraint(
            "materialization_mode IN ('REFERENCE_ONLY','VERIFIED_COPY')",
            name="workflow_artifact_requirement_materialization",
        ),
        sa.CheckConstraint(
            "cardinality_min >= 0 AND cardinality_max >= cardinality_min "
            "AND cardinality_max <= 100",
            name="workflow_artifact_requirement_cardinality",
        ),
    )
    op.create_index(
        "ix_workflow_artifact_requirements_type_schema",
        "workflow_artifact_requirements",
        ["artifact_type", "schema_constraint"],
    )

    op.create_table(
        "project_artifact_dependency_bindings",
        sa.Column("binding_id", sa.String(49), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("consumer_workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("consumer_workflow_definition_id", sa.String(128), nullable=False),
        sa.Column("consumer_workflow_version", sa.String(100), nullable=False),
        sa.Column("requirement_key", sa.String(128), nullable=False),
        sa.Column("artifact_id", sa.String(41), nullable=False),
        sa.Column("expected_checksum", sa.String(71), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["project_id", "consumer_workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_project_artifact_bindings_consumer_instance",
        ),
        sa.ForeignKeyConstraint(
            [
                "consumer_workflow_definition_id",
                "consumer_workflow_version",
                "requirement_key",
            ],
            [
                "workflow_artifact_requirements.workflow_definition_id",
                "workflow_artifact_requirements.workflow_version",
                "workflow_artifact_requirements.requirement_key",
            ],
            name="fk_project_artifact_bindings_requirement",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "artifact_id"],
            ["local_artifact_references.project_id", "local_artifact_references.artifact_id"],
            name="fk_project_artifact_bindings_artifact",
        ),
        sa.UniqueConstraint(
            "project_id",
            "consumer_workflow_instance_id",
            "idempotency_key",
            name="uq_project_artifact_bindings_idempotency",
        ),
        sa.CheckConstraint(
            "state IN ('ACTIVE','RETIRED')", name="project_artifact_binding_state"
        ),
    )
    op.create_index(
        "uq_project_artifact_bindings_active_requirement",
        "project_artifact_dependency_bindings",
        ["project_id", "consumer_workflow_instance_id", "requirement_key"],
        unique=True,
        postgresql_where=sa.text("state = 'ACTIVE'"),
    )
    op.create_index(
        "ix_project_artifact_bindings_artifact",
        "project_artifact_dependency_bindings",
        ["project_id", "artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_artifact_bindings_artifact",
        table_name="project_artifact_dependency_bindings",
    )
    op.drop_index(
        "uq_project_artifact_bindings_active_requirement",
        table_name="project_artifact_dependency_bindings",
    )
    op.drop_table("project_artifact_dependency_bindings")
    op.drop_index(
        "ix_workflow_artifact_requirements_type_schema",
        table_name="workflow_artifact_requirements",
    )
    op.drop_table("workflow_artifact_requirements")
    op.drop_index(
        "ix_local_artifact_references_checksum", table_name="local_artifact_references"
    )
    op.drop_index(
        "ix_local_artifact_references_type_state", table_name="local_artifact_references"
    )
    op.drop_index(
        "ix_local_artifact_references_producer", table_name="local_artifact_references"
    )
    op.drop_index(
        "ix_local_artifact_references_project_produced",
        table_name="local_artifact_references",
    )
    op.drop_table("local_artifact_references")
    op.drop_constraint(
        "uq_progress_reports_artifact_producer_identity",
        "uploaded_progress_reports",
        type_="unique",
    )
