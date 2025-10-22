"""Tests for the AbstractManagerBase class and inherited routes."""

from typing import ClassVar

import pytest
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
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


class TestManagerHealth(ManagerHealth):
    """Test health status for the manager."""

    test_value: int = Field(default=42)


class TestManager(AbstractManagerBase[TestManagerSettings, TestManagerDefinition]):
    """Test manager implementation."""

    SETTINGS_CLASS = TestManagerSettings
    DEFINITION_CLASS = TestManagerDefinition

    def get_health(self) -> TestManagerHealth:
        """Override health check to return custom health."""
        return TestManagerHealth(
            healthy=True,
            description="Test manager is healthy",
            test_value=100,
        )


@pytest.fixture
def test_manager() -> TestManager:
    """Create a test manager instance."""
    definition = TestManagerDefinition(name="Test Manager")
    return TestManager(definition=definition)


@pytest.fixture
def test_client(test_manager: TestManager) -> TestClient:
    """Create a test client for the manager."""
    app = test_manager.create_server()
    return TestClient(app)


def test_inherited_health_endpoint(test_client: TestClient) -> None:
    """Test that the /health endpoint is inherited from AbstractManagerBase."""
    response = test_client.get("/health")
    assert response.status_code == 200

    health_data = response.json()
    assert health_data["healthy"] is True
    assert health_data["description"] == "Test manager is healthy"
    assert health_data["test_value"] == 100


def test_inherited_root_endpoint(test_client: TestClient) -> None:
    """Test that the / endpoint returns the manager definition."""
    response = test_client.get("/")
    assert response.status_code == 200

    definition_data = response.json()
    assert definition_data["name"] == "Test Manager"
    assert definition_data["manager_type"] == "event_manager"


def test_inherited_definition_endpoint(test_client: TestClient) -> None:
    """Test that the /definition endpoint returns the manager definition."""
    response = test_client.get("/definition")
    assert response.status_code == 200

    definition_data = response.json()
    assert definition_data["name"] == "Test Manager"
    assert definition_data["manager_type"] == "event_manager"


def test_both_definition_endpoints_return_same_data(
    test_client: TestClient,
) -> None:
    """Test that / and /definition endpoints return the same data."""
    root_response = test_client.get("/")
    definition_response = test_client.get("/definition")

    assert root_response.json() == definition_response.json()


def test_inherited_routes_with_custom_subclass() -> None:
    """Test that inherited routes work with a custom subclass."""

    class CustomManager(TestManager):
        """Custom subclass that doesn't override health."""

    definition = TestManagerDefinition(name="Custom Manager")
    manager = CustomManager(definition=definition)
    app = manager.create_server()
    client = TestClient(app)

    # Test that inherited routes still work
    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Custom Manager"


def test_manager_with_overridden_health() -> None:
    """Test that managers can override the health method."""

    class HealthOverrideManager(
        AbstractManagerBase[TestManagerSettings, TestManagerDefinition]
    ):
        """Manager that overrides health."""

        SETTINGS_CLASS = TestManagerSettings
        DEFINITION_CLASS = TestManagerDefinition

        def get_health(self) -> ManagerHealth:
            """Override to return different health status."""
            return ManagerHealth(
                healthy=False,
                description="Custom health check failed",
            )

    definition = TestManagerDefinition(name="Override Manager")
    manager = HealthOverrideManager(definition=definition)
    app = manager.create_server()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["healthy"] is False
    assert health_data["description"] == "Custom health check failed"
