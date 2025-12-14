"""Automated unit tests for the Workcell Engine, using pytest."""

import copy
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from madsci.client.data_client import DataClient
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionFailed,
    ActionJSON,
    ActionResult,
    ActionStatus,
    ActionSucceeded,
)
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.datapoint_types import (
    FileDataPoint,
    ObjectStorageDataPoint,
    ValueDataPoint,
)
from madsci.common.types.node_types import Node, NodeCapabilities, NodeInfo
from madsci.common.types.parameter_types import (
    ParameterFeedForwardFile,
    ParameterFeedForwardJson,
)
from madsci.common.types.step_types import Step, StepParameters
from madsci.common.types.workcell_types import WorkcellManagerDefinition
from madsci.common.types.workflow_types import (
    SchedulerMetadata,
    Workflow,
    WorkflowParameters,
    WorkflowStatus,
)
from madsci.common.utils import new_ulid_str
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_engine import Engine
from pytest_mock_resources import RedisConfig, create_redis_fixture
from redis import Redis

from madsci_workcell_manager.madsci.workcell_manager.workflow_utils import (
    insert_parameters,
)


# Create a Redis server fixture for testing
@pytest.fixture(scope="session")
def pmr_redis_config() -> RedisConfig:
    """Configure the Redis server."""
    return RedisConfig(image="redis:7.4")


redis_server = create_redis_fixture()

test_node = Node(
    node_url="http://node-url",
    info=NodeInfo(
        node_name="Test Node",
        module_name="test_module",
        capabilities=NodeCapabilities(get_action_result=True),
        actions={
            "test_action": ActionDefinition(
                name="test_action",
            )
        },
    ),
)


@pytest.fixture
def state_handler(redis_server: Redis) -> WorkcellStateHandler:
    """Fixture for creating a WorkcellRedisHandler."""
    workcell_def = WorkcellManagerDefinition(
        name="Test Workcell",
    )
    return WorkcellStateHandler(
        workcell_definition=workcell_def, redis_connection=redis_server
    )


@pytest.fixture
def engine(state_handler: WorkcellStateHandler) -> Engine:
    """Fixture for creating an Engine instance."""
    # Create a mock context with all required URLs for LocationClient
    mock_context = MadsciContext(
        lab_server_url="http://localhost:8000/",
        event_server_url="http://localhost:8001/",
        experiment_server_url="http://localhost:8002/",
        data_server_url="http://localhost:8004/",
        resource_server_url="http://localhost:8003/",
        workcell_server_url="http://localhost:8005/",
        location_server_url="http://localhost:8006/",
    )

    with (
        warnings.catch_warnings(),
        patch(
            "madsci.client.location_client.get_current_madsci_context",
            return_value=mock_context,
        ),
        patch(
            "madsci.workcell_manager.workcell_engine.LocationClient"
        ) as mock_location_client,
    ):
        # Configure the mock location client to return empty location lists
        mock_location_client_instance = MagicMock()
        mock_location_client_instance.get_locations.return_value = []
        mock_location_client.return_value = mock_location_client_instance

        warnings.simplefilter("ignore", UserWarning)
        return Engine(state_handler=state_handler, data_client=DataClient())


def test_engine_initialization(engine: Engine) -> None:
    """Test the initialization of the Engine."""
    assert engine.state_handler is not None
    assert engine.workcell_definition.name == "Test Workcell"


def test_run_next_step_no_ready_workflows(engine: Engine) -> None:
    """Test run_next_step when no workflows are ready."""
    workflow = engine.run_next_step()
    assert workflow is None


def test_disconnect_node_on_connection_failure(engine: Engine) -> None:
    """Test run_next_step when no workflows are ready."""
    with patch(
        "madsci.client.node.rest_node_client.RestNodeClient.get_status",
        side_effect=Exception("Connection failed"),
    ):
        engine.update_active_nodes(engine.state_handler)
        for node in engine.state_handler.get_nodes().values():
            assert node.status.disconnected is True


def test_run_next_step_with_ready_workflow(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test run_next_step with a ready workflow."""
    workflow = Workflow(
        name="Test Workflow",
        steps=[Step(name="Test Step", action="test_action", node="test_node", args={})],
        scheduler_metadata=SchedulerMetadata(ready_to_run=True, priority=1),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.enqueue_workflow(workflow.workflow_id)
    state_handler.update_workflow_queue()
    with patch(
        "madsci.workcell_manager.workcell_engine.Engine.run_step"
    ) as mock_run_step:
        assert engine.run_next_step() is not None
        mock_run_step.assert_called_once()
    updated_workflow = state_handler.get_workflow(workflow.workflow_id)
    assert updated_workflow.status.running is True


def test_run_single_step(engine: Engine, state_handler: WorkcellStateHandler) -> None:
    """Test running a step in a workflow."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )
    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.return_value = ActionResult(
            status=ActionStatus.SUCCEEDED
        )
        thread = engine.run_step(workflow.workflow_id)
        thread.join()
        updated_workflow = state_handler.get_workflow(workflow.workflow_id)
        assert updated_workflow.steps[0].status == ActionStatus.SUCCEEDED
        assert updated_workflow.steps[0].result.status == ActionStatus.SUCCEEDED
        assert updated_workflow.status.current_step_index == 0
        assert updated_workflow.status.completed is True
        assert updated_workflow.end_time is not None
        assert updated_workflow.status.active is False


# Parameter Insertion Tests
def test_insert_parameter_values_basic() -> None:
    """Test basic parameter value insertion."""
    step = Step(
        name="step1",
        node="node1",
        action="action1",
        use_parameters=StepParameters(args={"param": "test_param"}),
    )

    step = insert_parameters(step, {"test_param": "custom_value"})

    assert step.args["param"] == "custom_value"


class UpdateParamJSON(ActionJSON):
    test: str


def test_run_single_step_with_update_parameters(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test running a step in a workflow."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            feed_forward=[ParameterFeedForwardJson(key="test_param", step=0)]
        ),
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )
    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.return_value = ActionResult(
            status=ActionStatus.SUCCEEDED, json_result="test_value"
        )
        thread = engine.run_step(workflow.workflow_id)
        thread.join()
        updated_workflow = state_handler.get_workflow(workflow.workflow_id)
        assert updated_workflow.steps[0].status == ActionStatus.SUCCEEDED
        assert updated_workflow.steps[0].result.status == ActionStatus.SUCCEEDED
        assert updated_workflow.status.current_step_index == 0
        assert updated_workflow.status.completed is True
        assert updated_workflow.end_time is not None
        assert updated_workflow.status.active is False
        assert updated_workflow.parameter_values["test_param"] == "test_value"


def test_run_single_step_of_workflow_with_multiple_steps(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test running a step in a workflow with multiple steps."""
    step1 = Step(name="Test Step 1", action="test_action", node="node1", args={})
    step2 = Step(name="Test Step 2", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step1, step2],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )
    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.return_value = ActionResult(
            status=ActionStatus.SUCCEEDED
        )
        thread = engine.run_step(workflow.workflow_id)
        thread.join()
        updated_workflow = state_handler.get_workflow(workflow.workflow_id)
        assert updated_workflow.steps[0].status == ActionStatus.SUCCEEDED
        assert updated_workflow.steps[0].result.status == ActionStatus.SUCCEEDED
        assert updated_workflow.steps[1].status == ActionStatus.NOT_STARTED
        assert updated_workflow.steps[1].result is None
        assert updated_workflow.status.current_step_index == 1
        assert updated_workflow.status.active is True


def test_finalize_step_success(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test finalizing a successful step."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    updated_step = copy.deepcopy(step)
    updated_step.status = ActionStatus.SUCCEEDED
    updated_step.result = ActionSucceeded()

    engine.finalize_step(workflow.workflow_id, updated_step)

    finalized_workflow = state_handler.get_workflow(workflow.workflow_id)
    assert finalized_workflow.status.completed is True
    assert finalized_workflow.end_time is not None
    assert finalized_workflow.steps[0].status == ActionStatus.SUCCEEDED


def test_finalize_step_failure(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test finalizing a failed step."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    updated_step = copy.deepcopy(step)
    updated_step.status = ActionStatus.FAILED
    updated_step.result = ActionFailed()

    engine.finalize_step(workflow.workflow_id, updated_step)

    finalized_workflow = state_handler.get_workflow(workflow.workflow_id)
    assert finalized_workflow.status.failed is True
    assert finalized_workflow.end_time is not None
    assert finalized_workflow.steps[0].status == ActionStatus.FAILED


def test_handle_data_and_files_with_data(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test handle_data_and_files with data points."""
    step = Step(
        name="Test Step",
        action="test_action",
        node="node1",
        args={},
    )
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )
    action_result = ActionSucceeded(json_result=42)

    # Create a mock datapoint that will be returned by submit_datapoint
    mock_returned_datapoint = ValueDataPoint(label="json_result", value=42)

    with patch.object(
        engine.data_client, "submit_datapoint", return_value=mock_returned_datapoint
    ) as mock_submit:
        updated_result = engine.handle_data_and_files(step, workflow, action_result)
        assert "json_result" in updated_result.datapoints.model_dump()
        mock_submit.assert_called_once()
        submitted_datapoint = mock_submit.call_args[0][0]
        assert isinstance(submitted_datapoint, ValueDataPoint)
        assert submitted_datapoint.label == "json_result"
        assert submitted_datapoint.value == 42

        # Verify the returned datapoint ID was added to the result
        assert (
            updated_result.datapoints.model_dump()["json_result"]
            == mock_returned_datapoint.datapoint_id
        )


def test_handle_data_and_files_with_files(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test handle_data_and_files with file points."""
    step = Step(
        name="Test Step",
        action="test_action",
        node="node1",
        args={},
        data_labels={"file1": "label1"},
    )
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )
    action_result = ActionSucceeded(files=Path("/path/to/file"))

    with (
        patch.object(engine.data_client, "submit_datapoint") as mock_submit,
        patch("pathlib.Path.exists", return_value=True),
    ):
        updated_result = engine.handle_data_and_files(step, workflow, action_result)
        assert "file" in updated_result.datapoints.model_dump()
        mock_submit.assert_called_once()
        submitted_datapoint = mock_submit.call_args[0][0]
        assert isinstance(submitted_datapoint, FileDataPoint)
        assert submitted_datapoint.label == "file"
        assert submitted_datapoint.path == "/path/to/file"


def test_run_step_send_action_exception_then_get_action_result_success(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test run_step where send_action raises an exception but get_action_result succeeds."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )

    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.side_effect = Exception(
            "send_action failed"
        )
        mock_client.return_value.get_action_result.return_value = ActionResult(
            status=ActionStatus.SUCCEEDED
        )

        thread = engine.run_step(workflow.workflow_id)
        thread.join()

        # TODO
        updated_workflow = state_handler.get_workflow(workflow.workflow_id)
        step = updated_workflow.steps[0]
        assert step.status == ActionStatus.SUCCEEDED
        assert step.result is not None
        assert step.result.status == ActionStatus.SUCCEEDED
        mock_client.return_value.get_action_result.assert_called_once()


def test_run_step_send_action_and_get_action_result_fail(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test run_step where both send_action and get_action_result fail."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        status=WorkflowStatus(running=True),
    )
    state_handler.set_active_workflow(workflow)
    state_handler.set_node(
        node_name="node1",
        node=test_node,
    )

    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.side_effect = Exception(
            "send_action failed"
        )
        mock_client.return_value.get_action_result.side_effect = Exception(
            "get_action_result failed"
        )

        thread = engine.run_step(workflow.workflow_id)
        thread.join()

        # TODO
        updated_workflow = state_handler.get_workflow(workflow.workflow_id)
        step = updated_workflow.steps[0]
        assert step.status == ActionStatus.UNKNOWN
        assert step.result.status == ActionStatus.UNKNOWN
        mock_client.return_value.get_action_result.assert_called()


# Feed Data Forward Tests
def test_feed_data_forward_value_by_label(engine: Engine) -> None:
    """Test feed forward with value datapoint matched by label."""
    value_datapoint = ValueDataPoint(label="output_label", value="test_value")

    # Mock the data client to return the datapoint when requested
    with patch.object(
        engine.data_client, "get_datapoint", return_value=value_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"output_label": value_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="param1", step="step1", label="output_label"
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert updated_wf.parameter_values["param1"] == "test_value"


def test_feed_data_forward_file_by_label(engine: Engine) -> None:
    """Test feed forward with file datapoint matched by label."""
    file_datapoint = FileDataPoint(label="output_file", path="/path/to/file.txt")

    # Mock the data client to return the datapoint when requested
    with patch.object(engine.data_client, "get_datapoint", return_value=file_datapoint):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"output_file": file_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardFile(
                        key="file_param", step="step1", label="output_file"
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert updated_wf.file_input_ids["file_param"] == file_datapoint.datapoint_id


def test_feed_data_forward_by_step_index(engine: Engine) -> None:
    """Test feed forward matched by step index."""
    value_datapoint = ValueDataPoint(label="output", value=42)

    # Mock the data client to return the datapoint when requested
    with patch.object(
        engine.data_client, "get_datapoint", return_value=value_datapoint
    ):
        step = Step(
            name="Test Step",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"output": value_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="param_by_index",
                        step=0,  # Match by step index
                        label="output",
                    )
                ]
            ),
            steps=[step],
            status=WorkflowStatus(current_step_index=0),
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert updated_wf.parameter_values["param_by_index"] == 42


def test_feed_data_forward_no_step_single_datapoint(engine: Engine) -> None:
    """Test feed forward with no step specified and single datapoint."""
    value_datapoint = ValueDataPoint(label="only_output", value="single_value")

    # Mock the data client to return the datapoint when requested
    with patch.object(
        engine.data_client, "get_datapoint", return_value=value_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"only_output": value_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="auto_param",
                        step="step1",  # Match by step, no label specified
                        label=None,
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert updated_wf.parameter_values["auto_param"] == "single_value"


def test_feed_data_forward_no_step_multiple_datapoints_error(engine: Engine) -> None:
    """Test feed forward error when no step/label specified with multiple datapoints."""
    value_datapoint1 = ValueDataPoint(label="output1", value="value1")
    value_datapoint2 = ValueDataPoint(label="output2", value="value2")

    # Mock the data client to return the datapoints when requested
    def mock_get_datapoint(datapoint_id):
        if datapoint_id == value_datapoint1.datapoint_id:
            return value_datapoint1
        if datapoint_id == value_datapoint2.datapoint_id:
            return value_datapoint2
        return None

    with patch.object(
        engine.data_client, "get_datapoint", side_effect=mock_get_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={
                    "output1": value_datapoint1.datapoint_id,
                    "output2": value_datapoint2.datapoint_id,
                },
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="ambiguous_param",
                        step="step1",  # Match by step, no label specified
                        label=None,
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        with pytest.raises(ValueError, match="Ambiguous feed-forward parameter"):
            engine._feed_data_forward(step, workflow)


def test_feed_data_forward_label_not_found_error(engine: Engine) -> None:
    """Test feed forward error when specified label is not found."""
    value_datapoint = ValueDataPoint(label="existing_output", value="value")

    # Mock the data client to return the datapoint when requested
    with patch.object(
        engine.data_client, "get_datapoint", return_value=value_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"existing_output": value_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="missing_param", step="step1", label="nonexistent_label"
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        with pytest.raises(
            ValueError, match="specified label nonexistent_label not found"
        ):
            engine._feed_data_forward(step, workflow)


def test_feed_data_forward_step_name_no_match(engine: Engine) -> None:
    """Test feed forward when step name doesn't match."""
    value_datapoint = ValueDataPoint(label="output", value="value")

    step = Step(
        name="Test Step",
        key="step1",  # Different key than parameter expects
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"output": value_datapoint}
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            feed_forward=[
                ParameterFeedForwardJson(
                    key="no_match_param",
                    step="different_step",  # Different step name
                    label="output",
                )
            ]
        ),
        steps=[step],
        parameter_values={},
        file_input_ids={},
    )

    # Should not update parameter values since step doesn't match
    updated_wf = engine._feed_data_forward(step, workflow)
    assert "no_match_param" not in updated_wf.parameter_values


def test_feed_data_forward_step_index_no_match(engine: Engine) -> None:
    """Test feed forward when step index doesn't match."""
    value_datapoint = ValueDataPoint(label="output", value="value")

    step = Step(
        name="Test Step",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"output": value_datapoint}
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            feed_forward=[
                ParameterFeedForwardJson(
                    key="index_param",
                    step=1,  # Step index 1, but current is 0
                    label="output",
                )
            ]
        ),
        steps=[step],
        status=WorkflowStatus(current_step_index=0),
        parameter_values={},
        file_input_ids={},
    )

    # Should not update parameter values since step index doesn't match
    updated_wf = engine._feed_data_forward(step, workflow)
    assert "index_param" not in updated_wf.parameter_values


def test_feed_data_forward_multiple_parameters(engine: Engine) -> None:
    """Test feed forward with multiple parameters from same step."""
    value_datapoint = ValueDataPoint(label="value_output", value="test_value")
    file_datapoint = FileDataPoint(label="file_output", path="/test/file.txt")

    # Mock the data client to return the appropriate datapoint when requested
    def mock_get_datapoint(datapoint_id):
        if datapoint_id == value_datapoint.datapoint_id:
            return value_datapoint
        if datapoint_id == file_datapoint.datapoint_id:
            return file_datapoint
        return None

    with patch.object(
        engine.data_client, "get_datapoint", side_effect=mock_get_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={
                    "value_output": value_datapoint.datapoint_id,
                    "file_output": file_datapoint.datapoint_id,
                },
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardJson(
                        key="value_param", step="step1", label="value_output"
                    ),
                    ParameterFeedForwardFile(
                        key="file_param", step="step1", label="file_output"
                    ),
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert updated_wf.parameter_values["value_param"] == "test_value"
        assert updated_wf.file_input_ids["file_param"] == file_datapoint.datapoint_id


def test_feed_data_forward_object_storage_by_label(engine: Engine) -> None:
    """Test feed forward with object storage datapoint matched by label."""
    object_storage_datapoint = ObjectStorageDataPoint(
        label="s3_output",
        storage_endpoint="localhost:9000",
        path="/local/path/file.dat",
        bucket_name="test-bucket",
        object_name="data/file.dat",
    )

    # Mock the data client to return the datapoint when requested
    with patch.object(
        engine.data_client, "get_datapoint", return_value=object_storage_datapoint
    ):
        step = Step(
            name="Test Step",
            key="step1",
            action="test_action",
            node="node1",
            result=ActionResult(
                status=ActionStatus.SUCCEEDED,
                datapoints={"s3_output": object_storage_datapoint.datapoint_id},
            ),
        )

        workflow = Workflow(
            name="Test Workflow",
            parameters=WorkflowParameters(
                feed_forward=[
                    ParameterFeedForwardFile(
                        key="storage_param", step="step1", label="s3_output"
                    )
                ]
            ),
            steps=[step],
            parameter_values={},
            file_input_ids={},
        )

        updated_wf = engine._feed_data_forward(step, workflow)
        assert (
            updated_wf.file_input_ids["storage_param"]
            == object_storage_datapoint.datapoint_id
        )


def test_feed_data_forward_no_matching_parameters(engine: Engine) -> None:
    """Test feed forward when no parameters match the step."""
    value_datapoint = ValueDataPoint(label="output", value="value")

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"output": value_datapoint}
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            feed_forward=[]  # No feed forward parameters
        ),
        steps=[step],
        parameter_values={"existing": "value"},
        file_input_ids={"existing_file": "file_id"},
    )

    updated_wf = engine._feed_data_forward(step, workflow)
    # Should not modify existing values
    assert updated_wf.parameter_values == {"existing": "value"}
    assert updated_wf.file_input_ids == {"existing_file": "file_id"}


# Workflow get_datapoint_id and get_datapoint method tests
def test_get_datapoint_id_single_datapoint_no_label() -> None:
    """Test get_datapoint_id with single datapoint and no label specified."""
    datapoint_id = new_ulid_str()
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"result": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should return the single datapoint ID when no label specified
    result_id = workflow.get_datapoint_id(step_key="step1")
    assert result_id == datapoint_id


def test_get_datapoint_id_single_datapoint_with_label() -> None:
    """Test get_datapoint_id with single datapoint and specific label."""
    datapoint_id = new_ulid_str()
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"output_file": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should return the datapoint ID for the specific label
    result_id = workflow.get_datapoint_id(step_key="step1", label="output_file")
    assert result_id == datapoint_id


def test_get_datapoint_id_multiple_datapoints_with_label() -> None:
    """Test get_datapoint_id with multiple datapoints and specific label."""
    datapoint_id_1 = new_ulid_str()
    datapoint_id_2 = new_ulid_str()
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={
                "result_data": datapoint_id_1,
                "log_file": datapoint_id_2,
            },
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should return the correct datapoint ID for the specified label
    result_id = workflow.get_datapoint_id(step_key="step1", label="log_file")
    assert result_id == datapoint_id_2


def test_get_datapoint_id_multiple_datapoints_no_label_raises_error() -> None:
    """Test get_datapoint_id with multiple datapoints but no label raises ValueError."""
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={
                "result_data": new_ulid_str(),
                "log_file": new_ulid_str(),
            },
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should raise ValueError when multiple datapoints exist but no label specified
    with pytest.raises(
        ValueError, match="Step step1 has multiple datapoints, label must be specified"
    ):
        workflow.get_datapoint_id(step_key="step1")


def test_get_datapoint_id_single_datapoint_ignores_wrong_label() -> None:
    """Test get_datapoint_id with single datapoint ignores wrong label."""
    datapoint_id = new_ulid_str()
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"existing_label": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should return the single datapoint even with wrong label (expected behavior)
    result_id = workflow.get_datapoint_id(step_key="step1", label="nonexistent_label")
    assert result_id == datapoint_id


def test_get_datapoint_id_label_not_found_raises_error() -> None:
    """Test get_datapoint_id with non-existent label raises KeyError (multiple datapoints case)."""
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={
                "existing_label": new_ulid_str(),
                "another_label": new_ulid_str(),
            },
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should raise KeyError when label doesn't exist in multiple datapoints case
    with pytest.raises(
        KeyError, match="Label nonexistent_label not found in step step1"
    ):
        workflow.get_datapoint_id(step_key="step1", label="nonexistent_label")


def test_get_datapoint_id_step_not_found_raises_error() -> None:
    """Test get_datapoint_id with non-existent step key raises KeyError."""
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"result": new_ulid_str()},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should raise KeyError when step doesn't exist
    with pytest.raises(KeyError, match="Datapoint ID not found in workflow run"):
        workflow.get_datapoint_id(step_key="nonexistent_step")


def test_get_datapoint_id_no_datapoints_raises_error() -> None:
    """Test get_datapoint_id with step having no datapoints raises KeyError."""
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints=None,  # No datapoints
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should raise KeyError when step has no datapoints
    with pytest.raises(KeyError, match="No datapoints found in step step1"):
        workflow.get_datapoint_id(step_key="step1")


def test_get_datapoint_id_no_step_key_single_step() -> None:
    """Test get_datapoint_id with no step key specified, single step with single datapoint."""
    datapoint_id = new_ulid_str()
    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"result": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Should return the datapoint from the first step when no step_key specified
    result_id = workflow.get_datapoint_id()
    assert result_id == datapoint_id


def test_get_datapoint_method_with_mock_client() -> None:
    """Test get_datapoint method calls DataClient correctly."""
    datapoint_id = new_ulid_str()
    mock_datapoint = ValueDataPoint(label="test_result", value=42)

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"test_result": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    # Mock the DataClient import and instantiation
    with patch("madsci.client.data_client.DataClient") as mock_data_client_class:
        mock_data_client = MagicMock()
        mock_data_client.get_datapoint.return_value = mock_datapoint
        mock_data_client_class.return_value = mock_data_client

        # Should call DataClient.get_datapoint with the correct datapoint_id
        result = workflow.get_datapoint(step_key="step1", label="test_result")

        mock_data_client_class.assert_called_once()
        mock_data_client.get_datapoint.assert_called_once_with(datapoint_id)
        assert result == mock_datapoint


def test_get_datapoint_method_integration_with_get_datapoint_id() -> None:
    """Test get_datapoint method properly uses get_datapoint_id."""
    datapoint_id = new_ulid_str()
    mock_datapoint = FileDataPoint(label="output_file", path="/test/path.txt")

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"output_file": datapoint_id},
        ),
    )

    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
    )

    with patch("madsci.client.data_client.DataClient") as mock_data_client_class:
        mock_data_client = MagicMock()
        mock_data_client.get_datapoint.return_value = mock_datapoint
        mock_data_client_class.return_value = mock_data_client

        # Test that get_datapoint correctly finds the datapoint_id and passes it to DataClient
        result = workflow.get_datapoint(step_key="step1", label="output_file")

        mock_data_client.get_datapoint.assert_called_once_with(datapoint_id)
        assert result == mock_datapoint


# Additional tests for handle_data_and_files method
class TestDatapointHandlingMethod:
    """Test cases for the handle_data_and_files method specifically."""

    def test_json_result_upload_isolated(self):
        """Test that JSON results are uploaded as ValueDataPoints in isolation."""
        # Mock the data client
        mock_data_client = MagicMock()
        submitted_datapoint = ValueDataPoint(
            value={"test": "data"}, label="json_result"
        )
        mock_data_client.submit_datapoint.return_value = submitted_datapoint

        # Create test data
        step = Step(name="Test Step", action="test_action", node="node1")
        workflow = Workflow(name="Test Workflow", steps=[step])
        response = ActionResult(
            status=ActionStatus.SUCCEEDED, json_result={"test": "data"}
        )

        # Mock the required attributes for the method
        mock_state_handler = MagicMock()
        mock_node_info = MagicMock()
        mock_node_info.info.node_id = "test_node_id"
        mock_state_handler.get_node.return_value = mock_node_info

        # Test the method directly by monkey-patching it onto a mock object
        with patch("madsci.workcell_manager.workcell_engine.ownership_context"):
            # Create a mock engine with just the required attributes
            mock_engine = MagicMock()
            mock_engine.data_client = mock_data_client
            mock_engine.state_handler = mock_state_handler
            mock_engine.workcell_definition = WorkcellManagerDefinition(
                name="Test Workcell"
            )

            # Bind the method to our mock
            result = Engine.handle_data_and_files(mock_engine, step, workflow, response)

            # Verify datapoint was uploaded
            mock_data_client.submit_datapoint.assert_called_once()
            call_args = mock_data_client.submit_datapoint.call_args[0][0]
            assert isinstance(call_args, ValueDataPoint)
            assert call_args.value == {"test": "data"}
            assert call_args.label == "json_result"

            # Verify response contains only datapoint IDs
            assert result.json_result is None  # Cleared after upload
            assert result.datapoints is not None
            assert result.datapoints.json_result == submitted_datapoint.datapoint_id
