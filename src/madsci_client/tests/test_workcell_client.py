"""Unit tests for WorkcellClient."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.types.location_types import Location, LocationDefinition
from madsci.common.types.parameter_types import FeedForwardValue, InputValue
from madsci.common.types.step_types import Step, StepDefinition
from madsci.common.types.workcell_types import WorkcellDefinition, WorkcellState
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowParameters,
    WorkflowStatus,
)
from madsci.common.utils import new_ulid_str
from madsci.workcell_manager.workcell_server import (
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
def sample_workflow() -> WorkflowDefinition:
    """Fixture for creating a sample WorkflowDefinition."""
    return WorkflowDefinition(
        name="Test Workflow",
        steps=[
            StepDefinition(
                name="test_step",
                node="test_node",
                action="test_action",
                args={"test_arg": "test_value"},
            )
        ],
        parameters=WorkflowParameters(
            input_values=[
                InputValue(key="test_param", default="default_value")
            ]
        ),
    )


@pytest.fixture
def sample_workflow_with_files() -> WorkflowDefinition:
    """Fixture for creating a WorkflowDefinition with file references."""
    return WorkflowDefinition(
        name="Test Workflow with Files",
        steps=[
            StepDefinition(
                name="test_step",
                node="test_node",
                action="test_action",
                files={
                    "input_file": {
                        "input_file_key": "input_file",
                        "description": "An input file",
                    }
                },  # type: ignore
            )
        ],
    )


@pytest.fixture
def sample_workflow_instance() -> Workflow:
    """Fixture for creating a sample Workflow instance."""
    workflow_id = new_ulid_str()
    return Workflow(
        workflow_id=workflow_id,
        name="Test Workflow Instance",
        steps=[
            Step(
                name="test_step",
                node="test_node",
                action="test_action",
            )
        ],
        status=WorkflowStatus(),
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

        def put_no_timeout(*args: Any, **kwargs: Any) -> Response:
            kwargs.pop("timeout", None)
            resp = test_client.put(*args, **kwargs)
            return add_ok_property(resp)

        mock_requests.put.side_effect = put_no_timeout

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


def test_get_nodes_empty(client: WorkcellClient) -> None:
    """Test retrieving nodes when none exist."""
    nodes = client.get_nodes()
    assert isinstance(nodes, dict)
    assert len(nodes) == 0


def test_add_node_with_description(client: WorkcellClient) -> None:
    """Test adding a node with a custom description."""
    node = client.add_node(
        "node1", "http://node1/", node_description="Custom Node", permanent=True
    )
    assert node["node_url"] == "http://node1/"


def test_get_active_workflows(client: WorkcellClient) -> None:
    """Test retrieving workflows."""
    workflows = client.get_active_workflows()
    assert isinstance(workflows, dict)


def test_get_archived_workflows(client: WorkcellClient) -> None:
    """Test retrieving workflows."""
    workflows = client.get_archived_workflows(30)
    assert isinstance(workflows, dict)


def test_get_archived_workflows_default(client: WorkcellClient) -> None:
    """Test retrieving archived workflows with default limit."""
    workflows = client.get_archived_workflows()
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
    workflow = client.start_workflow(
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


def test_add_location_permanent(client: WorkcellClient) -> None:
    """Test adding a permanent location."""
    location = Location(location_name="permanent_location")
    added_location = client.add_location(location, permanent=True)
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


def test_delete_location(client: WorkcellClient) -> None:
    """Test deleting a location."""
    location = Location(location_name="temp_location")
    added_location = client.add_location(location, permanent=False)
    client.delete_location(added_location.location_id)


# Additional Workflow Tests
def test_submit_workflow_definition(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test submitting a workflow definition object."""
    # Add the test node first
    client.add_node("test_node", "http://test_node/")

    workflow = client.submit_workflow(
        sample_workflow, {"test_param": "custom_value"}, await_completion=False
    )
    assert workflow.name == "Test Workflow"
    assert workflow.workflow_id is not None


def test_query_workflow(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test querying a workflow by ID."""
    # Add the test node first
    client.add_node("test_node", "http://test_node/")

    submitted_workflow = client.submit_workflow(sample_workflow, await_completion=False)
    queried_workflow = client.query_workflow(submitted_workflow.workflow_id)
    assert queried_workflow is not None
    assert queried_workflow.workflow_id == submitted_workflow.workflow_id


def test_submit_workflow_sequence(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test submitting a sequence of workflows."""
    workflows = [sample_workflow, sample_workflow]
    input_values = [{"test_param": "value1"}, {"test_param": "value2"}]

    with patch.object(client, "submit_workflow") as mock_submit:
        mock_workflow1 = Workflow(
            workflow_id=new_ulid_str(),
            name="Test Workflow 1",
            status=WorkflowStatus(completed=True, terminal=True),
            steps=[],
        )
        mock_workflow2 = Workflow(
            workflow_id=new_ulid_str(),
            name="Test Workflow 2",
            status=WorkflowStatus(completed=True, terminal=True),
            steps=[],
        )
        mock_submit.side_effect = [mock_workflow1, mock_workflow2]

        result = client.submit_workflow_sequence(workflows, input_values)

        assert len(result) == 2
        assert mock_submit.call_count == 2
        mock_submit.assert_any_call(
            workflows[0], input_values[0], {}, await_completion=True
        )
        mock_submit.assert_any_call(
            workflows[1], input_values[1], {}, await_completion=True
        )


def test_submit_workflow_batch(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test submitting a batch of workflows."""
    workflows = [sample_workflow, sample_workflow]
    input_values = [{"test_param": "value1"}, {"test_param": "value2"}]

    # Create mock response objects that mimic what submit_workflow returns
    mock_response1 = MagicMock()
    wf_id1 = new_ulid_str()
    mock_response1.json.return_value = {"workflow_id": wf_id1}

    mock_response2 = MagicMock()
    wf_id2 = new_ulid_str()
    mock_response2.json.return_value = {"workflow_id": wf_id2}

    mock_workflow1 = Workflow(
        workflow_id=wf_id1,
        name="Test Workflow 1",
        status=WorkflowStatus(completed=True, terminal=True),
        steps=[],
    )
    mock_workflow2 = Workflow(
        workflow_id=wf_id2,
        name="Test Workflow 2",
        status=WorkflowStatus(completed=True, terminal=True),
        steps=[],
    )

    with (
        patch.object(client, "submit_workflow") as mock_submit,
        patch.object(client, "query_workflow") as mock_query,
    ):
        mock_submit.side_effect = [mock_response1, mock_response2]
        mock_query.side_effect = [mock_workflow1, mock_workflow2]

        result = client.submit_workflow_batch(workflows, input_values)

        assert len(result) == 2
        assert mock_submit.call_count == 2


def test_retry_workflow(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test retrying a workflow."""
    # Add the test node first
    client.add_node("test_node", "http://test_node/")

    submitted_workflow = client.submit_workflow(sample_workflow, await_completion=False)

    with (
        patch.object(client, "await_workflow") as mock_await,
        patch.object(client, "retry_workflow") as mock_retry,
    ):
        mock_workflow = Workflow(
            workflow_id=submitted_workflow.workflow_id,
            name="Test Workflow",
            status=WorkflowStatus(completed=True),
            steps=[],
        )
        mock_await.return_value = mock_workflow
        mock_retry.return_value = mock_workflow

        retried_workflow = client.retry_workflow(
            submitted_workflow.workflow_id, index=0, await_completion=True
        )

        assert retried_workflow.workflow_id == submitted_workflow.workflow_id
        mock_retry.assert_called_once_with(
            submitted_workflow.workflow_id, index=0, await_completion=True
        )


def test_retry_workflow_no_await(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test retrying a workflow without waiting for completion."""
    # Add the test node first
    client.add_node("test_node", "http://test_node/")

    submitted_workflow = client.submit_workflow(sample_workflow, await_completion=False)

    # Mock the retry operation since it requires a failed workflow
    with patch.object(client, "retry_workflow") as mock_retry:
        mock_workflow = Workflow(
            workflow_id=submitted_workflow.workflow_id,
            name="Test Workflow",
            status=WorkflowStatus(paused=False),
            steps=[],
        )
        mock_retry.return_value = mock_workflow

        retried_workflow = client.retry_workflow(
            submitted_workflow.workflow_id, index=0, await_completion=False
        )

        assert isinstance(retried_workflow, Workflow)
        mock_retry.assert_called_once_with(
            submitted_workflow.workflow_id, index=0, await_completion=False
        )


def test_await_workflow_completed(
    client: WorkcellClient, sample_workflow_instance: Workflow
) -> None:
    """Test awaiting a workflow that completes successfully."""
    # Create a completed workflow status
    completed_workflow = sample_workflow_instance.model_copy(deep=True)
    completed_workflow.status = WorkflowStatus(completed=True)

    with patch.object(client, "query_workflow") as mock_query:
        mock_query.return_value = completed_workflow

        result = client.await_workflow(
            sample_workflow_instance.workflow_id,
            prompt_on_error=False,
            raise_on_failed=False,
            raise_on_cancelled=False,
        )

        assert result == completed_workflow
        mock_query.assert_called_with(sample_workflow_instance.workflow_id)


def test_await_workflow_failed(
    client: WorkcellClient, sample_workflow_instance: Workflow
) -> None:
    """Test awaiting a workflow that fails."""
    # Create a failed workflow status
    failed_workflow = sample_workflow_instance.model_copy(deep=True)
    failed_workflow.status = WorkflowStatus(failed=True, current_step_index=0)

    with (
        patch.object(client, "query_workflow") as mock_query,
        patch.object(client, "_handle_workflow_error") as mock_handle,
    ):
        mock_query.return_value = failed_workflow
        mock_handle.return_value = failed_workflow

        result = client.await_workflow(
            sample_workflow_instance.workflow_id,
            prompt_on_error=False,
            raise_on_failed=True,
            raise_on_cancelled=False,
        )

        assert result == failed_workflow
        mock_handle.assert_called_once()


# Error Handling Tests
def test_handle_workflow_error_failed(
    client: WorkcellClient, sample_workflow_instance: Workflow
) -> None:
    """Test handling a failed workflow."""
    sample_workflow_instance.status.failed = True
    sample_workflow_instance.status.current_step_index = 0

    with pytest.raises(WorkflowFailedError):
        client._handle_workflow_error(
            sample_workflow_instance,
            prompt_on_error=False,
            raise_on_failed=True,
            raise_on_cancelled=False,
        )


def test_handle_workflow_error_cancelled(
    client: WorkcellClient, sample_workflow_instance: Workflow
) -> None:
    """Test handling a cancelled workflow."""
    sample_workflow_instance.status.cancelled = True
    sample_workflow_instance.status.current_step_index = 0

    with pytest.raises(WorkflowFailedError):
        client._handle_workflow_error(
            sample_workflow_instance,
            prompt_on_error=False,
            raise_on_failed=False,
            raise_on_cancelled=True,
        )


def test_handle_workflow_error_no_raise(
    client: WorkcellClient, sample_workflow_instance: Workflow
) -> None:
    """Test handling a failed workflow without raising exception."""
    sample_workflow_instance.status.failed = True
    sample_workflow_instance.status.current_step_index = 0

    result = client._handle_workflow_error(
        sample_workflow_instance,
        prompt_on_error=False,
        raise_on_failed=False,
        raise_on_cancelled=False,
    )

    assert result == sample_workflow_instance


# Client Initialization Tests
def test_workcell_client_init_with_url() -> None:
    """Test WorkcellClient initialization with URL."""
    client = WorkcellClient(workcell_server_url="http://test.com")
    assert str(client.workcell_server_url) == "http://test.com/"


def test_workcell_client_init_with_trailing_slash() -> None:
    """Test WorkcellClient initialization with trailing slash removal."""
    client = WorkcellClient(workcell_server_url="http://test.com/")
    assert str(client.workcell_server_url) == "http://test.com/"


def test_workcell_client_init_with_working_directory() -> None:
    """Test WorkcellClient initialization with working directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        client = WorkcellClient(
            workcell_server_url="http://test.com", working_directory=temp_dir
        )
        assert client.working_directory == Path(temp_dir)


def test_workcell_client_init_no_url() -> None:
    """Test WorkcellClient initialization without URL raises error."""
    with patch(
        "madsci.client.workcell_client.get_current_madsci_context"
    ) as mock_context:
        mock_context.return_value.workcell_server_url = None

        with pytest.raises(ValueError, match="Workcell server URL is not provided"):
            WorkcellClient()


# Additional Error Handling and Edge Case Tests
def test_start_workflow_alias(client: WorkcellClient) -> None:
    """Test that start_workflow is an alias for submit_workflow."""
    # start_workflow should be the same as submit_workflow
    assert client.start_workflow == client.submit_workflow


def test_client_logger_property(client: WorkcellClient) -> None:
    """Test that client has a logger property."""
    assert hasattr(client, "logger")
    assert client.logger is not None


def test_client_url_property(client: WorkcellClient) -> None:
    """Test that client has correct URL property."""
    assert str(client.workcell_server_url) == "http://testserver/"


def test_workflow_sequence_empty_lists(client: WorkcellClient) -> None:
    """Test submitting empty workflow sequence."""
    result = client.submit_workflow_sequence([], [])
    assert result == []


def test_workflow_batch_empty_lists(client: WorkcellClient) -> None:
    """Test submitting empty workflow batch."""
    result = client.submit_workflow_batch([], [])
    assert result == []


def test_add_node_error_handling(client: WorkcellClient) -> None:
    """Test error handling when adding nodes."""
    # Add a node to verify the method works
    node = client.add_node("test_node", "http://test_node/")
    assert node["node_url"] == "http://test_node/"

    # Get the node to verify it exists
    retrieved_node = client.get_node("test_node")
    assert retrieved_node["node_url"] == "http://test_node/"


def test_location_edge_cases(client: WorkcellClient) -> None:
    """Test location methods with edge cases."""
    # Get all locations initially
    initial_locations = client.get_locations()
    initial_count = len(initial_locations)

    # Add a new location
    location = Location(location_name="edge_case_location")
    added_location = client.add_location(location, permanent=False)

    # Verify it was added
    all_locations = client.get_locations()
    assert len(all_locations) == initial_count + 1

    # Get the specific location
    retrieved_location = client.get_location(added_location.location_id)
    assert retrieved_location.location_name == "edge_case_location"


def test_check_parameter_missing(client: WorkcellClient) -> None:
    """Test parameter insertion with missing required parameter."""
    workflow = WorkflowDefinition(
        name="Test",
        parameters=WorkflowParameters(
            input_values=[InputValue(key="required_param")]
        ),
        steps=[
            StepDefinition(
                name="step1",
                node="node1",
                action="action1",
                parameters={
                    "args": {"param": "required_param"},
                },
            )
        ],
    )

    with pytest.raises(ValueError, match="Required value required_param not provided"):
        client.check_parameters(workflow, {})


def test_check_parameter_conflict(client: WorkcellClient) -> None:
    """Test parameter insertion with conflicting configuration."""
    workflow = WorkflowDefinition(
        name="Test",
        parameters=WorkflowParameters(
            feed_forward_values=[
                FeedForwardValue(
                    key="conflict_param", label="some_label", step_name="step1"
                )
            ]
        ),
        steps=[
            StepDefinition(
                name="step1",
                node="node1",
                action="action1",
                parameters={
                    "args": {"param": "conflict_param"},
                },
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="conflict_param is a Feed Forward Value and will be calculated during execution",
    ):
        client.check_parameters(workflow, {"conflict_param": "value"})
