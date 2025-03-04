"""Automated pytest unit tests for the madsci workcell manager's REST server."""

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowDefinition
from madsci.workcell_manager.workcell_server import create_workcell_server
from pytest_mock_resources import RedisConfig, create_redis_fixture
from redis import Redis


# Create a Redis server fixture for testing
@pytest.fixture(scope="session")
def pmr_redis_config() -> RedisConfig:
    """Configure the Redis server."""
    return RedisConfig(image="redis:7.4")


redis_server = create_redis_fixture()


@pytest.fixture
def workcell() -> WorkcellDefinition:
    """Fixture for creating a WorkcellDefinition."""
    # TODO: Add node(s) to this workcell for testing purposes
    return WorkcellDefinition(workcell_name="Test Workcell")


@pytest.fixture
def test_client(workcell: WorkcellDefinition, redis_server: Redis) -> TestClient:
    """Workcell Server Test Client Fixture"""
    app = create_workcell_server(workcell, redis_server)
    return TestClient(app)


def test_get_workcell(test_client: TestClient) -> None:
    """Test the /definition endpoint."""
    with test_client as client:
        response = client.get("/definition")
        assert response.status_code == 200
        WorkcellDefinition.model_validate(response.json())


def test_get_nodes(test_client: TestClient) -> None:
    """Test the /nodes endpoint."""
    response = test_client.get("/nodes")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_add_node(test_client: TestClient) -> None:
    """Test adding a node to the workcell."""
    node_name = "test_node"
    node_url = "http://localhost:8000"
    response = test_client.post(
        "/nodes/add_node",
        json={
            "node_name": node_name,
            "node_url": node_url,
            "node_description": "A Node",
            "permanent": False,
        },
    )
    assert response.status_code == 200
    node = Node.model_validate(response.json())
    assert node.node_url == node_url


def test_send_admin_command(test_client: TestClient) -> None:
    """Test sending an admin command to all nodes."""
    response = test_client.get("/admin/reset")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_all_workflows(test_client: TestClient) -> None:
    """Test the /workflows endpoint."""
    response = test_client.get("/workflows")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_start_workflow(test_client: TestClient) -> None:
    """Test starting a new workflow."""
    workflow_def = WorkflowDefinition(name="Test Workflow")
    response = test_client.post(
        "/workflows/start",
        data={"workflow": workflow_def.model_dump_json(), "validate_only": False},
    )
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.workflow_def.name == "Test Workflow"


def test_pause_workflow(test_client: TestClient) -> None:
    """Test pausing a workflow."""
    workflow_id = "test_workflow_id"
    response = test_client.get(f"/workflows/pause/{workflow_id}")
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.paused is True


def test_resume_workflow(test_client: TestClient) -> None:
    """Test resuming a paused workflow."""
    workflow_id = "test_workflow_id"
    response = test_client.get(f"/workflows/resume/{workflow_id}")
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.paused is False


def test_cancel_workflow(test_client: TestClient) -> None:
    """Test canceling a workflow."""
    workflow_id = "test_workflow_id"
    response = test_client.get(f"/workflows/cancel/{workflow_id}")
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.status == "cancelled"


def test_resubmit_workflow(test_client: TestClient) -> None:
    """Test resubmitting a workflow."""
    workflow_id = "test_workflow_id"
    response = test_client.get(f"/workflows/resubmit/{workflow_id}")
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.workflow_id != workflow_id


def test_retry_workflow(test_client: TestClient) -> None:
    """Test retrying a workflow."""
    workflow_id = "test_workflow_id"
    response = test_client.post(
        "/workflows/retry",
        json={"workflow_id": workflow_id, "index": 0},
    )
    assert response.status_code == 200
    workflow = Workflow.model_validate(response.json())
    assert workflow.status == "queued"
