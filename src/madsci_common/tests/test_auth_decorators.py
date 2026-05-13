# ruff: noqa: ARG001
"""Tests for the ``@requires`` authorization decorator."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from madsci.common.auth_decorators import requires
from madsci.common.types.auth_types import (
    JWTClaims,
    Principal,
    PrincipalType,
)
from madsci.common.utils import new_ulid_str


def _make_principal(
    *,
    permissions: list[str] | None = None,
    project_ids: list[str] | None = None,
    principal_type: PrincipalType = PrincipalType.USER,
) -> Principal:
    sub = new_ulid_str()
    claims = JWTClaims(
        iss="http://localhost:8007",
        aud=new_ulid_str(),
        sub=sub,
        iat=0,
        exp=2_000_000_000,
        jti=new_ulid_str(),
        principal_type=principal_type,
        permissions=permissions or [],
        project_ids=project_ids or [],
    )
    return Principal.from_claims(claims)


def _build_app(principal: Principal | None, **decorator_kwargs) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_principal(request: Request, call_next):
        request.state.principal = principal
        return await call_next(request)

    @app.get("/restricted")
    @requires(**decorator_kwargs)
    async def restricted(request: Request) -> dict:
        return {"ok": True}

    @app.get("/projects/{project_id}/items")
    @requires(permission="experiment.write", project_from="project_id")
    async def project_scoped(request: Request, project_id: str) -> dict:
        return {"project_id": project_id}

    return TestClient(app)


def test_unauthenticated_returns_401() -> None:
    client = _build_app(None, permission="event.read")
    r = client.get("/restricted")
    assert r.status_code == 401


def test_missing_permission_returns_403() -> None:
    p = _make_principal(permissions=["other.read"])
    client = _build_app(p, permission="event.read")
    r = client.get("/restricted")
    assert r.status_code == 403


def test_present_permission_allows() -> None:
    p = _make_principal(permissions=["event.read"])
    client = _build_app(p, permission="event.read")
    r = client.get("/restricted")
    assert r.status_code == 200


def test_wildcard_admin_allows_anything() -> None:
    p = _make_principal(permissions=["*"])
    client = _build_app(p, permission="event.read")
    r = client.get("/restricted")
    assert r.status_code == 200


def test_project_scoped_denies_outsider() -> None:
    p = _make_principal(
        permissions=["experiment.write"],
        project_ids=[new_ulid_str()],
    )
    client = _build_app(p, permission="event.read")  # other endpoint
    proj = new_ulid_str()
    r = client.get(f"/projects/{proj}/items")
    assert r.status_code == 403


def test_project_scoped_allows_member() -> None:
    proj = new_ulid_str()
    p = _make_principal(
        permissions=["experiment.write"],
        project_ids=[proj],
    )
    client = _build_app(p, permission="event.read")
    r = client.get(f"/projects/{proj}/items")
    assert r.status_code == 200
