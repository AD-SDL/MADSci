"""Shared fixtures for the CLI command tests."""

from __future__ import annotations

from typing import Callable

import httpx
import pytest
from click.testing import Result

_EXPECTED_MESSAGE = {
    "connect": "Connection refused",
    "timeout": "Request timed out",
    "http": "HTTP 500",
}


@pytest.fixture
def service_error() -> Callable[[str, str], httpx.HTTPError]:
    """Return a factory for the httpx error that a client raises when a URL fails.

    ``kind`` is ``"connect"``, ``"timeout"`` or ``"http"`` (an HTTP 500 response).
    """

    def _make(kind: str, url: str) -> httpx.HTTPError:
        request = httpx.Request("GET", url)
        if kind == "connect":
            return httpx.ConnectError("[Errno 111] Connection refused", request=request)
        if kind == "timeout":
            return httpx.ReadTimeout("timed out", request=request)
        response = httpx.Response(500, request=request, text="Internal Server Error")
        return httpx.HTTPStatusError(
            "500 Internal Server Error", request=request, response=response
        )

    return _make


@pytest.fixture
def assert_friendly_error() -> Callable[[Result, str, str], None]:
    """Return a check that the CLI printed a short error message and exited with code 1."""

    def _check(result: Result, kind: str, url: str) -> None:
        assert result.exit_code == 1, result.output
        assert isinstance(result.exception, SystemExit), result.exception
        assert url in result.output
        assert _EXPECTED_MESSAGE[kind] in result.output

    return _check
