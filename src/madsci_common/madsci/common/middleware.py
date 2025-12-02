"""
Middleware for MADSci REST servers.

This module provides middleware for enhancing server resilience,
including rate limiting and request tracking.
"""

import asyncio
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications.

    This middleware tracks requests by client IP address and enforces
    rate limits based on a sliding window algorithm. When a client
    exceeds the rate limit, a 429 Too Many Requests response is returned.

    Thread-safe implementation using asyncio locks to prevent race conditions
    in concurrent request handling. Includes periodic cleanup to prevent
    memory leaks from inactive client IPs.

    Attributes:
        requests_limit: Maximum number of requests allowed per time window
        time_window: Time window in seconds for rate limiting
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
        cleanup_interval: int = 300,
    ) -> None:
        """
        Initialize the rate limiting middleware.

        Args:
            app: The ASGI application
            requests_limit: Maximum number of requests allowed per time window
            time_window: Time window in seconds for rate limiting
            cleanup_interval: Interval in seconds between cleanup operations (default: 300)
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.time_window = time_window
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

        Thread-safe implementation that uses per-client locks to prevent
        race conditions in concurrent request handling.

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

        # Use client-specific lock to ensure thread-safe access
        async with client_lock:
            # Clean up old timestamps outside the current window
            cutoff = now - self.time_window
            self.storage[client_ip] = [
                ts for ts in self.storage[client_ip] if ts > cutoff
            ]

            # Check if client has exceeded rate limit
            if len(self.storage[client_ip]) >= self.requests_limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded: {self.requests_limit} requests per {self.time_window} seconds"
                    },
                    headers={
                        "Retry-After": str(int(self.time_window)),
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
            remaining = self.requests_limit - len(self.storage[client_ip])
            reset_time = (
                int(self.storage[client_ip][0] + self.time_window)
                if self.storage[client_ip]
                else 0
            )

        # Process the request (outside the lock to avoid blocking other clients)
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request statistics.

    This middleware logs information about incoming requests and their
    processing times, which can be useful for monitoring and debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and track timing information.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The HTTP response with timing headers
        """
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        return response
