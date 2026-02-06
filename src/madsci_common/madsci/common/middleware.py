"""
Middleware for MADSci REST servers.

This module provides middleware for enhancing server resilience,
including rate limiting, request tracking, and EventClient context propagation.
"""

import asyncio
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Optional

from fastapi import Request, Response, status
from madsci.common.utils import new_ulid_str
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import EventClientContext


class _LazyEventClientContext:
    """
    A lazy context that creates the EventClient only when accessed.

    This avoids the overhead of creating an EventClient for every request,
    especially when the endpoint doesn't use logging.

    Implements the same interface as EventClientContext for compatibility
    with the context system.
    """

    def __init__(
        self,
        name: str,
        hierarchy: list,
        metadata: dict,
    ) -> None:
        """Initialize the lazy context."""
        self._name = name
        self.hierarchy = hierarchy
        self.metadata = metadata
        self._client = None

    @property
    def name(self) -> str:
        """Get the full hierarchical name."""
        return ".".join(self.hierarchy) if self.hierarchy else "madsci"

    @property
    def client(self) -> "EventClient":
        """
        Get or create the EventClient.

        The client is created lazily on first access, avoiding the overhead
        of client creation for requests that don't use logging.
        """
        if self._client is None:
            from madsci.client.event_client import EventClient  # noqa: PLC0415

            self._client = EventClient(name=self._name)
            if self.metadata:
                self._client = self._client.bind(**self.metadata)
        return self._client

    def child(
        self,
        name: str,
        client: Optional["EventClient"] = None,
        **metadata: Any,
    ) -> "EventClientContext":
        """
        Create a child context with extended hierarchy.

        This maintains compatibility with EventClientContext.child().
        """
        from madsci.common.types.event_types import EventClientContext  # noqa: PLC0415

        merged_metadata = {**self.metadata, **metadata}

        if client is not None:
            child_client = client
        else:
            # Create bound child from this context's client
            child_client = self.client.bind(**metadata) if metadata else self.client

        return EventClientContext(
            client=child_client,
            hierarchy=[*self.hierarchy, name],
            metadata=merged_metadata,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications.

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
    """

    def __init__(
        self,
        app: Callable,
        requests_limit: int = 100,
        time_window: int = 60,
        short_requests_limit: Optional[int] = None,
        short_time_window: Optional[int] = None,
        cleanup_interval: int = 300,
        exempt_ips: Optional[set[str]] = None,
    ) -> None:
        """
        Initialize the rate limiting middleware.

        Args:
            app: The ASGI application
            requests_limit: Maximum number of requests allowed per long time window
            time_window: Long time window in seconds for rate limiting
            short_requests_limit: Maximum number of requests per short window (optional, for burst protection)
            short_time_window: Short time window in seconds (optional, typically 1 second)
            cleanup_interval: Interval in seconds between cleanup operations (default: 300)
            exempt_ips: Set of IP addresses exempt from rate limiting (default: localhost IPs)
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.time_window = time_window
        self.short_requests_limit = short_requests_limit
        self.short_time_window = short_time_window
        self.cleanup_interval = cleanup_interval
        # Default to exempting localhost if not specified
        self.exempt_ips = exempt_ips if exempt_ips is not None else {"127.0.0.1", "::1"}
        # Storage maps client IP addresses to lists of request timestamps
        self.storage: defaultdict[str, list[float]] = defaultdict(list)
        # Per-client locks for thread-safe access
        self.locks: dict[str, asyncio.Lock] = {}
        # Global lock for managing the locks dictionary (created lazily in async context)
        self._global_lock: Optional[asyncio.Lock] = None
        # Track last cleanup time
        self.last_cleanup = time.time()

    def _get_or_create_global_lock(self) -> asyncio.Lock:
        """
        Get or create the global lock.

        Must be called from an async context where an event loop is running.
        The lock is created lazily on first access to avoid requiring an
        event loop during __init__.

        Returns:
            asyncio.Lock: The global lock for managing the locks dictionary
        """
        if self._global_lock is None:
            self._global_lock = asyncio.Lock()
        return self._global_lock

    async def _get_client_lock(self, client_ip: str) -> asyncio.Lock:
        """
        Get or create a lock for a specific client IP.

        Args:
            client_ip: The client IP address

        Returns:
            asyncio.Lock: The lock for this client
        """
        # Use global lock to safely manage the locks dictionary
        async with self._get_or_create_global_lock():
            if client_ip not in self.locks:
                self.locks[client_ip] = asyncio.Lock()
            return self.locks[client_ip]

    async def _cleanup_inactive_clients(self, now: float) -> None:
        """
        Remove inactive client IPs from storage to prevent memory leaks.

        This method removes clients whose last request was more than
        time_window seconds ago, as they no longer need rate limiting tracking.

        Args:
            now: Current timestamp
        """
        async with self._get_or_create_global_lock():
            cutoff = now - self.time_window
            inactive_clients = [
                client_ip
                for client_ip, timestamps in self.storage.items()
                if not timestamps or timestamps[-1] < cutoff
            ]

            for client_ip in inactive_clients:
                del self.storage[client_ip]
                if client_ip in self.locks:
                    del self.locks[client_ip]

            self.last_cleanup = now

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and enforce rate limiting.

        Async-safe implementation that uses per-client locks to prevent
        race conditions in concurrent request handling.

        For dual rate limiting, both short and long window limits must be
        satisfied for a request to proceed.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The HTTP response (429 if rate limit is exceeded)
        """
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limiting for exempt IPs (e.g., localhost)
        if client_ip in self.exempt_ips:
            return await call_next(request)

        # Get current timestamp
        now = time.time()

        # Perform periodic cleanup to prevent memory leaks
        if now - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_inactive_clients(now)

        # Get the lock for this client IP
        client_lock = await self._get_client_lock(client_ip)

        # Use client-specific lock to ensure async-safe access
        async with client_lock:
            # Clean up old timestamps outside the longest window
            cutoff = now - self.time_window
            self.storage[client_ip] = [
                ts for ts in self.storage[client_ip] if ts > cutoff
            ]

            # Check short window limit (burst protection) if configured
            if (
                self.short_requests_limit is not None
                and self.short_time_window is not None
            ):
                short_cutoff = now - self.short_time_window
                short_window_requests = [
                    ts for ts in self.storage[client_ip] if ts > short_cutoff
                ]

                if len(short_window_requests) >= self.short_requests_limit:
                    # Calculate when the oldest request in short window will expire
                    retry_after = (
                        int(short_window_requests[0] + self.short_time_window - now) + 1
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": f"Rate limit exceeded: {self.short_requests_limit} requests per {self.short_time_window} seconds (burst limit)"
                        },
                        headers={
                            "Retry-After": str(max(1, retry_after)),
                            "X-RateLimit-Limit": str(self.requests_limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(
                                int(self.storage[client_ip][0] + self.time_window)
                                if self.storage[client_ip]
                                else int(now + self.time_window)
                            ),
                            "X-RateLimit-Burst-Limit": str(self.short_requests_limit),
                            "X-RateLimit-Burst-Remaining": "0",
                        },
                    )

            # Check long window limit (sustained load protection)
            if len(self.storage[client_ip]) >= self.requests_limit:
                # Calculate when the oldest request in long window will expire
                retry_after = (
                    int(self.storage[client_ip][0] + self.time_window - now) + 1
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded: {self.requests_limit} requests per {self.time_window} seconds"
                    },
                    headers={
                        "Retry-After": str(max(1, retry_after)),
                        "X-RateLimit-Limit": str(self.requests_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(
                            int(self.storage[client_ip][0] + self.time_window)
                        ),
                    },
                )

            # Add current request timestamp
            self.storage[client_ip].append(now)

            # Calculate remaining requests while still holding the lock
            long_remaining = self.requests_limit - len(self.storage[client_ip])
            reset_time = (
                int(self.storage[client_ip][0] + self.time_window)
                if self.storage[client_ip]
                else 0
            )

            # Calculate short window remaining if configured
            short_remaining = None
            if (
                self.short_requests_limit is not None
                and self.short_time_window is not None
            ):
                short_cutoff = now - self.short_time_window
                short_count = sum(
                    1 for ts in self.storage[client_ip] if ts > short_cutoff
                )
                short_remaining = self.short_requests_limit - short_count

        # Process the request (outside the lock to avoid blocking other clients)
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(long_remaining)
        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(reset_time)

        # Add burst limit headers if configured
        if short_remaining is not None:
            response.headers["X-RateLimit-Burst-Limit"] = str(self.short_requests_limit)
            response.headers["X-RateLimit-Burst-Remaining"] = str(short_remaining)

        return response


class EventClientContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that establishes EventClient context for each request.

    This enables hierarchical logging where all logs within a request
    share common context (request_id, path, method, etc.).

    When combined with manager-level context, this creates a hierarchy like:
    manager.resource_manager -> request.GET./resources -> [endpoint handlers]

    Attributes:
        manager_name: The name of the manager to include in context.

    Note:
        The context is stored in request.state to ensure propagation to
        endpoint handlers, as Python's contextvars don't always propagate
        correctly across Starlette's middleware async boundaries.
    """

    def __init__(
        self,
        app: Callable,
        manager_name: str = "manager",
    ) -> None:
        """
        Initialize the EventClient context middleware.

        Args:
            app: The ASGI application
            manager_name: The name of the manager to include in context
        """
        super().__init__(app)
        self.manager_name = manager_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request within an EventClient context.

        Establishes context with:
        - request_id: From X-Request-ID header or generated ULID
        - http_method: The HTTP method (GET, POST, etc.)
        - http_path: The request path
        - manager: The manager name

        The context is established using Python's contextvars. The EventClient
        is created lazily when first accessed via get_event_client().

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The HTTP response
        """
        from madsci.common.context import (  # noqa: PLC0415
            _event_client_context,
        )

        # Get request ID from header or generate a new one
        request_id = request.headers.get("X-Request-ID") or new_ulid_str()

        # Build a context name based on the request
        context_name = f"request.{request.method}.{request.url.path}"

        context_metadata = {
            "request_id": request_id,
            "http_method": request.method,
            "http_path": str(request.url.path),
            "manager": self.manager_name,
        }

        # Create a lazy context that will create the EventClient when first accessed
        # We use a special "lazy" context that defers client creation
        ctx = _LazyEventClientContext(
            name=context_name,
            hierarchy=[context_name],
            metadata=context_metadata,
        )

        # Set context manually to ensure it propagates
        # Note: We use type: ignore because _LazyEventClientContext is duck-typed
        # to be compatible with EventClientContext
        token = _event_client_context.set(ctx)  # type: ignore[arg-type]
        try:
            return await call_next(request)
        finally:
            _event_client_context.reset(token)
