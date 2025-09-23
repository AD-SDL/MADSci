"""Tests for the LocationManager server."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.location_types import (
    CapacityCostConfig,
    Location,
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerHealth,
    LocationManagerSettings,
    LocationTransferCapabilities,
    TransferStepTemplate,
    TransferTemplateOverrides,
)
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition, WorkflowParameters
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
        location_name="Test Location",
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
    """Test that resource initialization creates unique resources using templates."""

    # Create a location definition with resource_template_name
    location_def = LocationDefinition(
        location_name="location_with_resource",
        location_id=new_ulid_str(),
        description="Location with associated resource",
        resource_template_name="test_slot_template",
        resource_template_overrides={"resource_class": "test_slot_class"},
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

    # Mock create_resource_from_template to return a resource
    mock_resource_client.create_resource_from_template.return_value = mock_resource

    # Create manager instance
    manager = LocationManager(settings=settings, definition=definition)
    manager.resource_client = mock_resource_client
    manager.state_handler._redis_connection = redis_server

    # Run initialization to simulate startup behavior
    manager._initialize_locations_from_definition()

    # Verify that create_resource_from_template was called
    assert mock_resource_client.create_resource_from_template.call_count == 1

    # Verify resource was created with correct parameters
    call_args = mock_resource_client.create_resource_from_template.call_args
    assert call_args[1]["template_name"] == "test_slot_template"
    assert (
        "location_with_resource" in call_args[1]["resource_name"]
    )  # Should include location name
    assert call_args[1]["overrides"]["resource_class"] == "test_slot_class"
    assert call_args[1]["add_to_database"]

    # Verify location was created with correct resource_id
    client = TestClient(manager.create_server())
    response = client.get("/locations")
    assert response.status_code == 200

    locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(locations) == 1
    assert locations[0].resource_id == "test_resource_123"


def test_resource_initialization_with_matching_existing_resource(redis_server: Redis):
    """Test that the system creates resources from templates with proper error handling."""

    location_def = LocationDefinition(
        location_name="location_with_shared_resource",
        location_id=new_ulid_str(),
        description="Location sharing a resource",
        resource_template_name="shared_slot_template",
        resource_template_overrides={"resource_class": "shared_slot_class"},
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
    created_resource = Mock()
    created_resource.resource_id = "new_resource_456"

    # Mock template creation to succeed
    mock_resource_client.create_resource_from_template.return_value = created_resource

    manager = LocationManager(settings=settings, definition=definition)
    manager.resource_client = mock_resource_client
    manager.state_handler._redis_connection = redis_server

    # Run initialization
    manager._initialize_locations_from_definition()

    # Verify that create_resource_from_template was called
    assert mock_resource_client.create_resource_from_template.call_count == 1

    # Verify the location was associated with the new resource
    client = TestClient(manager.create_server())
    response = client.get("/locations")
    assert response.status_code == 200

    locations = [Location.model_validate(loc) for loc in response.json()]
    assert len(locations) == 1
    assert locations[0].resource_id == "new_resource_456"


# Transfer Graph Tests


@pytest.fixture
def transfer_setup(redis_server: Redis):
    """Create a location manager with transfer capabilities for testing."""
    # Create sample transfer templates with simplified format
    transfer_template1 = TransferStepTemplate(
        node_name="robotarm_1",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    transfer_template2 = TransferStepTemplate(
        node_name="conveyor",
        action="transfer",
        source_argument_name="from_location",
        target_argument_name="to_location",
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
            "robotarm_1": {"position": [1, 2, 3], "gripper": "closed"},
            "conveyor": {"belt_position": 0, "speed": 1.0},
        },
    )

    location2 = LocationDefinition(
        location_name="processing_station",
        location_id=new_ulid_str(),
        description="Processing station with robot arm access",
        representations={"robotarm_1": {"position": [4, 5, 6], "gripper": "open"}},
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
    graph = manager.transfer_planner._transfer_graph

    # Expected edges based on shared representations:
    # pickup <-> processing (robotarm_1)
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
    assert pickup_to_processing.cost == 1.0  # robotarm_1 template cost

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

    # Create transfer templates for testing with simplified format
    robot_template = TransferStepTemplate(
        node_name="robotarm_1",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    conveyor_template = TransferStepTemplate(
        node_name="conveyor",
        action="transfer",
        source_argument_name="from_location",
        target_argument_name="to_location",
        cost_weight=1.0,
    )

    nonexistent_template = TransferStepTemplate(
        node_name="nonexistent_device",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    # Test compatible transfers
    assert manager.transfer_planner._can_transfer_between_locations(
        pickup_location, processing_location, robot_template
    )
    assert manager.transfer_planner._can_transfer_between_locations(
        pickup_location, storage_location, conveyor_template
    )

    # Test incompatible transfers
    assert not manager.transfer_planner._can_transfer_between_locations(
        processing_location, storage_location, robot_template
    )
    assert not manager.transfer_planner._can_transfer_between_locations(
        pickup_location, isolated_location, robot_template
    )
    assert not manager.transfer_planner._can_transfer_between_locations(
        pickup_location, processing_location, nonexistent_template
    )


def test_shortest_transfer_path_direct(transfer_setup):
    """Test shortest path finding for direct transfers."""
    manager = transfer_setup["manager"]

    # Test direct path between connected locations
    path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["processing"]
    )

    assert path is not None
    assert len(path) == 1
    assert path[0].source_location_id == transfer_setup["locations"]["pickup"]
    assert path[0].destination_location_id == transfer_setup["locations"]["processing"]
    assert path[0].transfer_template.node_name == "robotarm_1"


def test_shortest_transfer_path_no_connection(transfer_setup):
    """Test shortest path finding when no path exists."""
    manager = transfer_setup["manager"]

    # Test path to isolated location (should return None)
    path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["isolated"]
    )

    assert path is None


def test_shortest_transfer_path_same_location(transfer_setup):
    """Test shortest path finding for same source and destination."""
    manager = transfer_setup["manager"]

    # Test same location (should return empty path)
    path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["pickup"]
    )

    assert path == []


def test_shortest_transfer_path_multi_hop(transfer_setup):
    """Test shortest path finding for multi-hop transfers."""
    manager = transfer_setup["manager"]

    # Add another location that creates a longer path
    # This would test processing -> pickup -> storage route
    path = manager.transfer_planner.find_shortest_transfer_path(
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


def test_multi_leg_transfer_workflow_step_count(transfer_setup):
    """Test that multi-leg transfers generate workflows with correct number of steps."""
    manager = transfer_setup["manager"]

    # Test direct transfer (1 hop)
    direct_path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["processing"]
    )
    assert direct_path is not None
    assert len(direct_path) == 1

    direct_workflow = manager.transfer_planner.create_composite_transfer_workflow(
        direct_path
    )
    assert isinstance(direct_workflow, WorkflowDefinition)
    assert len(direct_workflow.steps) == 1, (
        "Direct transfer should generate exactly 1 step"
    )

    # Test multi-hop transfer (2 hops: processing -> pickup -> storage)
    multi_hop_path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    )
    assert multi_hop_path is not None
    assert len(multi_hop_path) == 2

    multi_hop_workflow = manager.transfer_planner.create_composite_transfer_workflow(
        multi_hop_path
    )
    assert isinstance(multi_hop_workflow, WorkflowDefinition)
    assert len(multi_hop_workflow.steps) == 2, (
        "Multi-hop transfer should generate exactly 2 steps"
    )


def test_multi_leg_transfer_workflow_node_ordering(transfer_setup):
    """Test that multi-leg transfers generate steps on correct nodes in correct order."""
    manager = transfer_setup["manager"]

    # Get multi-hop transfer path: processing -> pickup -> storage
    # This should use: robotarm_1 (processing->pickup) then conveyor (pickup->storage)
    path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    )

    assert path is not None
    assert len(path) == 2

    # Verify path structure matches expected route
    assert path[0].source_location_id == transfer_setup["locations"]["processing"]
    assert path[0].destination_location_id == transfer_setup["locations"]["pickup"]
    assert path[0].transfer_template.node_name == "robotarm_1"

    assert path[1].source_location_id == transfer_setup["locations"]["pickup"]
    assert path[1].destination_location_id == transfer_setup["locations"]["storage"]
    assert path[1].transfer_template.node_name == "conveyor"

    # Generate workflow and verify step ordering
    workflow = manager.transfer_planner.create_composite_transfer_workflow(path)
    assert isinstance(workflow, WorkflowDefinition)
    assert len(workflow.steps) == 2

    # First step should be robotarm_1 transfer from processing to pickup
    step1 = workflow.steps[0]
    assert step1.node == "robotarm_1"
    assert step1.name == "transfer_step_1"
    assert step1.key == "transfer_step_1"
    assert "source_location" in step1.locations
    assert "target_location" in step1.locations
    # Verify step uses direct location names
    assert step1.locations["source_location"] == "processing_station"
    assert step1.locations["target_location"] == "pickup_station"

    # Second step should be conveyor transfer from pickup to storage
    step2 = workflow.steps[1]
    assert step2.node == "conveyor"
    assert step2.name == "transfer_step_2"
    assert step2.key == "transfer_step_2"
    assert "from_location" in step2.locations
    assert "to_location" in step2.locations
    # Verify step uses direct location names
    assert step2.locations["from_location"] == "pickup_station"
    assert step2.locations["to_location"] == "storage_area"


def test_multi_leg_transfer_workflow_parameters_injection(transfer_setup):
    """Test that workflow parameters are simplified for multi-leg transfers."""
    manager = transfer_setup["manager"]

    # Get multi-hop transfer path
    path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    )

    assert path is not None
    workflow = manager.transfer_planner.create_composite_transfer_workflow(path)

    # Verify workflow has simplified parameters (empty WorkflowParameters)
    assert workflow.parameters is not None
    assert isinstance(workflow.parameters, WorkflowParameters)
    # The simplified implementation should have no complex parameters
    assert len(workflow.parameters.json_inputs) == 0

    # Verify steps use direct location names instead of parameter references
    step1 = workflow.steps[0]
    step2 = workflow.steps[1]

    # Check that location names are directly assigned, not parameter references
    assert step1.locations["source_location"] == "processing_station"
    assert step1.locations["target_location"] == "pickup_station"
    assert step2.locations["from_location"] == "pickup_station"
    assert step2.locations["to_location"] == "storage_area"


def test_workflow_generation_with_various_path_lengths(transfer_setup):
    """Test workflow generation for different path lengths to ensure scalability."""
    manager = transfer_setup["manager"]

    # Test same location (0 hops)
    same_location_path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["pickup"]
    )
    assert same_location_path == []

    same_location_workflow = (
        manager.transfer_planner.create_composite_transfer_workflow(same_location_path)
    )
    assert isinstance(same_location_workflow, WorkflowDefinition)
    assert len(same_location_workflow.steps) == 0, (
        "Same location transfer should generate 0 steps"
    )

    # Test direct transfer (1 hop)
    direct_path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["pickup"], transfer_setup["locations"]["processing"]
    )
    assert len(direct_path) == 1

    direct_workflow = manager.transfer_planner.create_composite_transfer_workflow(
        direct_path
    )
    assert len(direct_workflow.steps) == 1

    # Test multi-hop transfer (2 hops)
    multi_hop_path = manager.transfer_planner.find_shortest_transfer_path(
        transfer_setup["locations"]["processing"],
        transfer_setup["locations"]["storage"],
    )
    assert len(multi_hop_path) == 2

    multi_hop_workflow = manager.transfer_planner.create_composite_transfer_workflow(
        multi_hop_path
    )
    assert len(multi_hop_workflow.steps) == 2

    # Verify that each workflow step count matches path length
    assert len(direct_workflow.steps) == len(direct_path)
    assert len(multi_hop_workflow.steps) == len(multi_hop_path)


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
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    assert isinstance(workflow_data, dict)

    # Validate that a workflow definition is returned
    workflow = WorkflowDefinition.model_validate(workflow_data)
    assert "Transfer:" in workflow.name

    assert len(workflow.steps) == 1


def test_plan_transfer_endpoint_multi_hop(transfer_setup):
    """Test the transfer planning API endpoint for multi-hop transfers."""
    client = transfer_setup["client"]

    # Request multi-hop transfer: processing -> pickup -> storage
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": transfer_setup["locations"]["processing"],
            "destination_location_id": transfer_setup["locations"]["storage"],
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    assert isinstance(workflow_data, dict)

    # Validate workflow structure
    workflow = WorkflowDefinition.model_validate(workflow_data)
    assert "Transfer:" in workflow.name
    assert len(workflow.steps) == 2, "Multi-hop transfer should generate 2 steps"

    # Verify step sequence and nodes
    step1 = workflow.steps[0]
    assert step1.node == "robotarm_1"
    assert step1.name == "transfer_step_1"
    assert step1.locations["source_location"] == "processing_station"
    assert step1.locations["target_location"] == "pickup_station"

    step2 = workflow.steps[1]
    assert step2.node == "conveyor"
    assert step2.name == "transfer_step_2"
    assert step2.locations["from_location"] == "pickup_station"
    assert step2.locations["to_location"] == "storage_area"

    # Verify workflow parameters are simplified (no complex parameter injection)
    assert workflow.parameters is not None
    assert (
        len(workflow.parameters.json_inputs) == 0
    )  # Simplified approach uses direct names


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
    # Should return a ResourceHierarchy object
    hierarchy = ResourceHierarchy.model_validate(resources)

    # For location with no attached resource, should return empty hierarchy
    assert hierarchy.ancestor_ids == []
    assert hierarchy.resource_id == ""
    assert hierarchy.descendant_ids == {}


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
    graph = manager.transfer_planner._transfer_graph
    assert len(graph) == 0

    # API endpoint should return empty adjacency list
    response = client.get("/transfer/graph")
    assert response.status_code == 200
    assert response.json() == {}


def test_get_location_by_name_endpoint(redis_server: Redis):
    """Test the get location by name API endpoint."""
    location_def = LocationDefinition(
        location_name="test_location_by_name",
        location_id=new_ulid_str(),
        description="A test location for name-based lookup",
    )

    definition = LocationManagerDefinition(
        name="Test Manager for Name Lookup",
        manager_id=new_ulid_str(),
        locations=[location_def],
    )

    settings = LocationManagerSettings(
        manager_id="test_name_lookup_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test successful lookup by name using query parameter
    response = client.get("/location?name=test_location_by_name")
    assert response.status_code == 200

    location_data = response.json()
    assert location_data["location_name"] == "test_location_by_name"
    assert location_data["location_id"] == location_def.location_id
    assert location_data["description"] == "A test location for name-based lookup"


def test_get_location_by_name_endpoint_not_found(redis_server: Redis):
    """Test the get location by name API endpoint when location doesn't exist."""
    definition = LocationManagerDefinition(
        name="Test Manager for Name Lookup",
        manager_id=new_ulid_str(),
        locations=[],  # No locations
    )

    settings = LocationManagerSettings(
        manager_id="test_name_lookup_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test lookup of non-existent location using query parameter
    response = client.get("/location?name=nonexistent_location")
    assert response.status_code == 404

    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    assert "nonexistent_location" in error_data["detail"]


def test_get_location_by_name_endpoint_multiple_locations(redis_server: Redis):
    """Test the get location by name API endpoint with multiple locations."""
    location_def1 = LocationDefinition(
        location_name="robot_station",
        location_id=new_ulid_str(),
        description="Robot workstation",
    )

    location_def2 = LocationDefinition(
        location_name="liquid_station",
        location_id=new_ulid_str(),
        description="Liquid handling station",
    )

    location_def3 = LocationDefinition(
        location_name="storage_rack",
        location_id=new_ulid_str(),
        description="Storage rack",
    )

    definition = LocationManagerDefinition(
        name="Test Manager with Multiple Locations",
        manager_id=new_ulid_str(),
        locations=[location_def1, location_def2, location_def3],
    )

    settings = LocationManagerSettings(
        manager_id="test_multiple_locations_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test lookup of first location using query parameter
    response = client.get("/location?name=robot_station")
    assert response.status_code == 200
    assert response.json()["location_name"] == "robot_station"
    assert response.json()["location_id"] == location_def1.location_id

    # Test lookup of second location using query parameter
    response = client.get("/location?name=liquid_station")
    assert response.status_code == 200
    assert response.json()["location_name"] == "liquid_station"
    assert response.json()["location_id"] == location_def2.location_id

    # Test lookup of third location using query parameter
    response = client.get("/location?name=storage_rack")
    assert response.status_code == 200
    assert response.json()["location_name"] == "storage_rack"
    assert response.json()["location_id"] == location_def3.location_id

    # Test lookup of non-existent location using query parameter
    response = client.get("/location?name=nonexistent")
    assert response.status_code == 404


def test_get_location_query_parameter_validation(redis_server: Redis):
    """Test query parameter validation for the new location endpoint."""
    definition = LocationManagerDefinition(
        name="Test Manager for Query Validation",
        manager_id=new_ulid_str(),
        locations=[],
    )

    settings = LocationManagerSettings(
        manager_id="test_query_validation_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test missing both parameters
    response = client.get("/location")
    assert response.status_code == 400
    error_data = response.json()
    assert "exactly one" in error_data["detail"].lower()

    # Test providing both parameters
    response = client.get("/location?location_id=test_id&name=test_name")
    assert response.status_code == 400
    error_data = response.json()
    assert "exactly one" in error_data["detail"].lower()


def test_get_location_by_id_query_parameter(redis_server: Redis):
    """Test lookup by location_id using query parameter."""
    location_def = LocationDefinition(
        location_name="test_location_by_id",
        location_id=new_ulid_str(),
        description="A test location for ID-based lookup via query parameter",
    )

    definition = LocationManagerDefinition(
        name="Test Manager for ID Lookup via Query",
        manager_id=new_ulid_str(),
        locations=[location_def],
    )

    settings = LocationManagerSettings(
        manager_id="test_id_lookup_query_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test successful lookup by ID using query parameter
    response = client.get(f"/location?location_id={location_def.location_id}")
    assert response.status_code == 200

    location_data = response.json()
    assert location_data["location_name"] == "test_location_by_id"
    assert location_data["location_id"] == location_def.location_id
    assert (
        location_data["description"]
        == "A test location for ID-based lookup via query parameter"
    )

    # Test lookup of non-existent ID using query parameter
    response = client.get("/location?location_id=nonexistent_id")
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    assert "nonexistent_id" in error_data["detail"]


# Non-transfer location tests
def test_non_transfer_location_creation(redis_server: Redis):
    """Test creating locations with allow_transfers=False."""
    non_transfer_location = LocationDefinition(
        location_name="non_transfer_station",
        location_id=new_ulid_str(),
        description="A station that doesn't allow transfers",
        allow_transfers=False,
    )

    transfer_location = LocationDefinition(
        location_name="transfer_station",
        location_id=new_ulid_str(),
        description="A station that allows transfers",
        allow_transfers=True,
    )

    definition = LocationManagerDefinition(
        name="Test Manager with Non-transfer Locations",
        manager_id=new_ulid_str(),
        locations=[non_transfer_location, transfer_location],
    )

    settings = LocationManagerSettings(
        manager_id="test_non_transfer_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Check that locations are created with correct allow_transfers values
    response = client.get(f"/location?location_id={non_transfer_location.location_id}")
    assert response.status_code == 200
    location_data = response.json()
    assert location_data["allow_transfers"] is False

    response = client.get(f"/location?location_id={transfer_location.location_id}")
    assert response.status_code == 200
    location_data = response.json()
    assert location_data["allow_transfers"] is True


def test_non_transfer_location_excluded_from_graph(redis_server: Redis):
    """Test that non-transfer locations are excluded from transfer graph construction."""
    # Create transfer templates
    robot_template = TransferStepTemplate(
        node_name="robot_arm",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[robot_template]
    )

    # Create locations - some allow transfers, others don't
    transfer_loc1 = LocationDefinition(
        location_name="transfer_station_1",
        location_id=new_ulid_str(),
        representations={"robot_arm": {"position": [1, 0, 0]}},
        allow_transfers=True,
    )

    transfer_loc2 = LocationDefinition(
        location_name="transfer_station_2",
        location_id=new_ulid_str(),
        representations={"robot_arm": {"position": [2, 0, 0]}},
        allow_transfers=True,
    )

    non_transfer_loc = LocationDefinition(
        location_name="non_transfer_station",
        location_id=new_ulid_str(),
        representations={"robot_arm": {"position": [0, 1, 0]}},
        allow_transfers=False,
    )

    definition = LocationManagerDefinition(
        name="Test Manager with Non-transfer Graph",
        manager_id=new_ulid_str(),
        locations=[transfer_loc1, transfer_loc2, non_transfer_loc],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_non_transfer_graph_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Check the transfer graph
    transfer_graph = manager.transfer_planner._transfer_graph

    # Should have edge between transfer_loc1 and transfer_loc2 in both directions
    assert (transfer_loc1.location_id, transfer_loc2.location_id) in transfer_graph
    assert (transfer_loc2.location_id, transfer_loc1.location_id) in transfer_graph

    # Should NOT have any edges involving non_transfer_loc
    for src, dst in transfer_graph:
        assert src != non_transfer_loc.location_id
        assert dst != non_transfer_loc.location_id


def test_non_transfer_location_plan_transfer_error(redis_server: Redis):
    """Test that planning transfers to/from non-transfer locations raises appropriate errors."""
    # Create transfer templates
    robot_template = TransferStepTemplate(
        node_name="robot_arm",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[robot_template]
    )

    transfer_loc = LocationDefinition(
        location_name="transfer_station",
        location_id=new_ulid_str(),
        representations={"robot_arm": {"position": [1, 0, 0]}},
        allow_transfers=True,
    )

    non_transfer_loc = LocationDefinition(
        location_name="non_transfer_station",
        location_id=new_ulid_str(),
        representations={"robot_arm": {"position": [0, 1, 0]}},
        allow_transfers=False,
    )

    definition = LocationManagerDefinition(
        name="Test Manager for Non-transfer Error Testing",
        manager_id=new_ulid_str(),
        locations=[transfer_loc, non_transfer_loc],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_non_transfer_error_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test transfer FROM non-transfer location
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": non_transfer_loc.location_id,
            "destination_location_id": transfer_loc.location_id,
        },
    )
    assert response.status_code == 400
    error_data = response.json()
    assert "does not allow transfers" in error_data["detail"]
    assert "non_transfer_station" in error_data["detail"]

    # Test transfer TO non-transfer location
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": transfer_loc.location_id,
            "destination_location_id": non_transfer_loc.location_id,
        },
    )
    assert response.status_code == 400
    error_data = response.json()
    assert "does not allow transfers" in error_data["detail"]
    assert "non_transfer_station" in error_data["detail"]


def test_location_definition_allow_transfers_default():
    """Test that LocationDefinition.allow_transfers defaults to True."""
    # Create location without specifying allow_transfers
    location_def = LocationDefinition(
        location_name="default_location",
        location_id=new_ulid_str(),
    )

    assert location_def.allow_transfers is True

    # Create location explicitly setting allow_transfers=True
    location_def_true = LocationDefinition(
        location_name="explicit_true_location",
        location_id=new_ulid_str(),
        allow_transfers=True,
    )

    assert location_def_true.allow_transfers is True

    # Create location explicitly setting allow_transfers=False
    location_def_false = LocationDefinition(
        location_name="explicit_false_location",
        location_id=new_ulid_str(),
        allow_transfers=False,
    )

    assert location_def_false.allow_transfers is False


def test_location_allow_transfers_default():
    """Test that Location.allow_transfers defaults to True."""
    # Create location without specifying allow_transfers
    location = Location(
        location_name="default_location",
        location_id=new_ulid_str(),
    )

    assert location.allow_transfers is True

    # Create location explicitly setting allow_transfers=True
    location_true = Location(
        location_name="explicit_true_location",
        location_id=new_ulid_str(),
        allow_transfers=True,
    )

    assert location_true.allow_transfers is True

    # Create location explicitly setting allow_transfers=False
    location_false = Location(
        location_name="explicit_false_location",
        location_id=new_ulid_str(),
        allow_transfers=False,
    )

    assert location_false.allow_transfers is False


# Override Transfer Template Tests


@pytest.fixture
def override_transfer_setup(redis_server: Redis):
    """Create a location manager with override transfer templates for testing."""
    # Create standard transfer templates
    default_robot_template = TransferStepTemplate(
        node_name="robot_default",
        action="transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=5.0,
    )

    default_conveyor_template = TransferStepTemplate(
        node_name="conveyor_default",
        action="move",
        source_argument_name="from_location",
        target_argument_name="to_location",
        cost_weight=3.0,
    )

    # Create override templates
    special_robot_template = TransferStepTemplate(
        node_name="robot_special",
        action="special_transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
    )

    fast_conveyor_template = TransferStepTemplate(
        node_name="conveyor_fast",
        action="fast_move",
        source_argument_name="from_location",
        target_argument_name="to_location",
        cost_weight=0.5,
    )

    # Create override configuration
    overrides = TransferTemplateOverrides(
        source_overrides={
            "station_a": [special_robot_template],
        },
        destination_overrides={
            "station_c": [fast_conveyor_template],
        },
        pair_overrides={
            "station_a": {
                "station_b": [special_robot_template, fast_conveyor_template],
            },
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_robot_template, default_conveyor_template],
        override_transfer_templates=overrides,
    )

    # Create locations with representations that support all templates
    station_a = LocationDefinition(
        location_name="station_a",
        location_id=new_ulid_str(),
        description="Station A with all device access",
        representations={
            "robot_default": {"position": [1, 0, 0]},
            "robot_special": {"position": [1, 0, 0]},
            "conveyor_default": {"belt_position": 0},
            "conveyor_fast": {"belt_position": 0},
        },
    )

    station_b = LocationDefinition(
        location_name="station_b",
        location_id=new_ulid_str(),
        description="Station B with all device access",
        representations={
            "robot_default": {"position": [2, 0, 0]},
            "robot_special": {"position": [2, 0, 0]},
            "conveyor_default": {"belt_position": 1},
            "conveyor_fast": {"belt_position": 1},
        },
    )

    station_c = LocationDefinition(
        location_name="station_c",
        location_id=new_ulid_str(),
        description="Station C with all device access",
        representations={
            "robot_default": {"position": [3, 0, 0]},
            "robot_special": {"position": [3, 0, 0]},
            "conveyor_default": {"belt_position": 2},
            "conveyor_fast": {"belt_position": 2},
        },
    )

    station_d = LocationDefinition(
        location_name="station_d",
        location_id=new_ulid_str(),
        description="Station D with all device access",
        representations={
            "robot_default": {"position": [4, 0, 0]},
            "robot_special": {"position": [4, 0, 0]},
            "conveyor_default": {"belt_position": 3},
            "conveyor_fast": {"belt_position": 3},
        },
    )

    definition = LocationManagerDefinition(
        name="Override Transfer Test Manager",
        manager_id=new_ulid_str(),
        locations=[station_a, station_b, station_c, station_d],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_override_transfer_manager",
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
            "station_a": station_a.location_id,
            "station_b": station_b.location_id,
            "station_c": station_c.location_id,
            "station_d": station_d.location_id,
        },
    }


def test_pair_override_templates_highest_priority(override_transfer_setup):
    """Test that pair-specific overrides have highest priority."""
    manager = override_transfer_setup["manager"]

    # Get edge from station_a to station_b - should use pair override
    graph = manager.transfer_planner._transfer_graph
    edge_key = (
        override_transfer_setup["locations"]["station_a"],
        override_transfer_setup["locations"]["station_b"],
    )

    # Should have exactly one edge (the best one from the pair override)
    assert edge_key in graph
    edge = graph[edge_key]

    # Should use the lowest cost template from pair override (conveyor_fast with cost 0.5)
    assert edge.transfer_template.node_name == "conveyor_fast"
    assert edge.transfer_template.action == "fast_move"
    assert edge.cost == 0.5

    # Should NOT use default templates for this pair
    assert edge.transfer_template.node_name != "robot_default"
    assert edge.transfer_template.node_name != "conveyor_default"


def test_source_override_templates(override_transfer_setup):
    """Test that source-specific overrides are used when no pair override exists."""
    manager = override_transfer_setup["manager"]

    # Get edge FROM station_a to station_c (no pair override, but source override exists)
    graph = manager.transfer_planner._transfer_graph
    edge_key = (
        override_transfer_setup["locations"]["station_a"],
        override_transfer_setup["locations"]["station_c"],
    )

    # Should have exactly one edge using source override
    assert edge_key in graph
    edge = graph[edge_key]

    # Should use source override (special_robot_template with cost 1.0)
    assert edge.transfer_template.node_name == "robot_special"
    assert edge.transfer_template.action == "special_transfer"
    assert edge.cost == 1.0

    # Should NOT use default robot template for this source
    assert edge.transfer_template.node_name != "robot_default"


def test_destination_override_templates(override_transfer_setup):
    """Test that destination-specific overrides are used when no pair or source override exists."""
    manager = override_transfer_setup["manager"]

    # Get edge TO station_c from station_d (no pair override, no source override from station_d)
    graph = manager.transfer_planner._transfer_graph
    edge_key = (
        override_transfer_setup["locations"]["station_d"],
        override_transfer_setup["locations"]["station_c"],
    )

    # Should have exactly one edge using destination override
    assert edge_key in graph
    edge = graph[edge_key]

    # Should use destination override (fast_conveyor_template with cost 0.5)
    assert edge.transfer_template.node_name == "conveyor_fast"
    assert edge.transfer_template.action == "fast_move"
    assert edge.cost == 0.5

    # Should NOT use default conveyor template for this destination
    assert edge.transfer_template.node_name != "conveyor_default"


def test_default_templates_when_no_overrides(override_transfer_setup):
    """Test that default templates are used when no overrides apply."""
    manager = override_transfer_setup["manager"]

    # Get edge from station_d to station_b (no overrides apply)
    graph = manager.transfer_planner._transfer_graph
    edge_key = (
        override_transfer_setup["locations"]["station_d"],
        override_transfer_setup["locations"]["station_b"],
    )

    # Should have exactly one edge using default templates
    assert edge_key in graph
    edge = graph[edge_key]

    # Should use the best default template (conveyor_default with cost 3.0 vs robot_default with cost 5.0)
    assert edge.transfer_template.node_name == "conveyor_default"
    assert edge.transfer_template.action == "move"
    assert edge.cost == 3.0

    # Should NOT use override templates
    assert edge.transfer_template.node_name != "robot_special"
    assert edge.transfer_template.node_name != "conveyor_fast"


def test_override_templates_with_location_ids(redis_server: Redis):
    """Test that override templates work with location IDs instead of names."""
    # Create locations
    station_x = LocationDefinition(
        location_name="station_x",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    station_y = LocationDefinition(
        location_name="station_y",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [2, 0, 0]}},
    )

    # Create override using location IDs
    special_template = TransferStepTemplate(
        node_name="robot",
        action="special_transfer",
        cost_weight=0.1,
    )

    overrides = TransferTemplateOverrides(
        pair_overrides={
            station_x.location_id: {  # Use location_id instead of name
                station_y.location_id: [special_template],
            },
        },
    )

    default_template = TransferStepTemplate(
        node_name="robot",
        action="default_transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_template],
        override_transfer_templates=overrides,
    )

    definition = LocationManagerDefinition(
        name="ID Override Test Manager",
        manager_id=new_ulid_str(),
        locations=[station_x, station_y],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_id_override_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Check that override is applied based on location ID
    graph = manager.transfer_planner._transfer_graph
    edge_key = (station_x.location_id, station_y.location_id)

    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.transfer_template.action == "special_transfer"
    assert edge.cost == 0.1


def test_override_templates_with_mixed_keys(redis_server: Redis):
    """Test that override templates work with mixed location names and IDs."""
    # Create locations
    station_1 = LocationDefinition(
        location_name="mixed_station_1",
        location_id=new_ulid_str(),
        representations={"device": {"config": "a"}},
    )

    station_2 = LocationDefinition(
        location_name="mixed_station_2",
        location_id=new_ulid_str(),
        representations={"device": {"config": "b"}},
    )

    # Create overrides using mixed keys
    override_template = TransferStepTemplate(
        node_name="device",
        action="override_action",
        cost_weight=0.5,
    )

    overrides = TransferTemplateOverrides(
        source_overrides={
            "mixed_station_1": [override_template],  # Use name
        },
        destination_overrides={
            station_1.location_id: [
                override_template
            ],  # Use ID for station_1 as destination
        },
    )

    default_template = TransferStepTemplate(
        node_name="device",
        action="default_action",
        cost_weight=2.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_template],
        override_transfer_templates=overrides,
    )

    definition = LocationManagerDefinition(
        name="Mixed Keys Test Manager",
        manager_id=new_ulid_str(),
        locations=[station_1, station_2],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_mixed_keys_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    graph = manager.transfer_planner._transfer_graph

    # Test source override by name (station_1 -> station_2: source override from station_1)
    edge_key_1to2 = (station_1.location_id, station_2.location_id)
    assert edge_key_1to2 in graph
    edge_1to2 = graph[edge_key_1to2]
    assert edge_1to2.transfer_template.action == "override_action"

    # Test destination override by ID (station_2 -> station_1: destination override to station_1)
    edge_key_2to1 = (station_2.location_id, station_1.location_id)
    assert edge_key_2to1 in graph
    edge_2to1 = graph[edge_key_2to1]
    assert edge_2to1.transfer_template.action == "override_action"


def test_plan_transfer_with_overrides(override_transfer_setup):
    """Test that transfer planning uses override templates correctly."""
    client = override_transfer_setup["client"]

    # Test transfer that should use pair override (station_a -> station_b)
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": override_transfer_setup["locations"]["station_a"],
            "destination_location_id": override_transfer_setup["locations"][
                "station_b"
            ],
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    # Should create a workflow with minimum cost path using override templates
    assert len(workflow.steps) == 1

    # The step should use one of the pair override templates (robot_special or conveyor_fast)
    step = workflow.steps[0]
    assert step.node in ["robot_special", "conveyor_fast"]
    assert step.action in ["special_transfer", "fast_move"]


def test_no_override_templates_defined(redis_server: Redis):
    """Test that system works correctly when no override templates are defined."""
    # Create basic transfer capabilities without overrides
    default_template = TransferStepTemplate(
        node_name="basic_robot",
        action="basic_transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_template],
        # No override_transfer_templates defined
    )

    station_1 = LocationDefinition(
        location_name="basic_station_1",
        location_id=new_ulid_str(),
        representations={"basic_robot": {"position": [0, 0, 0]}},
    )

    station_2 = LocationDefinition(
        location_name="basic_station_2",
        location_id=new_ulid_str(),
        representations={"basic_robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Basic Transfer Manager",
        manager_id=new_ulid_str(),
        locations=[station_1, station_2],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_basic_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Should work normally with default templates
    graph = manager.transfer_planner._transfer_graph
    assert len(graph) == 2  # Bidirectional edge

    # Verify templates are the default ones
    for edge in graph.values():
        assert edge.transfer_template.node_name == "basic_robot"
        assert edge.transfer_template.action == "basic_transfer"


def test_empty_override_templates(redis_server: Redis):
    """Test that system works correctly when override templates are defined but empty."""
    # Create transfer capabilities with empty overrides
    default_template = TransferStepTemplate(
        node_name="standard_robot",
        action="standard_transfer",
        cost_weight=1.0,
    )

    empty_overrides = TransferTemplateOverrides()  # All fields will be None

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_template],
        override_transfer_templates=empty_overrides,
    )

    station_1 = LocationDefinition(
        location_name="empty_override_station_1",
        location_id=new_ulid_str(),
        representations={"standard_robot": {"position": [0, 0, 0]}},
    )

    station_2 = LocationDefinition(
        location_name="empty_override_station_2",
        location_id=new_ulid_str(),
        representations={"standard_robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Empty Override Manager",
        manager_id=new_ulid_str(),
        locations=[station_1, station_2],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_empty_override_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Should work normally with default templates
    graph = manager.transfer_planner._transfer_graph
    assert len(graph) == 2  # Bidirectional edge

    # Verify templates are the default ones
    for edge in graph.values():
        assert edge.transfer_template.node_name == "standard_robot"
        assert edge.transfer_template.action == "standard_transfer"


# Capacity-Aware Transfer Planning Tests


@pytest.fixture
def mock_resource():
    """Mock resource for capacity testing."""

    class MockResource:
        def __init__(self, quantity=0, capacity=None):
            self.quantity = quantity
            self.capacity = capacity
            self.resource_id = new_ulid_str()

    return MockResource


def test_capacity_cost_adjustment_disabled(redis_server: Redis):
    """Test that capacity cost adjustments are not applied when disabled."""
    # Create basic setup without capacity config
    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        # No capacity_cost_config - defaults to disabled
    )

    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Capacity Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    # Create manager without resource client to test disabled path
    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Transfer planner should not have resource client
    assert (
        manager.transfer_planner.resource_client is not None
    )  # Has resource client by default

    # Check that costs are not adjusted (should be base cost)
    graph = manager.transfer_planner._transfer_graph
    edge_key = (location_a.location_id, location_b.location_id)
    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.cost == 1.0  # Should be base cost without adjustments


def test_capacity_cost_adjustment_enabled_no_resource(redis_server: Redis):
    """Test capacity cost adjustment when enabled but destination has no resource."""
    # Create setup with capacity config enabled
    capacity_config = CapacityCostConfig(
        enabled=True,
        high_capacity_threshold=0.8,
        full_capacity_threshold=1.0,
        high_capacity_multiplier=2.0,
        full_capacity_multiplier=10.0,
    )

    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        capacity_cost_config=capacity_config,
    )

    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
        # No resource_id attached
    )

    definition = LocationManagerDefinition(
        name="Capacity Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Check that costs are not adjusted when no resource attached
    graph = manager.transfer_planner._transfer_graph
    edge_key = (location_a.location_id, location_b.location_id)
    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.cost == 1.0  # Should be base cost without adjustments


def test_capacity_cost_adjustment_with_mock_resource(
    redis_server: Redis, mock_resource
):
    """Test capacity cost adjustments with various capacity levels."""
    # Create setup with capacity config enabled
    capacity_config = CapacityCostConfig(
        enabled=True,
        high_capacity_threshold=0.8,
        full_capacity_threshold=1.0,
        high_capacity_multiplier=2.0,
        full_capacity_multiplier=10.0,
    )

    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        capacity_cost_config=capacity_config,
    )

    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Capacity Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Test different capacity scenarios by mocking the resource client
    original_get_resource = manager.transfer_planner.resource_client.get_resource

    # Test 1: Low capacity utilization (no multiplier)
    def mock_get_resource_low_capacity(resource_id):  # noqa: ARG001
        return mock_resource(quantity=5, capacity=10)  # 50% utilization

    manager.transfer_planner.resource_client.get_resource = (
        mock_get_resource_low_capacity
    )

    # Attach a resource to location_b
    location_b_state = manager.state_handler.get_location(location_b.location_id)
    location_b_state.resource_id = "test_resource_id"
    manager.state_handler.update_location(location_b.location_id, location_b_state)

    # Rebuild graph to test capacity adjustments
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge_key = (location_a.location_id, location_b.location_id)
    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.cost == 1.0  # No multiplier for 50% utilization

    # Test 2: High capacity utilization (2x multiplier)
    def mock_get_resource_high_capacity(resource_id):  # noqa: ARG001
        return mock_resource(quantity=9, capacity=10)  # 90% utilization

    manager.transfer_planner.resource_client.get_resource = (
        mock_get_resource_high_capacity
    )
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge = graph[edge_key]
    assert edge.cost == 2.0  # 2x multiplier for high capacity

    # Test 3: Full capacity utilization (10x multiplier)
    def mock_get_resource_full_capacity(resource_id):  # noqa: ARG001
        return mock_resource(quantity=10, capacity=10)  # 100% utilization

    manager.transfer_planner.resource_client.get_resource = (
        mock_get_resource_full_capacity
    )
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge = graph[edge_key]
    assert edge.cost == 10.0  # 10x multiplier for full capacity

    # Test 4: Over capacity (10x multiplier)
    def mock_get_resource_over_capacity(resource_id):  # noqa: ARG001
        return mock_resource(quantity=12, capacity=10)  # 120% utilization

    manager.transfer_planner.resource_client.get_resource = (
        mock_get_resource_over_capacity
    )
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge = graph[edge_key]
    assert edge.cost == 10.0  # 10x multiplier for over capacity

    # Restore original method
    manager.transfer_planner.resource_client.get_resource = original_get_resource


def test_capacity_cost_adjustment_with_no_capacity_set(
    redis_server: Redis, mock_resource
):
    """Test that no adjustment is applied when resource has no capacity set."""
    capacity_config = CapacityCostConfig(
        enabled=True,
        high_capacity_threshold=0.8,
        full_capacity_threshold=1.0,
        high_capacity_multiplier=2.0,
        full_capacity_multiplier=10.0,
    )

    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        capacity_cost_config=capacity_config,
    )

    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Capacity Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Mock resource with no capacity set
    def mock_get_resource_no_capacity(resource_id):  # noqa: ARG001
        return mock_resource(quantity=5, capacity=None)  # No capacity

    manager.transfer_planner.resource_client.get_resource = (
        mock_get_resource_no_capacity
    )

    # Attach a resource to location_b
    location_b_state = manager.state_handler.get_location(location_b.location_id)
    location_b_state.resource_id = "test_resource_id"
    manager.state_handler.update_location(location_b.location_id, location_b_state)

    # Rebuild graph to test capacity adjustments
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge_key = (location_a.location_id, location_b.location_id)
    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.cost == 1.0  # No multiplier when capacity is None


def test_capacity_cost_adjustment_resource_client_error(redis_server: Redis):
    """Test that base cost is returned when resource client throws error."""
    capacity_config = CapacityCostConfig(
        enabled=True,
        high_capacity_threshold=0.8,
        full_capacity_threshold=1.0,
        high_capacity_multiplier=2.0,
        full_capacity_multiplier=10.0,
    )

    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        capacity_cost_config=capacity_config,
    )

    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Capacity Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Mock resource client to throw error
    def mock_get_resource_error(resource_id):  # noqa: ARG001
        raise Exception("Resource not found")

    manager.transfer_planner.resource_client.get_resource = mock_get_resource_error

    # Attach a resource to location_b
    location_b_state = manager.state_handler.get_location(location_b.location_id)
    location_b_state.resource_id = "test_resource_id"
    manager.state_handler.update_location(location_b.location_id, location_b_state)

    # Rebuild graph to test capacity adjustments
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph
    edge_key = (location_a.location_id, location_b.location_id)
    assert edge_key in graph
    edge = graph[edge_key]
    assert edge.cost == 1.0  # Should fallback to base cost on error


def test_transfer_planning_with_capacity_constraints(
    redis_server: Redis, mock_resource
):
    """Test that transfer planning chooses paths with lower capacity utilization."""
    capacity_config = CapacityCostConfig(
        enabled=True,
        high_capacity_threshold=0.8,
        full_capacity_threshold=1.0,
        high_capacity_multiplier=5.0,
        full_capacity_multiplier=20.0,
    )

    # Create two paths with same base cost
    template = TransferStepTemplate(
        node_name="robot",
        action="transfer",
        cost_weight=1.0,
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template],
        capacity_cost_config=capacity_config,
    )

    # Create three locations: A -> B (low capacity) or A -> C (high capacity)
    location_a = LocationDefinition(
        location_name="location_a",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="location_b",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [1, 0, 0]}},
    )

    location_c = LocationDefinition(
        location_name="location_c",
        location_id=new_ulid_str(),
        representations={"robot": {"position": [2, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Capacity Planning Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b, location_c],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_capacity_planning_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server

    # Mock different capacity levels for each location
    def mock_get_resource_by_id(resource_id):
        if resource_id == "resource_b":
            return mock_resource(quantity=3, capacity=10)  # 30% utilization (low)
        if resource_id == "resource_c":
            return mock_resource(quantity=9, capacity=10)  # 90% utilization (high)
        return mock_resource(quantity=0, capacity=10)  # Default

    manager.transfer_planner.resource_client.get_resource = mock_get_resource_by_id

    # Attach resources to locations
    location_b_state = manager.state_handler.get_location(location_b.location_id)
    location_b_state.resource_id = "resource_b"
    manager.state_handler.update_location(location_b.location_id, location_b_state)

    location_c_state = manager.state_handler.get_location(location_c.location_id)
    location_c_state.resource_id = "resource_c"
    manager.state_handler.update_location(location_c.location_id, location_c_state)

    # Rebuild graph to test capacity adjustments
    manager.transfer_planner._transfer_graph = (
        manager.transfer_planner._build_transfer_graph()
    )

    graph = manager.transfer_planner._transfer_graph

    # Check that location B (low capacity) has lower cost than location C (high capacity)
    edge_a_to_b = graph[(location_a.location_id, location_b.location_id)]
    edge_a_to_c = graph[(location_a.location_id, location_c.location_id)]

    assert edge_a_to_b.cost == 1.0  # Base cost for 30% utilization
    assert edge_a_to_c.cost == 5.0  # 5x multiplier for 90% utilization

    # Transfer planning should prefer the low-capacity path
    assert edge_a_to_b.cost < edge_a_to_c.cost


# Additional Arguments in Transfer Templates Tests


def test_transfer_template_with_additional_standard_args(redis_server: Redis):
    """Test that transfer templates with additional standard arguments are handled correctly."""
    # Create transfer template with additional standard arguments
    template_with_args = TransferStepTemplate(
        node_name="robot_with_args",
        action="parameterized_transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
        additional_args={
            "speed": 50,
            "force": "gentle",
            "retry_count": 3,
            "use_vision": True,
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template_with_args]
    )

    # Create locations
    location_a = LocationDefinition(
        location_name="station_alpha",
        location_id=new_ulid_str(),
        representations={"robot_with_args": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="station_beta",
        location_id=new_ulid_str(),
        representations={"robot_with_args": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Additional Args Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_additional_args_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Plan a transfer and verify additional arguments are included
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": location_a.location_id,
            "destination_location_id": location_b.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify the step includes all additional arguments
    assert step.args["speed"] == 50
    assert step.args["force"] == "gentle"
    assert step.args["retry_count"] == 3
    assert step.args["use_vision"] is True

    # Verify standard location arguments are still present
    assert step.locations["source_location"] == "station_alpha"
    assert step.locations["target_location"] == "station_beta"

    # Verify other fields are correct
    assert step.node == "robot_with_args"
    assert step.action == "parameterized_transfer"


def test_transfer_template_with_additional_location_args(redis_server: Redis):
    """Test that transfer templates with additional location arguments are handled correctly."""
    # Create transfer template with additional location arguments
    template_with_locations = TransferStepTemplate(
        node_name="multi_location_robot",
        action="multi_point_transfer",
        source_argument_name="pickup_location",
        target_argument_name="dropoff_location",
        cost_weight=1.0,
        additional_location_args={
            "staging_location": "intermediate_station",
            "calibration_location": "calibration_point",
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[template_with_locations]
    )

    # Create locations
    location_a = LocationDefinition(
        location_name="start_station",
        location_id=new_ulid_str(),
        representations={"multi_location_robot": {"position": [0, 0, 0]}},
    )

    location_b = LocationDefinition(
        location_name="end_station",
        location_id=new_ulid_str(),
        representations={"multi_location_robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Additional Location Args Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_a, location_b],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_additional_location_args_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Plan a transfer and verify additional location arguments are included
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": location_a.location_id,
            "destination_location_id": location_b.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify the step includes all location arguments
    assert step.locations["pickup_location"] == "start_station"
    assert step.locations["dropoff_location"] == "end_station"
    assert step.locations["staging_location"] == "intermediate_station"
    assert step.locations["calibration_location"] == "calibration_point"

    # Verify no additional standard arguments since none were specified
    assert len(step.args) == 0

    # Verify other fields are correct
    assert step.node == "multi_location_robot"
    assert step.action == "multi_point_transfer"


def test_transfer_template_with_both_additional_args_types(redis_server: Redis):
    """Test that transfer templates with both additional standard and location arguments work correctly."""
    # Create transfer template with both types of additional arguments
    comprehensive_template = TransferStepTemplate(
        node_name="comprehensive_robot",
        action="comprehensive_transfer",
        source_argument_name="from_location",
        target_argument_name="to_location",
        cost_weight=1.5,
        additional_args={
            "precision": "high",
            "timeout": 30,
            "enable_logging": True,
        },
        additional_location_args={
            "reference_location": "reference_point",
            "emergency_location": "safety_zone",
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[comprehensive_template]
    )

    # Create locations
    location_x = LocationDefinition(
        location_name="complex_station_x",
        location_id=new_ulid_str(),
        representations={"comprehensive_robot": {"config": "advanced"}},
    )

    location_y = LocationDefinition(
        location_name="complex_station_y",
        location_id=new_ulid_str(),
        representations={"comprehensive_robot": {"config": "standard"}},
    )

    definition = LocationManagerDefinition(
        name="Comprehensive Args Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_x, location_y],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_comprehensive_args_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Plan a transfer and verify both types of additional arguments are included
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": location_x.location_id,
            "destination_location_id": location_y.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify standard arguments
    assert step.args["precision"] == "high"
    assert step.args["timeout"] == 30
    assert step.args["enable_logging"] is True

    # Verify location arguments (both standard and additional)
    assert step.locations["from_location"] == "complex_station_x"
    assert step.locations["to_location"] == "complex_station_y"
    assert step.locations["reference_location"] == "reference_point"
    assert step.locations["emergency_location"] == "safety_zone"

    # Verify other fields
    assert step.node == "comprehensive_robot"
    assert step.action == "comprehensive_transfer"


def test_override_templates_with_additional_args(redis_server: Redis):
    """Test that override templates with additional arguments work correctly."""
    # Create default template with minimal arguments
    default_template = TransferStepTemplate(
        node_name="basic_robot",
        action="basic_transfer",
        cost_weight=5.0,
    )

    # Create override template with additional arguments
    enhanced_override_template = TransferStepTemplate(
        node_name="enhanced_robot",
        action="enhanced_transfer",
        cost_weight=1.0,
        additional_args={
            "enhanced_mode": True,
            "optimization_level": "maximum",
        },
        additional_location_args={
            "checkpoint_location": "checkpoint_station",
        },
    )

    # Create override configuration
    overrides = TransferTemplateOverrides(
        source_overrides={
            "enhanced_source_station": [enhanced_override_template],
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[default_template],
        override_transfer_templates=overrides,
    )

    # Create locations
    enhanced_source = LocationDefinition(
        location_name="enhanced_source_station",
        location_id=new_ulid_str(),
        representations={
            "basic_robot": {"position": [0, 0, 0]},
            "enhanced_robot": {"position": [0, 0, 0]},
        },
    )

    normal_destination = LocationDefinition(
        location_name="normal_destination_station",
        location_id=new_ulid_str(),
        representations={
            "basic_robot": {"position": [1, 0, 0]},
            "enhanced_robot": {"position": [1, 0, 0]},
        },
    )

    regular_source = LocationDefinition(
        location_name="regular_source_station",
        location_id=new_ulid_str(),
        representations={
            "basic_robot": {"position": [2, 0, 0]},
            "enhanced_robot": {"position": [2, 0, 0]},
        },
    )

    definition = LocationManagerDefinition(
        name="Override Args Test Manager",
        manager_id=new_ulid_str(),
        locations=[enhanced_source, normal_destination, regular_source],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_override_args_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Test transfer FROM enhanced source (should use override with additional args)
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": enhanced_source.location_id,
            "destination_location_id": normal_destination.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify override template was used with additional arguments
    assert step.node == "enhanced_robot"
    assert step.action == "enhanced_transfer"
    assert step.args["enhanced_mode"] is True
    assert step.args["optimization_level"] == "maximum"
    assert step.locations["checkpoint_location"] == "checkpoint_station"

    # Test transfer FROM regular source (should use default template without additional args)
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": regular_source.location_id,
            "destination_location_id": normal_destination.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify default template was used without additional arguments
    assert step.node == "basic_robot"
    assert step.action == "basic_transfer"
    assert len(step.args) == 0  # No additional args in default template
    assert "checkpoint_location" not in step.locations  # No additional location args


def test_multi_step_transfer_with_additional_args(redis_server: Redis):
    """Test that multi-step transfers preserve additional arguments for each step."""
    # Create templates with different additional arguments
    robot_template = TransferStepTemplate(
        node_name="precision_robot",
        action="precision_transfer",
        cost_weight=1.0,
        additional_args={
            "precision_level": "ultra_high",
            "scan_before_pickup": True,
        },
    )

    conveyor_template = TransferStepTemplate(
        node_name="smart_conveyor",
        action="conveyor_move",
        source_argument_name="belt_source",
        target_argument_name="belt_target",
        cost_weight=2.0,
        additional_args={
            "belt_speed": "variable",
            "item_tracking": True,
        },
        additional_location_args={
            "sensor_location": "belt_sensor_point",
        },
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[robot_template, conveyor_template]
    )

    # Create locations that form a multi-hop path
    station_a = LocationDefinition(
        location_name="multi_station_a",
        location_id=new_ulid_str(),
        representations={
            "precision_robot": {"position": [0, 0, 0]},
        },
    )

    station_b = LocationDefinition(
        location_name="multi_station_b",
        location_id=new_ulid_str(),
        representations={
            "precision_robot": {"position": [1, 0, 0]},
            "smart_conveyor": {"belt_position": 0},
        },
    )

    station_c = LocationDefinition(
        location_name="multi_station_c",
        location_id=new_ulid_str(),
        representations={
            "smart_conveyor": {"belt_position": 1},
        },
    )

    definition = LocationManagerDefinition(
        name="Multi-step Args Test Manager",
        manager_id=new_ulid_str(),
        locations=[station_a, station_b, station_c],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_multistep_args_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Plan a multi-step transfer (A -> B -> C)
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": station_a.location_id,
            "destination_location_id": station_c.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 2

    # Verify first step (robot transfer A -> B)
    step1 = workflow.steps[0]
    assert step1.node == "precision_robot"
    assert step1.action == "precision_transfer"
    assert step1.args["precision_level"] == "ultra_high"
    assert step1.args["scan_before_pickup"] is True
    assert step1.locations["source_location"] == "multi_station_a"
    assert step1.locations["target_location"] == "multi_station_b"

    # Verify second step (conveyor transfer B -> C)
    step2 = workflow.steps[1]
    assert step2.node == "smart_conveyor"
    assert step2.action == "conveyor_move"
    assert step2.args["belt_speed"] == "variable"
    assert step2.args["item_tracking"] is True
    assert step2.locations["belt_source"] == "multi_station_b"
    assert step2.locations["belt_target"] == "multi_station_c"
    assert step2.locations["sensor_location"] == "belt_sensor_point"


def test_empty_additional_args_default_behavior(redis_server: Redis):
    """Test that templates without additional arguments work exactly as before."""
    # Create template without any additional arguments (should behave exactly as before)
    traditional_template = TransferStepTemplate(
        node_name="traditional_robot",
        action="traditional_transfer",
        source_argument_name="source_location",
        target_argument_name="target_location",
        cost_weight=1.0,
        # additional_args and additional_location_args will default to empty dicts
    )

    transfer_capabilities = LocationTransferCapabilities(
        transfer_templates=[traditional_template]
    )

    # Create locations
    location_1 = LocationDefinition(
        location_name="traditional_station_1",
        location_id=new_ulid_str(),
        representations={"traditional_robot": {"position": [0, 0, 0]}},
    )

    location_2 = LocationDefinition(
        location_name="traditional_station_2",
        location_id=new_ulid_str(),
        representations={"traditional_robot": {"position": [1, 0, 0]}},
    )

    definition = LocationManagerDefinition(
        name="Traditional Test Manager",
        manager_id=new_ulid_str(),
        locations=[location_1, location_2],
        transfer_capabilities=transfer_capabilities,
    )

    settings = LocationManagerSettings(
        manager_id="test_traditional_manager",
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
    )

    manager = LocationManager(settings=settings, definition=definition)
    manager.state_handler._redis_connection = redis_server
    client = TestClient(manager.create_server())

    # Plan a transfer
    response = client.post(
        "/transfer/plan",
        params={
            "source_location_id": location_1.location_id,
            "destination_location_id": location_2.location_id,
        },
    )

    assert response.status_code == 200
    workflow_data = response.json()
    workflow = WorkflowDefinition.model_validate(workflow_data)

    assert len(workflow.steps) == 1
    step = workflow.steps[0]

    # Verify exactly the same behavior as before additional arguments were added
    assert step.node == "traditional_robot"
    assert step.action == "traditional_transfer"
    assert len(step.args) == 0  # No additional args
    assert len(step.locations) == 2  # Only source and target
    assert step.locations["source_location"] == "traditional_station_1"
    assert step.locations["target_location"] == "traditional_station_2"
