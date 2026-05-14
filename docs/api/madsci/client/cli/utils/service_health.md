Module madsci.client.cli.utils.service_health
=============================================
Unified service health checking for CLI and TUI.

Provides both synchronous and asynchronous health-check helpers so that
CLI commands (sync) and TUI widgets (async) can share the same logic.

Functions
---------

`check_all_services_async(service_urls: dict[str, str], timeout: float = 5.0) ‑> dict[str, madsci.client.cli.utils.service_health.ServiceHealthResult]`
:   Check all services concurrently and return the results.
    
    Args:
        service_urls: Mapping of service name to base URL.
        timeout: Per-request timeout in seconds.
    
    Returns:
        Mapping of service name to :class:`ServiceHealthResult`.

`check_service_health_async(name: str, url: str, timeout: float = 5.0) ‑> madsci.client.cli.utils.service_health.ServiceHealthResult`
:   Perform an asynchronous health check against ``/health``.
    
    Args:
        name: Display name of the service.
        url: Base URL of the service.
        timeout: Request timeout in seconds.
    
    Returns:
        :class:`ServiceHealthResult` describing the outcome.

`check_service_health_sync(name: str, url: str, timeout: float = 5.0) ‑> madsci.client.cli.utils.service_health.ServiceHealthResult`
:   Perform a synchronous health check against a service's ``/health`` endpoint.
    
    Args:
        name: Display name of the service.
        url: Base URL of the service (trailing slash optional).
        timeout: Request timeout in seconds.
    
    Returns:
        :class:`ServiceHealthResult` describing the outcome.

`get_default_service_urls() ‑> dict[str, str]`
:   Get the default service URL mapping.
    
    Attempts to read URLs from the global :class:`MadsciContext` when
    available; falls back to :data:`DEFAULT_SERVICE_URLS`.
    
    Returns:
        Mapping of service name to base URL.

Classes
-------

`ServiceHealthResult(name: str, url: str, is_available: bool, version: str | None = None, error: str | None = None, response_time_ms: float | None = None)`
:   Result of a single service health check.
    
    Attributes:
        name: Service display name.
        url: Base URL that was checked.
        is_available: ``True`` when the service responded with HTTP 200 on ``/health``.
        version: Version string extracted from the health response, if present.
        error: Human-readable error description, if the check failed.
        response_time_ms: Round-trip time of the health request in milliseconds.

    ### Instance variables

    `error: str | None`
    :

    `is_available: bool`
    :

    `name: str`
    :

    `response_time_ms: float | None`
    :

    `url: str`
    :

    `version: str | None`
    :