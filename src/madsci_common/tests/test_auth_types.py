# ruff: noqa: S105, S106
"""Unit tests for the extended ``auth_types`` module."""

from __future__ import annotations

import time

import pytest
from madsci.common.types.auth_types import (
    AuthManagerSettings,
    JWTClaims,
    NodeIdentity,
    OwnershipInfo,
    Permission,
    Principal,
    PrincipalType,
    ProjectMembership,
    Role,
    ServiceAccount,
    TokenResponse,
)
from madsci.common.utils import new_ulid_str
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# RBAC primitives
# ---------------------------------------------------------------------------


def test_permission_round_trip() -> None:
    perm = Permission(name="experiment.write", description="Create experiments")
    dumped = perm.model_dump()
    assert dumped["name"] == "experiment.write"
    assert Permission.model_validate(dumped) == perm


def test_role_default_role_id_is_ulid() -> None:
    role = Role(name="admin", permissions=["experiment.write"])
    # Should be a 26-char ULID and pass validation
    assert len(role.role_id) == 26
    Role.model_validate(role.model_dump())


def test_role_rejects_invalid_role_id() -> None:
    with pytest.raises(ValidationError):
        Role(role_id="not-a-ulid", name="bad")


def test_project_membership_validates_ulids() -> None:
    user_id = new_ulid_str()
    project_id = new_ulid_str()
    role_id = new_ulid_str()

    membership = ProjectMembership(
        user_id=user_id,
        project_id=project_id,
        role_ids=[role_id],
    )
    assert membership.user_id == user_id
    assert membership.role_ids == [role_id]

    with pytest.raises(ValidationError):
        ProjectMembership(user_id="bad", project_id=project_id, role_ids=[])


def test_service_account_requires_ulid_manager_id() -> None:
    sa = ServiceAccount(
        client_id="client-abc",
        manager_id=new_ulid_str(),
    )
    assert sa.is_active is True

    with pytest.raises(ValidationError):
        ServiceAccount(client_id="client", manager_id="not-a-ulid")


def test_node_identity_optional_workcell_validates() -> None:
    node_id = new_ulid_str()
    wc_id = new_ulid_str()

    NodeIdentity(client_id="c", node_id=node_id)
    NodeIdentity(client_id="c", node_id=node_id, workcell_id=wc_id)

    with pytest.raises(ValidationError):
        NodeIdentity(client_id="c", node_id=node_id, workcell_id="bad")


# ---------------------------------------------------------------------------
# JWTClaims and Principal
# ---------------------------------------------------------------------------


def _make_user_claims(**overrides: object) -> JWTClaims:
    base = {
        "iss": "http://localhost:8007",
        "aud": new_ulid_str(),  # lab_id
        "sub": new_ulid_str(),  # user_id
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "jti": new_ulid_str(),
        "principal_type": PrincipalType.USER,
        "permissions": ["experiment.read"],
        "roles": [new_ulid_str()],
        "user_id": new_ulid_str(),
        "project_ids": [new_ulid_str(), new_ulid_str()],
    }
    base.update(overrides)
    return JWTClaims(**base)


def test_jwt_claims_user_round_trip() -> None:
    claims = _make_user_claims()
    dumped = claims.model_dump()
    assert dumped["principal_type"] == "user"
    assert JWTClaims.model_validate(dumped) == claims


def test_principal_from_claims_user() -> None:
    claims = _make_user_claims()
    p = Principal.from_claims(claims)
    assert p.principal_type == PrincipalType.USER
    assert p.permissions == claims.permissions
    assert p.project_ids == claims.project_ids
    assert p.claims == claims


def test_ownership_from_jwt_claims_user() -> None:
    claims = _make_user_claims()
    o = OwnershipInfo.from_jwt_claims(claims)
    assert o.lab_id == claims.aud
    assert o.user_id == claims.user_id
    assert o.node_id is None
    assert o.workcell_id is None
    assert o.manager_id is None
    # project_id intentionally unset (project context is per-operation)
    assert o.project_id is None


def test_ownership_from_jwt_claims_node() -> None:
    workcell_id = new_ulid_str()
    node_id = new_ulid_str()
    lab_id = new_ulid_str()
    claims = JWTClaims(
        iss="http://localhost:8007",
        aud=lab_id,
        sub="client-node-abc",
        iat=int(time.time()),
        exp=int(time.time()) + 900,
        jti=new_ulid_str(),
        principal_type=PrincipalType.NODE,
        node_id=node_id,
        workcell_id=workcell_id,
    )
    o = OwnershipInfo.from_jwt_claims(claims)
    assert o.lab_id == lab_id
    assert o.node_id == node_id
    assert o.workcell_id == workcell_id
    assert o.user_id is None
    assert o.manager_id is None


def test_ownership_from_jwt_claims_service_account() -> None:
    manager_id = new_ulid_str()
    lab_id = new_ulid_str()
    claims = JWTClaims(
        iss="http://localhost:8007",
        aud=lab_id,
        sub="client-sa-xyz",
        iat=int(time.time()),
        exp=int(time.time()) + 900,
        jti=new_ulid_str(),
        principal_type=PrincipalType.SERVICE_ACCOUNT,
        manager_id=manager_id,
    )
    o = OwnershipInfo.from_jwt_claims(claims)
    assert o.lab_id == lab_id
    assert o.manager_id == manager_id
    assert o.user_id is None
    assert o.node_id is None


# ---------------------------------------------------------------------------
# TokenResponse
# ---------------------------------------------------------------------------


def test_token_response_defaults() -> None:
    tr = TokenResponse(access_token="abc", expires_in=900)
    assert tr.token_type == "Bearer"
    assert tr.refresh_token is None


# ---------------------------------------------------------------------------
# AuthManagerSettings
# ---------------------------------------------------------------------------


def test_auth_manager_settings_defaults() -> None:
    settings = AuthManagerSettings(enable_registry_resolution=False)
    assert str(settings.server_url).startswith("http://localhost:8007")
    # Secret-classified field must redact in safe dump
    safe = settings.model_dump_safe(include_secrets=False)
    assert "***REDACTED***" in str(safe.get("database_url"))


def test_auth_manager_settings_prefixed_yaml_keys() -> None:
    # Prefixed keys should be accepted via prefixed_model_validator
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        auth_access_token_ttl=600,
    )
    assert settings.access_token_ttl == 600
