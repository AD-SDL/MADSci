"""
Stress tests for MADSci REST servers.

These tests simulate high-load scenarios to ensure servers remain
resilient under stress conditions like request storms and high concurrency.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
def stress_test_manager() -> TestManager:
    """Create a manager configured for stress testing."""
    settings = TestManagerSettings(
        rate_limit_enabled=True,
        rate_limit_requests=100,
        rate_limit_window=10,
    )
    definition = TestManagerDefinition(name="Stress Test Manager")
    return TestManager(settings=settings, definition=definition)


@pytest.fixture
def stress_test_client(stress_test_manager: TestManager) -> TestClient:
    """Create a test client for stress testing."""
    app = stress_test_manager.create_server()
    return TestClient(app)


def make_request(client: TestClient, endpoint: str = "/health") -> dict:
    """
    Make a single request and return status and timing info.

    Args:
        client: The test client
        endpoint: The endpoint to request

    Returns:
        Dictionary with status_code, success, and response_time
    """
    start_time = time.time()
    try:
        response = client.get(endpoint)
        response_time = time.time() - start_time
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_time": response_time,
            "rate_limited": response.status_code == 429,
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "status_code": 0,
            "success": False,
            "response_time": response_time,
            "error": str(e),
            "rate_limited": False,
        }


def test_concurrent_requests(stress_test_client: TestClient) -> None:
    """Test server handles concurrent requests without crashing."""
    num_requests = 50
    results = []

    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_request, stress_test_client)
            for _ in range(num_requests)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    # Check that we got responses for all requests
    assert len(results) == num_requests

    # Count successes and rate limited responses
    successes = sum(1 for r in results if r["success"])
    rate_limited = sum(1 for r in results if r["rate_limited"])

    # At least some requests should succeed
    assert successes > 0, "No requests succeeded"

    # Some may be rate limited, but server should handle it gracefully
    if rate_limited > 0:
        assert all(r["status_code"] in [200, 429] for r in results), (
            "Server returned unexpected status codes"
        )

    # Calculate statistics
    response_times = [r["response_time"] for r in results if r["success"]]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Assert reasonable performance characteristics
        # Average response time should be under 1 second for health checks
        assert avg_response_time < 1.0, (
            f"Average response time too high: {avg_response_time:.3f}s"
        )
        # Max response time should be under 2 seconds
        assert max_response_time < 2.0, (
            f"Max response time too high: {max_response_time:.3f}s"
        )


def test_sustained_load(stress_test_client: TestClient) -> None:
    """Test server handles sustained load over time."""
    duration_seconds = 5
    request_interval = 0.05  # 20 requests per second
    results = []

    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        result = make_request(stress_test_client)
        results.append(result)
        time.sleep(request_interval)

    # Check results
    assert len(results) > 0, "No requests completed"

    successes = sum(1 for r in results if r["success"])
    rate_limited = sum(1 for r in results if r["rate_limited"])
    errors = sum(1 for r in results if not r["success"] and not r["rate_limited"])

    # Most requests should either succeed or be cleanly rate limited
    assert successes + rate_limited > errors, (
        f"Too many errors: {errors} vs {successes} successful"
    )

    # Server should not crash
    final_health = make_request(stress_test_client, "/health")
    assert final_health["success"], "Server became unhealthy after sustained load"


def test_burst_traffic(stress_test_client: TestClient) -> None:
    """Test server handles sudden traffic bursts."""
    # Send a burst of requests
    burst_size = 200
    results = []

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(make_request, stress_test_client) for _ in range(burst_size)
        ]

        for future in as_completed(futures):
            results.append(future.result())
    total_duration = time.time() - start_time

    # Analyze results
    successes = sum(1 for r in results if r["success"])
    rate_limited_count = sum(1 for r in results if r["rate_limited"])

    # Assert that burst was handled efficiently
    # With 200 requests, at least some should succeed before rate limiting kicks in
    assert successes > 0, "No requests succeeded during burst"

    # Total duration should be reasonable (not excessively long)
    assert total_duration < 10.0, (
        f"Burst took too long to process: {total_duration:.2f}s"
    )

    # With proper rate limiting, we expect some requests to be limited
    assert rate_limited_count > 0, (
        "Expected some requests to be rate limited during burst"
    )

    # With rate limiting, we expect some requests to be limited
    # but none should cause the server to crash
    assert all(
        r["status_code"] in [200, 429] for r in results if r["status_code"] != 0
    ), "Server returned unexpected status codes during burst"

    # Server should still be responsive after burst
    # Wait for rate limit window to expire so we can verify server is still functioning
    time.sleep(11)  # Wait for rate limit window (10s) + buffer
    health_check = make_request(stress_test_client, "/health")
    assert health_check["success"] or health_check["rate_limited"], (
        "Server became completely unresponsive after burst traffic"
    )


def test_multiple_endpoints_under_load(stress_test_client: TestClient) -> None:
    """Test that multiple endpoints handle load simultaneously."""
    endpoints = ["/health", "/definition", "/"]
    num_requests_per_endpoint = 20
    results = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = []
        for endpoint in endpoints:
            for _ in range(num_requests_per_endpoint):
                futures.append(
                    executor.submit(make_request, stress_test_client, endpoint)
                )

        for future in as_completed(futures):
            results.append(future.result())

    total_requests = len(endpoints) * num_requests_per_endpoint
    assert len(results) == total_requests

    successes = sum(1 for r in results if r["success"])
    rate_limited = sum(1 for r in results if r["rate_limited"])

    # Most requests should complete (either success or cleanly rate limited)
    assert successes + rate_limited >= total_requests * 0.5, (
        "Too many requests failed completely"
    )


@pytest.mark.slow
def test_extended_stress_test(stress_test_client: TestClient) -> None:
    """
    Extended stress test with variable load patterns.

    This test is marked as 'slow' and may be skipped in quick test runs.
    Use: pytest -m slow to run slow tests.
    """
    test_duration = 30  # seconds
    results = []
    start_time = time.time()

    # Variable load pattern: alternate between high and low load
    iteration = 0
    while time.time() - start_time < test_duration:
        # Every 5 seconds, switch between burst and normal load
        if (iteration % 100) < 50:
            # Normal load
            result = make_request(stress_test_client)
            results.append(result)
            time.sleep(0.1)
        else:
            # Burst load
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(make_request, stress_test_client) for _ in range(10)
                ]
                for future in as_completed(futures):
                    results.append(future.result())

        iteration += 1

    # Analyze results
    successes = sum(1 for r in results if r["success"])
    rate_limited_count = sum(1 for r in results if r["rate_limited"])
    errors = sum(1 for r in results if not r["success"] and not r["rate_limited"])

    # Assert that the extended stress test was handled properly
    assert successes > 0, "No requests succeeded during extended stress test"

    # Error rate should be low (less than 5% excluding rate limiting)
    total_requests = len(results)
    error_rate = errors / total_requests if total_requests > 0 else 0
    assert error_rate < 0.05, (
        f"Error rate too high: {error_rate:.2%} ({errors}/{total_requests})"
    )

    # Most requests should either succeed or be properly rate limited
    handled_requests = successes + rate_limited_count
    assert handled_requests >= total_requests * 0.95, (
        f"Too many unhandled requests: {total_requests - handled_requests} "
        f"out of {total_requests}"
    )

    # Wait for rate limit window to expire before final health check
    time.sleep(11)  # Rate limit window is 10 seconds + 1 for safety

    # Server should remain healthy
    final_health = make_request(stress_test_client, "/health")
    assert final_health["success"], "Server became unhealthy after extended stress test"
