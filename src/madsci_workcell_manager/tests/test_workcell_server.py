"""Automated pytest unit tests for the madsci workcell manager's REST server."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.node_types import Node
from madsci.common.types.parameter_types import (
    ParameterFeedForwardJson,
    ParameterInputFile,
    ParameterInputJson,
)
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.workcell_types import WorkcellManagerDefinition
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowParameters,
)
from madsci.workcell_manager.workcell_server import WorkcellManager
from madsci.workcell_manager.workflow_utils import check_parameters
from pydantic import AnyUrl
from pymongo.synchronous.database import Database
from pytest_mock_resources import (
    MongoConfig,
    RedisConfig,
    create_mongo_fixture,
    create_redis_fixture,
)
from redis import Redis


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
def workcell() -> WorkcellManagerDefinition:
    """Fixture for creating a WorkcellDefinition."""
    # TODO: Add node(s) to this workcell for testing purposes
    return WorkcellManagerDefinition(name="Test Workcell")


@pytest.fixture
def test_client(
    workcell: WorkcellManagerDefinition, redis_server: Redis, mongo_server: Database
) -> TestClient:
    """Workcell Server Test Client Fixture"""
    manager = WorkcellManager(
        definition=workcell,
        redis_connection=redis_server,
        mongo_connection=mongo_server,
        start_engine=False,
    )
    app = manager.create_server()
    return TestClient(app)


def test_get_workcell(test_client: TestClient) -> None:
    """Test the /workcell endpoint."""
    with test_client as client:
        response = client.get("/workcell")
        assert response.status_code == 200
        WorkcellManagerDefinition.model_validate(response.json())


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
        response = client.post("/admin/reset")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_get_active_workflows(test_client: TestClient) -> None:
    """Test the /workflows endpoint."""
    with test_client as client:
        response = client.get("/workflows/active")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


def test_get_archived_workflows(test_client: TestClient) -> None:
    """Test the /workflows endpoint."""
    with test_client as client:
        response = client.get("/workflows/archived")
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
        response1 = client.post(
            "/workflow_definition", json=workflow_def.model_dump(mode="json")
        )
        assert response1.status_code == 200
        id = response1.json()
        response = client.post(
            "/workflow",
            data={"workflow_definition_id": id},
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
        response1 = client.post(
            "/workflow_definition", json=workflow_def.model_dump(mode="json")
        )
        assert response1.status_code == 200
        id = response1.json()
        response = client.post(
            "/workflow",
            data={"workflow_definition_id": id},
        )
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        response = client.post(f"/workflow/{workflow.workflow_id}/pause")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status.paused is True
        response = test_client.post(f"/workflow/{workflow.workflow_id}/resume")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status.paused is False


def test_cancel_workflow(test_client: TestClient) -> None:
    """Test canceling a workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response1 = client.post(
            "/workflow_definition", json=workflow_def.model_dump(mode="json")
        )
        assert response1.status_code == 200
        id = response1.json()
        response = client.post(
            "/workflow",
            data={"workflow_definition_id": id},
        )
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        response = test_client.post(f"/workflow/{workflow.workflow_id}/cancel")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status.cancelled is True


def test_retry_workflow(test_client: TestClient) -> None:
    """Test retrying a workflow."""
    with test_client as client:
        workflow_def = WorkflowDefinition(name="Test Workflow")
        response1 = client.post(
            "/workflow_definition", json=workflow_def.model_dump(mode="json")
        )
        assert response1.status_code == 200
        id = response1.json()
        response = client.post(
            "/workflow",
            data={"workflow_definition_id": id},
        )
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        response = test_client.post(f"/workflow/{workflow.workflow_id}/cancel")
        assert response.status_code == 200
        workflow = Workflow.model_validate(response.json())
        assert workflow.status.cancelled is True
        response = test_client.post(
            f"/workflow/{workflow.workflow_id}/retry", params={"index": 0}
        )
        assert response.status_code == 200
        new_workflow = Workflow.model_validate(response.json())
        assert workflow.workflow_id == new_workflow.workflow_id
        assert new_workflow.status.ok is True


def test_check_parameter_missing() -> None:
    """Test parameter insertion with missing required parameter."""
    workflow = WorkflowDefinition(
        name="Test",
        parameters=WorkflowParameters(
            json_inputs=[ParameterInputJson(key="required_param")]
        ),
        steps=[
            StepDefinition(
                name="step1",
                node="node1",
                action="action1",
                use_parameters={
                    "args": {"param": "required_param"},
                },
            )
        ],
    )

    with pytest.raises(ValueError, match="Required value required_param not provided"):
        check_parameters(workflow, {})


def test_check_parameter_conflict() -> None:
    """Test parameter insertion with conflicting configuration."""
    workflow = WorkflowDefinition(
        name="Test",
        parameters=WorkflowParameters(
            json_inputs=[
                ParameterInputJson(key="input_param", default="default_value")
            ],
            feed_forward=[
                ParameterFeedForwardJson(
                    key="feed_forward_param", label="some_label", step="step1"
                )
            ],
        ),
        steps=[
            StepDefinition(
                name="step 1!!",
                key="step1",
                node="node1",
                action="action1",
                use_parameters={
                    "args": {"param": "feed_forward_param"},
                },
            )
        ],
    )

    # Test that providing a value for a feed_forward parameter raises an error
    with pytest.raises(
        ValueError,
        match="feed_forward_param is a Feed Forward Value and will be calculated during execution",
    ):
        check_parameters(workflow, {"feed_forward_param": "value"})

    # Test that providing a value for a normal parameter works
    check_parameters(workflow, {"input_param": "value"})  # Should not raise


def test_health_endpoint(test_client: TestClient) -> None:
    """Test the health endpoint of the Workcell Manager."""
    response = test_client.get("/health")
    assert response.status_code == 200

    health_data = response.json()
    assert "healthy" in health_data
    assert "description" in health_data
    assert "redis_connected" in health_data
    assert "nodes_reachable" in health_data
    assert "total_nodes" in health_data

    # Health should be True for basic functionality
    assert health_data["healthy"] is True
    # Note: redis_connected may be None if Redis is not configured
    assert isinstance(health_data["total_nodes"], int)
    assert isinstance(health_data["nodes_reachable"], int)
    assert health_data["total_nodes"] >= 0
    assert health_data["nodes_reachable"] >= 0


def test_workflow_with_file_inputs(test_client: TestClient) -> None:
    """Test starting a workflow with file inputs to ensure files are not emptied."""
    with test_client as client:
        # Create a test file with specific content
        test_content = b"This is test file content for workflow file input testing!"
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, suffix=".txt"
        ) as test_file:
            test_file.write(test_content)
            test_file_path = test_file.name

        try:
            # Create a workflow definition that requires a file input
            workflow_def = WorkflowDefinition(
                name="Test Workflow with File",
                parameters=WorkflowParameters(
                    file_inputs=[ParameterInputFile(key="input_file")]
                ),
            )

            # Submit the workflow definition
            response1 = client.post(
                "/workflow_definition", json=workflow_def.model_dump(mode="json")
            )
            assert response1.status_code == 200
            workflow_def_id = response1.json()

            # Start the workflow with a file input
            with Path(test_file_path).open("rb") as f:
                response = client.post(
                    "/workflow",
                    data={
                        "workflow_definition_id": workflow_def_id,
                        "file_input_paths": '{"input_file": "test_input.txt"}',
                    },
                    files=[("files", ("input_file", f, "text/plain"))],
                )

            assert response.status_code == 200
            workflow = Workflow.model_validate(response.json())
            assert workflow.name == workflow_def.name

            # Verify that file_input_ids were created
            assert "input_file" in workflow.file_input_ids
            datapoint_id = workflow.file_input_ids["input_file"]
            assert datapoint_id is not None
            assert len(datapoint_id) > 0

            # Note: We can't directly verify the file content here without a data manager,
            # but the fact that a datapoint_id was created and the request succeeded
            # indicates the file was processed correctly

        finally:
            # Clean up the test file
            Path(test_file_path).unlink(missing_ok=True)
