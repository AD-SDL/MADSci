"""Tests for LabClient with httpx / DualModeClientMixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from madsci.client.http import DualModeClientMixin
from madsci.client.lab_client import LabClient
from madsci.common.types.client_types import LabClientConfig
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabHealth
from madsci.common.types.manager_types import ManagerHealth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lab_client(url: str = "http://localhost:8000/") -> LabClient:
    """Create a LabClient with a mock httpx client, bypassing context lookup."""
    with (
        patch(
            "madsci.client.lab_client.get_current_madsci_context",
        ),
        patch(
            "madsci.client.lab_client.create_httpx_client",
            return_value=MagicMock(spec=httpx.Client),
        ),
    ):
        return LabClient(lab_server_url=url)


def _mock_json_response(data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with the given JSON data."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = status_code < 400
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


def _mock_error_response(status_code: int = 500) -> MagicMock:
    """Create a mock httpx.Response that raises on raise_for_status."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = False
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error",
        request=MagicMock(spec=httpx.Request),
        response=resp,
    )
    return resp


# ---------------------------------------------------------------------------
# Minimal context / health payloads for model_validate
# ---------------------------------------------------------------------------

_CONTEXT_PAYLOAD = {
    "lab_name": "test-lab",
}

_MANAGER_HEALTH_PAYLOAD = {
    "manager_type": "lab",
    "status": "ok",
}

_LAB_HEALTH_PAYLOAD = {
    "lab_name": "test-lab",
}


# ---------------------------------------------------------------------------
# Class: construction and mixin integration
# ---------------------------------------------------------------------------


class TestLabClientConstruction:
    """Tests for LabClient.__init__ and class hierarchy."""

    def test_inherits_dual_mode_mixin(self) -> None:
        """LabClient should inherit from DualModeClientMixin."""
        assert issubclass(LabClient, DualModeClientMixin)

    def test_creates_httpx_client(self) -> None:
        """__init__ should create an httpx.Client via create_httpx_client."""
        with (
            patch(
                "madsci.client.lab_client.get_current_madsci_context",
            ),
            patch(
                "madsci.client.lab_client.create_httpx_client",
            ) as mock_factory,
        ):
            mock_factory.return_value = MagicMock(spec=httpx.Client)
            client = LabClient(lab_server_url="http://localhost:8000/")
            mock_factory.assert_called_once()
            assert client._client is mock_factory.return_value
            assert client._async_client is None

    def test_accepts_custom_config(self) -> None:
        """__init__ should accept a custom LabClientConfig."""
        custom_config = LabClientConfig(timeout_default=99.0)
        with (
            patch(
                "madsci.client.lab_client.get_current_madsci_context",
            ),
            patch(
                "madsci.client.lab_client.create_httpx_client",
                return_value=MagicMock(spec=httpx.Client),
            ),
        ):
            client = LabClient(
                lab_server_url="http://localhost:8000/",
                config=custom_config,
            )
            assert client.config is custom_config
            assert client.config.timeout_default == 99.0

    def test_session_property_returns_client(self) -> None:
        """The backward-compat session property should return self._client."""
        client = _make_lab_client()
        assert client.session is client._client

    def test_raises_without_url_or_context(self) -> None:
        """__init__ should raise ValueError when no URL is available."""
        mock_context = MagicMock()
        mock_context.lab_server_url = None
        with (
            patch(
                "madsci.client.lab_client.get_current_madsci_context",
                return_value=mock_context,
            ),
            patch(
                "madsci.client.lab_client.create_httpx_client",
                return_value=MagicMock(spec=httpx.Client),
            ),
            pytest.raises(ValueError, match="No lab server URL"),
        ):
            LabClient()

    def test_context_manager_support(self) -> None:
        """LabClient should support sync context manager via the mixin."""
        client = _make_lab_client()
        with client as c:
            assert c is client
        # close should have been called on _client
        client._client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Sync methods
# ---------------------------------------------------------------------------


class TestSyncGetLabContext:
    """Tests for LabClient.get_lab_context (sync)."""

    def test_calls_request_with_correct_url(self) -> None:
        """get_lab_context should call _request with the context endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_CONTEXT_PAYLOAD)
        client._client.request.return_value = response

        client.get_lab_context()

        client._client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/context",
            timeout=client.config.timeout_default,
        )

    def test_returns_madsci_context(self) -> None:
        """get_lab_context should return a MadsciContext instance."""
        client = _make_lab_client()
        response = _mock_json_response(_CONTEXT_PAYLOAD)
        client._client.request.return_value = response

        result = client.get_lab_context()

        assert isinstance(result, MadsciContext)

    def test_uses_custom_timeout(self) -> None:
        """get_lab_context should use the provided timeout override."""
        client = _make_lab_client()
        response = _mock_json_response(_CONTEXT_PAYLOAD)
        client._client.request.return_value = response

        client.get_lab_context(timeout=42.0)

        _, kwargs = client._client.request.call_args
        assert kwargs["timeout"] == 42.0

    def test_raises_on_error(self) -> None:
        """get_lab_context should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(500)
        client._client.request.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            client.get_lab_context()


class TestSyncGetManagerHealth:
    """Tests for LabClient.get_manager_health (sync)."""

    def test_calls_request_with_correct_url(self) -> None:
        """get_manager_health should call _request with the health endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_MANAGER_HEALTH_PAYLOAD)
        client._client.request.return_value = response

        client.get_manager_health()

        client._client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/health",
            timeout=client.config.timeout_default,
        )

    def test_returns_manager_health(self) -> None:
        """get_manager_health should return a ManagerHealth instance."""
        client = _make_lab_client()
        response = _mock_json_response(_MANAGER_HEALTH_PAYLOAD)
        client._client.request.return_value = response

        result = client.get_manager_health()

        assert isinstance(result, ManagerHealth)

    def test_raises_on_error(self) -> None:
        """get_manager_health should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(503)
        client._client.request.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            client.get_manager_health()


class TestSyncGetLabHealth:
    """Tests for LabClient.get_lab_health (sync)."""

    def test_calls_request_with_correct_url(self) -> None:
        """get_lab_health should call _request with the lab_health endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_LAB_HEALTH_PAYLOAD)
        client._client.request.return_value = response

        client.get_lab_health()

        client._client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/lab_health",
            timeout=client.config.timeout_default,
        )

    def test_returns_lab_health(self) -> None:
        """get_lab_health should return a LabHealth instance."""
        client = _make_lab_client()
        response = _mock_json_response(_LAB_HEALTH_PAYLOAD)
        client._client.request.return_value = response

        result = client.get_lab_health()

        assert isinstance(result, LabHealth)

    def test_raises_on_error(self) -> None:
        """get_lab_health should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(404)
        client._client.request.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            client.get_lab_health()


# ---------------------------------------------------------------------------
# Async methods
# ---------------------------------------------------------------------------


class TestAsyncGetLabContext:
    """Tests for LabClient.async_get_lab_context."""

    @pytest.mark.asyncio
    async def test_calls_async_request_with_correct_url(self) -> None:
        """async_get_lab_context should call _async_request with the context endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_CONTEXT_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        await client.async_get_lab_context()

        mock_async_client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/context",
            timeout=client.config.timeout_default,
        )

    @pytest.mark.asyncio
    async def test_returns_madsci_context(self) -> None:
        """async_get_lab_context should return a MadsciContext instance."""
        client = _make_lab_client()
        response = _mock_json_response(_CONTEXT_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        result = await client.async_get_lab_context()

        assert isinstance(result, MadsciContext)

    @pytest.mark.asyncio
    async def test_uses_custom_timeout(self) -> None:
        """async_get_lab_context should use the provided timeout override."""
        client = _make_lab_client()
        response = _mock_json_response(_CONTEXT_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        await client.async_get_lab_context(timeout=42.0)

        _, kwargs = mock_async_client.request.call_args
        assert kwargs["timeout"] == 42.0

    @pytest.mark.asyncio
    async def test_raises_on_error(self) -> None:
        """async_get_lab_context should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(500)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        with pytest.raises(httpx.HTTPStatusError):
            await client.async_get_lab_context()


class TestAsyncGetManagerHealth:
    """Tests for LabClient.async_get_manager_health."""

    @pytest.mark.asyncio
    async def test_calls_async_request_with_correct_url(self) -> None:
        """async_get_manager_health should call _async_request with the health endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_MANAGER_HEALTH_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        await client.async_get_manager_health()

        mock_async_client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/health",
            timeout=client.config.timeout_default,
        )

    @pytest.mark.asyncio
    async def test_returns_manager_health(self) -> None:
        """async_get_manager_health should return a ManagerHealth instance."""
        client = _make_lab_client()
        response = _mock_json_response(_MANAGER_HEALTH_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        result = await client.async_get_manager_health()

        assert isinstance(result, ManagerHealth)

    @pytest.mark.asyncio
    async def test_raises_on_error(self) -> None:
        """async_get_manager_health should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(503)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        with pytest.raises(httpx.HTTPStatusError):
            await client.async_get_manager_health()


class TestAsyncGetLabHealth:
    """Tests for LabClient.async_get_lab_health."""

    @pytest.mark.asyncio
    async def test_calls_async_request_with_correct_url(self) -> None:
        """async_get_lab_health should call _async_request with the lab_health endpoint."""
        client = _make_lab_client("http://localhost:8000/")
        response = _mock_json_response(_LAB_HEALTH_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        await client.async_get_lab_health()

        mock_async_client.request.assert_called_once_with(
            "GET",
            "http://localhost:8000/lab_health",
            timeout=client.config.timeout_default,
        )

    @pytest.mark.asyncio
    async def test_returns_lab_health(self) -> None:
        """async_get_lab_health should return a LabHealth instance."""
        client = _make_lab_client()
        response = _mock_json_response(_LAB_HEALTH_PAYLOAD)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        result = await client.async_get_lab_health()

        assert isinstance(result, LabHealth)

    @pytest.mark.asyncio
    async def test_raises_on_error(self) -> None:
        """async_get_lab_health should raise on HTTP error status."""
        client = _make_lab_client()
        response = _mock_error_response(404)

        mock_async_client = AsyncMock(spec=httpx.AsyncClient)
        mock_async_client.request.return_value = response
        client._async_client = mock_async_client

        with pytest.raises(httpx.HTTPStatusError):
            await client.async_get_lab_health()


# ---------------------------------------------------------------------------
# Close / cleanup
# ---------------------------------------------------------------------------


class TestLabClientCleanup:
    """Tests for LabClient cleanup via the mixin."""

    def test_close_closes_httpx_client(self) -> None:
        """close() should close the underlying httpx client."""
        client = _make_lab_client()
        client.close()
        client._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_closes_both_clients(self) -> None:
        """aclose() should close both sync and async clients."""
        client = _make_lab_client()
        mock_sync = client._client
        mock_async = AsyncMock(spec=httpx.AsyncClient)
        client._async_client = mock_async

        await client.aclose()

        mock_sync.close.assert_called_once()
        assert client._client is None
        mock_async.aclose.assert_called_once()
        assert client._async_client is None
