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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
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


class LocalProjectORM(Base):
    """Cloud metadata for the teacher-aligned local V0.1 project flow."""

    __tablename__ = "local_projects"
    __table_args__ = (
        CheckConstraint(
            "selected_workflow = 'LITERATURE_SEARCH'",
            name="local_project_literature_search_only",
        ),
        CheckConstraint("char_length(name) BETWEEN 1 AND 160", name="local_project_name_length"),
        CheckConstraint(
            "char_length(research_topic) BETWEEN 1 AND 500",
            name="local_project_topic_length",
        ),
        Index("ix_local_projects_updated", "updated_at", "project_id"),
    )

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    research_topic: Mapped[str] = mapped_column(String(500), nullable=False)
    selected_workflow: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_package_id: Mapped[str | None] = mapped_column(String(255))
    current_package_schema_version: Mapped[str | None] = mapped_column(String(100))
    current_package_checksum: Mapped[str | None] = mapped_column(String(71))
    current_manifest_checksum: Mapped[str | None] = mapped_column(String(71))
    current_zip_checksum: Mapped[str | None] = mapped_column(String(71))
    current_workflow_id: Mapped[str | None] = mapped_column(String(255))
    current_workflow_version: Mapped[str | None] = mapped_column(String(100))
    current_workflow_checksum: Mapped[str | None] = mapped_column(String(71))
    current_archive_storage_key: Mapped[str | None] = mapped_column(Text)
    current_package_file_count: Mapped[int | None] = mapped_column(Integer)
    current_package_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    current_package_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class LocalWorkflowDefinitionORM(Base):
    __tablename__ = "local_workflow_definitions"
    __table_args__ = (Index("ix_local_workflow_definitions_lifecycle", "lifecycle"),)

    workflow_definition_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(20), nullable=False)
    allows_multiple_instances: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalWorkflowDefinitionVersionORM(Base):
    __tablename__ = "local_workflow_definition_versions"
    __table_args__ = (
        CheckConstraint(
            "core_capability_maturity IN ('REVIEWED_CORE', 'SCAFFOLD_CORE')",
            name="local_workflow_definition_version_core_maturity",
        ),
        Index(
            "ix_local_workflow_definition_versions_definition_review",
            "workflow_definition_id",
            "review_status",
        ),
    )

    workflow_definition_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("local_workflow_definitions.workflow_definition_id"),
        primary_key=True,
    )
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    contract_checksum: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)
    input_schema_id: Mapped[str] = mapped_column(String(200), nullable=False)
    output_schema_id: Mapped[str] = mapped_column(String(200), nullable=False)
    compatibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    core_capability_maturity: Mapped[str] = mapped_column(String(24), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalBuiltInSkillDefinitionORM(Base):
    __tablename__ = "local_builtin_skill_definitions"
    __table_args__ = (
        CheckConstraint(
            "lifecycle IN ('AVAILABLE','RETIRED')",
            name="local_builtin_skill_definition_lifecycle",
        ),
        CheckConstraint(
            "source_class = 'PLATFORM_BUILT_IN'",
            name="local_builtin_skill_definition_source_class",
        ),
        CheckConstraint(
            "trust_tier = 'BUILT_IN_REVIEWED'",
            name="local_builtin_skill_definition_trust",
        ),
        Index("ix_local_builtin_skill_definitions_lifecycle", "lifecycle", "skill_id"),
    )

    skill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(20), nullable=False)
    source_class: Mapped[str] = mapped_column(String(32), nullable=False)
    trust_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalSkillVersionORM(Base):
    __tablename__ = "local_skill_versions"
    __table_args__ = (
        CheckConstraint(
            "trust_tier IN ('BUILT_IN_REVIEWED','PRIVATE_DISABLED','IMPORTED_QUARANTINED')",
            name="local_skill_version_trust",
        ),
        CheckConstraint(
            "review_status IN ('REVIEWED','RETIRED','QUARANTINED')",
            name="local_skill_version_review_status",
        ),
        Index("ix_local_skill_versions_skill_review", "skill_id", "review_status"),
    )

    skill_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("local_builtin_skill_definitions.skill_id"),
        primary_key=True,
    )
    skill_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    content_checksum: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)
    manifest_schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    content_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trust_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    content_source_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowDefinitionVersionSkillPinORM(Base):
    __tablename__ = "workflow_definition_version_skill_pins"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_workflow_skill_pins_workflow_version",
        ),
        ForeignKeyConstraint(
            ["skill_id", "skill_version"],
            ["local_skill_versions.skill_id", "local_skill_versions.skill_version"],
            name="fk_workflow_skill_pins_skill_version",
        ),
        UniqueConstraint(
            "workflow_definition_id", "workflow_version", "skill_id",
            name="uq_workflow_skill_pins_exact_skill",
        ),
        CheckConstraint("pin_order BETWEEN 0 AND 99", name="workflow_skill_pin_order"),
        Index(
            "ix_workflow_skill_pins_workflow",
            "workflow_definition_id", "workflow_version", "pin_order",
        ),
    )

    workflow_definition_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    pin_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LocalWorkflowCapsuleVersionORM(Base):
    __tablename__ = "local_workflow_capsule_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_local_workflow_capsule_versions_definition_version",
        ),
        CheckConstraint(
            "archive_size_bytes BETWEEN 0 AND 536870912",
            name="local_workflow_capsule_archive_size",
        ),
        Index(
            "ix_local_workflow_capsule_versions_workflow_version",
            "workflow_definition_id",
            "workflow_version",
        ),
        Index("ix_local_workflow_capsule_versions_review_status", "review_status"),
    )

    capsule_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    capsule_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    workflow_definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    definition_checksum: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)
    archive_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    archive_media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    mutable_roots: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    capability_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    compatibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    legacy_package_compatible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectWorkflowInstanceORM(Base):
    __tablename__ = "project_workflow_instances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            name="fk_project_workflow_instances_project_id_projects",
        ),
        ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_project_workflow_instances_definition_version",
        ),
        ForeignKeyConstraint(
            ["capsule_id", "capsule_version"],
            [
                "local_workflow_capsule_versions.capsule_id",
                "local_workflow_capsule_versions.capsule_version",
            ],
            name="fk_project_workflow_instances_capsule_version",
        ),
        UniqueConstraint(
            "project_id",
            "workflow_instance_id",
            name="uq_project_workflow_instances_project_identity",
        ),
        CheckConstraint(
            "created_manifest_revision >= 0",
            name="project_workflow_instance_created_revision",
        ),
        CheckConstraint(
            "retired_manifest_revision IS NULL OR retired_manifest_revision >= 0",
            name="project_workflow_instance_retired_revision",
        ),
        CheckConstraint(
            "(capsule_id IS NULL AND capsule_version IS NULL) OR "
            "(capsule_id IS NOT NULL AND capsule_version IS NOT NULL)",
            name="project_workflow_instance_capsule_pair",
        ),
        CheckConstraint(
            "(desired_state = 'ACTIVE' AND retired_manifest_revision IS NULL) OR "
            "(desired_state = 'RETIRED' AND retired_manifest_revision IS NOT NULL)",
            name="project_workflow_instance_retirement_state",
        ),
        Index(
            "ix_project_workflow_instances_project_state",
            "project_id",
            "desired_state",
        ),
        Index(
            "ix_project_workflow_instances_project_definition",
            "project_id",
            "workflow_definition_id",
        ),
    )

    workflow_instance_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("local_projects.project_id"), nullable=False
    )
    workflow_definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    capsule_id: Mapped[str | None] = mapped_column(String(40))
    capsule_version: Mapped[str | None] = mapped_column(String(100))
    desired_state: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_manifest_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    retired_manifest_revision: Mapped[int | None] = mapped_column(BigInteger)
    legacy_package_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectORM(Base):
    """Canonical cloud Project identity and Desired Manifest revision head."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "workspace_id", name="uq_projects_project_workspace"
        ),
        CheckConstraint(
            "status IN ('ACTIVE','ARCHIVED')", name="project_status"
        ),
        CheckConstraint(
            "current_manifest_revision >= 0", name="project_manifest_revision"
        ),
        Index("ix_projects_status_updated", "status", "updated_at"),
    )

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(42), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    research_topic: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_manifest_revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    legacy_local_project_id: Mapped[str | None] = mapped_column(
        String(255), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectDesiredManifestORM(Base):
    __tablename__ = "project_desired_manifests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.project_id", "projects.workspace_id"],
            name="fk_project_desired_manifests_project_workspace",
        ),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_project_desired_manifests_project_idempotency",
        ),
        CheckConstraint(
            "manifest_revision > 0", name="desired_manifest_revision_positive"
        ),
        CheckConstraint(
            "base_revision >= 0 AND manifest_revision = base_revision + 1",
            name="desired_manifest_revision_step",
        ),
        Index(
            "ix_project_desired_manifests_project_revision",
            "project_id",
            "manifest_revision",
        ),
    )

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    manifest_revision: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(42), nullable=False)
    base_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_checksum: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectManifestEntryORM(Base):
    __tablename__ = "project_manifest_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "manifest_revision"],
            [
                "project_desired_manifests.project_id",
                "project_desired_manifests.manifest_revision",
            ],
            name="fk_project_manifest_entries_manifest",
        ),
        ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_project_manifest_entries_workflow_instance",
        ),
        UniqueConstraint(
            "project_id",
            "manifest_revision",
            "entry_kind",
            "entry_id",
            name="uq_project_manifest_entries_revision_identity",
        ),
        CheckConstraint(
            "entry_kind = 'WORKFLOW_INSTANCE'", name="manifest_entry_kind"
        ),
        CheckConstraint(
            "desired_action IN ('ENSURE_PRESENT','RETIRE')",
            name="manifest_entry_desired_action",
        ),
        Index(
            "ix_project_manifest_entries_instance", "workflow_instance_id"
        ),
        Index(
            "ix_project_manifest_entries_project_revision",
            "project_id",
            "manifest_revision",
        ),
    )

    entry_id: Mapped[str] = mapped_column(String(38), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    manifest_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entry_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    desired_action: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowCapsuleArtifactORM(Base):
    """Project/Workflow-Instance-bound downloadable Capsule archive metadata."""

    __tablename__ = "local_workflow_capsule_artifacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_local_workflow_capsule_artifacts_instance",
        ),
        ForeignKeyConstraint(
            ["capsule_id", "capsule_version"],
            [
                "local_workflow_capsule_versions.capsule_id",
                "local_workflow_capsule_versions.capsule_version",
            ],
            name="fk_local_workflow_capsule_artifacts_capsule_version",
        ),
        UniqueConstraint(
            "project_id",
            "workflow_instance_id",
            name="uq_local_workflow_capsule_artifacts_instance",
        ),
        UniqueConstraint(
            "project_id", "package_id", name="uq_local_workflow_capsule_artifacts_package"
        ),
        CheckConstraint(
            "status IN ('AVAILABLE','UNAVAILABLE')",
            name="local_workflow_capsule_artifact_status",
        ),
        CheckConstraint(
            "archive_size_bytes BETWEEN 0 AND 536870912",
            name="local_workflow_capsule_artifact_archive_size",
        ),
        CheckConstraint("file_count > 0", name="local_workflow_capsule_artifact_file_count"),
        Index(
            "ix_local_workflow_capsule_artifacts_project_status",
            "project_id",
            "status",
        ),
    )

    capsule_artifact_id: Mapped[str] = mapped_column(String(49), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    capsule_id: Mapped[str] = mapped_column(String(40), nullable=False)
    capsule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    package_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    package_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    archive_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    archive_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    archive_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceInstallationAcknowledgementORM(Base):
    """Cloud-retained report of a locally verified Workspace installation."""

    __tablename__ = "workspace_installation_acknowledgements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.project_id", "projects.workspace_id"],
            name="fk_workspace_installation_acknowledgements_project_workspace",
        ),
        ForeignKeyConstraint(
            ["project_id", "manifest_revision"],
            [
                "project_desired_manifests.project_id",
                "project_desired_manifests.manifest_revision",
            ],
            name="fk_workspace_installation_acknowledgements_manifest",
        ),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_workspace_installation_acknowledgements_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "manifest_revision",
            "installed_lock_checksum",
            name="uq_workspace_installation_acknowledgements_lock",
        ),
        CheckConstraint(
            "status = 'ACKNOWLEDGED'",
            name="workspace_installation_acknowledgement_status",
        ),
        CheckConstraint(
            "manifest_revision > 0",
            name="workspace_installation_acknowledgement_revision",
        ),
        Index(
            "ix_workspace_install_ack_project_revision",
            "project_id",
            "manifest_revision",
            "status",
        ),
    )

    installation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(42), nullable=False)
    manifest_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    installed_lock_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    installed_lock_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    plan_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    installed_capsules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
        UniqueConstraint(
            "receipt_id",
            "project_id",
            "workflow_instance_id",
            "report_id",
            name="uq_progress_reports_artifact_producer_identity",
        ),
        CheckConstraint("original_report_size > 0", name="progress_report_size_positive"),
        Index(
            "ix_progress_reports_project_package_received",
            "project_id",
            "package_id",
            "received_at",
        ),
        ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_uploaded_progress_reports_project_workflow_instance",
        ),
        Index(
            "ix_progress_reports_project_instance_received",
            "project_id",
            "workflow_instance_id",
            "received_at",
            "receipt_id",
        ),
        Index("ix_progress_reports_report_id", "report_id"),
        Index("ix_progress_reports_original_checksum", "original_report_checksum"),
    )

    receipt_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
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


class LocalArtifactReferenceORM(Base):
    """Cloud metadata for immutable local-product research outputs."""

    __tablename__ = "local_artifact_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "producer_workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_local_artifact_references_producer_instance",
        ),
        ForeignKeyConstraint(
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
        ForeignKeyConstraint(
            ["producer_capsule_id", "producer_capsule_version"],
            [
                "local_workflow_capsule_versions.capsule_id",
                "local_workflow_capsule_versions.capsule_version",
            ],
            name="fk_local_artifact_references_capsule_version",
        ),
        UniqueConstraint(
            "project_id", "artifact_id", name="uq_local_artifact_references_project_identity"
        ),
        UniqueConstraint(
            "producer_progress_receipt_id",
            "relative_path",
            name="uq_local_artifact_references_progress_path",
        ),
        CheckConstraint(
            "state IN ('DECLARED','LOCAL_AVAILABLE','EXTERNAL_AVAILABLE','METADATA_ONLY',"
            "'MISSING','STALE','INCOMPATIBLE','RETIRED')",
            name="local_artifact_reference_state",
        ),
        CheckConstraint(
            "producer_execution_round > 0", name="local_artifact_reference_round_positive"
        ),
        CheckConstraint(
            "size_bytes BETWEEN 0 AND 1099511627776",
            name="local_artifact_reference_size",
        ),
        CheckConstraint(
            "cloud_metadata_available", name="local_artifact_reference_cloud_metadata"
        ),
        Index(
            "ix_local_artifact_references_project_produced",
            "project_id", "produced_at", "artifact_id",
        ),
        Index(
            "ix_local_artifact_references_producer",
            "project_id", "producer_workflow_instance_id", "produced_at",
        ),
        Index(
            "ix_local_artifact_references_type_state",
            "project_id", "artifact_type", "state",
        ),
        Index("ix_local_artifact_references_checksum", "content_checksum"),
    )

    artifact_id: Mapped[str] = mapped_column(String(41), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    producer_workflow_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    producer_progress_receipt_id: Mapped[str] = mapped_column(String(255), nullable=False)
    producer_progress_report_id: Mapped[str] = mapped_column(String(255), nullable=False)
    producer_execution_round: Mapped[int] = mapped_column(Integer, nullable=False)
    producer_capsule_id: Mapped[str] = mapped_column(String(40), nullable=False)
    producer_capsule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(160), nullable=False)
    artifact_schema_version: Mapped[str] = mapped_column(String(200), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cloud_metadata_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowArtifactRequirementORM(Base):
    __tablename__ = "workflow_artifact_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_workflow_artifact_requirements_definition_version",
        ),
        CheckConstraint(
            "compatibility_mode IN ('EXACT','COMPATIBLE_RANGE','CONVERTER_REQUIRED')",
            name="workflow_artifact_requirement_compatibility",
        ),
        CheckConstraint(
            "materialization_mode IN ('REFERENCE_ONLY','VERIFIED_COPY')",
            name="workflow_artifact_requirement_materialization",
        ),
        CheckConstraint(
            "cardinality_min >= 0 AND cardinality_max >= cardinality_min "
            "AND cardinality_max <= 100",
            name="workflow_artifact_requirement_cardinality",
        ),
        Index(
            "ix_workflow_artifact_requirements_type_schema",
            "artifact_type", "schema_constraint",
        ),
    )

    workflow_definition_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    requirement_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(160), nullable=False)
    compatibility_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    schema_constraint: Mapped[str] = mapped_column(String(200), nullable=False)
    cardinality_min: Mapped[int] = mapped_column(Integer, nullable=False)
    cardinality_max: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    materialization_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    target_relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtifactDependencyBindingORM(Base):
    __tablename__ = "project_artifact_dependency_bindings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "consumer_workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_project_artifact_bindings_consumer_instance",
        ),
        ForeignKeyConstraint(
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
        ForeignKeyConstraint(
            ["project_id", "artifact_id"],
            ["local_artifact_references.project_id", "local_artifact_references.artifact_id"],
            name="fk_project_artifact_bindings_artifact",
        ),
        UniqueConstraint(
            "project_id",
            "consumer_workflow_instance_id",
            "idempotency_key",
            name="uq_project_artifact_bindings_idempotency",
        ),
        CheckConstraint(
            "state IN ('ACTIVE','RETIRED')", name="project_artifact_binding_state"
        ),
        Index(
            "uq_project_artifact_bindings_active_requirement",
            "project_id", "consumer_workflow_instance_id", "requirement_key",
            unique=True,
            postgresql_where=text("state = 'ACTIVE'"),
        ),
        Index(
            "ix_project_artifact_bindings_artifact", "project_id", "artifact_id"
        ),
    )

    binding_id: Mapped[str] = mapped_column(String(49), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    consumer_workflow_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    consumer_workflow_definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    consumer_workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    requirement_key: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(41), nullable=False)
    expected_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class ProxyCapabilityTokenORM(Base):
    """Digest-only capability credential for the experimental local-Harness Proxy."""

    __tablename__ = "proxy_capability_tokens"
    __table_args__ = (
        UniqueConstraint("token_digest_sha256", name="uq_proxy_capability_tokens_digest"),
        CheckConstraint("maximum_operations BETWEEN 0 AND 50", name="proxy_token_maximum_operations_valid"),
        CheckConstraint("admitted_operations BETWEEN 0 AND maximum_operations", name="proxy_token_admitted_operations_valid"),
        CheckConstraint(
            "maximum_provider_calls BETWEEN 0 AND 20",
            name="proxy_token_maximum_provider_calls_valid",
        ),
        CheckConstraint(
            "used_provider_calls BETWEEN 0 AND maximum_provider_calls",
            name="proxy_token_used_provider_calls_valid",
        ),
        CheckConstraint(
            "maximum_provider_cost_microusd BETWEEN 0 AND 50000",
            name="proxy_token_maximum_provider_cost_valid",
        ),
        CheckConstraint(
            "reserved_provider_cost_microusd BETWEEN 0 AND maximum_provider_cost_microusd",
            name="proxy_token_reserved_provider_cost_valid",
        ),
        CheckConstraint(
            "reported_provider_cost_microusd >= 0",
            name="proxy_token_reported_provider_cost_nonnegative",
        ),
        CheckConstraint("expires_at > issued_at", name="proxy_token_expiry_after_issue"),
        Index("ix_proxy_tokens_project_package", "project_id", "package_id"),
        Index("ix_proxy_tokens_expiry_revocation", "expires_at", "revoked"),
    )

    token_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    token_digest_sha256: Mapped[str] = mapped_column(String(71), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    allowed_capability: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_adapter: Mapped[str] = mapped_column(String(255), nullable=False)
    local_session_capabilities_json: Mapped[object] = mapped_column(
        JSONB, nullable=False, default=list
    )
    maximum_operations: Mapped[int] = mapped_column(Integer, nullable=False)
    admitted_operations: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    used_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_provider_cost_microusd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_provider_cost_microusd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reported_provider_cost_microusd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProxyOperationORM(Base):
    """Independent Proxy operation; deliberately has no Hosted Workflow foreign key."""

    __tablename__ = "proxy_operations"
    __table_args__ = (
        UniqueConstraint("token_id", "idempotency_key", name="uq_proxy_operations_scoped_idempotency"),
        CheckConstraint(
            "status IN ('RECEIVED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'RECONCILIATION_REQUIRED')",
            name="proxy_operation_status_valid",
        ),
        CheckConstraint(
            "provider_data_size IS NULL OR provider_data_size BETWEEN 0 AND 524288",
            name="proxy_operation_result_size_valid",
        ),
        CheckConstraint("estimated_cost_minor_units = 0", name="proxy_operation_zero_cost"),
        CheckConstraint("retry_count = 0", name="proxy_operation_zero_retry"),
        CheckConstraint(
            "request_retention_mode IN ('FULL_PARAMETERS', 'CHECKSUM_ONLY')",
            name="proxy_operation_request_retention_mode_valid",
        ),
        CheckConstraint(
            "provider_http_calls BETWEEN 0 AND 1",
            name="proxy_operation_provider_http_calls_valid",
        ),
        CheckConstraint(
            "reserved_cost_microusd BETWEEN 0 AND 50000",
            name="proxy_operation_reserved_cost_valid",
        ),
        CheckConstraint(
            "reported_cost_microusd >= 0",
            name="proxy_operation_reported_cost_nonnegative",
        ),
        CheckConstraint(
            "query_utf8_bytes IS NULL OR query_utf8_bytes > 0",
            name="proxy_operation_query_utf8_bytes_positive",
        ),
        CheckConstraint(
            "query_characters IS NULL OR query_characters > 0",
            name="proxy_operation_query_characters_positive",
        ),
        Index("ix_proxy_operations_project_package_created", "project_id", "package_id", "created_at"),
        Index("ix_proxy_operations_token_status", "token_id", "status"),
        Index("ix_proxy_operations_adapter_status", "adapter_id", "status"),
    )

    operation_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    token_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("proxy_capability_tokens.token_id", ondelete="RESTRICT"), nullable=False
    )
    proxy_contract_version: Mapped[str] = mapped_column(String(100), nullable=False)
    authorization_scope_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_id: Mapped[str] = mapped_column(String(255), nullable=False)
    package_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    capability: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False)
    request_content_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_retention_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    query_checksum: Mapped[str | None] = mapped_column(String(71))
    query_utf8_bytes: Mapped[int | None] = mapped_column(Integer)
    query_characters: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provider_data_checksum: Mapped[str | None] = mapped_column(String(71))
    provider_data_size: Mapped[int | None] = mapped_column(BigInteger)
    response_content_checksum: Mapped[str | None] = mapped_column(String(71))
    estimated_cost_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_http_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_cost_microusd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reported_cost_microusd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    provider_response_checksum: Mapped[str | None] = mapped_column(String(71))
    provider_http_status: Mapped[int | None] = mapped_column(Integer)
    provider_adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_rate_limit_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(100))
    reconciliation_evidence: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
