"""Tests for the LocationManager server."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerHealth,
    LocationManagerSettings,
)
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
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
    )


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    # Validate the response structure matches LocationManagerHealth
    health_data = response.json()
    health = LocationManagerHealth.model_validate(health_data)

    # Check that required fields are present
    assert isinstance(health.healthy, bool)
    assert isinstance(health.description, str)
    assert health.redis_connected is not None  # Should be True for test Redis
    assert isinstance(health.num_locations, int)
    assert health.num_locations >= 0


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


def test_set_references(client, sample_location):
    """Test setting references for a location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Set references
    references = {"key1": "value1", "key2": "value2"}
    response = client.post(
        f"/location/{sample_location.location_id}/set_reference/test_node",
        json=references,
    )
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.references is not None
    assert "test_node" in returned_location.references
    assert returned_location.references["test_node"] == references


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
        ),
        Location(
            location_id=new_ulid_str(),
            name="Location 2",
            description="Second test location",
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

    # Set references
    references = {"position": [1, 2, 3], "config": "test_config"}
    response = client.post(
        f"/location/{sample_location.location_id}/set_reference/test_robot",
        json=references,
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
    assert location.references is not None
    assert "test_robot" in location.references
    assert location.references["test_robot"] == references
    assert location.resource_id == resource_id


def test_automatic_location_initialization_from_definition(redis_server: Redis):
    """Test that locations are automatically initialized from definition."""

    # Create a definition with locations
    location_def1 = LocationDefinition(
        location_name="auto_location_1",
        location_id=new_ulid_str(),
        description="Automatically initialized location 1",
        references={"robot1": [1, 2, 3], "robot2": {"x": 10, "y": 20}},
    )

    location_def2 = LocationDefinition(
        location_name="auto_location_2",
        location_id=new_ulid_str(),
        description="Automatically initialized location 2",
        references={"robot1": [4, 5, 6]},
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

    # Verify references were preserved
    for location in returned_locations:
        if location.location_id == location_def1.location_id:
            assert location.name == "auto_location_1"
            assert location.references == {
                "robot1": [1, 2, 3],
                "robot2": {"x": 10, "y": 20},
            }
        elif location.location_id == location_def2.location_id:
            assert location.name == "auto_location_2"
            assert location.references == {"robot1": [4, 5, 6]}


def test_resource_initialization_prevents_duplicates(redis_server: Redis):
    """Test that resource initialization doesn't create duplicate resources on subsequent startups."""

    # Create a slot resource definition
    slot_resource_def = SlotResourceDefinition(
        resource_name="test_slot",
        resource_class="test_slot_class",
        capacity=1,
    )

    # Create a location definition with resource_definition
    location_def = LocationDefinition(
        location_name="location_with_resource",
        location_id=new_ulid_str(),
        description="Location with associated resource",
        resource_definition=slot_resource_def,
    )

    definition = LocationManagerDefinition(
        name="Test Resource Manager",
        manager_id=new_ulid_str(),
        locations=[location_def],
    )

    settings = LocationManagerSettings(
        manager_id="test_resource_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    # Mock the ResourceClient to track calls
    mock_resource_client = MagicMock()
    mock_resource = Mock()
    mock_resource.resource_id = "test_resource_123"
    mock_resource.resource_name = "test_slot"
    mock_resource.resource_class = "test_slot_class"
    mock_resource.base_type = Mock()
    mock_resource.base_type.value = "slot"
    mock_resource.capacity = 1

    # First startup - should create resource
    mock_resource_client.query_resource.return_value = []  # No existing resources
    mock_resource_client.add_or_update_resource.return_value = mock_resource

    # Create first manager instance (simulating first startup)
    manager1 = LocationManager(settings=settings, definition=definition)
    manager1.resource_client = mock_resource_client
    manager1.state_handler._redis_connection = redis_server

    # Re-run initialization to simulate startup behavior
    manager1._initialize_locations_from_definition()

    # Verify resource was created once
    assert mock_resource_client.add_or_update_resource.call_count == 1

    # Second startup - should NOT create another resource
    mock_resource_client.reset_mock()
    mock_resource_client.query_resource.return_value = [
        mock_resource
    ]  # Resource exists now
    mock_resource_client.add_or_update_resource.return_value = mock_resource

    # Create second manager instance (simulating restart)
    manager2 = LocationManager(settings=settings, definition=definition)
    manager2.resource_client = mock_resource_client
    manager2.state_handler._redis_connection = redis_server

    # Re-run initialization to simulate startup behavior
    manager2._initialize_locations_from_definition()

    # Verify query_resource was called to check for existing resources
    assert mock_resource_client.query_resource.call_count == 1

    # Verify no new resource was created on second startup
    # The implementation should detect existing resource and reuse it
    assert mock_resource_client.add_or_update_resource.call_count == 0


def test_resource_initialization_with_matching_existing_resource(redis_server: Redis):
    """Test that the system correctly identifies and reuses existing resources with same characteristics."""

    # Create a slot resource definition
    slot_resource_def = SlotResourceDefinition(
        resource_name="shared_slot",
        resource_class="shared_slot_class",
        capacity=1,
    )

    location_def = LocationDefinition(
        location_name="location_with_shared_resource",
        location_id=new_ulid_str(),
        description="Location sharing a resource",
        resource_definition=slot_resource_def,
    )

    definition = LocationManagerDefinition(
        name="Test Shared Resource Manager",
        manager_id=new_ulid_str(),
        locations=[location_def],
    )

    settings = LocationManagerSettings(
        manager_id="test_shared_resource_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    # Mock ResourceClient
    mock_resource_client = MagicMock()
    existing_resource = Mock()
    existing_resource.resource_id = "existing_resource_456"
    existing_resource.resource_name = "shared_slot"
    existing_resource.resource_class = "shared_slot_class"
    existing_resource.base_type = Mock()
    existing_resource.base_type.value = "slot"
    existing_resource.capacity = 1

    # Simulate finding an existing resource that matches our definition
    mock_resource_client.query_resource.return_value = [existing_resource]

    manager = LocationManager(settings=settings, definition=definition)
    manager.resource_client = mock_resource_client
    manager.state_handler._redis_connection = redis_server

    # Run initialization
    manager._initialize_locations_from_definition()

    # Verify that query_resource was called to check for existing resources
    assert mock_resource_client.query_resource.call_count >= 1

    # Verify that add_or_update_resource was NOT called (since resource already exists)
    assert mock_resource_client.add_or_update_resource.call_count == 0

    # Verify the location was associated with the existing resource
    client = TestClient(manager.create_server())
    response = client.get("/locations")
    assert response.status_code == 200

    locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(locations) == 1
    assert locations[0].resource_id == "existing_resource_456"
