"""Automated unit tests for the Workcell Engine, using pytest."""

import copy
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.action_types import (
    ActionFailed,
    ActionResult,
    ActionStatus,
    ActionSucceeded,
)
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.types.node_types import Node, NodeInfo
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellConfig, WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowStatus
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_engine import Engine


@pytest.fixture
def mock_workcell_definition() -> WorkcellDefinition:
    """Fixture for a mock WorkcellDefinition."""
    return WorkcellDefinition(
        workcell_name="Test Workcell",
        config=WorkcellConfig(
            clear_workflows=True,
            scheduler="madsci.workcell_manager.scheduler",
            data_server_url="http://data-server",
            resource_server_url="http://resource-server",
            cold_start_delay=0,
            node_update_interval=1,
            scheduler_update_interval=1,
        ),
    )


@pytest.fixture
def mock_state_handler() -> MagicMock:
    """Fixture for a mock WorkcellRedisHandler."""
    handler = MagicMock(spec=WorkcellRedisHandler)
    handler.get_node.return_value = Node(
        node_url="http://node-url",
        info=NodeInfo(
            node_name="Test Node",
            module_name="test_module",
        ),
    )
    handler.get_all_workflows.return_value = {}
    handler.has_state_changed.return_value = False
    handler.shutdown = False
    handler.paused = False
    return handler


@pytest.fixture
def engine(
    mock_workcell_definition: WorkcellDefinition, mock_state_handler: MagicMock
) -> Engine:
    """Fixture for the Engine instance."""
    with patch(
        "madsci.workcell_manager.workcell_engine.importlib.import_module"
    ) as mock_import:
        mock_import.return_value.Scheduler = MagicMock()
        return Engine(mock_workcell_definition, mock_state_handler)


def test_engine_initialization(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test the initialization of the Engine."""
    mock_state_handler.clear_state.assert_called_once()
    assert engine.definition.workcell_name == "Test Workcell"
    assert engine.state_handler == mock_state_handler


def test_run_next_step_no_ready_workflows(
    engine: Engine, mock_state_handler: MagicMock
) -> None:
    """Test run_next_step when no workflows are ready."""
    mock_state_handler.get_all_workflows.return_value = {}
    engine.run_next_step()
    mock_state_handler.set_workflow.assert_not_called()


def test_run_next_step_with_ready_workflow(
    engine: Engine, mock_state_handler: MagicMock
) -> None:
    """Test run_next_step with a ready workflow."""
    workflow = Workflow(
        name="Test Workflow",
        steps=[],
        scheduler_metadata=MagicMock(ready_to_run=True, priority=1),
        step_index=0,
        status=WorkflowStatus.QUEUED,
    )
    mock_state_handler.get_all_workflows.return_value = {workflow.workflow_id: workflow}
    engine.run_next_step()
    assert workflow.status == WorkflowStatus.RUNNING
    mock_state_handler.set_workflow.assert_called_once_with(workflow)


def test_run_step(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test running a step in a workflow."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        step_index=0,
        status=WorkflowStatus.RUNNING,
        ownership_info=OwnershipInfo(),
    )
    mock_state_handler.get_workflow.return_value = workflow
    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.return_value = ActionResult(
            status=ActionStatus.SUCCEEDED
        )
        thread = engine.run_step(workflow.workflow_id)
        thread.join()
        step = mock_state_handler.set_workflow.call_args[0][0].steps[0]
        assert step.start_time is not None
        assert step.end_time is not None
        assert step.status == ActionStatus.SUCCEEDED
        assert step.result is not None
        assert step.result.status == ActionStatus.SUCCEEDED
        mock_state_handler.set_workflow.assert_called()


def test_finalize_step_success(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test finalizing a successful step."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        step_index=0,
        status=WorkflowStatus.RUNNING,
    )
    mock_state_handler.get_workflow.return_value = workflow
    updated_step = copy.deepcopy(step)
    updated_step.status = ActionStatus.SUCCEEDED
    updated_step.result = ActionSucceeded()

    engine.finalize_step(workflow.workflow_id, updated_step)

    assert mock_state_handler.set_workflow.call_count == 1
    finalized_workflow = mock_state_handler.set_workflow.call_args[0][0]
    assert finalized_workflow.status == WorkflowStatus.COMPLETED
    assert finalized_workflow.end_time is not None
    assert finalized_workflow.steps[0].status == ActionStatus.SUCCEEDED


def test_finalize_step_failure(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test finalizing a failed step."""
    step = Step(name="Test Step 1", action="test_action", node="node1", args={})
    workflow = Workflow(
        name="Test Workflow",
        steps=[step],
        step_index=0,
        status=WorkflowStatus.RUNNING,
    )
    mock_state_handler.get_workflow.return_value = workflow
    updated_step = copy.deepcopy(step)
    updated_step.status = ActionStatus.FAILED
    updated_step.result = ActionFailed()

    engine.finalize_step(workflow.workflow_id, updated_step)

    finalized_workflow = mock_state_handler.set_workflow.call_args[0][0]
    assert finalized_workflow.status == WorkflowStatus.FAILED
    assert finalized_workflow.end_time is not None
    assert finalized_workflow.steps[0].status == ActionStatus.FAILED


def test_handle_data_and_files_with_data(engine: Engine) -> None:
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
        step_index=0,
        status=WorkflowStatus.RUNNING,
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


def test_handle_data_and_files_with_files(engine: Engine) -> None:
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
        step_index=0,
        status=WorkflowStatus.RUNNING,
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
