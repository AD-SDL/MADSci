# ruff: noqa: S105, S106
"""Unit tests for ``AuthClient``.

Tests use ``httpx.MockTransport`` to mount a real ``AuthManager`` so we
exercise the actual JWT/JWKS round-trip and refresh-token rotation logic.
"""

from __future__ import annotations

from typing import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from madsci.auth_manager.auth_server import AuthManager
from madsci.client.auth_client import AuthClient, AuthClientError
from madsci.common.db_handlers.postgres_handler import SQLiteHandler
from madsci.common.types.auth_types import AuthManagerSettings


@pytest.fixture
def auth_pair() -> Iterator[tuple[AuthManager, AuthClient]]:
    settings = AuthManagerSettings(
        enable_registry_resolution=False,
        lab_id="lab-test",
        otel_enabled=False,
        argon2_time_cost=1,
        argon2_memory_cost=8 * 1024,
        argon2_parallelism=1,
    )
    mgr = AuthManager(settings=settings, postgres_handler=SQLiteHandler())
    mgr.bootstrap(admin_username="admin", admin_password="hunter2")
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

    transport = httpx.MockTransport(handler)
    client = AuthClient(auth_server_url="http://localhost:8007/")
    client._http = httpx.Client(
        base_url=client.auth_server_url,
        transport=transport,
        timeout=10.0,
    )
    try:
        yield mgr, client
    finally:
        client.close()


def test_login_returns_tokens(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    tok = client.login("admin", "hunter2")
    assert tok.access_token
    assert tok.refresh_token
    assert tok.token_type == "Bearer"


def test_verify_jwt_round_trip(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    tok = client.login("admin", "hunter2")
    claims = client.verify_jwt(tok.access_token)
    assert claims.principal_type.value == "user"


def test_refresh_rotates_tokens(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    tok1 = client.login("admin", "hunter2")
    tok2 = client.refresh()
    assert tok2.access_token != tok1.access_token
    assert tok2.refresh_token != tok1.refresh_token


def test_refresh_reuse_detected(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    tok1 = client.login("admin", "hunter2")
    # Snapshot the first refresh token
    first_rt = tok1.refresh_token
    client.refresh()
    # Try to use the original refresh token again
    client._refresh_token = first_rt
    with pytest.raises(httpx.HTTPStatusError):
        client.refresh()


def test_introspect_and_revoke(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    tok = client.login("admin", "hunter2")
    intro = client.introspect(tok.access_token)
    assert intro["active"] is True
    client.revoke(token=tok.access_token)
    intro2 = client.introspect(tok.access_token)
    assert intro2["active"] is False


def test_jwks_caching(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    keys1 = client.jwks()
    keys2 = client.jwks()
    assert keys1 is keys2  # cached object reused
    keys3 = client.jwks(force_refresh=True)
    assert keys3 == keys1


def test_deny_list_polling_revokes(
    auth_pair: tuple[AuthManager, AuthClient],
) -> None:
    _, client = auth_pair
    tok = client.login("admin", "hunter2")
    # Verify works initially
    client.verify_jwt(tok.access_token)
    # Revoke at server
    client.revoke(token=tok.access_token)
    # Force a deny-list refresh and re-verify
    client.force_deny_list_refresh()
    with pytest.raises(AuthClientError):
        client.verify_jwt(tok.access_token)


def test_close_is_idempotent(auth_pair: tuple[AuthManager, AuthClient]) -> None:
    _, client = auth_pair
    client.close()
    client.close()
