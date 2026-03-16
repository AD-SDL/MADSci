"""Tests for location persistence via MongoDB state and settings initialization.

Locations are persisted in MongoDB at runtime. This module tests:
1. Locations added/modified/deleted via the API persist in MongoDB.
2. Initial location configuration is preserved across runtime changes.
"""

import pytest
from fastapi.testclient import TestClient
from madsci.common.db_handlers.mongo_handler import InMemoryMongoHandler
from madsci.common.db_handlers.redis_handler import InMemoryRedisHandler
from madsci.common.types.location_types import (
    Location,
    LocationManagerSettings,
)
from madsci.common.utils import new_ulid_str
from madsci.location_manager.location_server import LocationManager


@pytest.fixture
def mongo_handler():
    """Create an InMemoryMongoHandler for testing."""
    handler = InMemoryMongoHandler(database_name="test_locations")
    yield handler
    handler.close()


@pytest.fixture
def redis_handler():
    """Create an InMemoryRedisHandler for testing."""
    handler = InMemoryRedisHandler()
    yield handler
    handler.close()


@pytest.fixture
def location_defs():
    """Create test location definitions for settings."""
    return [
        Location(
            location_name="Station Alpha",
            location_id=new_ulid_str(),
            description="First station",
        ),
        Location(
            location_name="Station Beta",
            location_id=new_ulid_str(),
            description="Second station",
        ),
    ]


@pytest.fixture
def app_with_locations(redis_handler, mongo_handler, location_defs):
    """Create a test app with pre-configured locations and in-memory handlers."""
    settings = LocationManagerSettings(
        enable_registry_resolution=False,
    )

    manager = LocationManager(
        settings=settings,
        redis_handler=redis_handler,
        mongo_handler=mongo_handler,
    )
    for location in location_defs:
        manager.add_location(location)
    return manager.create_server(version="0.1.0")


@pytest.fixture
def client_with_locations(app_with_locations):
    """Create a test client for the app with pre-configured locations."""
    client = TestClient(app_with_locations)
    yield client
    client.close()


@pytest.fixture
def empty_app(redis_handler, mongo_handler):
    """Create a test app with no pre-configured locations."""
    settings = LocationManagerSettings(
        enable_registry_resolution=False,
    )

    manager = LocationManager(
        settings=settings,
        redis_handler=redis_handler,
        mongo_handler=mongo_handler,
    )
    return manager.create_server(version="0.1.0")


@pytest.fixture
def empty_client(empty_app):
    """Create a test client for the app with no locations."""
    client = TestClient(empty_app)
    yield client
    client.close()


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
    response = empty_client.get(f"/location/{location.location_name}")
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
    response = empty_client.delete(f"/location/{location.location_name}")
    assert response.status_code == 200

    # Should be gone
    response = empty_client.get(f"/location/{location.location_name}")
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
        f"/location/{location.location_name}/set_representation/test_robot",
        json=representation,
    )
    assert response.status_code == 200

    # Fetch and verify
    response = empty_client.get(f"/location/{location.location_name}")
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
