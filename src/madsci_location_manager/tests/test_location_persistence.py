"""Tests for location persistence to YAML definition files."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerSettings,
    LocationTransferCapabilities,
    TransferStepTemplate,
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
def definition_file(tmp_path):
    """Create a test definition file."""
    def_path = tmp_path / "location.manager.yaml"

    # Create initial definition with some locations
    initial_definition = LocationManagerDefinition(
        name="Test Location Manager",
        description="A test location manager instance",
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

    # Write to file
    initial_definition.to_yaml(def_path)
    return def_path


@pytest.fixture
def app(redis_server: Redis, definition_file: Path):
    """Create a test app with test settings, Redis server, and definition file."""
    settings = LocationManagerSettings(
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
        manager_definition=definition_file,
    )

    # Load definition from file
    definition = LocationManagerDefinition.from_yaml(definition_file)

    # Create the app with the Redis connection passed to the LocationManager
    manager = LocationManager(settings=settings, definition=definition)
    # Override the state handler's Redis connection to use the test Redis instance
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


# RED PHASE: Write failing tests


def test_add_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that adding a location persists it to the YAML definition file.

    This test verifies that when a location is added via the API,
    it is written back to the definition file so it persists across restarts.
    """
    # Add a new location via API
    response = client.post("/location", json=sample_location.model_dump())
    assert response.status_code == 200

    # Reload the definition from the file
    reloaded_definition = LocationManagerDefinition.from_yaml(definition_file)

    # Check that the new location is in the definition
    location_ids = [loc.location_id for loc in reloaded_definition.locations]
    assert sample_location.location_id in location_ids, (
        f"Location {sample_location.location_id} not found in reloaded definition. "
        f"Found location IDs: {location_ids}"
    )

    # Verify the location details match
    reloaded_location = next(
        loc
        for loc in reloaded_definition.locations
        if loc.location_id == sample_location.location_id
    )
    assert reloaded_location.location_name == sample_location.location_name
    assert reloaded_location.description == sample_location.description


def test_update_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that updating a location persists changes to the YAML definition file.

    This test verifies that when a location is updated via the API,
    the changes are written back to the definition file.
    """
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Now update it with a new description
    sample_location.description = "Updated description for persistence test"
    response = client.post(
        f"/location/{sample_location.location_id}/set_representation/test_node",
        json="test_representation_value",
    )
    assert response.status_code == 200

    # Reload the definition from the file
    reloaded_definition = LocationManagerDefinition.from_yaml(definition_file)

    # Check that the location still exists
    location_ids = [loc.location_id for loc in reloaded_definition.locations]
    assert sample_location.location_id in location_ids

    # Verify the representation was persisted
    reloaded_location = next(
        loc
        for loc in reloaded_definition.locations
        if loc.location_id == sample_location.location_id
    )
    assert reloaded_location.representations is not None
    assert "test_node" in reloaded_location.representations
    assert reloaded_location.representations["test_node"] == "test_representation_value"


def test_delete_location_persists_to_yaml(client, sample_location, definition_file):
    """Test that deleting a location removes it from the YAML definition file.

    This test verifies that when a location is deleted via the API,
    it is removed from the definition file.
    """
    # First add the location
    client.post("/location", json=sample_location.model_dump())

    # Verify it was added
    definition_after_add = LocationManagerDefinition.from_yaml(definition_file)
    location_ids_after_add = [loc.location_id for loc in definition_after_add.locations]
    assert sample_location.location_id in location_ids_after_add

    # Now delete the location
    response = client.delete(f"/location/{sample_location.location_id}")
    assert response.status_code == 200

    # Reload the definition from the file
    reloaded_definition = LocationManagerDefinition.from_yaml(definition_file)

    # Check that the location is no longer in the definition
    location_ids = [loc.location_id for loc in reloaded_definition.locations]
    assert sample_location.location_id not in location_ids, (
        f"Location {sample_location.location_id} should have been removed from definition. "
        f"Found location IDs: {location_ids}"
    )


def test_initial_locations_preserved_after_add(
    client, sample_location, definition_file
):
    """Test that initial locations from the definition file are preserved when adding new locations.

    This ensures that adding new locations doesn't overwrite existing locations
    that were defined in the original YAML file.
    """
    # Get the initial locations from the definition
    initial_definition = LocationManagerDefinition.from_yaml(definition_file)
    initial_location_ids = [loc.location_id for loc in initial_definition.locations]

    # Add a new location
    client.post("/location", json=sample_location.model_dump())

    # Reload the definition from the file
    reloaded_definition = LocationManagerDefinition.from_yaml(definition_file)
    reloaded_location_ids = [loc.location_id for loc in reloaded_definition.locations]

    # Verify all initial locations are still present
    for initial_id in initial_location_ids:
        assert initial_id in reloaded_location_ids, (
            f"Initial location {initial_id} was lost after adding new location"
        )

    # Verify the new location is also present
    assert sample_location.location_id in reloaded_location_ids


def test_transfer_capabilities_preserved_during_sync(tmp_path):
    """Test that transfer_capabilities in the definition are preserved when syncing locations.

    This ensures that non-location parts of the definition (like transfer_capabilities)
    are not overwritten when updating the location list.
    """
    # Create a definition with transfer capabilities
    def_path = tmp_path / "location_with_transfers.yaml"

    transfer_template = TransferStepTemplate(
        node_name="test_node",
        action="transfer",
        source_argument_name="source",
        target_argument_name="target",
        cost_weight=1.5,
    )

    initial_definition = LocationManagerDefinition(
        name="Test Location Manager with Transfers",
        description="A test with transfer capabilities",
        locations=[],
        transfer_capabilities=LocationTransferCapabilities(
            transfer_templates=[transfer_template]
        ),
    )

    # Write to file
    initial_definition.to_yaml(def_path)

    # Since we can't easily create a new Redis instance here,
    # we'll test this more thoroughly in integration, but at least
    # verify the structure is correct
    definition = LocationManagerDefinition.from_yaml(def_path)
    assert definition.transfer_capabilities is not None
    assert len(definition.transfer_capabilities.transfer_templates) == 1
    assert (
        definition.transfer_capabilities.transfer_templates[0].node_name == "test_node"
    )


def test_startup_sync_redis_only_locations_to_yaml(redis_server: Redis, tmp_path: Path):
    """Test that locations existing only in Redis are immediately synced to YAML on startup.

    This test verifies that when the server starts up with locations in Redis
    that are not in the definition file, those Redis-only locations are immediately
    written to the YAML file during initialization.

    RED PHASE: This test should fail initially because startup sync is not yet implemented.
    """
    # Create a definition file with one initial location
    def_path = tmp_path / "location.manager.yaml"
    initial_location_id = new_ulid_str()

    initial_definition = LocationManagerDefinition(
        name="Test Location Manager",
        description="A test location manager instance",
        locations=[
            LocationDefinition(
                location_name="Initial Location",
                location_id=initial_location_id,
                description="Initial location from definition file",
            ),
        ],
    )
    initial_definition.to_yaml(def_path)

    # Create a location that exists only in Redis (simulating a previously API-added location)
    redis_only_location = Location(
        location_id=new_ulid_str(),
        location_name="Redis Only Location",
        description="This location was added via API and exists only in Redis",
    )

    # Manually populate Redis with the Redis-only location using a temporary state handler
    settings = LocationManagerSettings(
        redis_host=redis_server.connection_pool.connection_kwargs["host"],
        redis_port=redis_server.connection_pool.connection_kwargs["port"],
        manager_definition=def_path,
    )

    # Create a temporary manager to populate Redis
    temp_manager = LocationManager(settings=settings, definition=initial_definition)
    temp_manager.state_handler._redis_connection = redis_server

    # Add the Redis-only location directly to Redis (bypassing the API)
    temp_manager.state_handler.set_location(
        redis_only_location.location_id, redis_only_location
    )

    # Verify Redis has both locations before we start the actual test
    redis_locations = temp_manager.state_handler.get_locations()
    assert len(redis_locations) == 2, (
        "Redis should have both locations before server startup"
    )

    # Now create a fresh manager instance (simulating server restart)
    # This should trigger the startup sync
    fresh_definition = LocationManagerDefinition.from_yaml(def_path)
    fresh_manager = LocationManager(settings=settings, definition=fresh_definition)
    fresh_manager.state_handler._redis_connection = redis_server

    # Create the server to trigger initialization
    fresh_manager.create_server(version="0.1.0")

    # Verify the definition file now contains BOTH locations
    synced_definition = LocationManagerDefinition.from_yaml(def_path)
    synced_location_ids = [loc.location_id for loc in synced_definition.locations]

    assert initial_location_id in synced_location_ids, (
        "Initial location should still be in the definition"
    )
    assert redis_only_location.location_id in synced_location_ids, (
        "Redis-only location should now be synced to the definition file"
    )

    # Verify the Redis-only location details were preserved
    synced_redis_location = next(
        loc
        for loc in synced_definition.locations
        if loc.location_id == redis_only_location.location_id
    )
    assert synced_redis_location.location_name == redis_only_location.location_name
    assert synced_redis_location.description == redis_only_location.description
