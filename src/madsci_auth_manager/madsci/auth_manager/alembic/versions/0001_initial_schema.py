"""Initial schema for the Auth Manager.

Revision ID: 0001
Revises:
Create Date: 2026-05-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all Auth Manager tables."""
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "roles",
        sa.Column("role_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("roles.role_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("permission", sa.String(), nullable=False, index=True),
        sa.UniqueConstraint("role_id", "permission", name="uix_role_permission"),
    )

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.user_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.project_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("roles.role_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "user_id", "project_id", "role_id", name="uix_user_project_role"
        ),
    )

    op.create_table(
        "service_accounts",
        sa.Column("client_id", sa.String(), primary_key=True),
        sa.Column("client_secret_hash", sa.String(), nullable=False),
        sa.Column("manager_id", sa.String(), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "node_identities",
        sa.Column("client_id", sa.String(), primary_key=True),
        sa.Column("client_secret_hash", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False, index=True),
        sa.Column("workcell_id", sa.String(), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mtls_cert_fingerprint", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "global_role_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "role_id",
            sa.String(),
            sa.ForeignKey("roles.role_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.user_id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "service_account_client_id",
            sa.String(),
            sa.ForeignKey("service_accounts.client_id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "node_identity_client_id",
            sa.String(),
            sa.ForeignKey("node_identities.client_id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("token_id", sa.String(), primary_key=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("principal_sub", sa.String(), nullable=False),
        sa.Column("principal_type", sa.String(), nullable=False),
        sa.Column(
            "issued_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rotated_to", sa.String(), nullable=True),
    )
    op.create_index("idx_refresh_principal", "refresh_tokens", ["principal_sub"])

    op.create_table(
        "revoked_access_tokens",
        sa.Column("jti", sa.String(), primary_key=True),
        sa.Column("exp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_revoked_exp", "revoked_access_tokens", ["exp"])

    op.create_table(
        "signing_keys",
        sa.Column("kid", sa.String(), primary_key=True),
        sa.Column("public_key_pem", sa.String(), nullable=False),
        sa.Column("private_key_pem", sa.String(), nullable=False),
        sa.Column("algorithm", sa.String(), nullable=False, server_default="RS256"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "active_for_signing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("retired_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(), nullable=False, unique=True),
        sa.Column("event_type", sa.String(), nullable=False, index=True),
        sa.Column(
            "event_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("principal_id", sa.String(), nullable=True, index=True),
        sa.Column("principal_type", sa.String(), nullable=True),
        sa.Column("grant_type", sa.String(), nullable=True),
        sa.Column("token_jti", sa.String(), nullable=True),
        sa.Column("source_ip", sa.String(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    op.create_index("idx_audit_principal", "audit_log", ["principal_id"])
    op.create_index("idx_audit_event_time", "audit_log", ["event_time"])

    op.create_table(
        "lab_binding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.String(), nullable=False),
        sa.Column(
            "bootstrapped_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    """Drop all Auth Manager tables."""
    op.drop_table("lab_binding")
    op.drop_index("idx_audit_event_time", table_name="audit_log")
    op.drop_index("idx_audit_principal", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("signing_keys")
    op.drop_index("idx_revoked_exp", table_name="revoked_access_tokens")
    op.drop_table("revoked_access_tokens")
    op.drop_index("idx_refresh_principal", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("global_role_grants")
    op.drop_table("node_identities")
    op.drop_table("service_accounts")
    op.drop_table("project_memberships")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("projects")
    op.drop_table("users")
