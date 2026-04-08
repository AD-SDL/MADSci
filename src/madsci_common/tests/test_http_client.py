"""Tests for madsci.common.http_client -- httpx client factory."""

from __future__ import annotations

import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from madsci.common.http_client import (
    AsyncRetryTransport,
    RetryTransport,
    _make_rate_limit_hook,
    create_httpx_client,
)
from madsci.common.types.client_types import MadsciClientConfig
from madsci.common.utils import RateLimitTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_response() -> httpx.Response:
    return httpx.Response(200)


def _error_response(status: int = 503) -> httpx.Response:
    return httpx.Response(status)


def _rate_limit_response() -> httpx.Response:
    return httpx.Response(
        200,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "42",
            "X-RateLimit-Reset": "1700000000",
        },
    )


class _StubTransport(httpx.BaseTransport):
    """Transport that returns a sequence of pre-canned responses."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    def close(self) -> None:
        pass


class _AsyncStubTransport(httpx.AsyncBaseTransport):
    """Async transport that returns a sequence of pre-canned responses."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# RetryTransport tests
# ---------------------------------------------------------------------------


class TestRetryTransport:
    """Tests for the synchronous RetryTransport."""

    def test_no_retry_on_success(self) -> None:
        stub = _StubTransport([_ok_response()])
        transport = RetryTransport(stub, retries=3, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 200
        assert stub._call_count == 1

    def test_retries_on_error_then_succeeds(self) -> None:
        stub = _StubTransport(
            [_error_response(503), _error_response(503), _ok_response()]
        )
        transport = RetryTransport(stub, retries=3, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 200
        assert stub._call_count == 3

    def test_exhausts_retries_returns_last_response(self) -> None:
        stub = _StubTransport([_error_response(503)] * 5)
        transport = RetryTransport(stub, retries=2, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 503
        # 1 initial + 2 retries = 3 attempts
        assert stub._call_count == 3

    def test_does_not_retry_unlisted_status(self) -> None:
        stub = _StubTransport([_error_response(400)])
        transport = RetryTransport(
            stub, retries=3, status_forcelist=[500, 503], backoff_factor=0.0
        )

        request = httpx.Request("GET", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 400
        assert stub._call_count == 1

    def test_respects_allowed_methods(self) -> None:
        """POST should not be retried when allowed_methods is ['GET']."""
        stub = _StubTransport([_error_response(503)])
        transport = RetryTransport(
            stub,
            retries=3,
            backoff_factor=0.0,
            allowed_methods=["GET"],
        )

        request = httpx.Request("POST", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 503
        assert stub._call_count == 1  # no retry

    def test_allowed_methods_none_retries_all(self) -> None:
        """When allowed_methods is None, all methods should be retried."""
        stub = _StubTransport([_error_response(503), _ok_response()])
        transport = RetryTransport(
            stub,
            retries=3,
            backoff_factor=0.0,
            allowed_methods=None,
        )

        request = httpx.Request("POST", "http://example.com/")
        response = transport.handle_request(request)

        assert response.status_code == 200
        assert stub._call_count == 2

    def test_backoff_delay(self) -> None:
        """Verify that exponential backoff introduces delays."""
        stub = _StubTransport([_error_response(503)] * 5)
        factor = 0.01  # small to keep test fast
        transport = RetryTransport(stub, retries=2, backoff_factor=factor)

        request = httpx.Request("GET", "http://example.com/")
        start = time.monotonic()
        transport.handle_request(request)
        elapsed = time.monotonic() - start

        # Expected minimum delay: factor*2^0 + factor*2^1 = 0.01 + 0.02 = 0.03
        assert elapsed >= 0.02  # a bit of margin

    def test_context_manager(self) -> None:
        stub = _StubTransport([_ok_response()])
        with RetryTransport(stub, retries=0) as transport:
            response = transport.handle_request(
                httpx.Request("GET", "http://example.com/")
            )
            assert response.status_code == 200

    def test_custom_status_forcelist(self) -> None:
        stub = _StubTransport([_error_response(429), _ok_response()])
        transport = RetryTransport(
            stub,
            retries=3,
            backoff_factor=0.0,
            status_forcelist=[429],
        )
        response = transport.handle_request(httpx.Request("GET", "http://example.com/"))
        assert response.status_code == 200
        assert stub._call_count == 2

    def test_zero_retries(self) -> None:
        stub = _StubTransport([_error_response(503)])
        transport = RetryTransport(stub, retries=0, backoff_factor=0.0)

        response = transport.handle_request(httpx.Request("GET", "http://example.com/"))
        assert response.status_code == 503
        assert stub._call_count == 1

    def test_closes_previous_failed_response_on_successful_retry(self) -> None:
        """Failed responses from earlier attempts must be closed when retry succeeds."""
        failed_response = MagicMock(spec=httpx.Response)
        failed_response.status_code = 503
        ok_response = httpx.Response(200)

        class _SequenceTransport(httpx.BaseTransport):
            def __init__(self) -> None:
                self._responses = [failed_response, ok_response]
                self._index = 0

            def handle_request(self, request: httpx.Request) -> httpx.Response:
                resp = self._responses[self._index]
                self._index += 1
                return resp

            def close(self) -> None:
                pass

        transport = RetryTransport(
            _SequenceTransport(),
            retries=3,
            status_forcelist=[503],
            backoff_factor=0.0,
        )
        result = transport.handle_request(httpx.Request("GET", "http://example.com/"))
        assert result.status_code == 200
        # The failed response must have been closed to avoid FD leaks
        failed_response.close.assert_called_once()


# ---------------------------------------------------------------------------
# AsyncRetryTransport tests
# ---------------------------------------------------------------------------


class TestAsyncRetryTransport:
    """Tests for the asynchronous AsyncRetryTransport."""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self) -> None:
        stub = _AsyncStubTransport([_ok_response()])
        transport = AsyncRetryTransport(stub, retries=3, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert stub._call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_error_then_succeeds(self) -> None:
        stub = _AsyncStubTransport([_error_response(500), _ok_response()])
        transport = AsyncRetryTransport(stub, retries=3, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert stub._call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self) -> None:
        stub = _AsyncStubTransport([_error_response(502)] * 5)
        transport = AsyncRetryTransport(stub, retries=2, backoff_factor=0.0)

        request = httpx.Request("GET", "http://example.com/")
        response = await transport.handle_async_request(request)

        assert response.status_code == 502
        assert stub._call_count == 3

    @pytest.mark.asyncio
    async def test_respects_allowed_methods(self) -> None:
        stub = _AsyncStubTransport([_error_response(503)])
        transport = AsyncRetryTransport(
            stub,
            retries=3,
            backoff_factor=0.0,
            allowed_methods=["GET"],
        )

        request = httpx.Request("DELETE", "http://example.com/")
        response = await transport.handle_async_request(request)

        assert response.status_code == 503
        assert stub._call_count == 1

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        stub = _AsyncStubTransport([_ok_response()])
        async with AsyncRetryTransport(stub, retries=0) as transport:
            response = await transport.handle_async_request(
                httpx.Request("GET", "http://example.com/"),
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_closes_previous_failed_response_on_successful_retry(self) -> None:
        """Failed async responses from earlier attempts must be closed when retry succeeds."""
        failed_response = MagicMock(spec=httpx.Response)
        failed_response.status_code = 500
        failed_response.aclose = AsyncMock()
        ok_response = httpx.Response(200)

        class _SequenceAsyncTransport(httpx.AsyncBaseTransport):
            def __init__(self) -> None:
                self._responses = [failed_response, ok_response]
                self._index = 0

            async def handle_async_request(
                self, request: httpx.Request
            ) -> httpx.Response:
                resp = self._responses[self._index]
                self._index += 1
                return resp

            async def aclose(self) -> None:
                pass

        transport = AsyncRetryTransport(
            _SequenceAsyncTransport(),
            retries=3,
            status_forcelist=[500],
            backoff_factor=0.0,
        )
        result = await transport.handle_async_request(
            httpx.Request("GET", "http://example.com/")
        )
        assert result.status_code == 200
        # The failed response must have been async-closed to avoid FD leaks
        failed_response.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Rate limit hook type annotation
# ---------------------------------------------------------------------------


class TestRateLimitHookTypeAnnotation:
    """Test that _make_rate_limit_hook has the correct return type annotation."""

    def test_return_type_annotation_is_callable(self) -> None:
        """_make_rate_limit_hook should be annotated with Callable, not callable."""
        hints: dict = {}
        with contextlib.suppress(AttributeError):
            hints = _make_rate_limit_hook.__annotations__

        # The return annotation should be Callable (not the built-in callable)
        return_annotation = hints.get("return")
        # It must not be the lowercase builtin callable
        assert return_annotation is not callable, (
            "Return type annotation should be Callable[...], not lowercase callable"
        )


# ---------------------------------------------------------------------------
# create_httpx_client tests
# ---------------------------------------------------------------------------


class TestCreateHttpxClient:
    """Tests for the create_httpx_client factory function."""

    def test_returns_sync_client_by_default(self) -> None:
        client = create_httpx_client()
        try:
            assert isinstance(client, httpx.Client)
        finally:
            client.close()

    def test_returns_async_client_when_requested(self) -> None:
        client = create_httpx_client(async_mode=True)
        try:
            assert isinstance(client, httpx.AsyncClient)
        finally:
            asyncio.run(client.aclose())

    def test_default_config(self) -> None:
        client = create_httpx_client()
        try:
            assert isinstance(client, httpx.Client)
            assert client.follow_redirects is True
        finally:
            client.close()

    def test_custom_config(self) -> None:
        cfg = MadsciClientConfig(
            retry_total=5,
            timeout_default=30.0,
            pool_maxsize=20,
            pool_connections=15,
        )
        client = create_httpx_client(config=cfg)
        try:
            assert client.timeout.read == 30.0
            assert client.timeout.write == 30.0
            assert client.timeout.connect == 5.0
            assert client.timeout.pool == 5.0
        finally:
            client.close()

    def test_retry_disabled(self) -> None:
        cfg = MadsciClientConfig(retry_enabled=False)
        client = create_httpx_client(config=cfg)
        try:
            # Transport should be the raw HTTPTransport, not RetryTransport
            transport = client._transport
            assert not isinstance(transport, RetryTransport)
        finally:
            client.close()

    def test_retry_enabled_wraps_transport(self) -> None:
        cfg = MadsciClientConfig(retry_enabled=True)
        client = create_httpx_client(config=cfg)
        try:
            transport = client._transport
            assert isinstance(transport, RetryTransport)
        finally:
            client.close()

    def test_async_retry_enabled_wraps_transport(self) -> None:
        cfg = MadsciClientConfig(retry_enabled=True)
        client = create_httpx_client(config=cfg, async_mode=True)
        try:
            transport = client._transport
            assert isinstance(transport, AsyncRetryTransport)
        finally:
            asyncio.run(client.aclose())

    def test_rate_limit_tracker_attached(self) -> None:
        cfg = MadsciClientConfig(rate_limit_tracking_enabled=True)
        client = create_httpx_client(config=cfg)
        try:
            assert hasattr(client, "rate_limit_tracker")
            assert isinstance(client.rate_limit_tracker, RateLimitTracker)
        finally:
            client.close()

    def test_rate_limit_tracker_not_attached_when_disabled(self) -> None:
        cfg = MadsciClientConfig(rate_limit_tracking_enabled=False)
        client = create_httpx_client(config=cfg)
        try:
            assert not hasattr(client, "rate_limit_tracker")
        finally:
            client.close()

    def test_follow_redirects_enabled(self) -> None:
        client = create_httpx_client()
        try:
            assert client.follow_redirects is True
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Rate limit hook integration
# ---------------------------------------------------------------------------


class TestRateLimitHook:
    """Test that the rate limit event hook updates the tracker."""

    def test_hook_updates_tracker(self) -> None:
        """Rate-limit headers from a response should populate the tracker."""
        cfg = MadsciClientConfig(rate_limit_tracking_enabled=True)

        # Create a client with a mock transport so we control the response.
        stub = _StubTransport([_rate_limit_response()])
        client = create_httpx_client(config=cfg)
        # Replace the transport so we can send a request without hitting the network
        client._transport = stub
        try:
            response = client.get("http://example.com/test")
            assert response.status_code == 200

            tracker = client.rate_limit_tracker
            assert tracker.limit == 100
            assert tracker.remaining == 42
            assert tracker.reset == 1700000000
        finally:
            client.close()

    def test_hook_respects_warning_threshold(self) -> None:
        """Tracker should warn when usage exceeds threshold."""
        cfg = MadsciClientConfig(
            rate_limit_tracking_enabled=True,
            rate_limit_warning_threshold=0.5,
        )
        resp = httpx.Response(
            200,
            headers={
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "10",
                "X-RateLimit-Reset": "1700000000",
            },
        )
        stub = _StubTransport([resp])
        client = create_httpx_client(config=cfg)
        client._transport = stub
        try:
            with patch("madsci.common.utils.logger") as mock_logger:
                client.get("http://example.com/test")
                # The tracker should have called logger.warning
                assert mock_logger.warning.called
        finally:
            client.close()


# ---------------------------------------------------------------------------
# End-to-end retry with factory
# ---------------------------------------------------------------------------


class TestEndToEndRetry:
    """End-to-end test combining factory + retry transport."""

    def test_factory_client_retries(self) -> None:
        """Client produced by the factory should retry on 503."""
        cfg = MadsciClientConfig(
            retry_enabled=True,
            retry_total=2,
            retry_backoff_factor=0.0,
            retry_status_forcelist=[503],
        )
        stub = _StubTransport([_error_response(503), _ok_response()])
        client = create_httpx_client(config=cfg)
        # Inject the stub transport into the retry wrapper
        client._transport._transport = stub
        try:
            response = client.get("http://example.com/test")
            assert response.status_code == 200
            assert stub._call_count == 2
        finally:
            client.close()

    def test_factory_client_no_retry_on_success(self) -> None:
        cfg = MadsciClientConfig(
            retry_enabled=True,
            retry_total=3,
            retry_backoff_factor=0.0,
        )
        stub = _StubTransport([_ok_response()])
        client = create_httpx_client(config=cfg)
        client._transport._transport = stub
        try:
            response = client.get("http://example.com/test")
            assert response.status_code == 200
            assert stub._call_count == 1
        finally:
            client.close()
