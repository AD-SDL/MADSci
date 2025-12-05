"""Tests for MADSci middleware including rate limiting and request tracking."""

import asyncio
import time
from typing import ClassVar

import httpx
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
        rate_limit_exempt_ips=[],  # Disable localhost exemption for testing
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
def test_manager_with_dual_rate_limiting() -> TestManager:
    """Create a test manager instance with dual rate limiting enabled."""
    settings = TestManagerSettings(
        rate_limit_enabled=True,
        rate_limit_requests=20,  # Long window: 20 requests per 10 seconds
        rate_limit_window=10,
        rate_limit_short_requests=5,  # Short window: 5 requests per 1 second (burst) - intentionally low for testing
        rate_limit_short_window=1,
        rate_limit_exempt_ips=[],  # Disable localhost exemption for testing
    )
    definition = TestManagerDefinition(name="Dual Rate Limited Manager")
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


@pytest.fixture
def dual_rate_limited_client(
    test_manager_with_dual_rate_limiting: TestManager,
) -> TestClient:
    """Create a test client with dual rate limiting."""
    app = test_manager_with_dual_rate_limiting.create_server()
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


@pytest.mark.anyio
async def test_race_condition_concurrent_access(
    test_manager_with_rate_limiting: TestManager,
) -> None:
    """
    Test that concurrent async requests are properly synchronized and do not cause race conditions.

    This test uses httpx.AsyncClient to create truly concurrent async requests,
    verifying that asyncio locks correctly prevent race conditions in the storage
    dictionary. All requests should succeed and remaining counts should form a
    proper monotonically decreasing sequence.
    """
    app = test_manager_with_rate_limiting.create_server()

    async def make_concurrent_request(_request_num: int) -> tuple[int, int]:
        """Make an async request and return status code and remaining count."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
            remaining = int(response.headers.get("X-RateLimit-Remaining", -1))
            return (response.status_code, remaining)

    # Make 5 concurrent async requests (exactly at the limit)
    results = await asyncio.gather(*[make_concurrent_request(i) for i in range(5)])

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


def test_dual_rate_limiting_burst_protection(
    dual_rate_limited_client: TestClient,
) -> None:
    """Test that burst limit (short window) prevents rapid request bursts."""
    # Make 5 requests rapidly (at the burst limit: 5 per second)
    for i in range(5):
        response = dual_rate_limited_client.get("/health")
        assert response.status_code == 200, f"Request {i + 1} should succeed"
        # Check that burst headers are present
        assert "X-RateLimit-Burst-Limit" in response.headers
        assert response.headers["X-RateLimit-Burst-Limit"] == "5"
        assert "X-RateLimit-Burst-Remaining" in response.headers

    # The 6th rapid request should be rejected by burst limit
    response = dual_rate_limited_client.get("/health")
    assert response.status_code == 429
    assert "burst limit" in response.json()["detail"]
    assert "X-RateLimit-Burst-Limit" in response.headers
    assert response.headers["X-RateLimit-Burst-Remaining"] == "0"


def test_dual_rate_limiting_long_window_protection(
    dual_rate_limited_client: TestClient,
) -> None:
    """Test that long window limit prevents sustained high load."""
    # Make requests slowly to avoid burst limit (20 requests over ~4 seconds)
    # Burst limit is 5/second, so we'll space them out
    for i in range(20):
        response = dual_rate_limited_client.get("/health")
        assert response.status_code == 200, f"Request {i + 1} should succeed"
        # Small delay to avoid burst limit (every 5th request, wait a bit longer)
        if (i + 1) % 5 == 0:
            time.sleep(1.1)  # Wait for burst window to reset

    # The 21st request should be rejected by long window limit
    response = dual_rate_limited_client.get("/health")
    assert response.status_code == 429
    # Should mention the long window (10 seconds), not burst
    assert "burst limit" not in response.json()["detail"]
    assert "20 requests per 10 seconds" in response.json()["detail"]


def test_dual_rate_limiting_headers(dual_rate_limited_client: TestClient) -> None:
    """Test that dual rate limiting includes both burst and long window headers."""
    # First request
    response = dual_rate_limited_client.get("/health")
    assert response.status_code == 200

    # Check long window headers
    assert "X-RateLimit-Limit" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "20"
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) == 19

    # Check burst window headers
    assert "X-RateLimit-Burst-Limit" in response.headers
    assert response.headers["X-RateLimit-Burst-Limit"] == "5"
    assert "X-RateLimit-Burst-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Burst-Remaining"]) == 4

    # Check reset header
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.anyio
async def test_dual_rate_limiting_concurrent_burst(
    test_manager_with_dual_rate_limiting: TestManager,
) -> None:
    """
    Test that concurrent requests properly enforce burst limiting.

    This test verifies that the burst limit correctly handles concurrent
    async requests and prevents more than the burst limit from succeeding
    in a single burst.
    """
    app = test_manager_with_dual_rate_limiting.create_server()

    async def make_concurrent_request(_request_num: int) -> tuple[int, str]:
        """Make an async request and return status code and detail."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
            detail = (
                response.json().get("detail", "") if response.status_code == 429 else ""
            )
            return (response.status_code, detail)

    # Make 10 concurrent async requests (burst limit is 5)
    results = await asyncio.gather(*[make_concurrent_request(i) for i in range(10)])

    # Count successful and rate-limited requests
    status_codes = [r[0] for r in results]
    success_count = sum(1 for code in status_codes if code == 200)
    rate_limited_count = sum(1 for code in status_codes if code == 429)

    # Exactly 5 should succeed (burst limit), rest should be rate limited
    assert success_count == 5, (
        f"Expected 5 successful requests (burst limit), got {success_count}"
    )
    assert rate_limited_count == 5, (
        f"Expected 5 rate limited requests, got {rate_limited_count}"
    )

    # Check that rate limited responses mention burst limit
    rate_limited_details = [r[1] for r in results if r[0] == 429]
    assert all("burst limit" in detail for detail in rate_limited_details), (
        "Rate limited responses should mention burst limit"
    )


def test_dual_rate_limiting_burst_reset(dual_rate_limited_client: TestClient) -> None:
    """Test that burst limit resets after the short window expires."""
    # Make 5 requests to hit burst limit
    for _ in range(5):
        response = dual_rate_limited_client.get("/health")
        assert response.status_code == 200

    # Next request should be burst limited
    response = dual_rate_limited_client.get("/health")
    assert response.status_code == 429
    assert "burst limit" in response.json()["detail"]

    # Wait for burst window to reset (1 second + margin)
    time.sleep(1.5)

    # Should be able to make more requests now (burst limit reset)
    for i in range(5):
        response = dual_rate_limited_client.get("/health")
        assert response.status_code == 200, (
            f"Request {i + 1} after burst reset should succeed"
        )


def test_localhost_exempt_by_default() -> None:
    """Test that localhost IPs are exempt from rate limiting by default."""
    # Create middleware with default exempt IPs
    middleware = RateLimitMiddleware(
        app=None,  # type: ignore
        requests_limit=5,
        time_window=10,
    )

    # Check that localhost IPs are in exempt_ips by default
    assert "127.0.0.1" in middleware.exempt_ips
    assert "::1" in middleware.exempt_ips


def test_custom_exempt_ips() -> None:
    """Test that custom exempt IPs can be configured."""
    custom_ips = {"192.168.1.100", "10.0.0.1"}
    middleware = RateLimitMiddleware(
        app=None,  # type: ignore
        requests_limit=5,
        time_window=10,
        exempt_ips=custom_ips,
    )

    # Check that custom IPs are set correctly
    assert middleware.exempt_ips == custom_ips


@pytest.fixture
def test_manager_with_exempt_ips() -> TestManager:
    """Create a test manager instance with custom exempt IPs."""
    settings = TestManagerSettings(
        rate_limit_enabled=True,
        rate_limit_requests=5,
        rate_limit_window=10,
        rate_limit_exempt_ips=["192.168.1.100"],
    )
    definition = TestManagerDefinition(name="Manager with Exempt IPs")
    return TestManager(settings=settings, definition=definition)
