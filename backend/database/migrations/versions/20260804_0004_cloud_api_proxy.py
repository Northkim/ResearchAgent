"""Add independent fake cloud API Proxy tokens and operations.

Revision ID: 20260804_0004
Revises: 20260803_0003
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260804_0004"
down_revision: str | None = "20260803_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proxy_capability_tokens",
        sa.Column("token_id", sa.String(length=255), nullable=False),
        sa.Column("token_digest_sha256", sa.String(length=71), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("package_id", sa.String(length=255), nullable=False),
        sa.Column("package_checksum", sa.String(length=71), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("workflow_checksum", sa.String(length=71), nullable=False),
        sa.Column("allowed_capability", sa.String(length=100), nullable=False),
        sa.Column("allowed_adapter", sa.String(length=255), nullable=False),
        sa.Column("maximum_operations", sa.Integer(), nullable=False),
        sa.Column("admitted_operations", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "admitted_operations BETWEEN 0 AND maximum_operations",
            name=op.f("ck_proxy_capability_tokens_proxy_token_admitted_operations_valid"),
        ),
        sa.CheckConstraint(
            "expires_at > issued_at",
            name=op.f("ck_proxy_capability_tokens_proxy_token_expiry_after_issue"),
        ),
        sa.CheckConstraint(
            "maximum_operations BETWEEN 1 AND 50",
            name=op.f("ck_proxy_capability_tokens_proxy_token_maximum_operations_valid"),
        ),
        sa.PrimaryKeyConstraint("token_id", name=op.f("pk_proxy_capability_tokens")),
        sa.UniqueConstraint(
            "token_digest_sha256",
            name="uq_proxy_capability_tokens_digest",
        ),
    )
    op.create_index("ix_proxy_tokens_expiry_revocation", "proxy_capability_tokens", ["expires_at", "revoked"])
    op.create_index("ix_proxy_tokens_project_package", "proxy_capability_tokens", ["project_id", "package_id"])
    op.create_table(
        "proxy_operations",
        sa.Column("operation_id", sa.String(length=255), nullable=False),
        sa.Column("token_id", sa.String(length=255), nullable=False),
        sa.Column("proxy_contract_version", sa.String(length=100), nullable=False),
        sa.Column("authorization_scope_checksum", sa.String(length=71), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("package_id", sa.String(length=255), nullable=False),
        sa.Column("package_checksum", sa.String(length=71), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("workflow_checksum", sa.String(length=71), nullable=False),
        sa.Column("capability", sa.String(length=100), nullable=False),
        sa.Column("adapter_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=36), nullable=False),
        sa.Column("request_content_checksum", sa.String(length=71), nullable=False),
        sa.Column("request_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("provider_data_json", postgresql.JSONB(), nullable=True),
        sa.Column("provider_data_checksum", sa.String(length=71), nullable=True),
        sa.Column("provider_data_size", sa.BigInteger(), nullable=True),
        sa.Column("response_content_checksum", sa.String(length=71), nullable=True),
        sa.Column("estimated_cost_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("usage_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("reconciliation_evidence", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estimated_cost_minor_units = 0",
            name=op.f("ck_proxy_operations_proxy_operation_zero_cost"),
        ),
        sa.CheckConstraint(
            "provider_data_size IS NULL OR provider_data_size BETWEEN 0 AND 524288",
            name=op.f("ck_proxy_operations_proxy_operation_result_size_valid"),
        ),
        sa.CheckConstraint(
            "retry_count = 0",
            name=op.f("ck_proxy_operations_proxy_operation_zero_retry"),
        ),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'RECONCILIATION_REQUIRED')",
            name=op.f("ck_proxy_operations_proxy_operation_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["token_id"],
            ["proxy_capability_tokens.token_id"],
            name=op.f("fk_proxy_operations_token_id_proxy_capability_tokens"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("operation_id", name=op.f("pk_proxy_operations")),
        sa.UniqueConstraint(
            "token_id",
            "idempotency_key",
            name="uq_proxy_operations_scoped_idempotency",
        ),
    )
    op.create_index("ix_proxy_operations_project_package_created", "proxy_operations", ["project_id", "package_id", "created_at"])
    op.create_index("ix_proxy_operations_token_status", "proxy_operations", ["token_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_proxy_operations_token_status", table_name="proxy_operations")
    op.drop_index("ix_proxy_operations_project_package_created", table_name="proxy_operations")
    op.drop_table("proxy_operations")
    op.drop_index("ix_proxy_tokens_project_package", table_name="proxy_capability_tokens")
    op.drop_index("ix_proxy_tokens_expiry_revocation", table_name="proxy_capability_tokens")
    op.drop_table("proxy_capability_tokens")
