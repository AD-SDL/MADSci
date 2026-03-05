"""Tests for the AbstractManagerBase class and inherited routes."""

from typing import ClassVar

import pytest
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import (
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from starlette.testclient import TestClient


class TestManagerSettings(ManagerSettings):
    """Test settings for the manager."""

    model_config: ClassVar[dict] = {"env_prefix": "TEST_"}


class TestManagerHealth(ManagerHealth):
    """Test health status for the manager."""

    test_value: int = 42


class TestManager(AbstractManagerBase[TestManagerSettings]):
    """Test manager implementation."""

    SETTINGS_CLASS = TestManagerSettings

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
    settings = TestManagerSettings(
        manager_name="Test Manager",
        manager_type=ManagerType.EVENT_MANAGER,
    )
    return TestManager(settings=settings)


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


def test_settings_endpoint(test_client: TestClient) -> None:
    """Test that the /settings endpoint returns the manager settings."""
    response = test_client.get("/settings")
    assert response.status_code == 200

    settings_data = response.json()
    assert "settings" in settings_data


def test_inherited_routes_with_custom_subclass() -> None:
    """Test that inherited routes work with a custom subclass."""

    class CustomManager(TestManager):
        """Custom subclass that doesn't override health."""

    settings = TestManagerSettings(
        manager_name="Custom Manager",
        manager_type=ManagerType.EVENT_MANAGER,
    )
    manager = CustomManager(settings=settings)
    app = manager.create_server()
    client = TestClient(app)

    # Test that inherited routes still work
    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/settings")
    assert response.status_code == 200


def test_manager_with_overridden_health() -> None:
    """Test that managers can override the health method."""

    class HealthOverrideManager(AbstractManagerBase[TestManagerSettings]):
        """Manager that overrides health."""

        SETTINGS_CLASS = TestManagerSettings

        def get_health(self) -> ManagerHealth:
            """Override to return different health status."""
            return ManagerHealth(
                healthy=False,
                description="Custom health check failed",
            )

    settings = TestManagerSettings(
        manager_name="Override Manager",
        manager_type=ManagerType.EVENT_MANAGER,
    )
    manager = HealthOverrideManager(settings=settings)
    app = manager.create_server()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["healthy"] is False
    assert health_data["description"] == "Custom health check failed"


def test_settings_endpoint_returns_data() -> None:
    """Test that the /settings endpoint returns settings data."""

    class DefaultManager(AbstractManagerBase[TestManagerSettings]):
        """Manager using default settings."""

        SETTINGS_CLASS = TestManagerSettings

    settings = TestManagerSettings(
        manager_name="Default Manager",
        manager_type=ManagerType.EVENT_MANAGER,
    )
    manager = DefaultManager(settings=settings)
    app = manager.create_server()
    client = TestClient(app)

    response = client.get("/settings")
    assert response.status_code == 200
    settings_data = response.json()
    assert "settings" in settings_data

    response = client.get("/health")
    assert response.status_code == 200
