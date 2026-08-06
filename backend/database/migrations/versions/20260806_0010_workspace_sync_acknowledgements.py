"""Add Capsule acquisition bindings and Workspace installation acknowledgements.

Revision ID: 20260806_0010
Revises: 20260806_0009
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0010"
down_revision: str | None = "20260806_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


def upgrade() -> None:
    op.create_table(
        "local_workflow_capsule_artifacts",
        sa.Column("capsule_artifact_id", sa.String(49), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("capsule_id", sa.String(40), nullable=False),
        sa.Column("capsule_version", sa.String(100), nullable=False),
        sa.Column("package_id", sa.String(255), nullable=False),
        sa.Column("package_schema_version", sa.String(100), nullable=False),
        sa.Column("package_checksum", sa.String(71), nullable=False),
        sa.Column("manifest_checksum", sa.String(71), nullable=False),
        sa.Column("archive_checksum", sa.String(71), nullable=False),
        sa.Column("archive_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("archive_storage_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_local_workflow_capsule_artifacts_instance",
        ),
        sa.ForeignKeyConstraint(
            ["capsule_id", "capsule_version"],
            [
                "local_workflow_capsule_versions.capsule_id",
                "local_workflow_capsule_versions.capsule_version",
            ],
            name="fk_local_workflow_capsule_artifacts_capsule_version",
        ),
        sa.UniqueConstraint(
            "project_id", "workflow_instance_id",
            name="uq_local_workflow_capsule_artifacts_instance",
        ),
        sa.UniqueConstraint(
            "project_id", "package_id",
            name="uq_local_workflow_capsule_artifacts_package",
        ),
        sa.CheckConstraint(
            "status IN ('AVAILABLE','UNAVAILABLE')",
            name=op.f("ck_local_workflow_capsule_artifacts_local_workflow_capsule_artifact_status"),
        ),
        sa.CheckConstraint(
            "archive_size_bytes BETWEEN 0 AND 536870912",
            name=op.f("ck_local_workflow_capsule_artifacts_local_workflow_capsule_artifact_archive_size"),
        ),
        sa.CheckConstraint(
            "file_count > 0",
            name=op.f("ck_local_workflow_capsule_artifacts_local_workflow_capsule_artifact_file_count"),
        ),
    )
    op.create_index(
        "ix_local_workflow_capsule_artifacts_project_status",
        "local_workflow_capsule_artifacts",
        ["project_id", "status"],
    )
    op.create_table(
        "workspace_installation_acknowledgements",
        sa.Column("installation_id", sa.String(40), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("workspace_id", sa.String(42), nullable=False),
        sa.Column("manifest_revision", sa.BigInteger(), nullable=False),
        sa.Column("manifest_checksum", sa.String(71), nullable=False),
        sa.Column("installed_lock_schema", sa.String(100), nullable=False),
        sa.Column("installed_lock_checksum", sa.String(71), nullable=False),
        sa.Column("plan_checksum", sa.String(71), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("installed_capsules", postgresql.JSONB(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.project_id", "projects.workspace_id"],
            name="fk_workspace_installation_acknowledgements_project_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "manifest_revision"],
            [
                "project_desired_manifests.project_id",
                "project_desired_manifests.manifest_revision",
            ],
            name="fk_workspace_installation_acknowledgements_manifest",
        ),
        sa.UniqueConstraint(
            "workspace_id", "idempotency_key",
            name="uq_workspace_installation_acknowledgements_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id", "manifest_revision", "installed_lock_checksum",
            name="uq_workspace_installation_acknowledgements_lock",
        ),
        sa.CheckConstraint(
            "status = 'ACKNOWLEDGED'",
            name=op.f("ck_workspace_installation_acknowledgements_workspace_installation_acknowledgement_status"),
        ),
        sa.CheckConstraint(
            "manifest_revision > 0",
            name=op.f("ck_workspace_installation_acknowledgements_workspace_installation_acknowledgement_revision"),
        ),
    )
    op.create_index(
        "ix_workspace_install_ack_project_revision",
        "workspace_installation_acknowledgements",
        ["project_id", "manifest_revision", "status"],
    )
    _backfill_legacy_artifacts(op.get_bind())


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_install_ack_project_revision",
        table_name="workspace_installation_acknowledgements",
    )
    op.drop_table("workspace_installation_acknowledgements")
    op.drop_index(
        "ix_local_workflow_capsule_artifacts_project_status",
        table_name="local_workflow_capsule_artifacts",
    )
    op.drop_table("local_workflow_capsule_artifacts")


def _backfill_legacy_artifacts(connection: sa.Connection) -> None:
    expected = connection.scalar(sa.text(
        "SELECT count(*) FROM local_projects WHERE current_package_id IS NOT NULL"
    ))
    bound = connection.scalar(sa.text("""
        SELECT count(*)
        FROM local_projects lp
        JOIN project_workflow_instances pwi ON pwi.project_id=lp.project_id
          AND pwi.legacy_package_id=lp.current_package_id
        WHERE lp.current_package_id IS NOT NULL
    """))
    if expected != bound:
        raise RuntimeError(
            "legacy Package is missing its deterministic Workflow Instance binding"
        )
    rows = connection.execute(sa.text("""
        SELECT lp.project_id,lp.current_package_id,lp.current_package_schema_version,
               lp.current_package_checksum,lp.current_manifest_checksum,
               lp.current_zip_checksum,lp.current_archive_storage_key,
               lp.current_package_file_count,lp.current_package_size_bytes,
               lp.current_package_generated_at,pwi.workflow_instance_id,
               pwi.capsule_id,pwi.capsule_version
        FROM local_projects lp
        JOIN project_workflow_instances pwi ON pwi.project_id=lp.project_id
        WHERE lp.current_package_id IS NOT NULL
          AND pwi.legacy_package_id=lp.current_package_id
        ORDER BY lp.project_id
    """)).mappings()
    for row in rows:
        required = (
            "current_package_schema_version", "current_package_checksum",
            "current_manifest_checksum", "current_zip_checksum",
            "current_archive_storage_key", "current_package_file_count",
            "current_package_size_bytes", "current_package_generated_at",
            "capsule_id", "capsule_version",
        )
        if any(row[name] is None for name in required):
            raise RuntimeError("legacy Package metadata incomplete during Capsule artifact backfill")
        artifact_id = "capsule-artifact-" + uuid5(
            _NAMESPACE,
            "capsule-artifact/v1|"
            f"project={row['project_id']}|instance={row['workflow_instance_id']}|"
            f"package={row['current_package_id']}",
        ).hex
        values = {
            "artifact_id": artifact_id,
            "project_id": row["project_id"],
            "instance_id": row["workflow_instance_id"],
            "capsule_id": row["capsule_id"],
            "capsule_version": row["capsule_version"],
            "package_id": row["current_package_id"],
            "package_schema": row["current_package_schema_version"],
            "package_checksum": row["current_package_checksum"],
            "manifest_checksum": row["current_manifest_checksum"],
            "archive_checksum": row["current_zip_checksum"],
            "archive_size": row["current_package_size_bytes"],
            "file_count": row["current_package_file_count"],
            "storage_key": row["current_archive_storage_key"],
            "created_at": row["current_package_generated_at"],
        }
        connection.execute(sa.text("""
            INSERT INTO local_workflow_capsule_artifacts
              (capsule_artifact_id,project_id,workflow_instance_id,capsule_id,
               capsule_version,package_id,package_schema_version,package_checksum,
               manifest_checksum,archive_checksum,archive_size_bytes,file_count,
               archive_storage_key,status,created_at,updated_at)
            VALUES (:artifact_id,:project_id,:instance_id,:capsule_id,
                    :capsule_version,:package_id,:package_schema,:package_checksum,
                    :manifest_checksum,:archive_checksum,:archive_size,:file_count,
                    :storage_key,'AVAILABLE',:created_at,:created_at)
            ON CONFLICT (capsule_artifact_id) DO NOTHING
        """), values)
        persisted = connection.execute(sa.text("""
            SELECT project_id,workflow_instance_id,package_id,archive_checksum
            FROM local_workflow_capsule_artifacts
            WHERE capsule_artifact_id=:artifact_id
        """), {"artifact_id": artifact_id}).mappings().one()
        if dict(persisted) != {
            "project_id": row["project_id"],
            "workflow_instance_id": row["workflow_instance_id"],
            "package_id": row["current_package_id"],
            "archive_checksum": row["current_zip_checksum"],
        }:
            raise RuntimeError("Capsule artifact backfill content conflict")
