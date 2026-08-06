"""Add the Project Workspace workflow persistence foundation.

Revision ID: 20260806_0008
Revises: 20260806_0007
Create Date: 2026-08-06
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0008"
down_revision: str | None = "20260806_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFINITION_ID = "literature-search-local-experimental"
_WORKFLOW_VERSION = "0.3.0"
_CAPSULE_ID = "capsule-0f827b56ed6c5ecf6634f5eee0171ead"
_CAPSULE_VERSION = "0.5.0"
_WORKFLOW_CHECKSUM = "sha256:efd338d84b33665da25118c7dce6927f62b231ff3bc73527f4132c7bcb410e7f"
_CAPSULE_CHECKSUM = "sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611"
_LEGACY_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


def upgrade() -> None:
    op.create_table(
        "local_workflow_definitions",
        sa.Column("workflow_definition_id", sa.String(128), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("lifecycle", sa.String(20), nullable=False),
        sa.Column("allows_multiple_instances", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "lifecycle IN ('AVAILABLE','PLANNED','RETIRED')",
            name=op.f("ck_local_workflow_definitions_lifecycle"),
        ),
    )
    op.create_index(
        "ix_local_workflow_definitions_lifecycle",
        "local_workflow_definitions",
        ["lifecycle"],
    )
    op.create_table(
        "local_workflow_definition_versions",
        sa.Column("workflow_definition_id", sa.String(128), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("contract_checksum", sa.String(71), nullable=False),
        sa.Column("input_schema_id", sa.String(200), nullable=False),
        sa.Column("output_schema_id", sa.String(200), nullable=False),
        sa.Column("compatibility", postgresql.JSONB(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id"],
            ["local_workflow_definitions.workflow_definition_id"],
            name=op.f("fk_local_workflow_definition_versions_workflow_definition_id_local_workflow_definitions"),
        ),
        sa.PrimaryKeyConstraint(
            "workflow_definition_id", "version", name=op.f("pk_local_workflow_definition_versions")
        ),
        sa.UniqueConstraint(
            "contract_checksum", name=op.f("uq_local_workflow_definition_versions_contract_checksum")
        ),
        sa.CheckConstraint(
            "review_status IN ('DRAFT','REVIEWED','RETIRED')",
            name=op.f("ck_local_workflow_definition_versions_review_status"),
        ),
    )
    op.create_index(
        "ix_local_workflow_definition_versions_definition_review",
        "local_workflow_definition_versions",
        ["workflow_definition_id", "review_status"],
    )
    op.create_table(
        "local_workflow_capsule_versions",
        sa.Column("capsule_id", sa.String(40), nullable=False),
        sa.Column("capsule_version", sa.String(100), nullable=False),
        sa.Column("workflow_definition_id", sa.String(128), nullable=False),
        sa.Column("workflow_version", sa.String(100), nullable=False),
        sa.Column("definition_checksum", sa.String(71), nullable=False),
        sa.Column("archive_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("archive_media_type", sa.String(100), nullable=False),
        sa.Column("mutable_roots", postgresql.JSONB(), nullable=False),
        sa.Column("capability_requirements", postgresql.JSONB(), nullable=False),
        sa.Column("compatibility", postgresql.JSONB(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("legacy_package_compatible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            [
                "local_workflow_definition_versions.workflow_definition_id",
                "local_workflow_definition_versions.version",
            ],
            name="fk_local_workflow_capsule_versions_definition_version",
        ),
        sa.PrimaryKeyConstraint("capsule_id", "capsule_version", name=op.f("pk_local_workflow_capsule_versions")),
        sa.UniqueConstraint("definition_checksum", name=op.f("uq_local_workflow_capsule_versions_definition_checksum")),
        sa.CheckConstraint(
            "archive_size_bytes BETWEEN 0 AND 536870912",
            name=op.f("ck_local_workflow_capsule_versions_local_workflow_capsule_archive_size"),
        ),
        sa.CheckConstraint(
            "review_status IN ('DRAFT','REVIEWED','RETIRED')",
            name=op.f("ck_local_workflow_capsule_versions_review_status"),
        ),
    )
    op.create_index(
        "ix_local_workflow_capsule_versions_workflow_version",
        "local_workflow_capsule_versions",
        ["workflow_definition_id", "workflow_version"],
    )
    op.create_index(
        "ix_local_workflow_capsule_versions_review_status",
        "local_workflow_capsule_versions",
        ["review_status"],
    )
    op.create_table(
        "project_workflow_instances",
        sa.Column("workflow_instance_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("workflow_definition_id", sa.String(128), nullable=False),
        sa.Column("workflow_version", sa.String(100), nullable=False),
        sa.Column("capsule_id", sa.String(40)),
        sa.Column("capsule_version", sa.String(100)),
        sa.Column("desired_state", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("created_manifest_revision", sa.BigInteger(), nullable=False),
        sa.Column("retired_manifest_revision", sa.BigInteger()),
        sa.Column("legacy_package_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["local_projects.project_id"], name=op.f("fk_project_workflow_instances_project_id_local_projects")),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            ["local_workflow_definition_versions.workflow_definition_id", "local_workflow_definition_versions.version"],
            name="fk_project_workflow_instances_definition_version",
        ),
        sa.ForeignKeyConstraint(
            ["capsule_id", "capsule_version"],
            ["local_workflow_capsule_versions.capsule_id", "local_workflow_capsule_versions.capsule_version"],
            name="fk_project_workflow_instances_capsule_version",
        ),
        sa.PrimaryKeyConstraint("workflow_instance_id", name=op.f("pk_project_workflow_instances")),
        sa.UniqueConstraint("project_id", "workflow_instance_id", name="uq_project_workflow_instances_project_identity"),
        sa.CheckConstraint("desired_state IN ('ACTIVE','RETIRED')", name=op.f("ck_project_workflow_instances_desired_state")),
        sa.CheckConstraint("created_manifest_revision >= 0", name=op.f("ck_project_workflow_instances_project_workflow_instance_created_revision")),
        sa.CheckConstraint("retired_manifest_revision IS NULL OR retired_manifest_revision >= 0", name=op.f("ck_project_workflow_instances_project_workflow_instance_retired_revision")),
        sa.CheckConstraint("(capsule_id IS NULL AND capsule_version IS NULL) OR (capsule_id IS NOT NULL AND capsule_version IS NOT NULL)", name=op.f("ck_project_workflow_instances_project_workflow_instance_capsule_pair")),
        sa.CheckConstraint("(desired_state = 'ACTIVE' AND retired_manifest_revision IS NULL) OR (desired_state = 'RETIRED' AND retired_manifest_revision IS NOT NULL)", name=op.f("ck_project_workflow_instances_project_workflow_instance_retirement_state")),
    )
    op.create_index("ix_project_workflow_instances_project_state", "project_workflow_instances", ["project_id", "desired_state"])
    op.create_index("ix_project_workflow_instances_project_definition", "project_workflow_instances", ["project_id", "workflow_definition_id"])
    _seed_and_backfill(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_project_workflow_instances_project_definition", table_name="project_workflow_instances")
    op.drop_index("ix_project_workflow_instances_project_state", table_name="project_workflow_instances")
    op.drop_table("project_workflow_instances")
    op.drop_index("ix_local_workflow_capsule_versions_review_status", table_name="local_workflow_capsule_versions")
    op.drop_index("ix_local_workflow_capsule_versions_workflow_version", table_name="local_workflow_capsule_versions")
    op.drop_table("local_workflow_capsule_versions")
    op.drop_index("ix_local_workflow_definition_versions_definition_review", table_name="local_workflow_definition_versions")
    op.drop_table("local_workflow_definition_versions")
    op.drop_index("ix_local_workflow_definitions_lifecycle", table_name="local_workflow_definitions")
    op.drop_table("local_workflow_definitions")


def _seed_and_backfill(connection: sa.Connection) -> None:
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definitions
              (workflow_definition_id, display_name, description, lifecycle,
               allows_multiple_instances, created_at, updated_at)
            VALUES (:id, 'Literature Search', '', 'AVAILABLE', true, :now, :now)
            ON CONFLICT (workflow_definition_id) DO NOTHING
        """),
        {"id": _DEFINITION_ID, "now": now},
    )
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status, published_at,
               created_at, updated_at)
            VALUES (:id, :version, :checksum, 'research-request/v0.2',
                    'literature-search-report/v0.2', CAST(:compatibility AS jsonb),
                    'REVIEWED', :now, :now, :now)
            ON CONFLICT (workflow_definition_id, version) DO NOTHING
        """),
        {
            "id": _DEFINITION_ID,
            "version": _WORKFLOW_VERSION,
            "checksum": _WORKFLOW_CHECKSUM,
            "compatibility": '{"package_schema_version":"workflow-package/v0.1"}',
            "now": now,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id, workflow_version,
               definition_checksum, archive_size_bytes, archive_media_type,
               mutable_roots, capability_requirements, compatibility, review_status,
               legacy_package_compatible, created_at, updated_at)
            VALUES (:capsule_id, :capsule_version, :definition_id, :workflow_version,
                    :checksum, 0, 'application/zip', CAST(:mutable_roots AS jsonb),
                    CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                    'REVIEWED', true, :now, :now)
            ON CONFLICT (capsule_id, capsule_version) DO NOTHING
        """),
        {
            "capsule_id": _CAPSULE_ID,
            "capsule_version": _CAPSULE_VERSION,
            "definition_id": _DEFINITION_ID,
            "workflow_version": _WORKFLOW_VERSION,
            "checksum": _CAPSULE_CHECKSUM,
            "mutable_roots": '["memory/context.md","memory/progress","memory/round-control.json","memory/search","outputs"]',
            "capabilities": '["paper.search/v0.1","progress.read/v0.1","progress.upload/v0.2"]',
            "compatibility": '{"package_schema_version":"workflow-package/v0.1","package_template_id":"literature-search-package-experimental","trust_classification":"TRUSTED_BUILT_IN_UNSIGNED"}',
            "now": now,
        },
    )
    _assert_seed_content(connection)
    projects = connection.execute(
        sa.text("SELECT project_id, selected_workflow, current_package_id, created_at, updated_at FROM local_projects ORDER BY project_id")
    ).mappings()
    for project in projects:
        if project["selected_workflow"] != "LITERATURE_SEARCH":
            raise RuntimeError("unsupported legacy selected_workflow during workspace backfill")
        identity_name = f"legacy-workflow-instance/v1|project={project['project_id']}|workflow=LITERATURE_SEARCH"
        instance_id = "wfi-" + uuid5(_LEGACY_NAMESPACE, identity_name).hex
        has_package = project["current_package_id"] is not None
        connection.execute(
            sa.text("""
                INSERT INTO project_workflow_instances
                  (workflow_instance_id, project_id, workflow_definition_id,
                   workflow_version, capsule_id, capsule_version, desired_state,
                   display_name, created_manifest_revision, retired_manifest_revision,
                   legacy_package_id, created_at, updated_at)
                VALUES (:instance_id, :project_id, :definition_id, :workflow_version,
                        :capsule_id, :capsule_version, 'ACTIVE', 'Literature Search',
                        0, NULL, :package_id, :created_at, :updated_at)
                ON CONFLICT (workflow_instance_id) DO NOTHING
            """),
            {
                "instance_id": instance_id,
                "project_id": project["project_id"],
                "definition_id": _DEFINITION_ID,
                "workflow_version": _WORKFLOW_VERSION,
                "capsule_id": _CAPSULE_ID if has_package else None,
                "capsule_version": _CAPSULE_VERSION if has_package else None,
                "package_id": project["current_package_id"],
                "created_at": project["created_at"],
                "updated_at": project["updated_at"],
            },
        )
        persisted = connection.execute(
            sa.text("""
                SELECT project_id, workflow_definition_id, workflow_version,
                       capsule_id, capsule_version, legacy_package_id
                FROM project_workflow_instances
                WHERE workflow_instance_id = :instance_id
            """),
            {"instance_id": instance_id},
        ).mappings().one()
        expected = {
            "project_id": project["project_id"],
            "workflow_definition_id": _DEFINITION_ID,
            "workflow_version": _WORKFLOW_VERSION,
            "capsule_id": _CAPSULE_ID if has_package else None,
            "capsule_version": _CAPSULE_VERSION if has_package else None,
            "legacy_package_id": project["current_package_id"],
        }
        if any(persisted[key] != value for key, value in expected.items()):
            raise RuntimeError("legacy Workflow Instance identity conflicts with immutable content")


def _assert_seed_content(connection: sa.Connection) -> None:
    definition = connection.execute(
        sa.text("""
            SELECT display_name, description, lifecycle, allows_multiple_instances
            FROM local_workflow_definitions
            WHERE workflow_definition_id = :id
        """),
        {"id": _DEFINITION_ID},
    ).mappings().one()
    if dict(definition) != {
        "display_name": "Literature Search",
        "description": "",
        "lifecycle": "AVAILABLE",
        "allows_multiple_instances": True,
    }:
        raise RuntimeError("Literature Search Workflow Definition seed conflict")
    version = connection.execute(
        sa.text("""
            SELECT contract_checksum, input_schema_id, output_schema_id,
                   compatibility, review_status
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id AND version = :version
        """),
        {"id": _DEFINITION_ID, "version": _WORKFLOW_VERSION},
    ).mappings().one()
    if (
        version["contract_checksum"] != _WORKFLOW_CHECKSUM
        or version["input_schema_id"] != "research-request/v0.2"
        or version["output_schema_id"] != "literature-search-report/v0.2"
        or version["compatibility"] != {"package_schema_version": "workflow-package/v0.1"}
        or version["review_status"] != "REVIEWED"
    ):
        raise RuntimeError("Literature Search Workflow Version seed conflict")
    capsule = connection.execute(
        sa.text("""
            SELECT workflow_definition_id, workflow_version, definition_checksum,
                   archive_size_bytes, archive_media_type, mutable_roots,
                   capability_requirements, compatibility, review_status,
                   legacy_package_compatible
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :capsule_id AND capsule_version = :capsule_version
        """),
        {"capsule_id": _CAPSULE_ID, "capsule_version": _CAPSULE_VERSION},
    ).mappings().one()
    expected_capsule = {
        "workflow_definition_id": _DEFINITION_ID,
        "workflow_version": _WORKFLOW_VERSION,
        "definition_checksum": _CAPSULE_CHECKSUM,
        "archive_size_bytes": 0,
        "archive_media_type": "application/zip",
        "mutable_roots": [
            "memory/context.md",
            "memory/progress",
            "memory/round-control.json",
            "memory/search",
            "outputs",
        ],
        "capability_requirements": [
            "paper.search/v0.1",
            "progress.read/v0.1",
            "progress.upload/v0.2",
        ],
        "compatibility": {
            "package_schema_version": "workflow-package/v0.1",
            "package_template_id": "literature-search-package-experimental",
            "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        },
        "review_status": "REVIEWED",
        "legacy_package_compatible": True,
    }
    if any(capsule[key] != value for key, value in expected_capsule.items()):
        raise RuntimeError("Literature Search Capsule Version seed conflict")
