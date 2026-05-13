# ruff: noqa: PLC0415
"""End-to-end integration tests for the Auth Manager foundation.

These exercise the full bootstrap → token → manager-call → revoke lifecycle
across the AuthManager service, AuthClient library, AuthMiddleware, and the
``@requires`` decorator.
"""

from __future__ import annotations

from typing import Iterator

import httpx
import pytest
from classy_fastapi import get
from fastapi import Request
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.auth_manager.testing import make_auth_client, make_auth_manager
from madsci.client.auth_client import AuthClient
from madsci.common.auth_decorators import requires
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import (
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl

_LAB_ID = new_ulid_str()


class _DemoSettings(ManagerSettings):
    server_url: AnyUrl = AnyUrl("http://localhost:9999")
    manager_type: ManagerType | None = None


class _ProtectedManager(AbstractManagerBase[_DemoSettings]):
    SETTINGS_CLASS = _DemoSettings

    @get("/whoami")
    @requires(permission="event.read")
    async def whoami(self, request: Request) -> dict:
        principal = request.state.principal
        return {
            "sub": principal.sub,
            "principal_type": principal.principal_type.value,
        }


@pytest.fixture
def auth_pair() -> Iterator[tuple[AuthManager, AuthClient]]:
    mgr = make_auth_manager(lab_id=_LAB_ID)
    client = make_auth_client(mgr)
    try:
        yield mgr, client
    finally:
        client.close()


def _protected_app(auth_client: AuthClient, *, required: bool = True):
    settings = _DemoSettings(
        enable_registry_resolution=False,
        otel_enabled=False,
        auth_enabled=True,
        auth_required=required,
        auth_server_url=AnyUrl("http://localhost:8007/"),
    )
    demo = _ProtectedManager(settings=settings)
    app = demo.create_server()
    for mw in app.user_middleware:
        if "AuthMiddleware" in str(mw.cls):
            mw.kwargs["auth_client"] = auth_client
    return TestClient(app)


# 11.2 - bootstrap → user login → call protected endpoint
def test_full_user_login_flow(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, ac = auth_pair
    # Grant the admin user the event.read permission via the read_only role
    roles = ac.list_roles()
    read_only_id = next(r["role_id"] for r in roles if r["name"] == "read_only")
    admin_id = next(u["user_id"] for u in ac.list_users() if u["username"] == "admin")
    ac.grant_role(role_id=read_only_id, user_id=admin_id)

    tok = ac.login("admin", "hunter2")
    client = _protected_app(ac, required=True)
    r = client.get("/whoami", headers={"Authorization": f"Bearer {tok.access_token}"})
    assert r.status_code == 200, r.text
    assert r.json()["principal_type"] == "user"


# 11.3 - service-account client_credentials → manager call
def test_service_account_call(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, ac = auth_pair
    # Grant read_only globally to the new SA so token has event.read
    roles = ac.list_roles()
    read_only_id = next(r["role_id"] for r in roles if r["name"] == "read_only")
    cred = ac.register_service_account(new_ulid_str(), [read_only_id])

    sa_client = ac
    sa_client.client_credentials_login(cred["client_id"], cred["client_secret"])
    client = _protected_app(ac, required=True)
    r = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {ac.access_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["principal_type"] == "service_account"


# 11.4 - refresh-token rotation including reuse-detection
def test_refresh_rotation_and_reuse_detection(
    auth_pair: tuple[AuthManager, AuthClient],
) -> None:
    _, ac = auth_pair
    tok = ac.login("admin", "hunter2")
    first_rt = tok.refresh_token

    new_tok = ac.refresh()
    assert new_tok.refresh_token != first_rt

    # Now try to reuse the *original* refresh token
    ac._refresh_token = first_rt
    with pytest.raises(httpx.HTTPStatusError):
        ac.refresh()

    # All refresh tokens for the principal should now be revoked — even the
    # newly issued one
    ac._refresh_token = new_tok.refresh_token
    with pytest.raises(httpx.HTTPStatusError):
        ac.refresh()


# 11.5 - JWKS rotation while in-flight token still valid
def test_jwks_rotation_keeps_in_flight_tokens_valid(
    auth_pair: tuple[AuthManager, AuthClient],
) -> None:
    mgr, ac = auth_pair
    tok = ac.login("admin", "hunter2")
    # Rotate signing keys at the manager directly
    mgr._signing_key_service.rotate()
    # Force the client to re-fetch JWKS
    ac.jwks(force_refresh=True)
    # In-flight token should still verify
    claims = ac.verify_jwt(tok.access_token)
    assert claims.user_id


# 11.6 - project-scoped @requires denies non-member
def test_project_scoped_requires(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, ac = auth_pair
    # Build a manager whose endpoint requires membership in path's project_id
    settings = _DemoSettings(
        enable_registry_resolution=False,
        otel_enabled=False,
        auth_enabled=True,
        auth_required=True,
        auth_server_url=AnyUrl("http://localhost:8007/"),
    )

    class _ProjectManager(AbstractManagerBase[_DemoSettings]):
        SETTINGS_CLASS = _DemoSettings

        @get("/projects/{project_id}/items")
        @requires(permission="experiment.write", project_from="project_id")
        async def items(self, request: Request, project_id: str) -> dict:
            return {"project_id": project_id}

    demo = _ProjectManager(settings=settings)
    app = demo.create_server()
    for mw in app.user_middleware:
        if "AuthMiddleware" in str(mw.cls):
            mw.kwargs["auth_client"] = ac
    client = TestClient(app)

    # Grant experimenter role to admin globally so the permission is satisfied
    roles = ac.list_roles()
    exp_role = next(r["role_id"] for r in roles if r["name"] == "experimenter")
    admin_id = next(u["user_id"] for u in ac.list_users() if u["username"] == "admin")
    ac.grant_role(role_id=exp_role, user_id=admin_id)

    tok = ac.login("admin", "hunter2")
    fake_proj = new_ulid_str()
    r = client.get(
        f"/projects/{fake_proj}/items",
        headers={"Authorization": f"Bearer {tok.access_token}"},
    )
    assert r.status_code == 403


# 11.8 - deny-list flow
def test_deny_list_flow_revokes_token_at_consumer(
    auth_pair: tuple[AuthManager, AuthClient],
) -> None:
    _, ac = auth_pair
    roles = ac.list_roles()
    read_only_id = next(r["role_id"] for r in roles if r["name"] == "read_only")
    admin_id = next(u["user_id"] for u in ac.list_users() if u["username"] == "admin")
    ac.grant_role(role_id=read_only_id, user_id=admin_id)

    tok = ac.login("admin", "hunter2")
    client = _protected_app(ac, required=True)
    r = client.get("/whoami", headers={"Authorization": f"Bearer {tok.access_token}"})
    assert r.status_code == 200

    # Revoke the access token at the Auth Manager
    ac.revoke(token=tok.access_token)
    # Force the client cache to refresh so the deny-list is applied
    ac.force_deny_list_refresh()
    # Subsequent verify should fail and the AuthMiddleware should 401
    r = client.get("/whoami", headers={"Authorization": f"Bearer {tok.access_token}"})
    assert r.status_code == 401


# 11.10 - deny-list restart durability
def test_deny_list_persists_across_restart(
    auth_pair: tuple[AuthManager, AuthClient],
) -> None:
    mgr, ac = auth_pair
    tok = ac.login("admin", "hunter2")
    ac.revoke(token=tok.access_token)
    snap = mgr._deny_list_service.snapshot()
    revoked_jtis = {e["jti"] for e in snap["entries"]}
    assert revoked_jtis  # something is in the persistent table

    # Build a new DenyListService (simulating Auth Manager restart) using the
    # same database
    from madsci.auth_manager.services import DenyListService

    fresh = DenyListService(mgr._postgres_handler.get_engine())
    fresh_snap = fresh.snapshot()
    assert {e["jti"] for e in fresh_snap["entries"]} == revoked_jtis
