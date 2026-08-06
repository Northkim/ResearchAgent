"""Add bounded local Workflow-session capabilities.

Revision ID: 20260806_0007
Revises: 20260805_0006
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0007"
down_revision: str | None = "20260805_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "proxy_capability_tokens",
        sa.Column(
            "local_session_capabilities_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_operations_valid"),
        "proxy_capability_tokens",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_operations_valid"),
        "proxy_capability_tokens",
        "maximum_operations BETWEEN 0 AND 50",
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM proxy_capability_tokens "
            "WHERE maximum_operations = 0"
        )
    ):
        raise RuntimeError(
            "cannot downgrade while upload-only local sessions are retained"
        )
    op.drop_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_operations_valid"),
        "proxy_capability_tokens",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_proxy_capability_tokens_proxy_token_maximum_operations_valid"),
        "proxy_capability_tokens",
        "maximum_operations BETWEEN 1 AND 50",
    )
    op.drop_column("proxy_capability_tokens", "local_session_capabilities_json")
