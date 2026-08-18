"""Add lightweight Owner-managed Skills and Project associations.

Revision ID: 20260818_0033
Revises: 20260818_0032
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260818_0033"
down_revision: str | None = "20260818_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_managed_skills",
        sa.Column("skill_id", sa.String(38), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("source_locator", sa.String(500), nullable=False),
        sa.Column("source_revision", sa.String(40), nullable=False),
        sa.Column("source_checksum", sa.String(71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_user_managed_skills_slug"),
        sa.CheckConstraint(
            "source_locator ~ '^https://github\\.com/'",
            name="user_managed_skill_github_source",
        ),
        sa.CheckConstraint(
            "source_revision ~ '^[0-9a-f]{40}$'",
            name="user_managed_skill_exact_revision",
        ),
        sa.CheckConstraint(
            "source_checksum ~ '^sha256:[0-9a-f]{64}$'",
            name="user_managed_skill_source_checksum",
        ),
    )
    op.create_index(
        "ix_user_managed_skills_name", "user_managed_skills", ["name", "skill_id"]
    )
    op.create_table(
        "project_user_skills",
        sa.Column(
            "project_id", sa.String(255),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "skill_id", sa.String(38),
            sa.ForeignKey("user_managed_skills.skill_id", ondelete="RESTRICT"), primary_key=True,
        ),
        sa.Column("reported_source_checksum", sa.String(71)),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "reported_source_checksum IS NULL OR "
            "reported_source_checksum ~ '^sha256:[0-9a-f]{64}$'",
            name="project_user_skill_reported_checksum",
        ),
        sa.CheckConstraint(
            "(reported_source_checksum IS NULL AND reported_at IS NULL) OR "
            "(reported_source_checksum IS NOT NULL AND reported_at IS NOT NULL)",
            name="project_user_skill_report_all_or_none",
        ),
    )
    op.create_index(
        "ix_project_user_skills_skill", "project_user_skills", ["skill_id", "project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_project_user_skills_skill", table_name="project_user_skills")
    op.drop_table("project_user_skills")
    op.drop_index("ix_user_managed_skills_name", table_name="user_managed_skills")
    op.drop_table("user_managed_skills")
