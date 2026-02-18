"""Tests for location persistence to YAML definition files.

NOTE: These tests are skipped because the definition file persistence feature
has been removed as part of the definition file purge. The LocationManager
no longer writes back to definition files, and `_sync_locations_to_definition()`
no longer exists. Locations are now configured via LocationManagerSettings.locations
and persisted only in Redis state.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Definition file persistence has been removed in the definition file purge. "
    "Locations are now configured via LocationManagerSettings and persisted in Redis only."
)

from pathlib import Path  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from madsci.common.types.location_types import (  # noqa: E402
    Location,
    LocationDefinition,
    LocationManagerSettings,
)
from madsci.common.utils import new_ulid_str  # noqa: E402
from madsci.location_manager.location_server import LocationManager  # noqa: E402
from pytest_mock_resources import RedisConfig, create_redis_fixture  # noqa: E402
from redis import Redis  # noqa: E402


# Create a Redis server fixture for testing
@pytest.fixture(scope="session")
def pmr_redis_config() -> RedisConfig:
    """Configure the Redis server."""
    return RedisConfig(image="redis:7.4")


redis_server = create_redis_fixture()


@pytest.fixture
def definition_file(tmp_path):
    """Create a test definition file."""
    return tmp_path / "location.manager.yaml"


@pytest.fixture
def app(redis_server: Redis):
    """Create a test app with test settings and Redis server."""
    settings = LocationManagerSettings(
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
        locations=[
            LocationDefinition(
                location_name="Initial Location 1",
                location_id=new_ulid_str(),
                description="First initial location",
            ),
            LocationDefinition(
                location_name="Initial Location 2",
                location_id=new_ulid_str(),
                description="Second initial location",
            ),
        ],
    )

    manager = LocationManager(settings=settings)
    manager.state_handler._redis_connection = redis_server

    return manager.create_server(version="0.1.0")


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        location_id=new_ulid_str(),
        location_name="Test Location",
        description="A test location for persistence testing",
    )


def test_add_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that adding a location persists it to the YAML definition file."""


def test_update_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that updating a location persists changes to the YAML definition file."""


def test_delete_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that deleting a location removes it from the YAML definition file."""


def test_initial_locations_preserved_after_add(
    client, sample_location, definition_file
):
    """Test that initial locations from the definition file are preserved when adding new locations."""


def test_transfer_capabilities_preserved_during_sync(tmp_path):
    """Test that transfer_capabilities in the definition are preserved when syncing locations."""


def test_startup_sync_redis_only_locations_to_yaml(redis_server: Redis, tmp_path: Path):
    """Test that locations existing only in Redis are immediately synced to YAML on startup."""
