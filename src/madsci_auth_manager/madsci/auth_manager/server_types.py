"""Pydantic request/response models specific to the Auth Manager server."""

from __future__ import annotations

from typing import Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field


class CreateUserRequest(MadsciBaseModel):
    """Request body for ``POST /users``."""

    username: str
    password: str
    email: Optional[str] = None


class UserResponse(MadsciBaseModel):
    """User-resource response (``password_hash`` is never returned)."""

    user_id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True


class UpdateUserRequest(MadsciBaseModel):
    """Partial-update body for ``PATCH /users/{id}``."""

    is_active: Optional[bool] = None
    new_password: Optional[str] = None
    email: Optional[str] = None


class CreateProjectRequest(MadsciBaseModel):
    """Request body for ``POST /projects``."""

    name: str
    description: Optional[str] = None


class ProjectResponse(MadsciBaseModel):
    """Project-resource response."""

    project_id: str
    name: str
    description: Optional[str] = None


class AddMemberRequest(MadsciBaseModel):
    """Request body for ``POST /projects/{id}/members``."""

    user_id: str
    role_id: str


class CreateRoleRequest(MadsciBaseModel):
    """Request body for ``POST /roles``."""

    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class RoleResponse(MadsciBaseModel):
    """Role-resource response, including its flattened permission strings."""

    role_id: str
    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class GrantRoleRequest(MadsciBaseModel):
    """Request body for ``POST /roles/grant``.

    Exactly one of ``user_id`` (with or without ``project_id``),
    ``service_account_client_id``, or ``node_identity_client_id`` should be
    supplied to identify the grant target.
    """

    role_id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    service_account_client_id: Optional[str] = None
    node_identity_client_id: Optional[str] = None


class RegisterServiceAccountRequest(MadsciBaseModel):
    """Request body for ``POST /service-accounts``."""

    manager_id: str
    role_ids: list[str] = Field(default_factory=list)


class RegisterNodeRequest(MadsciBaseModel):
    """Request body for ``POST /node-identities``."""

    node_id: str
    workcell_id: Optional[str] = None
    role_ids: list[str] = Field(default_factory=list)


class CredentialResponse(MadsciBaseModel):
    """Response that returns a freshly-issued client_id + plaintext secret.

    The plaintext secret is returned exactly once; only its Argon2 hash is
    stored. Callers are responsible for distributing the secret out-of-band.
    """

    client_id: str
    client_secret: str
    note: str = "Store this secret immediately — it will never be displayed again."


class IntrospectRequest(MadsciBaseModel):
    """Request body for ``POST /introspect`` (RFC 7662)."""

    token: str


class RevokeRequest(MadsciBaseModel):
    """Request body for ``POST /revoke``.

    Either ``token`` (an access-token JWT) or ``refresh_token`` may be set;
    callers usually send both during logout.
    """

    token: Optional[str] = None
    refresh_token: Optional[str] = None


class KeyInfo(MadsciBaseModel):
    """Public summary of a signing key (``private_key_pem`` is never returned)."""

    kid: str
    algorithm: str
    active: bool
    active_for_signing: bool
    created_at: Optional[str] = None
    retired_at: Optional[str] = None


class KeysHealthResponse(MadsciBaseModel):
    """Response body for ``GET /health/keys``."""

    active_keys: int
    oldest_key_age_seconds: Optional[int] = None
    signing_kid: Optional[str] = None


class DenyListEntry(MadsciBaseModel):
    """A single entry in the deny-list (jti + its access-token expiration)."""

    jti: str
    exp: int


class DenyListResponse(MadsciBaseModel):
    """Response body for ``GET /deny-list``.

    Consumers SHOULD send ``If-None-Match: "<etag>"`` on subsequent polls
    to receive HTTP 304 when the list is unchanged.
    """

    etag: str
    entries: list[DenyListEntry]


class BootstrapResponse(MadsciBaseModel):
    """Response body for the bootstrap CLI / API call."""

    user_id: str
    username: str
    admin_role_id: str
    signing_kid: str
    note: str = "Bootstrap successful — store the admin password securely."


class TokenErrorResponse(MadsciBaseModel):
    """OAuth 2.0 token-endpoint error body (RFC 6749 §5.2)."""

    error: str
    error_description: Optional[str] = None
