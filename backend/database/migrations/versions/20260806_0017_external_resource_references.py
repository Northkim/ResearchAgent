"""Add Project Resource references and Experiment 0.3 Resource shell.

Revision ID: 20260806_0017
Revises: 20260806_0016
Create Date: 2026-08-09
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0017"
down_revision: str | None = "20260806_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "reproduction-experiment-local-experimental"
OLD_VERSION = "0.2.0"
VERSION = "0.3.0"
CONTRACT_CHECKSUM = "sha256:5851dc2ca70d4f47c73c0a7d84fe7a2beb4f67f853f103667c10079b7990cf81"
CAPSULE_ID = "capsule-4aa162608aafec3c67db316957f57349"
CAPSULE_CHECKSUM = "sha256:4aa162608aafec3c67db316957f57349de3c35c8167bd24b9d008e6e0f1f0da7"
REQUIREMENTS = (
    ("source_repository", "SOURCE_REPOSITORY", ("GITHUB", "LOCAL_TEST")),
    ("dataset", "DATASET", ("HUGGING_FACE", "LOCAL_TEST")),
    ("model", "MODEL", ("HUGGING_FACE", "LOCAL_TEST")),
    ("checkpoint", "CHECKPOINT", ("HUGGING_FACE", "LOCAL_TEST")),
)


def upgrade() -> None:
    op.create_table(
        "project_resource_references",
        sa.Column("resource_id", sa.String(41), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("resource_kind", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("locator", sa.String(300), nullable=False),
        sa.Column("exact_revision", sa.String(128), nullable=False),
        sa.Column("expected_content_checksum", sa.String(71), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lifecycle", sa.String(20), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], name="fk_project_resource_references_project"),
        sa.UniqueConstraint("project_id", "resource_id", name="uq_project_resource_references_scope"),
        sa.CheckConstraint("resource_kind IN ('SOURCE_REPOSITORY','DATASET','MODEL','CHECKPOINT','GENERIC_FILE')", name="project_resource_reference_kind"),
        sa.CheckConstraint("provider IN ('GITHUB','HUGGING_FACE','LOCAL_TEST')", name="project_resource_reference_provider"),
        sa.CheckConstraint("lifecycle IN ('ACTIVE','RETIRED')", name="project_resource_reference_lifecycle"),
    )
    op.create_index("ix_project_resource_references_project_created", "project_resource_references", ["project_id", "created_at", "resource_id"])
    op.create_index("ix_project_resource_references_kind_provider", "project_resource_references", ["project_id", "resource_kind", "provider"])
    op.create_table(
        "workflow_resource_requirements",
        sa.Column("workflow_definition_id", sa.String(128), primary_key=True),
        sa.Column("workflow_version", sa.String(100), primary_key=True),
        sa.Column("requirement_key", sa.String(128), primary_key=True),
        sa.Column("resource_kind", sa.String(32), nullable=False),
        sa.Column("cardinality_min", sa.Integer(), nullable=False),
        sa.Column("cardinality_max", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("allowed_providers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("usage_description", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            ["local_workflow_definition_versions.workflow_definition_id", "local_workflow_definition_versions.version"],
            name="fk_workflow_resource_requirements_definition_version",
        ),
        sa.CheckConstraint("resource_kind IN ('SOURCE_REPOSITORY','DATASET','MODEL','CHECKPOINT','GENERIC_FILE')", name="workflow_resource_requirement_kind"),
        sa.CheckConstraint("cardinality_min >= 0 AND cardinality_max >= cardinality_min AND cardinality_max <= 20", name="workflow_resource_requirement_cardinality"),
    )
    op.create_index("ix_workflow_resource_requirements_kind", "workflow_resource_requirements", ["resource_kind", "workflow_definition_id", "workflow_version"])
    op.create_table(
        "project_workflow_resource_bindings",
        sa.Column("binding_id", sa.String(49), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("workflow_definition_id", sa.String(128), nullable=False),
        sa.Column("workflow_version", sa.String(100), nullable=False),
        sa.Column("requirement_key", sa.String(128), nullable=False),
        sa.Column("resource_id", sa.String(41), nullable=False),
        sa.Column("expected_content_checksum", sa.String(71), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["project_id", "workflow_instance_id"], ["project_workflow_instances.project_id", "project_workflow_instances.workflow_instance_id"], name="fk_workflow_resource_bindings_instance_scope"),
        sa.ForeignKeyConstraint(["workflow_definition_id", "workflow_version", "requirement_key"], ["workflow_resource_requirements.workflow_definition_id", "workflow_resource_requirements.workflow_version", "workflow_resource_requirements.requirement_key"], name="fk_workflow_resource_bindings_requirement"),
        sa.ForeignKeyConstraint(["project_id", "resource_id"], ["project_resource_references.project_id", "project_resource_references.resource_id"], name="fk_workflow_resource_bindings_resource_scope"),
        sa.UniqueConstraint("project_id", "workflow_instance_id", "idempotency_key", name="uq_workflow_resource_bindings_idempotency"),
        sa.CheckConstraint("state IN ('ACTIVE','RETIRED')", name="workflow_resource_binding_state"),
    )
    op.create_index("uq_workflow_resource_bindings_active_requirement", "project_workflow_resource_bindings", ["project_id", "workflow_instance_id", "requirement_key"], unique=True, postgresql_where=sa.text("state = 'ACTIVE'"))
    op.create_index("ix_workflow_resource_bindings_resource", "project_workflow_resource_bindings", ["project_id", "resource_id"])

    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    _assert_preconditions(connection)
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        SELECT workflow_definition_id, :version, :contract,
               'artifact-and-resource-bindings/v0.1', output_schema_id,
               compatibility || jsonb_build_object(
                 'resource_delivery', 'EXACT_PROJECT_BINDING_LOCAL_RESOLVER',
                 'paper_reproduction', 'NOT_YET_ENABLED'),
               'REVIEWED', 'SCAFFOLD_CORE', :now, :now, :now
        FROM local_workflow_definition_versions
        WHERE workflow_definition_id = :id AND version = :old_version
    """), {"id": WORKFLOW_ID, "version": VERSION, "old_version": OLD_VERSION, "contract": CONTRACT_CHECKSUM, "now": now})
    connection.execute(sa.text("""
        INSERT INTO local_workflow_capsule_versions
          (capsule_id, capsule_version, workflow_definition_id, workflow_version,
           definition_checksum, archive_size_bytes, archive_media_type, mutable_roots,
           capability_requirements, compatibility, review_status,
           legacy_package_compatible, created_at, updated_at)
        SELECT :capsule_id, :version, workflow_definition_id, :version,
               :checksum, 0, archive_media_type, mutable_roots,
               capability_requirements || CAST(:capability AS jsonb),
               compatibility || jsonb_build_object(
                 'resource_delivery', 'EXACT_PROJECT_BINDING_LOCAL_RESOLVER'),
               'REVIEWED', false, :now, :now
        FROM local_workflow_capsule_versions
        WHERE workflow_definition_id = :id AND workflow_version = :old_version
          AND capsule_version = :old_version
    """), {"id": WORKFLOW_ID, "version": VERSION, "old_version": OLD_VERSION, "capsule_id": CAPSULE_ID, "checksum": CAPSULE_CHECKSUM, "capability": json.dumps(["resource.index.verify/v0.1"]), "now": now})
    for table in ("workflow_artifact_requirements", "workflow_definition_version_skill_pins"):
        columns = (
            "workflow_definition_id, workflow_version, requirement_key, artifact_type, compatibility_mode, schema_constraint, cardinality_min, cardinality_max, required, materialization_mode, target_relative_path, created_at, updated_at"
            if table == "workflow_artifact_requirements" else
            "workflow_definition_id, workflow_version, pin_order, skill_id, skill_version, skill_checksum, purpose, created_at"
        )
        select_columns = columns.replace("workflow_version", ":version", 1).replace("created_at, updated_at", ":now, :now").replace("created_at", ":now")
        connection.execute(sa.text(f"INSERT INTO {table} ({columns}) SELECT {select_columns} FROM {table} WHERE workflow_definition_id = :id AND workflow_version = :old_version"), {"id": WORKFLOW_ID, "version": VERSION, "old_version": OLD_VERSION, "now": now})
    for key, kind, providers in REQUIREMENTS:
        connection.execute(sa.text("""
            INSERT INTO workflow_resource_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               resource_kind, cardinality_min, cardinality_max, required,
               allowed_providers_json, usage_description, created_at, updated_at)
            VALUES (:id, :version, :key, :kind, 0, 1, false,
                    CAST(:providers AS jsonb), :description, :now, :now)
        """), {"id": WORKFLOW_ID, "version": VERSION, "key": key, "kind": kind, "providers": json.dumps(providers), "description": "Optional external asset reference for the non-executing Idea Experiment scaffold.", "now": now})
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    for table in ("project_workflow_resource_bindings", "workflow_resource_requirements", "workflow_definition_version_skill_pins", "workflow_artifact_requirements"):
        connection.execute(sa.text(f"DELETE FROM {table} WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_capsule_versions WHERE capsule_id = :capsule_id AND capsule_version = :version"), {"capsule_id": CAPSULE_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_definition_versions WHERE workflow_definition_id = :id AND version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    op.drop_table("project_workflow_resource_bindings")
    op.drop_table("workflow_resource_requirements")
    op.drop_table("project_resource_references")


def _assert_preconditions(connection: sa.Connection) -> None:
    value = connection.scalar(sa.text("SELECT count(*) FROM local_workflow_definition_versions WHERE workflow_definition_id = :id AND version = :version"), {"id": WORKFLOW_ID, "version": OLD_VERSION})
    if value != 1:
        raise RuntimeError("F1E requires immutable Experiment 0.2")


def _assert_seed(connection: sa.Connection) -> None:
    requirements = connection.scalar(sa.text("SELECT count(*) FROM workflow_resource_requirements WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    pins = connection.scalar(sa.text("SELECT count(*) FROM workflow_definition_version_skill_pins WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    if requirements != 4 or pins != 2:
        raise RuntimeError("F1E deterministic Experiment Resource seed conflict")
