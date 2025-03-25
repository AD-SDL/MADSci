"""Automated pytest unit tests for the madsci workcell manager's REST server."""

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowDefinition
from madsci.workcell_manager.workcell_server import create_workcell_server
from pydantic import AnyUrl
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
    app = create_workcell_server(workcell, redis_server, start_engine=False)
    return TestClient(app)


def test_get_workcell(test_client: TestClient) -> None:
    """Test the /definition endpoint."""
    with test_client as client:
        response = client.get("/definition")
        assert response.status_code == 200
        WorkcellDefinition.model_validate(response.json())


def test_get_nodes(test_client: TestClient) -> None:
    """Test the /nodes endpoint."""
    with test_client as client:
        response = client.get("/nodes")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


def test_add_node(test_client: TestClient) -> None:
    """Test adding a node to the workcell."""
    with test_client as client:
        node_name = "test_node"
        node_url = "http://localhost:8000"
        response = client.post(
            "/node",
            params={
                "node_name": node_name,
                "node_url": node_url,
                "node_description": "A Node",
                "permanent": False,
            },
        )
        assert response.status_code == 200
        node = Node.model_validate(response.json())
        assert node.node_url == AnyUrl(node_url)

        response = client.get("/node/test_node")
        assert response.status_code == 200
        node = Node.model_validate(response.json())
        assert node.node_url == AnyUrl(node_url)

        response = client.get("/nodes")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        assert len(response.json()) == 1
        assert node_name in response.json()


def test_send_admin_command(test_client: TestClient) -> None:
    """Test sending an admin command to all nodes."""
    with test_client as client:
        response = client.get("/admin/reset")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_get_workflows(test_client: TestClient) -> None:
    """Test the /workflows endpoint."""
    with test_client as client:
        response = client.get("/workflows")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


def test_get_workflow_queue(test_client: TestClient) -> None:
    """Test the /workflow_queue endpoint."""
    with test_client as client:
        response = client.get("/workflows/queue")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_start_workflow(test_client: TestClient) -> None:
    """Test starting a new workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response = client.post(
            "/workflow",
            data={"workflow": workflow_def.model_dump_json(), "validate_only": False},
        )
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.name == workflow_def.name
        response = client.get(f"/workflow/{workflow.workflow_id}")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.name == workflow_def.name


def test_pause_and_resume_workflow(test_client: TestClient) -> None:
    """Test pausing and resuming a workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response = client.post(
            "/workflow",
            data={"workflow": workflow_def.model_dump_json(), "validate_only": False},
        )
        workflow = Workflow.model_validate(response.json())
        response = client.post(f"/workflow/{workflow.workflow_id}/pause")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.paused is True
        response = test_client.post(f"/workflow/{workflow.workflow_id}/resume")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.paused is False


def test_cancel_workflow(test_client: TestClient) -> None:
    """Test canceling and resubmitting a workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response = client.post(
            "/workflow",
            data={"workflow": workflow_def.model_dump_json(), "validate_only": False},
        )
        workflow = Workflow.model_validate(response.json())
        response = test_client.post(f"/workflow/{workflow.workflow_id}/cancel")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status == "cancelled"
        response = test_client.post(f"/workflow/{workflow.workflow_id}/resubmit")
        assert response.status_code == 200
        new_workflow = Workflow.model_validate(response.json())
        assert workflow.workflow_id != new_workflow.workflow_id


def test_retry_workflow(test_client: TestClient) -> None:
    """Test retrying a workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response = client.post(
            "/workflow",
            data={"workflow": workflow_def.model_dump_json(), "validate_only": False},
        )
        workflow = Workflow.model_validate(response.json())
        response = test_client.post(f"/workflow/{workflow.workflow_id}/cancel")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status == "cancelled"
        response = test_client.post(
            f"/workflow/{workflow.workflow_id}/retry", params={"index": 0}
        )
        assert response.status_code == 200
        new_workflow = Workflow.model_validate(response.json())
        assert workflow.workflow_id == new_workflow.workflow_id
        assert new_workflow.status == "queued"
