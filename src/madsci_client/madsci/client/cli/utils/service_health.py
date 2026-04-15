"""Unified service health checking for CLI and TUI.

Provides both synchronous and asynchronous health-check helpers so that
CLI commands (sync) and TUI widgets (async) can share the same logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

# ---------------------------------------------------------------------------
# Default service URLs (mirrors TUI constants but lives in the shared utils
# layer so CLI commands can use it without importing TUI code).
# ---------------------------------------------------------------------------

DEFAULT_SERVICE_URLS: dict[str, str] = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ServiceHealthResult:
    """Result of a single service health check.

    Attributes:
        name: Service display name.
        url: Base URL that was checked.
        is_available: ``True`` when the service responded with HTTP 200 on ``/health``.
        version: Version string extracted from the health response, if present.
        error: Human-readable error description, if the check failed.
        response_time_ms: Round-trip time of the health request in milliseconds.
    """

    name: str
    url: str
    is_available: bool
    version: str | None = None
    error: str | None = None
    response_time_ms: float | None = None


# ---------------------------------------------------------------------------
# Synchronous health check (for CLI commands)
# ---------------------------------------------------------------------------


def check_service_health_sync(
    name: str,
    url: str,
    timeout: float = 5.0,
) -> ServiceHealthResult:
    """Perform a synchronous health check against a service's ``/health`` endpoint.

    Args:
        name: Display name of the service.
        url: Base URL of the service (trailing slash optional).
        timeout: Request timeout in seconds.

    Returns:
        :class:`ServiceHealthResult` describing the outcome.
    """
    health_url = url.rstrip("/") + "/health"
    start = time.monotonic()

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(health_url)
        elapsed_ms = (time.monotonic() - start) * 1000

        if response.status_code == 200:
            data = response.json() if response.text else {}
            return ServiceHealthResult(
                name=name,
                url=url,
                is_available=True,
                version=data.get("version"),
                response_time_ms=elapsed_ms,
            )
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error=f"HTTP {response.status_code}",
            response_time_ms=elapsed_ms,
        )

    except httpx.ConnectError:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error="Connection refused",
            response_time_ms=elapsed_ms,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error="Timeout",
            response_time_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error=str(exc),
            response_time_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Asynchronous health check (for TUI widgets)
# ---------------------------------------------------------------------------


async def check_service_health_async(
    name: str,
    url: str,
    timeout: float = 5.0,
) -> ServiceHealthResult:
    """Perform an asynchronous health check against ``/health``.

    Args:
        name: Display name of the service.
        url: Base URL of the service.
        timeout: Request timeout in seconds.

    Returns:
        :class:`ServiceHealthResult` describing the outcome.
    """
    health_url = url.rstrip("/") + "/health"
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)
        elapsed_ms = (time.monotonic() - start) * 1000

        if response.status_code == 200:
            data = response.json() if response.text else {}
            return ServiceHealthResult(
                name=name,
                url=url,
                is_available=True,
                version=data.get("version"),
                response_time_ms=elapsed_ms,
            )
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error=f"HTTP {response.status_code}",
            response_time_ms=elapsed_ms,
        )

    except httpx.ConnectError:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error="Connection refused",
            response_time_ms=elapsed_ms,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error="Timeout",
            response_time_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ServiceHealthResult(
            name=name,
            url=url,
            is_available=False,
            error=str(exc),
            response_time_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Batch / concurrent helpers
# ---------------------------------------------------------------------------


async def check_all_services_async(
    service_urls: dict[str, str],
    timeout: float = 5.0,
) -> dict[str, ServiceHealthResult]:
    """Check all services concurrently and return the results.

    Args:
        service_urls: Mapping of service name to base URL.
        timeout: Per-request timeout in seconds.

    Returns:
        Mapping of service name to :class:`ServiceHealthResult`.
    """
    import asyncio

    names = list(service_urls.keys())
    coros = [
        check_service_health_async(name, service_urls[name], timeout=timeout)
        for name in names
    ]
    results_list = await asyncio.gather(*coros)
    return dict(zip(names, results_list, strict=True))


def get_default_service_urls() -> dict[str, str]:
    """Get the default service URL mapping.

    Attempts to read URLs from the global :class:`MadsciContext` when
    available; falls back to :data:`DEFAULT_SERVICE_URLS`.

    Returns:
        Mapping of service name to base URL.
    """
    try:
        from madsci.client.cli.tui.constants import get_default_services

        return get_default_services()
    except Exception:
        return dict(DEFAULT_SERVICE_URLS)
