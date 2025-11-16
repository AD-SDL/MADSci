"""Tests for MADSci middleware including rate limiting and request tracking."""

import time
from typing import ClassVar

import pytest
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerSettings,
    ManagerType,
)
from pydantic import Field
from starlette.testclient import TestClient


class TestManagerSettings(ManagerSettings):
    """Test settings for the manager."""

    model_config: ClassVar[dict] = {"env_prefix": "TEST_"}


class TestManagerDefinition(ManagerDefinition):
    """Test definition for the manager."""

    manager_type: ManagerType = Field(default=ManagerType.EVENT_MANAGER)


class TestManager(AbstractManagerBase[TestManagerSettings, TestManagerDefinition]):
    """Test manager implementation."""

    SETTINGS_CLASS = TestManagerSettings
    DEFINITION_CLASS = TestManagerDefinition


@pytest.fixture
def test_manager_with_rate_limiting() -> TestManager:
    """Create a test manager instance with rate limiting enabled."""
    settings = TestManagerSettings(
        rate_limit_enabled=True,
        rate_limit_requests=5,
        rate_limit_window=10,
    )
    definition = TestManagerDefinition(name="Rate Limited Manager")
    return TestManager(settings=settings, definition=definition)


@pytest.fixture
def test_manager_without_rate_limiting() -> TestManager:
    """Create a test manager instance with rate limiting disabled."""
    settings = TestManagerSettings(rate_limit_enabled=False)
    definition = TestManagerDefinition(name="Unlimited Manager")
    return TestManager(settings=settings, definition=definition)


@pytest.fixture
def rate_limited_client(test_manager_with_rate_limiting: TestManager) -> TestClient:
    """Create a test client with rate limiting."""
    app = test_manager_with_rate_limiting.create_server()
    return TestClient(app)


@pytest.fixture
def unlimited_client(test_manager_without_rate_limiting: TestManager) -> TestClient:
    """Create a test client without rate limiting."""
    app = test_manager_without_rate_limiting.create_server()
    return TestClient(app)


def test_request_tracking_headers(unlimited_client: TestClient) -> None:
    """Test that request tracking middleware adds timing headers."""
    response = unlimited_client.get("/health")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    # Processing time should be a valid float
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0


def test_rate_limiting_within_limit(rate_limited_client: TestClient) -> None:
    """Test that requests within the rate limit are allowed."""
    # Make 5 requests (within the limit)
    for i in range(5):
        response = rate_limited_client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


def test_rate_limiting_exceeds_limit(rate_limited_client: TestClient) -> None:
    """Test that requests exceeding the rate limit are rejected."""
    # Make 5 requests (at the limit)
    for _ in range(5):
        response = rate_limited_client.get("/health")
        assert response.status_code == 200

    # The 6th request should be rate limited
    response = rate_limited_client.get("/health")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert response.headers["X-RateLimit-Remaining"] == "0"


def test_rate_limit_reset_after_window(rate_limited_client: TestClient) -> None:
    """Test that rate limit resets after the time window."""
    # Make 5 requests (at the limit)
    for _ in range(5):
        response = rate_limited_client.get("/health")
        assert response.status_code == 200

    # Wait for the time window to pass
    time.sleep(11)  # Rate limit window is 10 seconds + 1 for safety

    # Next request should succeed
    response = rate_limited_client.get("/health")
    assert response.status_code == 200


def test_rate_limiting_disabled(unlimited_client: TestClient) -> None:
    """Test that rate limiting can be disabled."""
    # Make many requests - all should succeed
    for _ in range(20):
        response = unlimited_client.get("/health")
        assert response.status_code == 200

    # No rate limit headers should be present when disabled
    # (only the tracking headers)
    assert "X-Process-Time" in response.headers


def test_rate_limit_headers_values(rate_limited_client: TestClient) -> None:
    """Test that rate limit headers contain correct values."""
    # First request
    response = rate_limited_client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    # Remaining should be 4 after first request
    remaining = int(response.headers["X-RateLimit-Remaining"])
    assert remaining == 4

    # Second request
    response = rate_limited_client.get("/health")
    assert response.status_code == 200
    remaining = int(response.headers["X-RateLimit-Remaining"])
    assert remaining == 3
