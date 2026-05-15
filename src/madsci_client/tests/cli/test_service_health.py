"""Tests for madsci.client.cli.utils.service_health."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from madsci.client.cli.utils.service_health import (
    DEFAULT_SERVICE_URLS,
    ServiceHealthResult,
    check_all_services_async,
    check_service_health_async,
    check_service_health_sync,
    get_default_service_urls,
)

# ---------------------------------------------------------------------------
# ServiceHealthResult
# ---------------------------------------------------------------------------


class TestServiceHealthResult:
    """Tests for the ServiceHealthResult dataclass."""

    def test_defaults(self) -> None:
        result = ServiceHealthResult(name="svc", url="http://x/", is_available=True)
        assert result.version is None
        assert result.error is None
        assert result.response_time_ms is None

    def test_full_construction(self) -> None:
        result = ServiceHealthResult(
            name="event",
            url="http://localhost:8001/",
            is_available=True,
            version="1.2.3",
            response_time_ms=42.5,
        )
        assert result.name == "event"
        assert result.is_available is True
        assert result.version == "1.2.3"


# ---------------------------------------------------------------------------
# Synchronous health check
# ---------------------------------------------------------------------------


class TestCheckServiceHealthSync:
    """Tests for check_service_health_sync()."""

    def test_healthy_service(self) -> None:
        mock_response = httpx.Response(
            200,
            json={"version": "1.0.0"},
            request=httpx.Request("GET", "http://localhost:8001/health"),
        )
        with patch(
            "madsci.client.cli.utils.service_health.httpx.Client"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response

            result = check_service_health_sync("event", "http://localhost:8001/")

        assert result.is_available is True
        assert result.version == "1.0.0"
        assert result.error is None
        assert result.response_time_ms is not None

    def test_unhealthy_service(self) -> None:
        mock_response = httpx.Response(
            503,
            text="Service Unavailable",
            request=httpx.Request("GET", "http://localhost:8001/health"),
        )
        with patch(
            "madsci.client.cli.utils.service_health.httpx.Client"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.return_value = mock_response

            result = check_service_health_sync("event", "http://localhost:8001/")

        assert result.is_available is False
        assert "503" in result.error

    def test_connection_refused(self) -> None:
        with patch(
            "madsci.client.cli.utils.service_health.httpx.Client"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.side_effect = httpx.ConnectError("refused")

            result = check_service_health_sync("event", "http://localhost:8001/")

        assert result.is_available is False
        assert result.error == "Connection refused"

    def test_timeout(self) -> None:
        with patch(
            "madsci.client.cli.utils.service_health.httpx.Client"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.side_effect = httpx.TimeoutException("timed out")

            result = check_service_health_sync("event", "http://localhost:8001/")

        assert result.is_available is False
        assert result.error == "Timeout"

    def test_unexpected_error(self) -> None:
        with patch(
            "madsci.client.cli.utils.service_health.httpx.Client"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.get.side_effect = RuntimeError("surprise")

            result = check_service_health_sync("event", "http://localhost:8001/")

        assert result.is_available is False
        assert "surprise" in result.error


# ---------------------------------------------------------------------------
# Asynchronous health check
# ---------------------------------------------------------------------------


class TestCheckServiceHealthAsync:
    """Tests for check_service_health_async()."""

    @pytest.mark.asyncio
    async def test_healthy_service(self) -> None:
        mock_response = httpx.Response(
            200,
            json={"version": "2.0.0"},
            request=httpx.Request("GET", "http://localhost:8001/health"),
        )
        with patch(
            "madsci.client.cli.utils.service_health.httpx.AsyncClient"
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await check_service_health_async("event", "http://localhost:8001/")

        assert result.is_available is True
        assert result.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_connection_refused(self) -> None:
        with patch(
            "madsci.client.cli.utils.service_health.httpx.AsyncClient"
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("refused")

            result = await check_service_health_async("event", "http://localhost:8001/")

        assert result.is_available is False
        assert result.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        with patch(
            "madsci.client.cli.utils.service_health.httpx.AsyncClient"
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("timeout")

            result = await check_service_health_async("event", "http://localhost:8001/")

        assert result.is_available is False
        assert result.error == "Timeout"


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


class TestCheckAllServicesAsync:
    """Tests for check_all_services_async()."""

    @pytest.mark.asyncio
    async def test_checks_all_services(self) -> None:
        urls = {"svc_a": "http://a:8000/", "svc_b": "http://b:8001/"}

        async def fake_check(
            name: str,
            url: str,
            timeout: float = 5.0,  # noqa: ARG001
        ) -> ServiceHealthResult:
            return ServiceHealthResult(name=name, url=url, is_available=True)

        with patch(
            "madsci.client.cli.utils.service_health.check_service_health_async",
            side_effect=fake_check,
        ):
            results = await check_all_services_async(urls)

        assert len(results) == 2
        assert results["svc_a"].is_available is True
        assert results["svc_b"].is_available is True


# ---------------------------------------------------------------------------
# Default service URLs
# ---------------------------------------------------------------------------


class TestGetDefaultServiceUrls:
    """Tests for get_default_service_urls()."""

    def test_returns_dict(self) -> None:
        urls = get_default_service_urls()
        assert isinstance(urls, dict)
        assert "lab_manager" in urls or "event_manager" in urls

    def test_default_fallback(self) -> None:
        with patch(
            "madsci.client.cli.tui.constants.get_default_services",
            side_effect=Exception("boom"),
        ):
            urls = get_default_service_urls()
        assert urls == DEFAULT_SERVICE_URLS
