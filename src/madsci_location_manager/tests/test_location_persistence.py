"""Tests for location persistence via Redis state and settings initialization.

Locations are configured via LocationManagerSettings.locations and persisted
in Redis at runtime. This module tests:
1. Locations from settings are properly loaded into Redis on startup.
2. Locations added/modified/deleted via the API persist in Redis.
3. The settings export endpoint reflects the initial location configuration.
"""

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerSettings,
)
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_server import LocationManager
from pytest_mock_resources import RedisConfig, create_redis_fixture
from redis import Redis


# Create a Redis server fixture for testing
@pytest.fixture(scope="session")
def pmr_redis_config() -> RedisConfig:
    """Configure the Redis server."""
    return RedisConfig(image="redis:7.4")


redis_server = create_redis_fixture()


@pytest.fixture
def location_defs():
    """Create test location definitions for settings."""
    return [
        LocationDefinition(
            location_name="Station Alpha",
            location_id=new_ulid_str(),
            description="First station",
        ),
        LocationDefinition(
            location_name="Station Beta",
            location_id=new_ulid_str(),
            description="Second station",
        ),
    ]


@pytest.fixture
def app_with_locations(redis_server: Redis, location_defs):
    """Create a test app with pre-configured locations in settings."""
    settings = LocationManagerSettings(
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
        locations=location_defs,
    )

    manager = LocationManager(settings=settings)
    manager.state_handler._redis_connection = redis_server
    return manager.create_server(version="0.1.0")


@pytest.fixture
def client_with_locations(app_with_locations):
    """Create a test client for the app with pre-configured locations."""
    client = TestClient(app_with_locations)
    yield client
    client.close()


@pytest.fixture
def empty_app(redis_server: Redis):
    """Create a test app with no pre-configured locations."""
    settings = LocationManagerSettings(
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings)
    manager.state_handler._redis_connection = redis_server
    return manager.create_server(version="0.1.0")


@pytest.fixture
def empty_client(empty_app):
    """Create a test client for the app with no locations."""
    client = TestClient(empty_app)
    yield client
    client.close()


# --- Settings-to-Redis initialization tests ---


def test_settings_locations_loaded_into_redis(client_with_locations, location_defs):
    """Locations from settings should be present in Redis after startup."""
    response = client_with_locations.get("/locations")
    assert response.status_code == 200

    locations = [Location.model_validate(loc) for loc in response.json()]
    location_ids = {loc.location_id for loc in locations}
    expected_ids = {loc_def.location_id for loc_def in location_defs}
    assert expected_ids.issubset(location_ids)


def test_settings_location_names_match(client_with_locations, location_defs):
    """Location names from settings should match what's stored in Redis."""
    for loc_def in location_defs:
        response = client_with_locations.get(f"/location/{loc_def.location_id}")
        assert response.status_code == 200
        location = Location.model_validate(response.json())
        assert location.location_name == loc_def.location_name
        assert location.description == loc_def.description


def test_empty_settings_yields_no_locations(empty_client):
    """When no locations are configured in settings, Redis should be empty."""
    response = empty_client.get("/locations")
    assert response.status_code == 200
    assert response.json() == []


# --- Runtime persistence tests ---


def test_added_location_persists_in_redis(empty_client):
    """A location added via the API should be retrievable from Redis."""
    location = Location(
        location_id=new_ulid_str(),
        location_name="Runtime Location",
        description="Added at runtime",
    )

    response = empty_client.post("/location", json=location.model_dump())
    assert response.status_code == 200

    # Fetch it back
    response = empty_client.get(f"/location/{location.location_id}")
    assert response.status_code == 200
    fetched = Location.model_validate(response.json())
    assert fetched.location_id == location.location_id
    assert fetched.location_name == "Runtime Location"


def test_deleted_location_removed_from_redis(empty_client):
    """A deleted location should no longer be retrievable."""
    location = Location(
        location_id=new_ulid_str(),
        location_name="To Be Deleted",
    )
    empty_client.post("/location", json=location.model_dump())

    # Delete it
    response = empty_client.delete(f"/location/{location.location_id}")
    assert response.status_code == 200

    # Should be gone
    response = empty_client.get(f"/location/{location.location_id}")
    assert response.status_code == 404


def test_updated_representation_persists_in_redis(empty_client):
    """Representations set via the API should persist in Redis."""
    location = Location(
        location_id=new_ulid_str(),
        location_name="Rep Test Location",
    )
    empty_client.post("/location", json=location.model_dump())

    representation = {"position": [1, 2, 3], "config": "test"}
    response = empty_client.post(
        f"/location/{location.location_id}/set_representation/test_robot",
        json=representation,
    )
    assert response.status_code == 200

    # Fetch and verify
    response = empty_client.get(f"/location/{location.location_id}")
    assert response.status_code == 200
    fetched = Location.model_validate(response.json())
    assert fetched.representations is not None
    assert fetched.representations["test_robot"] == representation


def test_initial_locations_preserved_after_runtime_add(
    client_with_locations, location_defs
):
    """Adding a new location at runtime should not affect settings-defined locations."""
    new_location = Location(
        location_id=new_ulid_str(),
        location_name="New Runtime Location",
    )
    response = client_with_locations.post("/location", json=new_location.model_dump())
    assert response.status_code == 200

    # Verify all original locations still present
    response = client_with_locations.get("/locations")
    assert response.status_code == 200
    locations = [Location.model_validate(loc) for loc in response.json()]
    location_ids = {loc.location_id for loc in locations}

    for loc_def in location_defs:
        assert loc_def.location_id in location_ids


# --- Settings export tests ---


def test_settings_export_includes_initial_locations(
    client_with_locations, location_defs
):
    """The settings export endpoint should reflect the configured locations."""
    response = client_with_locations.get("/settings")
    assert response.status_code == 200

    data = response.json()
    # Settings export nests fields under "settings"
    settings_data = data.get("settings", data)
    assert "locations" in settings_data
    exported_locations = settings_data["locations"]
    assert len(exported_locations) == len(location_defs)

    exported_ids = {loc["location_id"] for loc in exported_locations}
    expected_ids = {loc_def.location_id for loc_def in location_defs}
    assert exported_ids == expected_ids
