"""Automated pytest unit tests for the madsci lab server."""

import pytest
from madsci.common.ownership import global_ownership_info
from madsci.common.types.lab_types import LabManagerDefinition, LabManagerSettings
from madsci.squid.lab_server import LabManager
from starlette.testclient import TestClient


@pytest.fixture
def lab_manager_definition():
    """Fixture providing a LabManagerDefinition instance for testing."""
    return LabManagerDefinition(name="Test Lab Manager")


@pytest.fixture
def lab_manager(lab_manager_definition):
    """Fixture providing a LabManager instance with a LabManagerDefinition."""
    return LabManager(definition=lab_manager_definition)


def test_lab_manager_with_custom_settings():
    """Test LabManager creation with custom settings."""
    settings = LabManagerSettings(
        server_url="http://localhost:9000", manager_definition="custom_lab.yaml"
    )
    definition = LabManagerDefinition(name="Custom Lab Manager")

    manager = LabManager(settings=settings, definition=definition)

    assert str(manager.settings.server_url) == "http://localhost:9000/"
    assert manager.definition.name == "Custom Lab Manager"


def test_lab_manager_server_creation(lab_manager_definition):
    """Test that the server can be created and has the expected endpoints."""
    # Disable dashboard files for this test to avoid static file conflicts
    settings = LabManagerSettings(dashboard_files_path=None)
    manager = LabManager(settings=settings, definition=lab_manager_definition)
    app = manager.create_server()

    assert app is not None

    with TestClient(app) as client:
        # Test the root endpoint (should return 200 even without dashboard files)
        response = client.get("/")
        assert response.status_code == 200

        # Test the definition endpoint
        response = client.get("/definition")
        assert response.status_code == 200

        # Test the context endpoint (lab-specific)
        response = client.get("/context")
        assert response.status_code == 200


def test_lab_manager_dashboard_files_none(lab_manager_definition):
    """Test lab manager with dashboard files disabled."""
    settings = LabManagerSettings(dashboard_files_path=None)
    manager = LabManager(settings=settings, definition=lab_manager_definition)
    app = manager.create_server()

    # Should still create the app successfully
    assert app is not None

    with TestClient(app) as client:
        response = client.get("/definition")
        assert response.status_code == 200


def test_lab_manager_ownership_setup(lab_manager_definition):
    """Test that ownership information is properly set up."""

    _ = LabManager(definition=lab_manager_definition)

    # Lab manager should set both manager_id and lab_id
    assert global_ownership_info.manager_id == lab_manager_definition.manager_id
    assert global_ownership_info.lab_id == lab_manager_definition.manager_id


def test_health_endpoint(lab_manager):
    """Test the basic health endpoint of the Lab Manager."""
    app = lab_manager.create_server()

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "healthy" in health_data
        assert "description" in health_data

        # Basic lab manager should be healthy
        assert health_data["healthy"] is True


def test_lab_health_endpoint(lab_manager):
    """Test the lab health endpoint that checks all managers."""
    app = lab_manager.create_server()

    with TestClient(app) as client:
        response = client.get("/lab_health")
        assert response.status_code == 200

        health_data = response.json()
        assert "healthy" in health_data
        assert "description" in health_data
        assert "managers" in health_data
        assert "total_managers" in health_data
        assert "healthy_managers" in health_data

        # Verify the structure of the lab health response
        assert isinstance(health_data["managers"], dict)
        assert isinstance(health_data["total_managers"], int)
        assert isinstance(health_data["healthy_managers"], int)
        assert (
            health_data["total_managers"] >= 0
        )  # May be 0 in test environment with no configured managers

        # Each manager in the response should have health information
        for _, manager_health in health_data["managers"].items():
            assert "healthy" in manager_health
            assert "description" in manager_health
            assert isinstance(manager_health["healthy"], bool)
