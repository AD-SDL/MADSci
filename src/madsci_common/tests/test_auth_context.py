# ruff: noqa: S106, S107, ARG001
"""Tests for the ambient AuthClient context propagation."""

from __future__ import annotations

import httpx
from madsci.common.auth_context import (
    auth_client_context,
    get_current_auth_client,
)
from madsci.common.http_client import create_httpx_client


class _FakeAuthClient:
    def __init__(self, token: str = "bearer-abc") -> None:
        self._token = token
        self.refresh_calls = 0
        self.force_deny_calls = 0

    def get_access_token(self) -> str:
        return self._token

    def refresh(self) -> None:
        self.refresh_calls += 1
        self._token = f"refreshed-{self.refresh_calls}"

    def force_deny_list_refresh(self) -> None:
        self.force_deny_calls += 1


def test_no_ambient_client_no_header() -> None:
    transport_calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append(request)
        return httpx.Response(200)

    client = create_httpx_client()
    # Inject mock transport
    client._transport = httpx.MockTransport(handler)
    client.get("http://example.com/foo")
    assert "authorization" not in {k.lower() for k in transport_calls[0].headers}


def test_ambient_client_injects_bearer() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    fake = _FakeAuthClient()
    client = create_httpx_client()
    client._transport = httpx.MockTransport(handler)

    with auth_client_context(fake):
        assert get_current_auth_client() is fake
        client.get("http://example.com/foo")

    assert captured[0].headers["authorization"] == "Bearer bearer-abc"


def test_ambient_client_refresh_on_401() -> None:
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        return httpx.Response(401)

    fake = _FakeAuthClient()
    client = create_httpx_client()
    client._transport = httpx.MockTransport(handler)

    with auth_client_context(fake):
        client.get("http://example.com/foo")

    # Refresh and force_deny_list_refresh both called from the response hook
    assert fake.refresh_calls == 1
    assert fake.force_deny_calls == 1


def test_explicit_authorization_header_not_overwritten() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    fake = _FakeAuthClient(token="ambient-token")
    client = create_httpx_client()
    client._transport = httpx.MockTransport(handler)

    with auth_client_context(fake):
        client.get(
            "http://example.com/foo", headers={"Authorization": "Bearer caller-token"}
        )

    assert captured[0].headers["authorization"] == "Bearer caller-token"
