Module madsci.common.middleware
===============================
Middleware for MADSci REST servers.

This module provides middleware for enhancing server resilience,
including rate limiting and request tracking.

Classes
-------

`RateLimitMiddleware(app: Callable, requests_limit: int = 100, time_window: int = 60, short_requests_limit: int | None = None, short_time_window: int | None = None, cleanup_interval: int = 300, exempt_ips: set[str] | None = None)`
:   Rate limiting middleware for FastAPI applications.

    This middleware tracks requests by client IP address and enforces
    rate limits based on a sliding window algorithm. When a client
    exceeds the rate limit, a 429 Too Many Requests response is returned.

    Supports dual rate limiting with both short (burst) and long (sustained)
    windows. Both limits must be satisfied for a request to proceed.

    Async-safe implementation using asyncio locks to prevent race conditions
    in concurrent coroutine handling. Includes periodic cleanup to prevent
    memory leaks from inactive client IPs.

    Attributes:
        requests_limit: Maximum number of requests allowed per long time window
        time_window: Long time window in seconds for rate limiting
        short_requests_limit: Maximum number of requests allowed per short time window (optional)
        short_time_window: Short time window in seconds for burst protection (optional)
        exempt_ips: Set of IP addresses exempt from rate limiting (defaults to localhost)
        storage: Dictionary tracking request timestamps per client IP
        locks: Dictionary of locks for thread-safe access per client IP
        _global_lock: Lock for managing the locks dictionary itself (created lazily)
        cleanup_interval: Interval in seconds between cleanup operations
        last_cleanup: Timestamp of last cleanup operation

    Initialize the rate limiting middleware.

    Args:
        app: The ASGI application
        requests_limit: Maximum number of requests allowed per long time window
        time_window: Long time window in seconds for rate limiting
        short_requests_limit: Maximum number of requests per short window (optional, for burst protection)
        short_time_window: Short time window in seconds (optional, typically 1 second)
        cleanup_interval: Interval in seconds between cleanup operations (default: 300)
        exempt_ips: Set of IP addresses exempt from rate limiting (default: localhost IPs)

    ### Ancestors (in MRO)

    * starlette.middleware.base.BaseHTTPMiddleware

    ### Methods

    `dispatch(self, request: starlette.requests.Request, call_next: Callable) ‑> starlette.responses.Response`
    :   Process each request and enforce rate limiting.

        Async-safe implementation that uses per-client locks to prevent
        race conditions in concurrent request handling.

        For dual rate limiting, both short and long window limits must be
        satisfied for a request to proceed.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The HTTP response (429 if rate limit is exceeded)
