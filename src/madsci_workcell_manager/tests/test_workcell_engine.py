"""Automated unit tests for the Workcell Engine, using pytest."""

import copy
import warnings
from unittest.mock import patch

import pytest
from madsci.client.data_client import DataClient
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionFailed,
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
    ):
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


def test_run_single_step_with_update_parameters(
    engine: Engine, state_handler: WorkcellStateHandler
) -> None:
    """Test running a step in a workflow."""
    step = Step(
        name="Test Step 1",
        action="test_action",
        node="node1",
        args={},
        data_labels={"test": "test_label"},
    )
    workflow = Workflow(
        name="Test Workflow",
        parameters=WorkflowParameters(
            feed_forward=[
                ParameterFeedForwardJson(key="test_param", step=0, label="test_label")
            ]
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
            status=ActionStatus.SUCCEEDED, data={"test": "test_value"}
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
        data_labels={"key1": "label1"},
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
    action_result = ActionSucceeded(data={"key1": 42})

    with patch.object(engine.data_client, "submit_datapoint") as mock_submit:
        updated_result = engine.handle_data_and_files(step, workflow, action_result)
        assert "label1" in updated_result.data
        mock_submit.assert_called_once()
        submitted_datapoint = mock_submit.call_args[0][0]
        assert isinstance(submitted_datapoint, ValueDataPoint)
        assert submitted_datapoint.label == "label1"
        assert submitted_datapoint.value == 42


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
    action_result = ActionSucceeded(files={"file1": "/path/to/file"})

    with (
        patch.object(engine.data_client, "submit_datapoint") as mock_submit,
        patch("pathlib.Path.exists", return_value=True),
    ):
        updated_result = engine.handle_data_and_files(step, workflow, action_result)
        assert "label1" in updated_result.data
        mock_submit.assert_called_once()
        submitted_datapoint = mock_submit.call_args[0][0]
        assert isinstance(submitted_datapoint, FileDataPoint)
        assert submitted_datapoint.label == "label1"
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"output_label": value_datapoint}
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"output_file": file_datapoint}
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED, datapoints={"only_output": value_datapoint}
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"output1": value_datapoint1, "output2": value_datapoint2},
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"existing_output": value_datapoint},
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

    with pytest.raises(ValueError, match="specified label nonexistent_label not found"):
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"value_output": value_datapoint, "file_output": file_datapoint},
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

    step = Step(
        name="Test Step",
        key="step1",
        action="test_action",
        node="node1",
        result=ActionResult(
            status=ActionStatus.SUCCEEDED,
            datapoints={"s3_output": object_storage_datapoint},
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
