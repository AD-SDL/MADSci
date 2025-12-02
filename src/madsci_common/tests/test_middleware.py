"""Tests for MADSci middleware including rate limiting and request tracking."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar

import pytest
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.middleware import RateLimitMiddleware
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


def test_rate_limiting_within_limit(rate_limited_client: TestClient) -> None:
    """Test that requests within the rate limit are allowed."""
    # Make 5 requests (within the limit)
    for _i in range(5):
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


def test_race_condition_concurrent_access(
    test_manager_with_rate_limiting: TestManager,
) -> None:
    """
    Test that concurrent requests don't cause race conditions in storage access.

    This test exposes the race condition where multiple threads access the
    storage dictionary simultaneously without synchronization, leading to
    inaccurate request counts.
    """
    app = test_manager_with_rate_limiting.create_server()

    # Create multiple clients to simulate different threads
    def make_concurrent_request(_client_num: int) -> tuple[int, int]:
        """Make a request and return status code and remaining count."""
        client = TestClient(app)
        response = client.get("/health")
        remaining = int(response.headers.get("X-RateLimit-Remaining", -1))
        return (response.status_code, remaining)

    # Make 5 concurrent requests (exactly at the limit)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_concurrent_request, i) for i in range(5)]
        results = [future.result() for future in futures]

    # All requests should succeed (we're at the limit, not over)
    status_codes = [r[0] for r in results]
    assert all(code == 200 for code in status_codes), (
        f"Expected all 200 status codes, got: {status_codes}"
    )

    # The remaining counts should be monotonically decreasing
    # Without proper synchronization, we might see duplicate or incorrect counts
    remaining_counts = [r[1] for r in results]
    # Sort the remaining counts to check they form a proper sequence
    sorted_remaining = sorted(remaining_counts, reverse=True)
    # Should see [4, 3, 2, 1, 0] in some order
    expected = [4, 3, 2, 1, 0]
    assert sorted_remaining == expected, (
        f"Race condition detected: remaining counts are {remaining_counts}, "
        f"sorted to {sorted_remaining}, expected {expected}"
    )


def test_memory_leak_prevention(test_manager_with_rate_limiting: TestManager) -> None:
    """
    Test that storage dictionary doesn't grow unbounded.

    This test verifies that inactive client IPs are periodically cleaned up
    from the storage dictionary to prevent memory leaks.
    """
    # Create middleware with short cleanup interval for testing
    rate_limit_middleware = RateLimitMiddleware(
        app=None,  # type: ignore
        requests_limit=test_manager_with_rate_limiting.settings.rate_limit_requests,
        time_window=test_manager_with_rate_limiting.settings.rate_limit_window,
        cleanup_interval=1,  # Very short interval for testing
    )

    # Simulate requests from many different IPs (old timestamps)
    num_unique_ips = 100
    old_timestamp = time.time() - 20  # 20 seconds ago (older than time window)
    for i in range(num_unique_ips):
        fake_ip = f"192.168.1.{i}"
        rate_limit_middleware.storage[fake_ip].append(old_timestamp)

    # Check that storage has grown
    initial_size = len(rate_limit_middleware.storage)
    assert initial_size == num_unique_ips, (
        f"Expected {num_unique_ips} entries, got {initial_size}"
    )

    # Wait for cleanup interval to pass
    time.sleep(2)

    # Trigger cleanup by calling the cleanup method with a current timestamp
    asyncio.run(rate_limit_middleware._cleanup_inactive_clients(time.time()))

    # Storage should be empty now since all entries are old
    final_size = len(rate_limit_middleware.storage)

    # Verify cleanup happened
    assert final_size == 0, (
        f"Memory leak detected: storage should be 0 after cleanup, but is {final_size}"
    )
