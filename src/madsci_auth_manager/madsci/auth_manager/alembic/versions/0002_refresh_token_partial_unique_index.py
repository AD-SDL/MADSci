"""Partial unique index on refresh_tokens(token_hash) WHERE revoked_at IS NULL.

Belt-and-suspenders for the atomic ``UPDATE ... WHERE revoked_at IS NULL
RETURNING ...`` pattern in ``TokenService.consume_refresh_token`` — guarantees
at the DB level that at most one unrevoked refresh-token row may share a
hash, even under concurrent inserts.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-05

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the partial unique index. PostgreSQL supports ``WHERE`` clauses on indexes."""
    op.create_index(
        "uix_refresh_tokens_active_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        postgresql_where="revoked_at IS NULL",
    )


def downgrade() -> None:
    """Drop the partial unique index."""
    op.drop_index("uix_refresh_tokens_active_hash", table_name="refresh_tokens")
