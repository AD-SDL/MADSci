"""Unit tests for WorkcellClient."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.location_types import Location, LocationDefinition
from madsci.common.types.workcell_types import WorkcellDefinition, WorkcellState
from madsci.common.utils import new_ulid_str
from madsci.workcell_manager.workcell_server import (
    WorkflowDefinition,
    create_workcell_server,
)
from pymongo.synchronous.database import Database
from pytest_mock_resources import (
    MongoConfig,
    RedisConfig,
    create_mongo_fixture,
    create_redis_fixture,
)
from redis import Redis
from requests import Response


# Create a Redis server fixture for testing
@pytest.fixture(scope="session")
def pmr_redis_config() -> RedisConfig:
    """Configure the Redis server."""
    return RedisConfig(image="redis:7.4")


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Congifure the MongoDB fixture."""
    return MongoConfig(image="mongo:8.0")


redis_server = create_redis_fixture()
mongo_server = create_mongo_fixture()


@pytest.fixture
def workcell() -> WorkcellDefinition:
    """Fixture for creating a WorkcellDefinition."""
    return WorkcellDefinition(
        workcell_name="Test Workcell",
        locations=[
            LocationDefinition(location_name="test_location"),
        ],
    )


@pytest.fixture
def test_client(
    workcell: WorkcellDefinition, redis_server: Redis, mongo_server: Database
) -> Generator[TestClient, None, None]:
    """Workcell Server Test Client Fixture."""
    app = create_workcell_server(
        workcell=workcell,
        redis_connection=redis_server,
        mongo_connection=mongo_server,
        start_engine=False,
    )
    client = TestClient(app)
    with client:
        yield client


@pytest.fixture
def client(test_client: TestClient) -> Generator[WorkcellClient, None, None]:
    """Fixture for WorkcellClient patched to use TestClient."""
    with patch("madsci.client.workcell_client.requests") as mock_requests:

        def add_ok_property(resp: Response) -> Response:
            if not hasattr(resp, "ok"):
                resp.ok = resp.status_code < 400
            return resp

        def post_no_timeout(*args: Any, **kwargs: Any) -> Response:
            kwargs.pop("timeout", None)
            resp = test_client.post(*args, **kwargs)
            return add_ok_property(resp)

        mock_requests.post.side_effect = post_no_timeout

        def get_no_timeout(*args: Any, **kwargs: Any) -> Response:
            kwargs.pop("timeout", None)
            resp = test_client.get(*args, **kwargs)
            return add_ok_property(resp)

        mock_requests.get.side_effect = get_no_timeout

        def delete_no_timeout(*args: Any, **kwargs: Any) -> Response:
            kwargs.pop("timeout", None)
            resp = test_client.delete(*args, **kwargs)
            return add_ok_property(resp)

        mock_requests.delete.side_effect = delete_no_timeout

        yield WorkcellClient(workcell_server_url="http://testserver")


def test_get_nodes(client: WorkcellClient) -> None:
    """Test retrieving nodes from the workcell."""
    response = client.add_node("node1", "http://node1/")
    assert response["node_url"] == "http://node1/"
    nodes = client.get_nodes()
    assert "node1" in nodes
    assert nodes["node1"]["node_url"] == "http://node1/"


def test_get_node(client: WorkcellClient) -> None:
    """Test retrieving a specific node."""
    client.add_node("node1", "http://node1/")
    node = client.get_node("node1")
    assert node["node_url"] == "http://node1/"


def test_add_node(client: WorkcellClient) -> None:
    """Test adding a node to the workcell."""
    node = client.add_node("node1", "http://node1/")
    assert node["node_url"] == "http://node1/"


def test_get_active_workflows(client: WorkcellClient) -> None:
    """Test retrieving workflows."""
    workflows = client.get_active_workflows()
    assert isinstance(workflows, dict)


def test_get_archived_workflows(client: WorkcellClient) -> None:
    """Test retrieving workflows."""
    workflows = client.get_archived_workflows(30)
    assert isinstance(workflows, dict)


def test_get_workflow_queue(client: WorkcellClient) -> None:
    """Test retrieving the workflow queue."""
    queue = client.get_workflow_queue()
    assert isinstance(queue, list)


def test_get_workcell_state(client: WorkcellClient) -> None:
    """Test retrieving the workcell state."""
    state = client.get_workcell_state()
    assert isinstance(state, WorkcellState)


def test_pause_workflow(client: WorkcellClient) -> None:
    """Test pausing a workflow."""
    workflow = client.submit_workflow(
        WorkflowDefinition(name="Test Workflow"), None, await_completion=False
    )
    paused_workflow = client.pause_workflow(workflow.workflow_id)
    assert paused_workflow.status.paused is True


def test_resume_workflow(client: WorkcellClient) -> None:
    """Test resuming a workflow."""
    workflow = client.submit_workflow(
        WorkflowDefinition(name="Test Workflow"), {}, await_completion=False
    )
    client.pause_workflow(workflow.workflow_id)
    resumed_workflow = client.resume_workflow(workflow.workflow_id)
    assert resumed_workflow.status.paused is False


def test_cancel_workflow(client: WorkcellClient) -> None:
    """Test canceling a workflow."""
    workflow = client.submit_workflow(
        WorkflowDefinition(name="Test Workflow"), {}, await_completion=False
    )
    canceled_workflow = client.cancel_workflow(workflow.workflow_id)
    assert canceled_workflow.status.cancelled is True


def test_get_locations(client: WorkcellClient) -> None:
    """Test retrieving locations."""
    locations = client.get_locations()
    assert isinstance(locations, list)
    assert len(locations) == 1
    assert locations[0].location_name == "test_location"


def test_get_location(client: WorkcellClient) -> None:
    """Test retrieving a specific location."""
    location_id = client.get_locations()[0].location_id
    fetched_location = client.get_location(location_id)
    assert fetched_location.location_id == location_id


def test_add_location(client: WorkcellClient) -> None:
    """Test adding a location."""
    location = Location(location_name="test_location2")
    added_location = client.add_location(location, permanent=False)
    assert added_location.location_id == location.location_id
    assert added_location.location_name == location.location_name


def test_attach_resource_to_location(client: WorkcellClient) -> None:
    """Test attaching a resource to a location."""
    location = Location(location_name="test_location3")
    client.add_location(location, permanent=False)
    mock_resource_id = new_ulid_str()
    updated_location = client.attach_resource_to_location(
        location.location_id, mock_resource_id
    )
    assert updated_location.resource_id == mock_resource_id
