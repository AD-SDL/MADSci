"""Automated unit tests for the Workcell Engine, using pytest."""

import copy
import warnings
from unittest.mock import patch

import pytest
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionFailed,
    ActionResult,
    ActionStatus,
    ActionSucceeded,
)
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.types.node_types import Node, NodeCapabilities, NodeInfo
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    SchedulerMetadata,
    Workflow,
    WorkflowParameter,
    WorkflowStatus,
)
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_engine import Engine
from pytest_mock_resources import RedisConfig, create_redis_fixture
from redis import Redis


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
    workcell_def = WorkcellDefinition(
        workcell_name="Test Workcell",
    )
    return WorkcellStateHandler(
        workcell_definition=workcell_def, redis_connection=redis_server
    )


@pytest.fixture
def engine(state_handler: WorkcellStateHandler) -> Engine:
    """Fixture for creating an Engine instance."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return Engine(state_handler=state_handler)


def test_engine_initialization(engine: Engine) -> None:
    """Test the initialization of the Engine."""
    assert engine.state_handler is not None
    assert engine.workcell_definition.workcell_name == "Test Workcell"


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
        parameters=[
            WorkflowParameter(
                name="test_param", step_name="Test Step 1", label="test_label"
            )
        ],
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
