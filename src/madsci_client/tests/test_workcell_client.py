"""Unit tests for WorkcellClient."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from madsci.client.workcell_client import WorkcellClient
from madsci.common.db_handlers import (
    InMemoryCacheHandler,
    InMemoryDocumentStorageHandler,
)
from madsci.common.exceptions import WorkflowFailedError
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.node_types import Node
from madsci.common.types.parameter_types import ParameterInputJson
from madsci.common.types.step_types import Step, StepDefinition
from madsci.common.types.workcell_types import (
    WorkcellManagerSettings,
    WorkcellState,
)
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowDefinition,
    WorkflowParameters,
    WorkflowStatus,
)
from madsci.common.utils import new_ulid_str
from madsci.workcell_manager.workcell_server import WorkcellManager


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
            json_inputs=[ParameterInputJson(key="test_param", default="default_value")]
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
                    "file_input": {
                        "key": "file_input",
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
def test_client() -> Generator[TestClient, None, None]:
    """Workcell Server Test Client Fixture."""
    # Create a mock context with all required URLs
    mock_context = MadsciContext(
        lab_server_url="http://localhost:8000/",
        event_server_url="http://localhost:8001/",
        experiment_server_url="http://localhost:8002/",
        data_server_url="http://localhost:8004/",
        resource_server_url="http://localhost:8003/",
        workcell_server_url="http://localhost:8005/",
        location_server_url="http://localhost:8006/",
    )

    custom_settings = WorkcellManagerSettings(
        manager_name="Test Workcell",
        enable_registry_resolution=False,
    )

    with (
        patch(
            "madsci.workcell_manager.workcell_server.get_current_madsci_context",
            return_value=mock_context,
        ),
        patch(
            "madsci.client.location_client.get_current_madsci_context",
            return_value=mock_context,
        ),
        patch(
            "madsci.workcell_manager.workcell_server.LocationClient"
        ) as mock_location_client,
        patch(
            "madsci.workcell_manager.workcell_engine.LocationClient"
        ) as mock_engine_location_client,
        patch(
            "madsci.client.client_mixin.LocationClient"
        ) as mock_mixin_location_client,
    ):
        # Configure the mock location clients to return empty location lists
        mock_location_client_instance = MagicMock()
        mock_location_client_instance.get_locations.return_value = []
        mock_location_client.return_value = mock_location_client_instance

        mock_engine_location_client_instance = MagicMock()
        mock_engine_location_client_instance.get_locations.return_value = []
        mock_engine_location_client.return_value = mock_engine_location_client_instance

        mock_mixin_location_client_instance = MagicMock()
        mock_mixin_location_client_instance.get_locations.return_value = []
        mock_mixin_location_client.return_value = mock_mixin_location_client_instance

        manager = WorkcellManager(
            settings=custom_settings,
            cache_handler=InMemoryCacheHandler(),
            document_handler=InMemoryDocumentStorageHandler(),
            start_engine=False,
        )
        app = manager.create_server()
        client = TestClient(app)
        with client:
            yield client


@pytest.fixture
def client(test_client: TestClient) -> Generator[WorkcellClient, None, None]:
    """Fixture for WorkcellClient patched to use TestClient."""

    method_map = {
        "GET": test_client.get,
        "POST": test_client.post,
        "PUT": test_client.put,
        "DELETE": test_client.delete,
        "PATCH": test_client.patch,
    }

    def request_via_test_client(method: str, url: str, **kwargs: Any) -> Response:
        kwargs.pop("timeout", None)
        handler = method_map.get(method.upper(), test_client.get)
        resp = handler(url, **kwargs)
        if not hasattr(resp, "is_success"):
            resp.is_success = resp.status_code < 400
        return resp

    # Create a mock event client to prevent connection attempts
    mock_event_client = Mock()

    # Create the client
    workcell_client = WorkcellClient(
        workcell_server_url="http://testserver", event_client=mock_event_client
    )

    # Patch the httpx client's request method to use the test client
    workcell_client._client.request = request_via_test_client

    yield workcell_client


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
    json_inputs = [{"test_param": "value1"}, {"test_param": "value2"}]

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

        result = client.submit_workflow_sequence(workflows, json_inputs)

        assert len(result) == 2
        assert mock_submit.call_count == 2
        mock_submit.assert_any_call(
            workflows[0], json_inputs[0], {}, await_completion=True
        )
        mock_submit.assert_any_call(
            workflows[1], json_inputs[1], {}, await_completion=True
        )


def test_submit_workflow_batch(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test submitting a batch of workflows."""
    workflows = [sample_workflow, sample_workflow]
    json_inputs = [{"test_param": "value1"}, {"test_param": "value2"}]

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

        result = client.submit_workflow_batch(workflows, json_inputs)

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


def test_resubmit_workflow(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test resubmitting a workflow."""
    client.add_node("test_node", "http://test_node/")
    submitted_workflow = client.submit_workflow(sample_workflow, await_completion=False)

    with patch.object(client, "await_workflow") as mock_await:
        mock_workflow = Workflow(
            workflow_id=new_ulid_str(),
            name="Test Workflow",
            status=WorkflowStatus(completed=True),
            steps=[],
        )
        mock_await.return_value = mock_workflow

        resubmitted = client.resubmit_workflow(
            submitted_workflow.workflow_id, await_completion=True
        )

        assert isinstance(resubmitted, Workflow)
        # resubmit creates a new workflow, so await_workflow is called with the new ID
        mock_await.assert_called_once()


def test_resubmit_workflow_no_await(
    client: WorkcellClient, sample_workflow: WorkflowDefinition
) -> None:
    """Test resubmitting a workflow without waiting for completion."""
    client.add_node("test_node", "http://test_node/")
    submitted_workflow = client.submit_workflow(sample_workflow, await_completion=False)

    resubmitted = client.resubmit_workflow(
        submitted_workflow.workflow_id, await_completion=False
    )

    assert isinstance(resubmitted, Workflow)
    # Resubmit creates a new workflow with a new ID
    assert resubmitted.workflow_id != submitted_workflow.workflow_id
    assert resubmitted.name == submitted_workflow.name


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
    mock_event_client = Mock()
    client = WorkcellClient(
        workcell_server_url="http://test.com", event_client=mock_event_client
    )
    assert str(client.workcell_server_url) == "http://test.com/"


def test_workcell_client_init_with_trailing_slash() -> None:
    """Test WorkcellClient initialization with trailing slash removal."""
    mock_event_client = Mock()
    client = WorkcellClient(
        workcell_server_url="http://test.com/", event_client=mock_event_client
    )
    assert str(client.workcell_server_url) == "http://test.com/"


def test_workcell_client_init_with_working_directory() -> None:
    """Test WorkcellClient initialization with working directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_event_client = Mock()
        client = WorkcellClient(
            workcell_server_url="http://test.com",
            working_directory=temp_dir,
            event_client=mock_event_client,
        )
        assert client.working_directory == Path(temp_dir)


def test_workcell_client_init_no_url() -> None:
    """Test WorkcellClient initialization without URL raises error."""
    with (
        patch(
            "madsci.client.workcell_client.get_current_madsci_context"
        ) as mock_context,
        patch("madsci.client.workcell_client.EventClient") as mock_event_client_class,
    ):
        mock_context.return_value.workcell_server_url = None
        mock_event_client_class.return_value = Mock()

        with pytest.raises(ValueError, match="Workcell server URL was not provided"):
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


# ------------------------------------------------------------------
# Async method tests
# ------------------------------------------------------------------


def _make_mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with the given JSON data."""
    mock_resp = MagicMock(spec=Response)
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.is_success = status_code < 400
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture
def async_client() -> Generator[WorkcellClient, None, None]:
    """Fixture for WorkcellClient with mocked async request for async tests."""
    mock_event_client = Mock()
    workcell_client = WorkcellClient(
        workcell_server_url="http://testserver", event_client=mock_event_client
    )
    yield workcell_client


class TestAsyncGetNodes:
    """Tests for async_get_nodes returning proper Node models."""

    @pytest.mark.asyncio
    async def test_async_get_nodes_returns_dict_of_node_models(
        self, async_client: WorkcellClient
    ) -> None:
        """async_get_nodes should return dict[str, Node], not raw JSON."""
        node_data = {
            "node1": {
                "node_url": "http://node1/",
                "node_name": "node1",
            },
        }
        mock_resp = _make_mock_response(node_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        result = await async_client.async_get_nodes()

        assert isinstance(result, dict)
        assert "node1" in result
        assert isinstance(result["node1"], Node)
        assert str(result["node1"].node_url) == "http://node1/"

    @pytest.mark.asyncio
    async def test_async_get_nodes_calls_raise_for_status(
        self, async_client: WorkcellClient
    ) -> None:
        """async_get_nodes should call raise_for_status on the response."""
        node_data = {}
        mock_resp = _make_mock_response(node_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_get_nodes()

        mock_resp.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_get_nodes_empty(self, async_client: WorkcellClient) -> None:
        """async_get_nodes should handle an empty nodes dict."""
        mock_resp = _make_mock_response({})
        async_client._async_request = AsyncMock(return_value=mock_resp)

        result = await async_client.async_get_nodes()

        assert result == {}


class TestAsyncGetNode:
    """Tests for async_get_node returning a proper Node model."""

    @pytest.mark.asyncio
    async def test_async_get_node_returns_node_model(
        self, async_client: WorkcellClient
    ) -> None:
        """async_get_node should return a Node instance, not raw JSON."""
        node_data = {
            "node_url": "http://node1/",
            "node_name": "node1",
        }
        mock_resp = _make_mock_response(node_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        result = await async_client.async_get_node("node1")

        assert isinstance(result, Node)
        assert str(result.node_url) == "http://node1/"

    @pytest.mark.asyncio
    async def test_async_get_node_calls_raise_for_status(
        self, async_client: WorkcellClient
    ) -> None:
        """async_get_node should call raise_for_status on the response."""
        node_data = {
            "node_url": "http://node1/",
            "node_name": "node1",
        }
        mock_resp = _make_mock_response(node_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_get_node("node1")

        mock_resp.raise_for_status.assert_called_once()


class TestAsyncRetryWorkflow:
    """Tests for the async_retry_workflow method."""

    @pytest.mark.asyncio
    async def test_async_retry_workflow_exists(
        self, async_client: WorkcellClient
    ) -> None:
        """async_retry_workflow method should exist on WorkcellClient."""
        assert hasattr(async_client, "async_retry_workflow")
        assert callable(async_client.async_retry_workflow)

    @pytest.mark.asyncio
    async def test_async_retry_workflow_returns_workflow(
        self, async_client: WorkcellClient
    ) -> None:
        """async_retry_workflow should return a Workflow instance."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {"completed": False},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        result = await async_client.async_retry_workflow(workflow_id)

        assert isinstance(result, Workflow)
        assert result.workflow_id == workflow_id

    @pytest.mark.asyncio
    async def test_async_retry_workflow_calls_raise_for_status(
        self, async_client: WorkcellClient
    ) -> None:
        """async_retry_workflow should call raise_for_status."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_retry_workflow(workflow_id)

        mock_resp.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_retry_workflow_posts_to_correct_url(
        self, async_client: WorkcellClient
    ) -> None:
        """async_retry_workflow should POST to the correct retry endpoint."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_retry_workflow(workflow_id)

        call_args = async_client._async_request.call_args
        assert call_args[0][0] == "POST"
        assert f"workflow/{workflow_id}/retry" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_retry_workflow_with_index(
        self, async_client: WorkcellClient
    ) -> None:
        """async_retry_workflow should pass index as a query param when provided."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_retry_workflow(workflow_id, index=2)

        call_args = async_client._async_request.call_args
        params = call_args[1].get("params", {})
        assert params.get("index") == 2


class TestAsyncResubmitWorkflow:
    """Tests for the async_resubmit_workflow method."""

    @pytest.mark.asyncio
    async def test_async_resubmit_workflow_exists(
        self, async_client: WorkcellClient
    ) -> None:
        """async_resubmit_workflow method should exist on WorkcellClient."""
        assert hasattr(async_client, "async_resubmit_workflow")
        assert callable(async_client.async_resubmit_workflow)

    @pytest.mark.asyncio
    async def test_async_resubmit_workflow_returns_workflow(
        self, async_client: WorkcellClient
    ) -> None:
        """async_resubmit_workflow should return a Workflow instance."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        result = await async_client.async_resubmit_workflow(workflow_id)

        assert isinstance(result, Workflow)

    @pytest.mark.asyncio
    async def test_async_resubmit_workflow_calls_raise_for_status(
        self, async_client: WorkcellClient
    ) -> None:
        """async_resubmit_workflow should call raise_for_status."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_resubmit_workflow(workflow_id)

        mock_resp.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_resubmit_workflow_posts_to_correct_url(
        self, async_client: WorkcellClient
    ) -> None:
        """async_resubmit_workflow should POST to the correct resubmit endpoint."""
        workflow_id = new_ulid_str()
        workflow_data = {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "steps": [],
            "status": {},
        }
        mock_resp = _make_mock_response(workflow_data)
        async_client._async_request = AsyncMock(return_value=mock_resp)

        await async_client.async_resubmit_workflow(workflow_id)

        call_args = async_client._async_request.call_args
        assert call_args[0][0] == "POST"
        assert f"workflow/{workflow_id}/resubmit" in call_args[0][1]
