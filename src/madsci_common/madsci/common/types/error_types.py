"""Service communication error types for MADSci.

Provides a hierarchy of exceptions for service-related errors,
enabling consistent error handling across CLI commands and client code.
"""

from __future__ import annotations


class MadsciServiceError(Exception):
    """Base exception for service communication errors.

    All service-related exceptions inherit from this class, making it
    easy to catch any service error with a single ``except`` clause.

    Attributes:
        service_name: Human-readable name of the target service.
        service_url: URL that was being contacted.
    """

    def __init__(self, service_name: str, service_url: str, message: str) -> None:
        """Initialise with service identification and a human-readable message."""
        self.service_name = service_name
        self.service_url = service_url
        super().__init__(f"{service_name} ({service_url}): {message}")


class ServiceUnavailableError(MadsciServiceError):
    """Service could not be reached (connection refused, DNS failure, etc.)."""


class ServiceTimeoutError(MadsciServiceError):
    """Service did not respond within the configured timeout."""


class ServiceResponseError(MadsciServiceError):
    """Service returned an error HTTP response.

    Attributes:
        status_code: HTTP status code from the response.
        response_body: Raw response body text, if available.
    """

    def __init__(
        self,
        service_name: str,
        service_url: str,
        message: str,
        status_code: int,
        response_body: str | None = None,
    ) -> None:
        """Initialise with the HTTP status code and optional response body."""
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(service_name, service_url, message)
