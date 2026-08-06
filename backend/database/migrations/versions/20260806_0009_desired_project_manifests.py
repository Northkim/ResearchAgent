"""Add canonical Projects and Desired Project Manifest revisions.

Revision ID: 20260806_0009
Revises: 20260806_0008
Create Date: 2026-08-06
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import timezone
from uuid import UUID, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from backend.workflow_packages.serialization import canonical_hash

revision: str = "20260806_0009"
down_revision: str | None = "20260806_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFINITION_ID = "literature-search-local-experimental"
_WORKFLOW_VERSION = "0.3.0"
_CAPSULE_ID = "capsule-0f827b56ed6c5ecf6634f5eee0171ead"
_CAPSULE_VERSION = "0.5.0"
_CAPSULE_CHECKSUM = "sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611"
_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")
_SCHEMA = "reagent.project-desired-manifest/v0.1"


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(255), primary_key=True),
        sa.Column("workspace_id", sa.String(42), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("research_topic", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_manifest_revision", sa.BigInteger(), nullable=False),
        sa.Column("legacy_local_project_id", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "project_id", "workspace_id", name="uq_projects_project_workspace"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','ARCHIVED')", name=op.f("ck_projects_project_status")
        ),
        sa.CheckConstraint(
            "current_manifest_revision >= 0",
            name=op.f("ck_projects_project_manifest_revision"),
        ),
    )
    op.create_index(
        "ix_projects_status_updated", "projects", ["status", "updated_at"]
    )
    op.create_table(
        "project_desired_manifests",
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("manifest_revision", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.String(42), nullable=False),
        sa.Column("base_revision", sa.BigInteger(), nullable=False),
        sa.Column("schema_version", sa.String(100), nullable=False),
        sa.Column("canonical_checksum", sa.String(71), nullable=False, unique=True),
        sa.Column("manifest_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_subject_id", sa.String(255), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.project_id", "projects.workspace_id"],
            name="fk_project_desired_manifests_project_workspace",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "manifest_revision",
            name=op.f("pk_project_desired_manifests"),
        ),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_project_desired_manifests_project_idempotency",
        ),
        sa.CheckConstraint(
            "manifest_revision > 0",
            name=op.f("ck_project_desired_manifests_desired_manifest_revision_positive"),
        ),
        sa.CheckConstraint(
            "base_revision >= 0 AND manifest_revision = base_revision + 1",
            name=op.f("ck_project_desired_manifests_desired_manifest_revision_step"),
        ),
    )
    op.create_index(
        "ix_project_desired_manifests_project_revision",
        "project_desired_manifests",
        ["project_id", "manifest_revision"],
    )
    op.create_table(
        "project_manifest_entries",
        sa.Column("entry_id", sa.String(38), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("manifest_revision", sa.BigInteger(), nullable=False),
        sa.Column("entry_kind", sa.String(40), nullable=False),
        sa.Column("workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("desired_action", sa.String(20), nullable=False),
        sa.Column("entry_checksum", sa.String(71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "manifest_revision"],
            [
                "project_desired_manifests.project_id",
                "project_desired_manifests.manifest_revision",
            ],
            name="fk_project_manifest_entries_manifest",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "workflow_instance_id"],
            [
                "project_workflow_instances.project_id",
                "project_workflow_instances.workflow_instance_id",
            ],
            name="fk_project_manifest_entries_workflow_instance",
        ),
        sa.UniqueConstraint(
            "project_id",
            "manifest_revision",
            "entry_kind",
            "entry_id",
            name="uq_project_manifest_entries_revision_identity",
        ),
        sa.CheckConstraint(
            "entry_kind = 'WORKFLOW_INSTANCE'",
            name=op.f("ck_project_manifest_entries_manifest_entry_kind"),
        ),
        sa.CheckConstraint(
            "desired_action IN ('ENSURE_PRESENT','RETIRE')",
            name=op.f("ck_project_manifest_entries_manifest_entry_desired_action"),
        ),
    )
    op.create_index(
        "ix_project_manifest_entries_instance",
        "project_manifest_entries",
        ["workflow_instance_id"],
    )
    op.create_index(
        "ix_project_manifest_entries_project_revision",
        "project_manifest_entries",
        ["project_id", "manifest_revision"],
    )
    _backfill(op.get_bind())
    op.create_foreign_key(
        "fk_project_workflow_instances_project_id_projects",
        "project_workflow_instances",
        "projects",
        ["project_id"],
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_project_workflow_instances_project_id_projects",
        "project_workflow_instances",
        type_="foreignkey",
    )
    # Restore the exact B1 representation for pre-Package legacy instances.
    op.execute(sa.text("""
        UPDATE project_workflow_instances
        SET capsule_id = NULL, capsule_version = NULL
        WHERE workflow_definition_id = :definition_id
          AND workflow_version = :workflow_version
          AND created_manifest_revision = 0
          AND legacy_package_id IS NULL
    """).bindparams(
        definition_id=_DEFINITION_ID,
        workflow_version=_WORKFLOW_VERSION,
    ))
    op.drop_index(
        "ix_project_manifest_entries_project_revision",
        table_name="project_manifest_entries",
    )
    op.drop_index(
        "ix_project_manifest_entries_instance", table_name="project_manifest_entries"
    )
    op.drop_table("project_manifest_entries")
    op.drop_index(
        "ix_project_desired_manifests_project_revision",
        table_name="project_desired_manifests",
    )
    op.drop_table("project_desired_manifests")
    op.drop_index("ix_projects_status_updated", table_name="projects")
    op.drop_table("projects")


def _backfill(connection: sa.Connection) -> None:
    projects = connection.execute(
        sa.text(
            "SELECT project_id, name, research_topic, selected_workflow, "
            "created_at, updated_at FROM local_projects ORDER BY project_id"
        )
    ).mappings()
    for project in projects:
        if project["selected_workflow"] != "LITERATURE_SEARCH":
            raise RuntimeError("unsupported legacy selected_workflow during manifest backfill")
        project_id = project["project_id"]
        instance_id = "wfi-" + uuid5(
            _NAMESPACE,
            "legacy-workflow-instance/v1|"
            f"project={project_id}|workflow=LITERATURE_SEARCH",
        ).hex
        instance = connection.execute(
            sa.text(
                "SELECT workflow_definition_id, workflow_version, desired_state "
                "FROM project_workflow_instances "
                "WHERE workflow_instance_id=:instance_id AND project_id=:project_id"
            ),
            {"instance_id": instance_id, "project_id": project_id},
        ).mappings().one_or_none()
        if instance is None:
            raise RuntimeError("legacy Workflow Instance missing during manifest backfill")
        if dict(instance) != {
            "workflow_definition_id": _DEFINITION_ID,
            "workflow_version": _WORKFLOW_VERSION,
            "desired_state": "ACTIVE",
        }:
            raise RuntimeError("legacy Workflow Instance conflicts during manifest backfill")

        # A missing historical Package does not remove the reviewed desired
        # Capsule pin; legacy_package_id remains the sole historical Package fact.
        connection.execute(
            sa.text(
                "UPDATE project_workflow_instances "
                "SET capsule_id=:capsule_id, capsule_version=:capsule_version "
                "WHERE workflow_instance_id=:instance_id AND capsule_id IS NULL "
                "AND capsule_version IS NULL"
            ),
            {
                "capsule_id": _CAPSULE_ID,
                "capsule_version": _CAPSULE_VERSION,
                "instance_id": instance_id,
            },
        )
        workspace_id = "workspace-" + project_id.removeprefix("project-")
        created_at = _utc(project["created_at"])
        updated_at = _utc(project["updated_at"])
        idempotency = uuid5(
            _NAMESPACE,
            f"legacy-project-manifest/v1|project={project_id}|revision=1",
        )
        payload = {
            "schema_version": _SCHEMA,
            "project_id": project_id,
            "workspace_id": workspace_id,
            "manifest_revision": 1,
            "base_revision": 0,
            "workflow_instances": [
                {
                    "workflow_instance_id": instance_id,
                    "workflow_definition_id": _DEFINITION_ID,
                    "workflow_definition_version": _WORKFLOW_VERSION,
                    "capsule_id": _CAPSULE_ID,
                    "capsule_version": _CAPSULE_VERSION,
                    "capsule_definition_checksum": _CAPSULE_CHECKSUM,
                    "desired_state": "ACTIVE",
                }
            ],
            "skill_pins": [],
            "artifact_requirements": [],
            "resource_bindings": [],
            "compatibility": {
                "workspace_schema": "reagent.project-workspace/v0.1",
                "minimum_cli_version": "0.1.0",
            },
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        }
        checksum = canonical_hash(payload)
        stored = {**payload, "canonical_checksum": checksum}
        entry_payload = {
            "schema_version": "reagent.project-manifest-entry/v0.1",
            "project_id": project_id,
            "manifest_revision": 1,
            "entry_kind": "WORKFLOW_INSTANCE",
            "workflow_instance_id": instance_id,
            "desired_action": "ENSURE_PRESENT",
            "workflow_definition_id": _DEFINITION_ID,
            "workflow_definition_version": _WORKFLOW_VERSION,
            "capsule_id": _CAPSULE_ID,
            "capsule_version": _CAPSULE_VERSION,
            "capsule_definition_checksum": _CAPSULE_CHECKSUM,
        }
        entry_id = "entry-" + uuid5(
            idempotency,
            f"workflow-instance-entry/v1|instance={instance_id}",
        ).hex
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(project_id,workspace_id,name,research_topic,status,"
                "current_manifest_revision,legacy_local_project_id,created_at,updated_at) "
                "VALUES (:project_id,:workspace_id,:name,:topic,'ACTIVE',1,"
                ":project_id,:created_at,:updated_at) ON CONFLICT (project_id) DO NOTHING"
            ),
            {
                "project_id": project_id,
                "workspace_id": workspace_id,
                "name": project["name"],
                "topic": project["research_topic"],
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_desired_manifests "
                "(project_id,manifest_revision,workspace_id,base_revision,schema_version,"
                "canonical_checksum,manifest_json,created_by_subject_id,idempotency_key,"
                "created_at,updated_at) VALUES (:project_id,1,:workspace_id,0,:schema,"
                ":checksum,CAST(:document AS jsonb),'reagent-system',:idempotency,"
                ":created_at,:created_at) ON CONFLICT (project_id,manifest_revision) DO NOTHING"
            ),
            {
                "project_id": project_id,
                "workspace_id": workspace_id,
                "schema": _SCHEMA,
                "checksum": checksum,
                "document": json.dumps(stored, sort_keys=True, separators=(",", ":")),
                "idempotency": str(idempotency),
                "created_at": created_at,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_manifest_entries "
                "(entry_id,project_id,manifest_revision,entry_kind,workflow_instance_id,"
                "desired_action,entry_checksum,created_at) VALUES "
                "(:entry_id,:project_id,1,'WORKFLOW_INSTANCE',:instance_id,"
                "'ENSURE_PRESENT',:entry_checksum,:created_at) "
                "ON CONFLICT (entry_id) DO NOTHING"
            ),
            {
                "entry_id": entry_id,
                "project_id": project_id,
                "instance_id": instance_id,
                "entry_checksum": canonical_hash(entry_payload),
                "created_at": created_at,
            },
        )
        persisted = connection.execute(
            sa.text(
                "SELECT p.workspace_id,p.current_manifest_revision,m.canonical_checksum,"
                "m.manifest_json,e.workflow_instance_id FROM projects p "
                "JOIN project_desired_manifests m ON m.project_id=p.project_id "
                "AND m.manifest_revision=p.current_manifest_revision "
                "JOIN project_manifest_entries e ON e.project_id=m.project_id "
                "AND e.manifest_revision=m.manifest_revision WHERE p.project_id=:project_id"
            ),
            {"project_id": project_id},
        ).mappings().one()
        if (
            persisted["workspace_id"] != workspace_id
            or persisted["current_manifest_revision"] != 1
            or persisted["canonical_checksum"] != checksum
            or persisted["manifest_json"] != stored
            or persisted["workflow_instance_id"] != instance_id
        ):
            raise RuntimeError("Desired Project Manifest backfill content conflict")


def _utc(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeError("legacy project timestamp is not timezone-aware")
    return value.astimezone(timezone.utc)
