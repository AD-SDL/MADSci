"""
Shared fixtures and configuration for example lab tests.

This module provides common test fixtures for testing the MADSci example lab,
including service setup, database cleanup, and test data generation.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.context_types import MadsciContext
from madsci.common.utils import new_ulid_str


@pytest.fixture
def ownership_info() -> OwnershipInfo:
    """Generate test ownership information."""
    return OwnershipInfo(
        user_id=new_ulid_str(), lab_id=new_ulid_str(), experiment_id=new_ulid_str()
    )


@pytest.fixture
def madsci_context() -> MadsciContext:
    """Generate test MADSci context."""
    return MadsciContext(
        lab_server_url="http://localhost:8000",
        event_server_url="http://localhost:8001",
        experiment_server_url="http://localhost:8002",
        resource_server_url="http://localhost:8003",
        data_server_url="http://localhost:8004",
        workcell_server_url="http://localhost:8005",
    )


@pytest.fixture
def temp_lab_dir() -> Path:
    """Create temporary directory for lab test files."""
    with tempfile.TemporaryDirectory(prefix="madsci_test_lab_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def example_lab_config() -> Dict[str, Any]:
    """Load example lab configuration for testing."""
    return {
        "lab_id": "example-lab-test",
        "name": "Example Lab Test",
        "description": "Test instance of the MADSci example lab",
        "managers": {
            "event_manager": {"port": 8001},
            "experiment_manager": {"port": 8002},
            "resource_manager": {"port": 8003},
            "data_manager": {"port": 8004},
            "workcell_manager": {"port": 8005},
        },
    }


@pytest.fixture
def lab_services_health_check() -> bool:
    """
    Check if lab services are running and healthy.

    This fixture assumes services are started externally (e.g., via docker-compose).
    In CI/CD, services should be started before running tests.
    """
    services = {
        "event_manager": "http://localhost:8001/",
        "experiment_manager": "http://localhost:8002/",
        "resource_manager": "http://localhost:8003/",
        "data_manager": "http://localhost:8004/",
        "workcell_manager": "http://localhost:8005/",
    }

    health_status = {}
    for service, url in services.items():
        try:
            response = httpx.get(url, timeout=5.0)
            health_status[service] = response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            health_status[service] = False

    all_healthy = all(health_status.values())
    if not all_healthy:
        pytest.skip(f"Required services not healthy: {health_status}")

    return all_healthy


@pytest.fixture
def sample_resource_template() -> Dict[str, Any]:
    """Generate sample resource template for testing."""
    return {
        "template_id": new_ulid_str(),
        "name": "test-96-well-plate",
        "type": "container",
        "category": "plate",
        "specifications": {
            "well_count": 96,
            "well_volume_ul": 200,
            "dimensions": {"length_mm": 127.8, "width_mm": 85.5, "height_mm": 14.4},
        },
        "metadata": {"manufacturer": "Test Corp", "part_number": "TEST-96-PLATE"},
    }


@pytest.fixture
def sample_workflow_definition() -> Dict[str, Any]:
    """Generate sample workflow definition for testing."""
    return {
        "workflow_id": new_ulid_str(),
        "name": "test-workflow",
        "version": "1.0.0",
        "steps": [
            {
                "step_id": new_ulid_str(),
                "name": "test_step",
                "node": "test_node",
                "action": "test_action",
                "parameters": {"input_param": "test_value"},
            }
        ],
    }


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """
    Automatically clean up test data after each test.

    This fixture runs after every test to ensure clean state.
    """
    yield

    # Cleanup logic would go here if needed
    # For now, we rely on service isolation and test databases


class TestConfig:
    """Test configuration constants."""

    # Service URLs
    EVENT_MANAGER_URL = "http://localhost:8001"
    EXPERIMENT_MANAGER_URL = "http://localhost:8002"
    RESOURCE_MANAGER_URL = "http://localhost:8003"
    DATA_MANAGER_URL = "http://localhost:8004"
    WORKCELL_MANAGER_URL = "http://localhost:8005"

    # Test timeouts
    SERVICE_STARTUP_TIMEOUT = 30  # seconds
    WORKFLOW_EXECUTION_TIMEOUT = 60  # seconds

    # Test data limits
    MAX_RESOURCES_PER_TEST = 100
    MAX_WORKFLOW_STEPS = 10


# Mark module as providing pytest fixtures
# Note: pytest_plugins moved to root conftest.py to avoid deprecation warning
