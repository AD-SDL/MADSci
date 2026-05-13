"""SQLModel tables for the Auth Manager.

All entities are scoped to a single ``lab_id`` (Decision 12). The schema is
single-tenant and intentionally has no ``tenant_id`` column.

Tables:

- ``users`` — local user accounts with Argon2id password hashes
- ``projects`` — project records
- ``project_memberships`` — many-to-many user ↔ project ↔ role
- ``roles`` — named bundles of permissions
- ``role_permissions`` — many-to-many role ↔ permission string
- ``service_accounts`` — manager principals
- ``node_identities`` — node principals (with reserved ``mtls_cert_fingerprint``)
- ``refresh_tokens`` — opaque refresh tokens, server-stored
- ``revoked_access_tokens`` — persistent deny-list (jti, exp, revoked_at)
- ``signing_keys`` — RSA keypairs for JWT signing
- ``audit_log`` — append-only security event log

The ``mtls_cert_fingerprint`` column on ``node_identities`` is forward-compat
with the future mTLS follow-on; it is not validated or used by this change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from madsci.common.utils import new_ulid_str
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlmodel import JSON, Field, SQLModel, text


def _utc_default() -> datetime:
    return datetime.now(timezone.utc)


class UserTable(SQLModel, table=True):
    """Local user account."""

    __tablename__ = "users"

    user_id: str = Field(
        default_factory=new_ulid_str,
        primary_key=True,
        description="ULID identifier for the user.",
    )
    username: str = Field(
        sa_column=Column(
            "username",
            nullable=False,
            unique=True,
            type_=__import__("sqlalchemy").String,
        ),
        description="Unique login name.",
    )
    email: Optional[str] = Field(default=None, description="Optional email.")
    password_hash: str = Field(
        nullable=False, description="Argon2id hash of the password."
    )
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    updated_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class ProjectTable(SQLModel, table=True):
    """Project record."""

    __tablename__ = "projects"

    project_id: str = Field(default_factory=new_ulid_str, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class RoleTable(SQLModel, table=True):
    """Role record (a named bundle of permissions)."""

    __tablename__ = "roles"

    role_id: str = Field(default_factory=new_ulid_str, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class RolePermissionTable(SQLModel, table=True):
    """Many-to-many between roles and permission strings.

    Permissions are stored as plain strings (``<resource>.<action>``) drawn
    from the canonical namespace documented in ``docs/guides/auth.md``.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission", name="uix_role_permission"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: str = Field(nullable=False, foreign_key="roles.role_id", index=True)
    permission: str = Field(nullable=False, index=True)


class ProjectMembershipTable(SQLModel, table=True):
    """A user's role grant within a project."""

    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", "role_id", name="uix_user_project_role"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(nullable=False, foreign_key="users.user_id", index=True)
    project_id: str = Field(
        nullable=False, foreign_key="projects.project_id", index=True
    )
    role_id: str = Field(nullable=False, foreign_key="roles.role_id", index=True)
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class GlobalRoleGrantTable(SQLModel, table=True):
    """Global (non-project-scoped) role grants for users / service accounts / nodes.

    A row applies to exactly one principal. The unused id columns are NULL.
    """

    __tablename__ = "global_role_grants"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: str = Field(nullable=False, foreign_key="roles.role_id", index=True)
    user_id: Optional[str] = Field(
        default=None, foreign_key="users.user_id", index=True
    )
    service_account_client_id: Optional[str] = Field(
        default=None,
        foreign_key="service_accounts.client_id",
        index=True,
    )
    node_identity_client_id: Optional[str] = Field(
        default=None,
        foreign_key="node_identities.client_id",
        index=True,
    )
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class ServiceAccountTable(SQLModel, table=True):
    """Service account principal (a manager service)."""

    __tablename__ = "service_accounts"

    client_id: str = Field(primary_key=True, description="OAuth client_id.")
    client_secret_hash: str = Field(
        nullable=False, description="Argon2id hash of the client_secret."
    )
    manager_id: str = Field(
        nullable=False, index=True, description="ULID of the represented manager."
    )
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class NodeIdentityTable(SQLModel, table=True):
    """Node principal."""

    __tablename__ = "node_identities"

    client_id: str = Field(primary_key=True, description="OAuth client_id.")
    client_secret_hash: str = Field(
        nullable=False, description="Argon2id hash of the client_secret."
    )
    node_id: str = Field(
        nullable=False, index=True, description="ULID of the represented node."
    )
    workcell_id: Optional[str] = Field(
        default=None, index=True, description="Optional workcell scope."
    )
    is_active: bool = Field(default=True, nullable=False)
    mtls_cert_fingerprint: Optional[str] = Field(
        default=None,
        description=(
            "Reserved for the future mTLS follow-on. SHA-256 fingerprint of"
            " the node's mTLS client certificate."
        ),
    )
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class RefreshTokenTable(SQLModel, table=True):
    """Opaque refresh token, server-stored."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("idx_refresh_principal", "principal_sub"),)

    token_id: str = Field(default_factory=new_ulid_str, primary_key=True)
    token_hash: str = Field(
        nullable=False, unique=True, description="SHA-256 hash of the opaque token."
    )
    principal_sub: str = Field(
        nullable=False, description="The sub claim this refresh token belongs to."
    )
    principal_type: str = Field(nullable=False)
    issued_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    expires_at: datetime = Field(nullable=False, sa_type=TIMESTAMP(timezone=True))
    revoked_at: Optional[datetime] = Field(
        default=None, sa_type=TIMESTAMP(timezone=True)
    )
    rotated_to: Optional[str] = Field(
        default=None,
        description="token_id of the refresh token this was rotated into, if any.",
    )


class RevokedAccessTokenTable(SQLModel, table=True):
    """Persistent deny-list of revoked access-token jtis."""

    __tablename__ = "revoked_access_tokens"
    __table_args__ = (Index("idx_revoked_exp", "exp"),)

    jti: str = Field(primary_key=True)
    exp: datetime = Field(nullable=False, sa_type=TIMESTAMP(timezone=True))
    revoked_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


class SigningKeyTable(SQLModel, table=True):
    """RSA signing keypair for JWT issuance."""

    __tablename__ = "signing_keys"

    kid: str = Field(primary_key=True, description="Key ID (ULID).")
    public_key_pem: str = Field(nullable=False)
    private_key_pem: str = Field(
        nullable=False,
        description=(
            "PEM-encoded private key. Operators are responsible for"
            " disk/database encryption-at-rest."
        ),
    )
    algorithm: str = Field(default="RS256", nullable=False)
    active: bool = Field(
        default=True,
        nullable=False,
        description="Whether the key is published in JWKS for verification.",
    )
    active_for_signing: bool = Field(
        default=False,
        nullable=False,
        description="Whether new tokens are signed with this key.",
    )
    created_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    retired_at: Optional[datetime] = Field(
        default=None, sa_type=TIMESTAMP(timezone=True)
    )


class AuditLogTable(SQLModel, table=True):
    """Append-only audit log."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_principal", "principal_id"),
        Index("idx_audit_event_time", "event_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(default_factory=new_ulid_str, unique=True, nullable=False)
    event_type: str = Field(nullable=False, index=True)
    event_time: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    principal_id: Optional[str] = Field(default=None, index=True)
    principal_type: Optional[str] = Field(default=None)
    grant_type: Optional[str] = Field(default=None)
    token_jti: Optional[str] = Field(default=None)
    source_ip: Optional[str] = Field(default=None)
    success: bool = Field(default=True, nullable=False)
    details: Optional[dict] = Field(default=None, sa_type=JSON)


class LabBindingTable(SQLModel, table=True):
    """Records the lab_id this Auth Manager database is bound to.

    Per Decision 12, an Auth Manager refuses to start later against a
    different lab_id without an explicit operator-acknowledged migration.
    """

    __tablename__ = "lab_binding"

    id: int = Field(primary_key=True, default=1)
    lab_id: str = Field(nullable=False)
    bootstrapped_at: datetime = Field(
        default_factory=_utc_default,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )


# Convenience handle for create_all / Alembic
metadata = SQLModel.metadata


__all__ = [
    "AuditLogTable",
    "GlobalRoleGrantTable",
    "LabBindingTable",
    "NodeIdentityTable",
    "ProjectMembershipTable",
    "ProjectTable",
    "RefreshTokenTable",
    "RevokedAccessTokenTable",
    "RolePermissionTable",
    "RoleTable",
    "ServiceAccountTable",
    "SigningKeyTable",
    "UserTable",
    "metadata",
]
