"""Tests for madsci.common.types.error_types."""

from __future__ import annotations

from madsci.common.types.error_types import (
    MadsciServiceError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)


class TestMadsciServiceError:
    """Tests for the base MadsciServiceError exception."""

    def test_attributes(self) -> None:
        exc = MadsciServiceError("event_manager", "http://localhost:8001/", "boom")
        assert exc.service_name == "event_manager"
        assert exc.service_url == "http://localhost:8001/"
        assert "event_manager" in str(exc)
        assert "http://localhost:8001/" in str(exc)
        assert "boom" in str(exc)

    def test_is_exception(self) -> None:
        exc = MadsciServiceError("svc", "http://x/", "msg")
        assert isinstance(exc, Exception)

    def test_catchable_as_base(self) -> None:
        """All subclasses can be caught as MadsciServiceError."""
        for cls in (ServiceUnavailableError, ServiceTimeoutError, ServiceResponseError):
            if cls is ServiceResponseError:
                exc = cls("svc", "http://x/", "msg", status_code=500)
            else:
                exc = cls("svc", "http://x/", "msg")
            assert isinstance(exc, MadsciServiceError)


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError."""

    def test_message(self) -> None:
        exc = ServiceUnavailableError("lab", "http://localhost:8000/", "refused")
        assert "refused" in str(exc)

    def test_inherits_base(self) -> None:
        exc = ServiceUnavailableError("lab", "http://localhost:8000/", "refused")
        assert isinstance(exc, MadsciServiceError)


class TestServiceTimeoutError:
    """Tests for ServiceTimeoutError."""

    def test_message(self) -> None:
        exc = ServiceTimeoutError("data", "http://localhost:8004/", "timed out")
        assert "timed out" in str(exc)


class TestServiceResponseError:
    """Tests for ServiceResponseError."""

    def test_status_code(self) -> None:
        exc = ServiceResponseError(
            "resource",
            "http://localhost:8003/",
            "not found",
            status_code=404,
            response_body='{"detail":"not found"}',
        )
        assert exc.status_code == 404
        assert exc.response_body == '{"detail":"not found"}'
        assert "resource" in str(exc)

    def test_response_body_optional(self) -> None:
        exc = ServiceResponseError(
            "resource",
            "http://localhost:8003/",
            "error",
            status_code=500,
        )
        assert exc.response_body is None
        assert exc.status_code == 500

    def test_inherits_base(self) -> None:
        exc = ServiceResponseError("svc", "http://x/", "err", status_code=502)
        assert isinstance(exc, MadsciServiceError)
