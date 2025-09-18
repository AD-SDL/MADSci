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
    LocationTransferCapabilities,
    TransferWorkflowTemplate,
)
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.common.types.workflow_types import WorkflowDefinition
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


def test_set_representations(client, sample_location):
    """Test setting representations for a location."""
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Set representations
    representations = {"key1": "value1", "key2": "value2"}
    response = client.post(
        f"/location/{sample_location.location_id}/set_representation/test_node",
        json=representations,
    )
    assert response.status_code == 200

    returned_location = Location.model_validate(response.json())
    assert returned_location.representations is not None
    assert "test_node" in returned_location.representations
    assert returned_location.representations["test_node"] == representations


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

    # Set representations
    representations = {"position": [1, 2, 3], "config": "test_config"}
    response = client.post(
        f"/location/{sample_location.location_id}/set_representation/test_robot",
        json=representations,
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
    assert location.representations is not None
    assert "test_robot" in location.representations
    assert location.representations["test_robot"] == representations
    assert location.resource_id == resource_id


def test_automatic_location_initialization_from_definition(redis_server: Redis):
    """Test that locations are automatically initialized from definition."""

    # Create a definition with locations
    location_def1 = LocationDefinition(
        location_name="auto_location_1",
        location_id=new_ulid_str(),
        description="Automatically initialized location 1",
        representations={"robot1": [1, 2, 3], "robot2": {"x": 10, "y": 20}},
    )

    location_def2 = LocationDefinition(
        location_name="auto_location_2",
        location_id=new_ulid_str(),
        description="Automatically initialized location 2",
        representations={"robot1": [4, 5, 6]},
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

    # Verify representations were preserved
    for location in returned_locations:
        if location.location_id == location_def1.location_id:
            assert location.name == "auto_location_1"
            assert location.representations == {
                "robot1": [1, 2, 3],
                "robot2": {"x": 10, "y": 20},
            }
        elif location.location_id == location_def2.location_id:
            assert location.name == "auto_location_2"
            assert location.representations == {"robot1": [4, 5, 6]}


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


# Transfer Graph Tests


@pytest.fixture
def transfer_setup(redis_server: Redis):
    """Create a location manager with transfer capabilities for testing."""
    # Create sample transfer templates
    transfer_template1 = TransferWorkflowTemplate(
        node_name="robot_arm",
        workflow_template=WorkflowDefinition(name="pick_and_place_workflow"),
        cost_weight=1.0,
    )

    transfer_template2 = TransferWorkflowTemplate(
        node_name="conveyor",
        workflow_template=WorkflowDefinition(name="conveyor_transfer_workflow"),
        cost_weight=2.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[transfer_template1, transfer_template2]
    )

    # Create locations with representations that match transfer templates
    location1 = LocationDefinition(
        location_name="pickup_station",
        location_id=new_ulid_str(),
        description="Pickup station with robot arm and conveyor access",
        representations={
            "robot_arm": {"position": [1, 2, 3], "gripper": "closed"},
            "conveyor": {"belt_position": 0, "speed": 1.0},
        },
    )

    location2 = LocationDefinition(
        location_name="processing_station",
        location_id=new_ulid_str(),
        description="Processing station with robot arm access",
        representations={"robot_arm": {"position": [4, 5, 6], "gripper": "open"}},
    )

    location3 = LocationDefinition(
        location_name="storage_area",
        location_id=new_ulid_str(),
        description="Storage area with conveyor access",
        representations={"conveyor": {"belt_position": 10, "speed": 0.5}},
    )

    location4 = LocationDefinition(
        location_name="isolated_station",
        location_id=new_ulid_str(),
        description="Isolated station with no transfer connections",
        representations={"other_device": {"status": "idle"}},
    )

    definition = LocationManagerDefinition(
        name="Transfer Test Location Manager",
        manager_id=new_ulid_str(),
        locations=[location1, location2, location3, location4],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_transfer_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    return {
        "client": client,
        "manager": manager,
        "locations": {
            "pickup": location1.location_id,
            "processing": location2.location_id,
            "storage": location3.location_id,
            "isolated": location4.location_id,
        },
    }


def test_transfer_graph_construction(transfer_setup):
    """Test that transfer graph is correctly constructed from location representations."""
    manager = transfer_setup["manager"]

    # Build the transfer graph
    graph = manager._build_transfer_graph()

    # Expected edges based on shared representations:
    # pickup <-> processing (robot_arm)
    # pickup <-> storage (conveyor)
    # processing and storage should not be directly connected

    expected_edges = {
        (
            transfer_setup["locations"]["pickup"],
            transfer_setup["locations"]["processing"],
        ),
        (
            transfer_setup["locations"]["processing"],
            transfer_setup["locations"]["pickup"],
        ),
        (transfer_setup["locations"]["pickup"], transfer_setup["locations"]["storage"]),
        (transfer_setup["locations"]["storage"], transfer_setup["locations"]["pickup"]),
    }

    actual_edges = set(graph.keys())
    assert actual_edges == expected_edges

    # Verify edge costs are set correctly
    pickup_to_processing = graph[
        (
            transfer_setup["locations"]["pickup"],
            transfer_setup["locations"]["processing"],
        )
    ]
    assert pickup_to_processing.cost == 1.0  # robot_arm template cost

    pickup_to_storage = graph[
        (transfer_setup["locations"]["pickup"], transfer_setup["locations"]["storage"])
    ]
    assert pickup_to_storage.cost == 2.0  # conveyor template cost


def test_can_transfer_between_locations(transfer_setup):
    """Test the location compatibility checking logic."""
    manager = transfer_setup["manager"]

    # Get locations from state
    pickup_location = manager.state_handler.get_location(
        transfer_setup["locations"]["pickup"]
    )
    processing_location = manager.state_handler.get_location(
        transfer_setup["locations"]["processing"]
    )
    storage_location = manager.state_handler.get_location(
        transfer_setup["locations"]["storage"]
    )
    isolated_location = manager.state_handler.get_location(
        transfer_setup["locations"]["isolated"]
    )

    # Create transfer template for testing
    robot_template = TransferWorkflowTemplate(
        node_name="robot_arm",
        workflow_template=WorkflowDefinition(name="test_workflow"),
        cost_weight=1.0,
    )

    conveyor_template = TransferWorkflowTemplate(
        node_name="conveyor",
        workflow_template=WorkflowDefinition(name="test_workflow"),
        cost_weight=1.0,
    )

    nonexistent_template = TransferWorkflowTemplate(
        node_name="nonexistent_device",
        workflow_template=WorkflowDefinition(name="test_workflow"),
        cost_weight=1.0,
    )

    # Test compatible transfers
    assert manager._can_transfer_between_locations(
        pickup_location, processing_location, robot_template
    )
    assert manager._can_transfer_between_locations(
        pickup_location, storage_location, conveyor_template
    )

    # Test incompatible transfers
    assert not manager._can_transfer_between_locations(
        processing_location, storage_location, robot_template
    )
    assert not manager._can_transfer_between_locations(
        pickup_location, isolated_location, robot_template
    )
    assert not manager._can_transfer_between_locations(
        pickup_location, processing_location, nonexistent_template
    )


def test_shortest_transfer_path_direct(transfer_setup):
    """Test shortest path finding for direct transfers."""
    manager = transfer_setup["manager"]

    # Test direct path between connected locations
    path = manager._find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["processing"]
    )

    assert path is not None
    assert len(path) == 1
    assert path[0].source_location_id == transfer_setup["locations"]["pickup"]
    assert path[0].destination_location_id == transfer_setup["locations"]["processing"]
    assert path[0].transfer_template.node_name == "robot_arm"


def test_shortest_transfer_path_no_connection(transfer_setup):
    """Test shortest path finding when no path exists."""
    manager = transfer_setup["manager"]

    # Test path to isolated location (should return None)
    path = manager._find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["isolated"]
    )

    assert path is None


def test_shortest_transfer_path_same_location(transfer_setup):
    """Test shortest path finding for same source and destination."""
    manager = transfer_setup["manager"]

    # Test same location (should return empty path)
    path = manager._find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["pickup"]
    )

    assert path == []


def test_shortest_transfer_path_multi_hop(transfer_setup):
    """Test shortest path finding for multi-hop transfers."""
    manager = transfer_setup["manager"]

    # Add another location that creates a longer path
    # This would test processing -> pickup -> storage route
    path = manager._find_shortest_transfer_path(
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    )

    # Since processing and storage are not directly connected,
    # the path should go through pickup
    assert path is not None
    assert len(path) == 2
    assert path[0].source_location_id == transfer_setup["locations"]["processing"]
    assert path[0].destination_location_id == transfer_setup["locations"]["pickup"]
    assert path[1].source_location_id == transfer_setup["locations"]["pickup"]
    assert path[1].destination_location_id == transfer_setup["locations"]["storage"]


def test_composite_transfer_workflow(transfer_setup):
    """Test creation of composite transfer workflows."""
    manager = transfer_setup["manager"]

    # Get a transfer path
    path = manager._find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["processing"]
    )

    assert path is not None

    # Create composite workflow
    workflow = manager._composite_transfer_workflow(path, "test_resource_123")

    assert isinstance(workflow, WorkflowDefinition)
    assert "transfer_" in workflow.name
    # TODO: Add more detailed workflow composition tests when implementation is enhanced


def test_get_transfer_graph_endpoint(transfer_setup):
    """Test the transfer graph API endpoint."""
    client = transfer_setup["client"]

    response = client.get("/transfer/graph")
    assert response.status_code == 200

    graph_data = response.json()
    assert isinstance(graph_data, dict)

    # Verify adjacency list structure
    pickup_id = transfer_setup["locations"]["pickup"]
    assert pickup_id in graph_data

    # pickup should connect to both processing and storage
    expected_connections = {
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    }
    actual_connections = set(graph_data[pickup_id])
    assert actual_connections == expected_connections


def test_plan_transfer_endpoint_direct(transfer_setup):
    """Test the transfer planning API endpoint for direct transfers."""
    client = transfer_setup["client"]

    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": transfer_setup["locations"]["pickup"],
            "destination_location_id": transfer_setup["locations"]["processing"],
            "resource_id": "test_resource_123",
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    assert isinstance(workflow_data, dict)

    # Validate that a workflow definition is returned
    workflow = WorkflowDefinition.model_validate(workflow_data)
    assert "transfer_" in workflow.name


def test_plan_transfer_endpoint_no_path(transfer_setup):
    """Test the transfer planning API endpoint when no path exists."""
    client = transfer_setup["client"]

    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": transfer_setup["locations"]["pickup"],
            "destination_location_id": transfer_setup["locations"]["isolated"],
        },
    )

    assert response.status_code == 404
    error_data = response.json()
    assert "No transfer path exists" in error_data["detail"]


def test_plan_transfer_endpoint_invalid_location(transfer_setup):
    """Test the transfer planning API endpoint with invalid location IDs."""
    client = transfer_setup["client"]

    # Test invalid source location
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": "invalid_location_id",
            "destination_location_id": transfer_setup["locations"]["processing"],
        },
    )

    assert response.status_code == 404
    error_data = response.json()
    assert (
        "Source location" in error_data["detail"]
        and "not found" in error_data["detail"]
    )

    # Test invalid destination location
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": transfer_setup["locations"]["pickup"],
            "destination_location_id": "invalid_location_id",
        },
    )

    assert response.status_code == 404
    error_data = response.json()
    assert (
        "Destination location" in error_data["detail"]
        and "not found" in error_data["detail"]
    )


def test_get_location_resources_endpoint(transfer_setup):
    """Test the location resources API endpoint."""
    client = transfer_setup["client"]

    response = client.get(
        f"/location/{transfer_setup['locations']['pickup']}/resources"
    )
    assert response.status_code == 200

    resources = response.json()
    assert isinstance(resources, list)
    # Currently returns empty list as placeholder
    assert len(resources) == 0


def test_get_location_resources_endpoint_invalid_location(transfer_setup):
    """Test the location resources API endpoint with invalid location ID."""
    client = transfer_setup["client"]

    response = client.get("/location/invalid_location_id/resources")
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"]


def test_transfer_graph_without_transfer_capabilities(redis_server: Redis):
    """Test transfer graph behavior when no transfer capabilities are defined."""
    # Create a location manager without transfer capabilities
    definition = LocationManagerDefinition(
        name="No Transfer Location Manager",
        manager_id=new_ulid_str(),
        locations=[
            LocationDefinition(
                location_name="location1",
                location_id=new_ulid_str(),
                representations={"device": "config"},
            )
        ],
    )

    settings = LocationManagerSettings(
        manager_id="test_no_transfer_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Transfer graph should be empty
    graph = manager._build_transfer_graph()
    assert len(graph) == 0

    # API endpoint should return empty adjacency list
    response = client.get("/transfer/graph")
    assert response.status_code == 200
    assert response.json() == {}
