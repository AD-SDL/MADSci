"""Automated pytest unit tests for the madsci lab server."""

import pytest
from madsci.common.ownership import global_ownership_info
from madsci.common.types.lab_types import LabManagerSettings
from madsci.squid.lab_server import LabManager
from starlette.testclient import TestClient


@pytest.fixture
def lab_manager_settings():
    """Fixture providing LabManagerSettings for testing."""
    return LabManagerSettings(
        manager_name="Test Lab Manager", enable_registry_resolution=False
    )


@pytest.fixture
def lab_manager(lab_manager_settings):
    """Fixture providing a LabManager instance with LabManagerSettings."""
    return LabManager(settings=lab_manager_settings)


def test_lab_manager_with_custom_settings():
    """Test LabManager creation with custom settings."""
    settings = LabManagerSettings(
        server_url="http://localhost:9000",
        manager_name="Custom Lab Manager",
        enable_registry_resolution=False,
    )

    manager = LabManager(settings=settings)

    assert str(manager.settings.server_url) == "http://localhost:9000/"
    assert manager.settings.manager_name == "Custom Lab Manager"


def test_lab_manager_server_creation():
    """Test that the server can be created and has the expected endpoints."""
    # Disable dashboard files for this test to avoid static file conflicts
    settings = LabManagerSettings(
        dashboard_files_path=None,
        manager_name="Test Lab Manager",
        enable_registry_resolution=False,
    )
    manager = LabManager(settings=settings)
    app = manager.create_server()

    assert app is not None

    with TestClient(app) as client:
        # Test the root endpoint (should return 404 since LabManager disables it)
        response = client.get("/")
        assert response.status_code == 404

        # Test the settings endpoint
        response = client.get("/settings")
        assert response.status_code == 200

        # Test the context endpoint (lab-specific)
        response = client.get("/context")
        assert response.status_code == 200


def test_lab_manager_root_endpoint_disabled():
    """Test that LabManager disables the root definition endpoint."""
    # Disable dashboard files for this test to avoid static file conflicts
    settings = LabManagerSettings(
        dashboard_files_path=None,
        manager_name="Test Lab Manager",
        enable_registry_resolution=False,
    )
    manager = LabManager(settings=settings)
    app = manager.create_server()

    with TestClient(app) as client:
        # Root endpoint should return 404 (disabled for lab manager)
        response = client.get("/")
        assert response.status_code == 404

        # /settings should work
        response = client.get("/settings")
        assert response.status_code == 200
        settings_data = response.json()
        assert settings_data["settings"]["manager_name"] == "Test Lab Manager"

        # Other endpoints should still work
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/context")
        assert response.status_code == 200


def test_lab_manager_dashboard_files_none():
    """Test lab manager with dashboard files disabled."""
    settings = LabManagerSettings(
        dashboard_files_path=None,
        manager_name="Test Lab Manager",
        enable_registry_resolution=False,
    )
    manager = LabManager(settings=settings)
    app = manager.create_server()

    # Should still create the app successfully
    assert app is not None

    with TestClient(app) as client:
        response = client.get("/settings")
        assert response.status_code == 200


def test_lab_manager_ownership_setup(lab_manager_settings):
    """Test that ownership information is properly set up."""

    _ = LabManager(settings=lab_manager_settings)

    # Lab manager should set both manager_id and lab_id
    assert global_ownership_info.manager_id == lab_manager_settings.manager_id
    assert global_ownership_info.lab_id == lab_manager_settings.manager_id


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
