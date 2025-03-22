"""Automated unit tests for the Workcell Engine, using pytest."""

from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.action_types import ActionResult, ActionStatus
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
    )
    mock_state_handler.get_workflow.return_value = workflow
    mock_state_handler.get_node.return_value = MagicMock(node_url="http://node-url")
    with patch(
        "madsci.workcell_manager.workcell_engine.find_node_client"
    ) as mock_client:
        mock_client.return_value.send_action.return_value = ActionResult(
            action_id="action1", status=ActionStatus.SUCCEEDED
        )
        engine.run_step(workflow.workflow_id)
        assert step.start_time is not None
        mock_state_handler.set_workflow.assert_called()


def test_finalize_step_success(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test finalizing a successful step."""
    step = Step(step_id="step1", status=ActionStatus.SUCCEEDED)
    workflow = Workflow(
        workflow_id="wf1",
        steps=[step],
        step_index=0,
        status=WorkflowStatus.RUNNING,
    )
    mock_state_handler.get_workflow.return_value = workflow
    engine.finalize_step("wf1", step)
    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.end_time is not None
    mock_state_handler.set_workflow.assert_called_with(workflow)


def test_finalize_step_failure(engine: Engine, mock_state_handler: MagicMock) -> None:
    """Test finalizing a failed step."""
    step = Step(step_id="step1", status=ActionStatus.FAILED)
    workflow = Workflow(
        workflow_id="wf1",
        steps=[step],
        step_index=0,
        status=WorkflowStatus.RUNNING,
    )
    mock_state_handler.get_workflow.return_value = workflow
    engine.finalize_step("wf1", step)
    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.end_time is not None
    mock_state_handler.set_workflow.assert_called_with(workflow)
