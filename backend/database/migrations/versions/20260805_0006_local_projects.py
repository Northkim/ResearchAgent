"""Add teacher-aligned local V0.1 project metadata.

Revision ID: 20260805_0006
Revises: 20260805_0005
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260805_0006"
down_revision: str | None = "20260805_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "local_projects",
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("research_topic", sa.String(length=500), nullable=False),
        sa.Column("selected_workflow", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_package_id", sa.String(length=255)),
        sa.Column("current_package_schema_version", sa.String(length=100)),
        sa.Column("current_package_checksum", sa.String(length=71)),
        sa.Column("current_manifest_checksum", sa.String(length=71)),
        sa.Column("current_zip_checksum", sa.String(length=71)),
        sa.Column("current_workflow_id", sa.String(length=255)),
        sa.Column("current_workflow_version", sa.String(length=100)),
        sa.Column("current_workflow_checksum", sa.String(length=71)),
        sa.Column("current_archive_storage_key", sa.Text()),
        sa.Column("current_package_file_count", sa.Integer()),
        sa.Column("current_package_size_bytes", sa.BigInteger()),
        sa.Column("current_package_generated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "selected_workflow = 'LITERATURE_SEARCH'",
            name=op.f("ck_local_projects_local_project_literature_search_only"),
        ),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 160",
            name=op.f("ck_local_projects_local_project_name_length"),
        ),
        sa.CheckConstraint(
            "char_length(research_topic) BETWEEN 1 AND 500",
            name=op.f("ck_local_projects_local_project_topic_length"),
        ),
        sa.PrimaryKeyConstraint("project_id", name=op.f("pk_local_projects")),
    )
    op.create_index(
        "ix_local_projects_updated",
        "local_projects",
        ["updated_at", "project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_local_projects_updated", table_name="local_projects")
    op.drop_table("local_projects")
