"""Add privacy-safe OpenAlex Proxy usage and exact microusd accounting.

Revision ID: 20260805_0005
Revises: 20260804_0004
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260805_0005"
down_revision: str | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "proxy_capability_tokens",
        sa.Column("maximum_provider_calls", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_capability_tokens",
        sa.Column("used_provider_calls", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_capability_tokens",
        sa.Column("maximum_provider_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_capability_tokens",
        sa.Column("reserved_provider_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_capability_tokens",
        sa.Column("reported_provider_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_provider_calls_valid"),
        "proxy_capability_tokens",
        "maximum_provider_calls BETWEEN 0 AND 20",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_used_provider_calls_valid"),
        "proxy_capability_tokens",
        "used_provider_calls BETWEEN 0 AND maximum_provider_calls",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_provider_cost_valid"),
        "proxy_capability_tokens",
        "maximum_provider_cost_microusd BETWEEN 0 AND 50000",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_reserved_provider_cost_valid"),
        "proxy_capability_tokens",
        "reserved_provider_cost_microusd BETWEEN 0 AND maximum_provider_cost_microusd",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_reported_provider_cost_nonnegative"),
        "proxy_capability_tokens",
        "reported_provider_cost_microusd >= 0",
    )

    op.add_column(
        "proxy_operations",
        sa.Column(
            "request_retention_mode",
            sa.String(length=50),
            nullable=False,
            server_default="FULL_PARAMETERS",
        ),
    )
    op.add_column("proxy_operations", sa.Column("query_checksum", sa.String(length=71)))
    op.add_column("proxy_operations", sa.Column("query_utf8_bytes", sa.Integer()))
    op.add_column("proxy_operations", sa.Column("query_characters", sa.Integer()))
    op.add_column(
        "proxy_operations",
        sa.Column("provider_http_calls", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_operations",
        sa.Column("reserved_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_operations",
        sa.Column("reported_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column("proxy_operations", sa.Column("provider_response_checksum", sa.String(length=71)))
    op.add_column("proxy_operations", sa.Column("provider_http_status", sa.Integer()))
    op.add_column(
        "proxy_operations",
        sa.Column("provider_adapter_version", sa.String(length=50), nullable=False, server_default="v0.1"),
    )
    op.add_column("proxy_operations", sa.Column("provider_rate_limit_json", postgresql.JSONB()))
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_request_retention_mode_valid"),
        "proxy_operations",
        "request_retention_mode IN ('FULL_PARAMETERS', 'CHECKSUM_ONLY')",
    )
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_provider_http_calls_valid"),
        "proxy_operations",
        "provider_http_calls BETWEEN 0 AND 1",
    )
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_reserved_cost_valid"),
        "proxy_operations",
        "reserved_cost_microusd BETWEEN 0 AND 50000",
    )
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_reported_cost_nonnegative"),
        "proxy_operations",
        "reported_cost_microusd >= 0",
    )
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_query_utf8_bytes_positive"),
        "proxy_operations",
        "query_utf8_bytes IS NULL OR query_utf8_bytes > 0",
    )
    op.create_check_constraint(
        op.f("ck_proxy_operations_proxy_operation_query_characters_positive"),
        "proxy_operations",
        "query_characters IS NULL OR query_characters > 0",
    )
    op.create_index(
        "ix_proxy_operations_adapter_status",
        "proxy_operations",
        ["adapter_id", "status"],
    )

    for table, columns in (
        (
            "proxy_capability_tokens",
            (
                "maximum_provider_calls",
                "used_provider_calls",
                "maximum_provider_cost_microusd",
                "reserved_provider_cost_microusd",
                "reported_provider_cost_microusd",
            ),
        ),
        (
            "proxy_operations",
            (
                "request_retention_mode",
                "provider_http_calls",
                "reserved_cost_microusd",
                "reported_cost_microusd",
                "provider_adapter_version",
            ),
        ),
    ):
        for column in columns:
            op.alter_column(table, column, server_default=None)


def downgrade() -> None:
    op.drop_index("ix_proxy_operations_adapter_status", table_name="proxy_operations")
    for name in (
        "proxy_operation_query_characters_positive",
        "proxy_operation_query_utf8_bytes_positive",
        "proxy_operation_reported_cost_nonnegative",
        "proxy_operation_reserved_cost_valid",
        "proxy_operation_provider_http_calls_valid",
        "proxy_operation_request_retention_mode_valid",
    ):
        op.drop_constraint(op.f(f"ck_proxy_operations_{name}"), "proxy_operations", type_="check")
    for column in (
        "provider_rate_limit_json",
        "provider_adapter_version",
        "provider_http_status",
        "provider_response_checksum",
        "reported_cost_microusd",
        "reserved_cost_microusd",
        "provider_http_calls",
        "query_characters",
        "query_utf8_bytes",
        "query_checksum",
        "request_retention_mode",
    ):
        op.drop_column("proxy_operations", column)

    for name in (
        "proxy_token_reported_provider_cost_nonnegative",
        "proxy_token_reserved_provider_cost_valid",
        "proxy_token_maximum_provider_cost_valid",
        "proxy_token_used_provider_calls_valid",
        "proxy_token_maximum_provider_calls_valid",
    ):
        op.drop_constraint(op.f(f"ck_proxy_capability_tokens_{name}"), "proxy_capability_tokens", type_="check")
    for column in (
        "reported_provider_cost_microusd",
        "reserved_provider_cost_microusd",
        "maximum_provider_cost_microusd",
        "used_provider_calls",
        "maximum_provider_calls",
    ):
        op.drop_column("proxy_capability_tokens", column)
