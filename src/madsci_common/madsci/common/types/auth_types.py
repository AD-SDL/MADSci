"""Types related to authentication, authorization, and ownership of MADSci objects."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from madsci.common.types.base_types import (
    MadsciBaseModel,
    prefixed_alias_generator,
    prefixed_model_validator,
)
from madsci.common.types.manager_types import (
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from madsci.common.validators import optional_ulid_validator, ulid_validator
from pydantic import (
    AliasChoices,
    AnyUrl,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)
from pydantic.functional_validators import field_validator
from pydantic_settings import SettingsConfigDict


class PrincipalType(str, Enum):
    """Type of principal a token represents."""

    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    NODE = "node"


class GrantType(str, Enum):
    """OAuth 2.0 grant types supported by the Auth Manager."""

    PASSWORD = "password"  # noqa: S105
    REFRESH_TOKEN = "refresh_token"  # noqa: S105
    CLIENT_CREDENTIALS = "client_credentials"


class OwnershipInfo(MadsciBaseModel):
    """Information about the ownership of a MADSci object."""

    user_id: Optional[str] = Field(
        title="User ID",
        description="The ID of the user who owns the object.",
        default=None,
    )
    experiment_id: Optional[str] = Field(
        title="Experiment ID",
        description="The ID of the experiment that owns the object.",
        default=None,
    )
    campaign_id: Optional[str] = Field(
        title="Campaign ID",
        description="The ID of the campaign that owns the object.",
        default=None,
    )
    project_id: Optional[str] = Field(
        title="Project ID",
        description="The ID of the project that owns the object.",
        default=None,
    )
    node_id: Optional[str] = Field(
        title="Node ID",
        description="The ID of the node that owns the object.",
        default=None,
    )
    workcell_id: Optional[str] = Field(
        title="Workcell ID",
        description="The ID of the workcell that owns the object.",
        default=None,
    )
    lab_id: Optional[str] = Field(
        title="Lab ID",
        description="The ID of the lab that owns the object.",
        default=None,
    )
    step_id: Optional[str] = Field(
        title="Step ID",
        description="The ID of the step that owns the object.",
        default=None,
    )
    workflow_id: Optional[str] = Field(
        title="Workflow ID",
        description="The ID of the workflow that owns the object.",
        default=None,
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description="The ID of the manager that owns the object.",
        default=None,
    )

    is_ulid = field_validator(
        "user_id",
        "experiment_id",
        "campaign_id",
        "project_id",
        "node_id",
        "workcell_id",
        "step_id",
        "lab_id",
        "workflow_id",
        "manager_id",
        mode="after",
    )(optional_ulid_validator)

    @model_serializer(mode="wrap")
    def exclude_unset_by_default(
        self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Exclude unset fields by default."""
        serialized = nxt(self, info)
        return {k: v for k, v in serialized.items() if v is not None}

    def check(self, other: "OwnershipInfo") -> bool:
        """Check if this ownership is the same as another."""
        for key in self.model_dump(exclude_none=True):
            if getattr(self, key) != getattr(other, key):
                return False
        return True

    @classmethod
    def from_jwt_claims(cls, claims: "JWTClaims") -> "OwnershipInfo":
        """Build an OwnershipInfo from validated JWT claims.

        - ``lab_id``      ← ``claims.aud``
        - ``user_id``     ← ``claims.user_id`` (when ``principal_type=user``)
        - ``node_id``     ← ``claims.node_id`` (when ``principal_type=node``)
        - ``workcell_id`` ← ``claims.workcell_id``
        - ``manager_id``  ← ``claims.manager_id`` (when ``principal_type=service_account``)

        ``project_id`` is intentionally left unset; project context is
        established per-operation via ``@requires(project_from=...)``.
        """
        return cls(
            lab_id=claims.aud,
            user_id=claims.user_id
            if claims.principal_type == PrincipalType.USER
            else None,
            node_id=claims.node_id
            if claims.principal_type == PrincipalType.NODE
            else None,
            workcell_id=claims.workcell_id,
            manager_id=(
                claims.manager_id
                if claims.principal_type == PrincipalType.SERVICE_ACCOUNT
                else None
            ),
        )


class UserInfo(MadsciBaseModel):
    """Information about a user."""

    user_id: str = Field(title="User ID", description="The ID of the user.")
    user_name: str = Field(title="User Name", description="The name of the user.")
    user_email: str = Field(title="User Email", description="The email of the user.")

    is_ulid = field_validator("user_id", mode="after")(ulid_validator)


class ProjectInfo(MadsciBaseModel):
    """Information about a project."""

    project_id: str = Field(title="Project ID", description="The ID of the project.")
    project_name: str = Field(
        title="Project Name",
        description="The name of the project.",
    )
    project_description: str = Field(
        title="Project Description",
        description="The description of the project.",
    )
    project_owner: UserInfo = Field(
        title="Project Owner",
        description="The owner of the project.",
    )
    project_members: list[UserInfo] = Field(
        title="Project Members",
        description="The members of the project.",
    )

    is_ulid = field_validator("project_id", mode="after")(ulid_validator)


# ---------------------------------------------------------------------------
# RBAC primitives
# ---------------------------------------------------------------------------


class Permission(MadsciBaseModel):
    """A permission string in the canonical ``<resource>.<action>`` namespace."""

    name: str = Field(
        title="Permission Name",
        description="The canonical permission string (e.g., 'experiment.write').",
    )
    description: Optional[str] = Field(
        title="Description",
        description="Human-readable description of what this permission grants.",
        default=None,
    )


class Role(MadsciBaseModel):
    """A named bundle of permissions that can be granted to principals."""

    role_id: str = Field(
        title="Role ID",
        description="ULID for this role.",
        default_factory=new_ulid_str,
    )
    name: str = Field(
        title="Role Name",
        description="Unique role name (e.g., 'admin', 'experimenter').",
    )
    description: Optional[str] = Field(
        title="Description",
        description="Human-readable description of the role.",
        default=None,
    )
    permissions: list[str] = Field(
        title="Permissions",
        description="List of permission strings granted by this role.",
        default_factory=list,
    )

    is_ulid = field_validator("role_id", mode="after")(ulid_validator)


class ProjectMembership(MadsciBaseModel):
    """A user's membership in a project, with one or more roles scoped to it."""

    user_id: str = Field(
        title="User ID",
        description="The user who is a member.",
    )
    project_id: str = Field(
        title="Project ID",
        description="The project the user is a member of.",
    )
    role_ids: list[str] = Field(
        title="Role IDs",
        description="Roles granted to this user within this project.",
        default_factory=list,
    )

    is_ulid_user = field_validator("user_id", mode="after")(ulid_validator)
    is_ulid_project = field_validator("project_id", mode="after")(ulid_validator)


class ServiceAccount(MadsciBaseModel):
    """A non-human principal representing a manager service.

    ``client_secret`` is never stored or returned in plaintext after the
    initial registration; only the Argon2 hash is persisted.
    """

    client_id: str = Field(
        title="Client ID",
        description="OAuth 2.0 client identifier for this service account.",
    )
    manager_id: str = Field(
        title="Manager ID",
        description="The ULID of the manager this service account represents.",
    )
    is_active: bool = Field(
        title="Is Active",
        description="Whether this service account can authenticate.",
        default=True,
    )
    role_ids: list[str] = Field(
        title="Role IDs",
        description="Roles granted to this service account (typically global).",
        default_factory=list,
    )
    created_at: Optional[datetime] = Field(
        title="Created At",
        description="When this service account was created.",
        default=None,
    )

    is_ulid_manager = field_validator("manager_id", mode="after")(ulid_validator)


class NodeIdentity(MadsciBaseModel):
    """A principal representing a laboratory node.

    ``client_secret`` is never stored or returned in plaintext after the
    initial registration; only the Argon2 hash is persisted.

    The ``mtls_cert_fingerprint`` field is reserved for the future mTLS
    follow-on change.
    """

    client_id: str = Field(
        title="Client ID",
        description="OAuth 2.0 client identifier for this node identity.",
    )
    node_id: str = Field(
        title="Node ID",
        description="The ULID of the node this identity represents.",
    )
    workcell_id: Optional[str] = Field(
        title="Workcell ID",
        description="Optional workcell scope for this node.",
        default=None,
    )
    is_active: bool = Field(
        title="Is Active",
        description="Whether this node identity can authenticate.",
        default=True,
    )
    role_ids: list[str] = Field(
        title="Role IDs",
        description="Roles granted to this node identity.",
        default_factory=list,
    )
    mtls_cert_fingerprint: Optional[str] = Field(
        title="mTLS Certificate Fingerprint",
        description=(
            "Reserved for the future mTLS follow-on change. SHA-256"
            " fingerprint of the node's mTLS client certificate."
        ),
        default=None,
    )
    created_at: Optional[datetime] = Field(
        title="Created At",
        description="When this node identity was created.",
        default=None,
    )

    is_ulid_node = field_validator("node_id", mode="after")(ulid_validator)
    is_ulid_workcell = field_validator("workcell_id", mode="after")(
        optional_ulid_validator
    )


# ---------------------------------------------------------------------------
# JWT / token model
# ---------------------------------------------------------------------------


class JWTClaims(MadsciBaseModel):
    """The decoded claims of a MADSci access token."""

    iss: str = Field(
        title="Issuer",
        description="The Auth Manager URL that issued the token.",
    )
    aud: str = Field(
        title="Audience",
        description="The deployment's lab_id (single string, not an array).",
    )
    sub: str = Field(
        title="Subject",
        description=(
            "The canonical principal identifier — user_id for users, client_id"
            " for service accounts and nodes."
        ),
    )
    iat: int = Field(
        title="Issued At",
        description="Token issuance time (Unix epoch seconds).",
    )
    exp: int = Field(
        title="Expiration",
        description="Token expiration time (Unix epoch seconds).",
    )
    jti: str = Field(
        title="JWT ID",
        description="Unique identifier for this token (ULID).",
    )
    principal_type: PrincipalType = Field(
        title="Principal Type",
        description="user, service_account, or node.",
    )
    roles: list[str] = Field(
        title="Roles",
        description="List of role IDs granted to this principal.",
        default_factory=list,
    )
    permissions: list[str] = Field(
        title="Permissions",
        description="Flattened list of permission strings.",
        default_factory=list,
    )
    user_id: Optional[str] = Field(
        title="User ID",
        description="Set for user tokens.",
        default=None,
    )
    project_ids: list[str] = Field(
        title="Project IDs",
        description="Project memberships at issuance time (user tokens).",
        default_factory=list,
    )
    manager_id: Optional[str] = Field(
        title="Manager ID",
        description=(
            "Operational manager identity for service accounts (distinct from"
            " ``sub``/``client_id``)."
        ),
        default=None,
    )
    node_id: Optional[str] = Field(
        title="Node ID",
        description="Set for node tokens.",
        default=None,
    )
    workcell_id: Optional[str] = Field(
        title="Workcell ID",
        description="Set for node tokens scoped to a workcell.",
        default=None,
    )


class TokenResponse(MadsciBaseModel):
    """The OAuth 2.0 token-endpoint response."""

    access_token: str = Field(
        title="Access Token",
        description="The signed JWT access token.",
    )
    token_type: str = Field(
        title="Token Type",
        description="Always 'Bearer'.",
        default="Bearer",
    )
    expires_in: int = Field(
        title="Expires In",
        description="Lifetime of the access token in seconds.",
    )
    refresh_token: Optional[str] = Field(
        title="Refresh Token",
        description="Opaque refresh token. Absent for client_credentials grants.",
        default=None,
    )
    scope: Optional[str] = Field(
        title="Scope",
        description="Granted scope (currently unused; reserved for future).",
        default=None,
    )


class Principal(MadsciBaseModel):
    """The validated principal of an authenticated request."""

    sub: str = Field(
        title="Subject",
        description="The token's sub claim.",
    )
    principal_type: PrincipalType = Field(
        title="Principal Type",
        description="user, service_account, or node.",
    )
    permissions: list[str] = Field(
        title="Permissions",
        description="Flattened list of permission strings from the token.",
        default_factory=list,
    )
    roles: list[str] = Field(
        title="Roles",
        description="Role IDs granted to this principal.",
        default_factory=list,
    )
    project_ids: list[str] = Field(
        title="Project IDs",
        description="Project memberships at token-issuance time.",
        default_factory=list,
    )
    claims: JWTClaims = Field(
        title="JWT Claims",
        description="The full decoded claims for downstream inspection.",
    )

    @classmethod
    def from_claims(cls, claims: JWTClaims) -> "Principal":
        """Build a Principal from validated JWT claims."""
        return cls(
            sub=claims.sub,
            principal_type=claims.principal_type,
            permissions=list(claims.permissions),
            roles=list(claims.roles),
            project_ids=list(claims.project_ids),
            claims=claims,
        )


# ---------------------------------------------------------------------------
# Auth Manager settings
# ---------------------------------------------------------------------------


class AuthManagerSettings(
    ManagerSettings,
    env_file=(".env", "auth.env"),
    toml_file=("settings.toml", "auth.settings.toml"),
    yaml_file=("settings.yaml", "auth.settings.yaml"),
    json_file=("settings.json", "auth.settings.json"),
    env_prefix="AUTH_",
):
    """Settings for the Auth Manager."""

    model_config = SettingsConfigDict(
        alias_generator=prefixed_alias_generator("auth"),
        populate_by_name=True,
    )
    _accept_prefixed_keys = prefixed_model_validator("auth")

    server_url: AnyUrl = Field(
        title="Auth Server URL",
        description="The URL of the Auth Manager server.",
        default=AnyUrl("http://localhost:8007"),
    )
    manager_type: Optional[ManagerType] = Field(
        title="Manager Type",
        description="The type of manager.",
        default=ManagerType.AUTH_MANAGER,
    )
    database_url: str = Field(
        default="postgresql://madsci:madsci@localhost/madsci_auth",
        title="Database URL",
        description="PostgreSQL URL for Auth Manager persistence.",
        validation_alias=AliasChoices("database_url", "AUTH_DB_URL", "db_url"),
        json_schema_extra={"secret": True},
    )
    lab_id: Optional[str] = Field(
        default=None,
        title="Lab ID",
        description=(
            "The lab_id this Auth Manager binds to. Read at bootstrap; an"
            " Auth Manager refuses to start later against a different lab_id"
            " without an explicit operator-acknowledged migration."
        ),
    )
    access_token_ttl: int = Field(
        default=900,
        title="Access Token TTL",
        description="Default access-token lifetime in seconds (15 min).",
        ge=60,
    )
    refresh_token_ttl: int = Field(
        default=60 * 60 * 24 * 30,
        title="Refresh Token TTL",
        description="Default refresh-token lifetime in seconds (30 days).",
        ge=60,
    )
    signing_key_ttl: int = Field(
        default=60 * 60 * 24 * 90,
        title="Signing Key TTL",
        description=(
            "Recommended lifetime of a signing key before rotation, in seconds"
            " (90 days)."
        ),
        ge=3600,
    )
    argon2_time_cost: int = Field(
        default=3,
        title="Argon2 Time Cost",
        description="Argon2id time-cost parameter.",
        ge=1,
    )
    argon2_memory_cost: int = Field(
        default=64 * 1024,
        title="Argon2 Memory Cost",
        description="Argon2id memory-cost parameter (in KiB; 64 MiB).",
        ge=8 * 1024,
    )
    argon2_parallelism: int = Field(
        default=4,
        title="Argon2 Parallelism",
        description="Argon2id parallelism parameter.",
        ge=1,
    )
    deny_list_persist_grace: int = Field(
        default=300,
        title="Deny-list Persist Grace",
        description=(
            "Seconds past a revoked token's exp to retain its row in"
            " revoked_access_tokens."
        ),
        ge=0,
    )
    local_audit_log_path: Optional[str] = Field(
        default=None,
        title="Local Audit Log Path",
        description=(
            "Path to the on-disk fallback audit log. Defaults to"
            " ``.madsci/audit/auth-fallback.log``."
        ),
    )
    local_audit_log_max_bytes: int = Field(
        default=100 * 1024 * 1024,
        title="Local Audit Log Max Size",
        description="Maximum total size of the local audit log in bytes (100 MB).",
        ge=1024 * 1024,
    )


__all__ = [
    "AuthManagerSettings",
    "GrantType",
    "JWTClaims",
    "NodeIdentity",
    "OwnershipInfo",
    "Permission",
    "Principal",
    "PrincipalType",
    "ProjectInfo",
    "ProjectMembership",
    "Role",
    "ServiceAccount",
    "TokenResponse",
    "UserInfo",
]
