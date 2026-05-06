"""Reusable in-memory Auth Manager fixture and helpers for tests.

Importable by any test suite that needs a real Auth Manager wired up against
``SQLiteHandler`` plus an ``AuthClient`` whose HTTP transport is bound to
the in-memory FastAPI app via ``httpx.MockTransport``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import httpx
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.client.auth_client import AuthClient
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.types.auth_types import AuthManagerSettings
from madsci.common.utils import new_ulid_str


def make_auth_manager(
    *,
    lab_id: str | None = None,
    admin_username: str = "admin",
    admin_password: str = "hunter2",  # noqa: S107
    auth_enforced: bool = False,
) -> AuthManager:
    """Build a fully-bootstrapped in-memory AuthManager.

    ``auth_enforced=False`` (the default for tests) disables the auth
    middleware so admin endpoints can be exercised without going through
    the password-grant + bearer-token dance. Production deployments default
    to ``True`` (security review HIGH finding); pass ``True`` here when the
    test specifically wants to verify auth enforcement.
    """
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id=lab_id or new_ulid_str(),
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    if not auth_enforced:
        settings.auth_enabled = False
        settings.auth_required = False
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username=admin_username, admin_password=admin_password)
    return mgr


def make_mock_transport(mgr: AuthManager) -> httpx.MockTransport:
    """Build an httpx MockTransport that forwards requests to ``mgr``."""
    test_client = TestClient(mgr.create_server())

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode("ascii")
        kwargs: dict = {"headers": dict(request.headers.items())}
        if request.content:
            kwargs["content"] = request.content
        resp = test_client.request(request.method, path, **kwargs)
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
        )

    return httpx.MockTransport(handler)


def make_auth_client(mgr: AuthManager) -> AuthClient:
    """Build an AuthClient whose HTTP transport is bound to ``mgr``."""
    transport = make_mock_transport(mgr)
    client = AuthClient(auth_server_url="http://localhost:8007/")
    client._http = httpx.Client(
        base_url=client.auth_server_url,
        transport=transport,
        timeout=10.0,
    )
    return client


@contextmanager
def in_memory_auth(
    *, lab_id: str | None = None
) -> Iterator[tuple[AuthManager, AuthClient]]:
    """Context-managed (mgr, client) pair for one-off use."""
    mgr = make_auth_manager(lab_id=lab_id)
    client = make_auth_client(mgr)
    try:
        yield mgr, client
    finally:
        client.close()


__all__ = [
    "in_memory_auth",
    "make_auth_client",
    "make_auth_manager",
    "make_mock_transport",
]
