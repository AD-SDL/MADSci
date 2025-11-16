"""
Middleware for MADSci REST servers.

This module provides middleware for enhancing server resilience,
including rate limiting and request tracking.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications.

    This middleware tracks requests by client IP address and enforces
    rate limits based on a sliding window algorithm. When a client
    exceeds the rate limit, a 429 Too Many Requests response is returned.

    Attributes:
        requests_limit: Maximum number of requests allowed per time window
        time_window: Time window in seconds for rate limiting
        storage: Dictionary tracking request timestamps per client IP
    """

    def __init__(
        self,
        app: Callable,
        requests_limit: int = 100,
        time_window: int = 60,
    ) -> None:
        """
        Initialize the rate limiting middleware.

        Args:
            app: The ASGI application
            requests_limit: Maximum number of requests allowed per time window
            time_window: Time window in seconds for rate limiting
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.time_window = time_window
        # Storage: {client_ip: [timestamps]}
        self.storage: defaultdict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and enforce rate limiting.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The HTTP response

        Raises:
            HTTPException: 429 if rate limit is exceeded
        """
        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"

        # Get current timestamp
        now = time.time()

        # Clean up old timestamps outside the current window
        cutoff = now - self.time_window
        self.storage[client_ip] = [
            ts for ts in self.storage[client_ip] if ts > cutoff
        ]

        # Check if client has exceeded rate limit
        if len(self.storage[client_ip]) >= self.requests_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.requests_limit} requests per {self.time_window} seconds",
                headers={
                    "Retry-After": str(int(self.time_window)),
                    "X-RateLimit-Limit": str(self.requests_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(self.storage[client_ip][0] + self.time_window)),
                },
            )

        # Add current request timestamp
        self.storage[client_ip].append(now)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_limit - len(self.storage[client_ip])
        )
        if self.storage[client_ip]:
            response.headers["X-RateLimit-Reset"] = str(
                int(self.storage[client_ip][0] + self.time_window)
            )

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
