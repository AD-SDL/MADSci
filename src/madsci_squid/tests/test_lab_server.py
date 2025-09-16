"""Automated pytest unit tests for the madsci lab server."""

from madsci.common.ownership import global_ownership_info
from madsci.common.types.lab_types import LabManagerDefinition, LabManagerSettings
from madsci.squid.lab_server import LabManager
from starlette.testclient import TestClient


def test_lab_manager_creation():
    """Test that LabManager can be created with default settings."""
    manager = LabManager()
    assert manager is not None
    assert isinstance(manager.settings, LabManagerSettings)
    assert isinstance(manager.definition, LabManagerDefinition)


def test_lab_manager_with_custom_settings():
    """Test LabManager creation with custom settings."""
    settings = LabManagerSettings(
        server_url="http://localhost:9000", manager_definition="custom_lab.yaml"
    )
    definition = LabManagerDefinition(name="Custom Lab Manager")

    manager = LabManager(settings=settings, definition=definition)

    assert str(manager.settings.server_url) == "http://localhost:9000/"
    assert manager.definition.name == "Custom Lab Manager"


def test_lab_manager_server_creation():
    """Test that the server can be created and has the expected endpoints."""
    # Disable dashboard files for this test to avoid static file conflicts
    settings = LabManagerSettings(dashboard_files_path=None)
    manager = LabManager(settings=settings)
    app = manager.create_server()

    assert app is not None

    with TestClient(app) as client:
        # Test the root endpoint (should return 404 since no dashboard files are configured)
        response = client.get("/")
        assert response.status_code == 404

        # Test the definition endpoint
        response = client.get("/definition")
        assert response.status_code == 200

        # Test the context endpoint (lab-specific)
        response = client.get("/context")
        assert response.status_code == 200


def test_lab_manager_dashboard_files_none():
    """Test lab manager with dashboard files disabled."""
    settings = LabManagerSettings(dashboard_files_path=None)
    manager = LabManager(settings=settings)
    app = manager.create_server()

    # Should still create the app successfully
    assert app is not None

    with TestClient(app) as client:
        response = client.get("/definition")
        assert response.status_code == 200


def test_lab_manager_ownership_setup():
    """Test that ownership information is properly set up."""

    definition = LabManagerDefinition(name="Ownership Test Lab")
    _ = LabManager(definition=definition)

    # Lab manager should set both manager_id and lab_id
    assert global_ownership_info.manager_id == definition.manager_id
    assert global_ownership_info.lab_id == definition.manager_id
