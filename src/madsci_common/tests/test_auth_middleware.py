# ruff: noqa: S106
"""Integration tests for AuthMiddleware on AbstractManagerBase."""

from __future__ import annotations

import httpx
from classy_fastapi import get
from fastapi import Request
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.client.auth_client import AuthClient
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.auth_types import AuthManagerSettings
from madsci.common.types.manager_types import (
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl

_LAB_ID = new_ulid_str()


class _DemoSettings(ManagerSettings):
    """Stub settings for the demo manager."""

    server_url: AnyUrl = AnyUrl("http://localhost:9999")
    manager_type: ManagerType | None = None


class _DemoManager(AbstractManagerBase[_DemoSettings]):
    SETTINGS_CLASS = _DemoSettings

    @get("/whoami")
    async def whoami(self, request: Request) -> dict:
        principal = getattr(request.state, "principal", None)
        if principal is None:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "sub": principal.sub,
            "principal_type": principal.principal_type.value,
        }


def _build_auth_pair() -> tuple[AuthManager, AuthClient]:
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id=_LAB_ID,
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
    auth_app = mgr.create_server()
    auth_test = TestClient(auth_app)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode("ascii")
        kwargs: dict = {"headers": dict(request.headers.items())}
        if request.content:
            kwargs["content"] = request.content
        resp = auth_test.request(request.method, path, **kwargs)
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
        )

    transport = httpx.MockTransport(handler)
    client = AuthClient(auth_server_url="http://localhost:8007/")
    client._http = httpx.Client(
        base_url=client.auth_server_url, transport=transport, timeout=10.0
    )
    return mgr, client


def test_middleware_off_by_default() -> None:
    settings = _DemoSettings(enable_registry_resolution=False, otel_enabled=False)
    demo = _DemoManager(settings=settings)
    client = TestClient(demo.create_server())
    r = client.get("/whoami")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_middleware_required_rejects_missing_token() -> None:
    _, auth_client = _build_auth_pair()
    settings = _DemoSettings(
        enable_registry_resolution=False,
        otel_enabled=False,
        auth_enabled=True,
        auth_required=True,
        auth_server_url=AnyUrl("http://localhost:8007/"),
    )
    demo = _DemoManager(settings=settings)
    # Inject the patched AuthClient that talks to the in-memory auth manager
    demo._auth_client = auth_client
    app = demo.create_server()
    # Manually replace the AuthMiddleware's client with the patched one
    for mw in app.user_middleware:
        if "AuthMiddleware" in str(mw.cls):
            mw.kwargs["auth_client"] = auth_client
    client = TestClient(app)
    r = client.get("/whoami")
    assert r.status_code == 401
    assert r.json()["error"] == "missing_token"


def test_middleware_migration_mode_passes_through() -> None:
    _, auth_client = _build_auth_pair()
    settings = _DemoSettings(
        enable_registry_resolution=False,
        otel_enabled=False,
        auth_enabled=True,
        auth_required=False,
        auth_server_url=AnyUrl("http://localhost:8007/"),
    )
    demo = _DemoManager(settings=settings)
    app = demo.create_server()
    for mw in app.user_middleware:
        if "AuthMiddleware" in str(mw.cls):
            mw.kwargs["auth_client"] = auth_client
    client = TestClient(app)
    r = client.get("/whoami")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_middleware_validates_token() -> None:
    _, auth_client = _build_auth_pair()
    # Get a valid access token
    tok = auth_client.login("admin", "hunter2")

    settings = _DemoSettings(
        enable_registry_resolution=False,
        otel_enabled=False,
        auth_enabled=True,
        auth_required=True,
        auth_server_url=AnyUrl("http://localhost:8007/"),
    )
    demo = _DemoManager(settings=settings)
    app = demo.create_server()
    for mw in app.user_middleware:
        if "AuthMiddleware" in str(mw.cls):
            mw.kwargs["auth_client"] = auth_client
    client = TestClient(app)

    r = client.get("/whoami", headers={"Authorization": f"Bearer {tok.access_token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["authenticated"] is True
    assert body["principal_type"] == "user"
