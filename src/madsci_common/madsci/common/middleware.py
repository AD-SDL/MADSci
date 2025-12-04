"""
Middleware for MADSci REST servers.

This module provides middleware for enhancing server resilience,
including rate limiting and request tracking.
"""

import asyncio
import time
from collections import defaultdict
from typing import Callable, Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


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
        storage: Dictionary tracking request timestamps per client IP
        locks: Dictionary of locks for thread-safe access per client IP
        global_lock: Lock for managing the locks dictionary itself
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
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.time_window = time_window
        self.short_requests_limit = short_requests_limit
        self.short_time_window = short_time_window
        self.cleanup_interval = cleanup_interval
        # Storage maps client IP addresses to lists of request timestamps
        self.storage: defaultdict[str, list[float]] = defaultdict(list)
        # Per-client locks for thread-safe access
        self.locks: dict[str, asyncio.Lock] = {}
        # Global lock for managing the locks dictionary
        self.global_lock = asyncio.Lock()
        # Track last cleanup time
        self.last_cleanup = time.time()

    async def _get_client_lock(self, client_ip: str) -> asyncio.Lock:
        """
        Get or create a lock for a specific client IP.

        Args:
            client_ip: The client IP address

        Returns:
            asyncio.Lock: The lock for this client
        """
        # Use global lock to safely manage the locks dictionary
        async with self.global_lock:
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
        async with self.global_lock:
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
