"""Tests for DualModeClientMixin."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from madsci.client.http import DualModeClientMixin
from madsci.common.types.client_types import MadsciClientConfig

# ---------------------------------------------------------------------------
# Helper: concrete class that uses the mixin
# ---------------------------------------------------------------------------


class _StubClient(DualModeClientMixin):
    """Minimal concrete class for testing the mixin."""

    def __init__(self, *, config: MadsciClientConfig | None = None) -> None:
        self.config = config or MadsciClientConfig()
        # Use a mock for the sync client so we don't open real connections
        self._client = MagicMock(spec=httpx.Client)
        self._async_client = None


# ---------------------------------------------------------------------------
# Sync _request tests
# ---------------------------------------------------------------------------


class TestSyncRequest:
    """Tests for DualModeClientMixin._request."""

    def test_delegates_to_client_request(self) -> None:
        """_request forwards method, url, and kwargs to self._client.request."""
        stub = _StubClient()
        mock_response = MagicMock(spec=httpx.Response)
        stub._client.request.return_value = mock_response

        result = stub._request("GET", "http://localhost/test", params={"a": "1"})

        stub._client.request.assert_called_once_with(
            "GET", "http://localhost/test", params={"a": "1"}
        )
        assert result is mock_response

    def test_propagates_connect_error(self) -> None:
        """_request lets httpx.ConnectError propagate."""
        stub = _StubClient()
        stub._client.request.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(httpx.ConnectError):
            stub._request("GET", "http://localhost/fail")

    def test_propagates_timeout_exception(self) -> None:
        """_request lets httpx.TimeoutException propagate."""
        stub = _StubClient()
        stub._client.request.side_effect = httpx.ReadTimeout("timed out")

        with pytest.raises(httpx.TimeoutException):
            stub._request("GET", "http://localhost/slow")

    def test_post_with_json(self) -> None:
        """_request passes json payload through."""
        stub = _StubClient()
        mock_response = MagicMock(spec=httpx.Response)
        stub._client.request.return_value = mock_response

        result = stub._request("POST", "http://localhost/data", json={"key": "value"})

        stub._client.request.assert_called_once_with(
            "POST", "http://localhost/data", json={"key": "value"}
        )
        assert result is mock_response

    def test_timeout_kwarg_forwarded(self) -> None:
        """_request forwards a timeout kwarg."""
        stub = _StubClient()
        stub._client.request.return_value = MagicMock(spec=httpx.Response)

        stub._request("GET", "http://localhost/test", timeout=42.0)

        stub._client.request.assert_called_once_with(
            "GET", "http://localhost/test", timeout=42.0
        )


# ---------------------------------------------------------------------------
# Async _async_request tests
# ---------------------------------------------------------------------------


class TestAsyncRequest:
    """Tests for DualModeClientMixin._async_request."""

    @pytest.mark.asyncio
    async def test_creates_async_client_lazily(self) -> None:
        """_async_request creates the async client on first call."""
        stub = _StubClient()
        assert stub._async_client is None

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_async_client.request.return_value = mock_response

        with patch(
            "madsci.common.http_client.create_httpx_client",
            return_value=mock_async_client,
        ) as mock_factory:
            result = await stub._async_request("GET", "http://localhost/test")

            mock_factory.assert_called_once_with(config=stub.config, async_mode=True)
            assert stub._async_client is mock_async_client
            assert result is mock_response

    @pytest.mark.asyncio
    async def test_reuses_existing_async_client(self) -> None:
        """_async_request does not recreate the async client if it already exists."""
        stub = _StubClient()
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_async_client.request.return_value = mock_response
        stub._async_client = mock_async_client

        with patch(
            "madsci.common.http_client.create_httpx_client",
        ) as mock_factory:
            await stub._async_request("GET", "http://localhost/test")
            mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_propagates_connect_error(self) -> None:
        """_async_request lets httpx.ConnectError propagate."""
        stub = _StubClient()
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.side_effect = httpx.ConnectError("connection refused")
        stub._async_client = mock_async_client

        with pytest.raises(httpx.ConnectError):
            await stub._async_request("GET", "http://localhost/fail")

    @pytest.mark.asyncio
    async def test_propagates_timeout_exception(self) -> None:
        """_async_request lets httpx.TimeoutException propagate."""
        stub = _StubClient()
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.side_effect = httpx.ReadTimeout("timed out")
        stub._async_client = mock_async_client

        with pytest.raises(httpx.TimeoutException):
            await stub._async_request("GET", "http://localhost/slow")

    @pytest.mark.asyncio
    async def test_forwards_kwargs(self) -> None:
        """_async_request forwards json, params, etc."""
        stub = _StubClient()
        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_async_client.request.return_value = mock_response
        stub._async_client = mock_async_client

        await stub._async_request(
            "POST", "http://localhost/data", json={"x": 1}, timeout=5.0
        )

        mock_async_client.request.assert_called_once_with(
            "POST", "http://localhost/data", json={"x": 1}, timeout=5.0
        )


# ---------------------------------------------------------------------------
# _ensure_async_client tests
# ---------------------------------------------------------------------------


class TestEnsureAsyncClient:
    """Tests for DualModeClientMixin._ensure_async_client."""

    def test_creates_client_when_none(self) -> None:
        """_ensure_async_client creates an async client when _async_client is None."""
        stub = _StubClient()
        assert stub._async_client is None

        mock_async_client = MagicMock(spec=httpx.AsyncClient)
        with patch(
            "madsci.common.http_client.create_httpx_client",
            return_value=mock_async_client,
        ) as mock_factory:
            result = stub._ensure_async_client()

            mock_factory.assert_called_once_with(config=stub.config, async_mode=True)
            assert result is mock_async_client
            assert stub._async_client is mock_async_client

    def test_returns_existing_client(self) -> None:
        """_ensure_async_client returns the existing client without creating a new one."""
        stub = _StubClient()
        existing = MagicMock(spec=httpx.AsyncClient)
        stub._async_client = existing

        with patch(
            "madsci.common.http_client.create_httpx_client",
        ) as mock_factory:
            result = stub._ensure_async_client()

            mock_factory.assert_not_called()
            assert result is existing


# ---------------------------------------------------------------------------
# Cleanup tests
# ---------------------------------------------------------------------------


class TestClose:
    """Tests for DualModeClientMixin.close and aclose."""

    def test_close_closes_sync_client(self) -> None:
        """close() calls _client.close()."""
        stub = _StubClient()
        mock_sync = stub._client
        stub.close()
        mock_sync.close.assert_called_once()

    def test_close_skips_async_client_when_none(self) -> None:
        """close() does not fail when _async_client is None."""
        stub = _StubClient()
        assert stub._async_client is None
        stub.close()  # Should not raise

    def test_close_closes_async_client_and_nullifies(self) -> None:
        """close() attempts async cleanup and nullifies the async client."""
        stub = _StubClient()
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        stub._async_client = mock_async

        stub.close()

        # Either the loop ran aclose() or we fell back to dropping the reference --
        # either way _async_client must be None afterward.
        assert stub._async_client is None

    def test_close_attempts_loop_run_when_no_loop_running(self) -> None:
        """close() runs aclose() via asyncio.run() when no loop is running."""
        stub = _StubClient()
        aclose_called = []

        class _FakeAsyncClient:
            async def aclose(self) -> None:
                aclose_called.append(True)

        stub._async_client = _FakeAsyncClient()

        # No running event loop in this sync test, so close() should
        # attempt to run aclose() via asyncio.run()
        stub.close()
        assert aclose_called, "aclose() should have been called via asyncio.run()"
        assert stub._async_client is None

    def test_close_sets_sync_client_to_none(self) -> None:
        """close() sets _client to None for symmetry with aclose()."""
        stub = _StubClient()
        assert stub._client is not None
        stub.close()
        assert stub._client is None

    @pytest.mark.asyncio
    async def test_close_schedules_aclose_in_running_loop(self) -> None:
        """close() schedules aclose() via loop.create_task() when inside a running loop."""
        stub = _StubClient()
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        stub._async_client = mock_async

        # We are inside a running event loop (pytest-asyncio provides one).
        # close() should schedule aclose() via create_task instead of leaking.
        stub.close()

        # The task has been scheduled but may not have run yet.
        # Give the event loop a chance to execute the scheduled task.
        await asyncio.sleep(0)

        mock_async.aclose.assert_called_once()
        assert stub._async_client is None

    def test_close_idempotent(self) -> None:
        """close() can be called multiple times without error."""
        stub = _StubClient()
        stub.close()
        stub.close()

    @pytest.mark.asyncio
    async def test_aclose_closes_sync_client(self) -> None:
        """aclose() calls _client.close() and sets it to None."""
        stub = _StubClient()
        mock_sync = stub._client
        await stub.aclose()
        mock_sync.close.assert_called_once()
        assert stub._client is None

    @pytest.mark.asyncio
    async def test_aclose_awaits_async_client_aclose(self) -> None:
        """aclose() awaits _async_client.aclose() and sets it to None."""
        stub = _StubClient()
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        stub._async_client = mock_async

        await stub.aclose()

        mock_async.aclose.assert_called_once()
        assert stub._async_client is None

    @pytest.mark.asyncio
    async def test_aclose_skips_async_when_none(self) -> None:
        """aclose() does not fail when _async_client is None."""
        stub = _StubClient()
        await stub.aclose()  # Should not raise


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------


class TestContextManagers:
    """Tests for sync and async context manager support."""

    def test_sync_context_manager(self) -> None:
        """Entering and exiting the sync context manager calls close()."""
        stub = _StubClient()
        mock_sync = stub._client

        with stub as client:
            assert client is stub

        # After exiting, _client.close() should have been called
        mock_sync.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Entering and exiting the async context manager calls aclose()."""
        stub = _StubClient()
        mock_sync = stub._client
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        stub._async_client = mock_async

        async with stub as client:
            assert client is stub

        # After exiting, both sync and async clients should be closed
        mock_sync.close.assert_called_once()
        assert stub._client is None
        mock_async.aclose.assert_called_once()
        assert stub._async_client is None

    def test_sync_context_manager_on_exception(self) -> None:
        """Sync context manager still closes on exception."""
        stub = _StubClient()
        mock_sync = stub._client

        with pytest.raises(RuntimeError, match="boom"), stub:
            raise RuntimeError("boom")

        mock_sync.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_on_exception(self) -> None:
        """Async context manager still closes on exception."""
        stub = _StubClient()
        mock_sync = stub._client
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        stub._async_client = mock_async

        with pytest.raises(RuntimeError, match="boom"):
            async with stub:
                raise RuntimeError("boom")

        mock_sync.close.assert_called_once()
        assert stub._client is None
        mock_async.aclose.assert_called_once()
        assert stub._async_client is None


# ---------------------------------------------------------------------------
# Integration-style: verify mixin does not require __init__
# ---------------------------------------------------------------------------


class TestMixinIsNotABaseClass:
    """Verify DualModeClientMixin has no __init__ and is purely a mixin."""

    def test_no_init_defined(self) -> None:
        """DualModeClientMixin should not define its own __init__."""
        assert "__init__" not in DualModeClientMixin.__dict__

    def test_works_with_multiple_inheritance(self) -> None:
        """The mixin can be combined with another base class."""

        class OtherBase:
            def __init__(self) -> None:
                self.other_attr = "hello"

        class Combined(DualModeClientMixin, OtherBase):
            def __init__(self) -> None:
                super().__init__()
                self.config = MadsciClientConfig()
                self._client = MagicMock(spec=httpx.Client)
                self._async_client = None

        obj = Combined()
        assert obj.other_attr == "hello"
        assert obj._async_client is None

        # Sync request should work
        obj._client.request.return_value = MagicMock(spec=httpx.Response)
        result = obj._request("GET", "http://localhost/test")
        assert result is not None
