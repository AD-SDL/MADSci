"""Tests for the LocationManager server."""

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerDefinition,
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
def app(redis_server: Redis):
    """Create a test app with test settings and Redis server."""
    settings = LocationManagerSettings(
        manager_id="test_location_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )
    definition = LocationManagerDefinition(
        name="Test Location Manager",
        description="A test location manager instance",
    )

    # Create the app with the Redis connection passed to the LocationManager
    manager = LocationManager(settings=settings, definition=definition)
    # Override the state handler's Redis connection to use the test Redis instance
    manager.state_handler._redis_connection = redis_server
    return manager.create_server(
        version="0.1.0",
    )


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        location_id=new_ulid_str(),
        name="Test Location",
        description="A test location",
        x=10.0,
        y=20.0,
        z=30.0,
    )


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200


def test_definition_endpoint(client):
    """Test the definition endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    response = client.get("/definition")
    assert response.status_code == 200


def test_get_locations_empty(client):
    """Test getting locations when none exist."""
    response = client.get("/locations")
    assert response.status_code == 200
    assert response.json() == []


def test_add_location(client, sample_location):
    """Test adding a new location."""
    response = client.post("/location", json=sample_location.model_dump())
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.location_id == sample_location.location_id
    assert returned_location.name == sample_location.name


def test_get_location(client, sample_location):
    """Test getting a specific location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Then get it
    response = client.get(f"/location/{sample_location.location_id}")
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.location_id == sample_location.location_id


def test_get_nonexistent_location(client):
    """Test getting a location that doesn't exist."""
    response = client.get("/location/nonexistent_id")
    assert response.status_code == 404


def test_delete_location(client, sample_location):
    """Test deleting a location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Then delete it
    response = client.delete(f"/location/{sample_location.location_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it's gone
    response = client.get(f"/location/{sample_location.location_id}")
    assert response.status_code == 404


def test_delete_nonexistent_location(client):
    """Test deleting a location that doesn't exist."""
    response = client.delete("/location/nonexistent_id")
    assert response.status_code == 404


def test_add_lookup_values(client, sample_location):
    """Test adding lookup values to a location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Add lookup values
    lookup_values = {"key1": "value1", "key2": "value2"}
    response = client.post(
        f"/location/{sample_location.location_id}/add_lookup/test_node",
        json=lookup_values,
    )
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.lookup_values is not None
    assert "test_node" in returned_location.lookup_values
    assert returned_location.lookup_values["test_node"] == lookup_values


def test_attach_resource(client, sample_location):
    """Test attaching a resource to a location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Attach a resource
    resource_id = "test_resource_id"
    response = client.post(
        f"/location/{sample_location.location_id}/attach_resource",
        params={"resource_id": resource_id},
    )
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.resource_id is not None
    assert resource_id == returned_location.resource_id


def test_get_locations_with_data(client, sample_location):
    """Test getting all locations when data exists."""
    # Add a location
    client.post("/location", json=sample_location.model_dump())

    # Get all locations
    response = client.get("/locations")
    assert response.status_code == 200

    locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(locations) == 1
    assert locations[0].location_id == sample_location.location_id


def test_multiple_locations(client):
    """Test adding and retrieving multiple locations."""
    # Create multiple locations
    locations = [
        Location(
            location_id=new_ulid_str(),
            name="Location 1",
            description="First test location",
            x=10.0,
            y=20.0,
        ),
        Location(
            location_id=new_ulid_str(),
            name="Location 2",
            description="Second test location",
            x=30.0,
            y=40.0,
        ),
    ]

    # Add both locations
    for location in locations:
        response = client.post("/location", json=location.model_dump())
        assert response.status_code == 200

    # Get all locations
    response = client.get("/locations")
    assert response.status_code == 200

    returned_locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(returned_locations) == 2

    # Verify both locations are present
    returned_ids = {loc.location_id for loc in returned_locations}
    expected_ids = {loc.location_id for loc in locations}
    assert returned_ids == expected_ids


def test_location_state_persistence(client, sample_location):
    """Test that location state persists in Redis."""
    # Add a location
    response = client.post("/location", json=sample_location.model_dump())
    assert response.status_code == 200

    # Add lookup values
    lookup_values = {"position": [1, 2, 3], "config": "test_config"}
    response = client.post(
        f"/location/{sample_location.location_id}/add_lookup/test_robot",
        json=lookup_values,
    )
    assert response.status_code == 200

    # Attach a resource
    resource_id = "test_resource_123"
    response = client.post(
        f"/location/{sample_location.location_id}/attach_resource",
        params={"resource_id": resource_id},
    )
    assert response.status_code == 200

    # Verify all data persists by fetching the location
    response = client.get(f"/location/{sample_location.location_id}")
    assert response.status_code == 200

    location = Location.model_validate(response.json())
    assert location.lookup_values is not None
    assert "test_robot" in location.lookup_values
    assert location.lookup_values["test_robot"] == lookup_values
    assert location.resource_id == resource_id


def test_automatic_location_initialization_from_definition(redis_server: Redis):
    """Test that locations are automatically initialized from definition."""

    # Create a definition with locations
    location_def1 = LocationDefinition(
        location_name="auto_location_1",
        location_id=new_ulid_str(),
        description="Automatically initialized location 1",
        lookup={"robot1": [1, 2, 3], "robot2": {"x": 10, "y": 20}},
    )

    location_def2 = LocationDefinition(
        location_name="auto_location_2",
        location_id=new_ulid_str(),
        description="Automatically initialized location 2",
        lookup={"robot1": [4, 5, 6]},
    )

    definition = LocationManagerDefinition(
        name="Test Auto Location Manager",
        manager_id=new_ulid_str(),
        locations=[location_def1, location_def2],
    )

    settings = LocationManagerSettings(
        manager_id="test_auto_location_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    # Create manager with definition (this should trigger automatic initialization)
    manager = LocationManager(settings=settings, definition=definition)
    client = TestClient(manager.create_server())

    # Verify locations were automatically created
    response = client.get("/locations")
    assert response.status_code == 200

    returned_locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(returned_locations) == 2

    # Verify location details
    location_ids = {loc.location_id for loc in returned_locations}
    expected_ids = {location_def1.location_id, location_def2.location_id}
    assert location_ids == expected_ids

    # Verify lookup values were preserved
    for location in returned_locations:
        if location.location_id == location_def1.location_id:
            assert location.name == "auto_location_1"
            assert location.lookup_values == {
                "robot1": [1, 2, 3],
                "robot2": {"x": 10, "y": 20},
            }
        elif location.location_id == location_def2.location_id:
            assert location.name == "auto_location_2"
            assert location.lookup_values == {"robot1": [4, 5, 6]}
