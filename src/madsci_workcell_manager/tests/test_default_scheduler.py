"""Tests for the default scheduler"""

from collections.abc import Generator
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from madsci.client.resource_client import Resource
from madsci.common.types.condition_types import (
    NoResourceInLocationCondition,
    ResourceInLocationCondition,
)
from madsci.common.types.location_types import Location, LocationDefinition
from madsci.common.types.node_types import Node, NodeInfo, NodeStatus
from madsci.common.types.resource_types import Slot
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import (
    SchedulerMetadata,
    Workflow,
    WorkflowStatus,
)
from madsci.workcell_manager.schedulers.default_scheduler import Scheduler


@pytest.fixture
def mock_scheduler() -> Generator[Scheduler, None, None]:
    """Fixture to create a mock scheduler"""
    mock_workcell_definition = WorkcellDefinition(
        workcell_name="test workcell",
        locations=[
            LocationDefinition(
                location_name="loc1",
                resource_id=None,
            ),
            LocationDefinition(
                location_name="loc2",
                resource_id=None,
            ),
        ],
    )
    mock_state_handler = MagicMock()
    mock_state_handler.get_node.return_value = Node(
        node_url="http://test_node",
        status=NodeStatus(),
        info=NodeInfo(
            node_name="test_node",
            module_name="test_module",
        ),
    )
    mock_state_handler.get_locations.return_value = [
        Location(
            location_name="loc1",
            resource_id=None,
        ),
        Location(
            location_name="loc2",
            resource_id=None,
        ),
    ]
    scheduler = Scheduler(mock_workcell_definition, mock_state_handler)
    yield scheduler


@pytest.fixture
def workflows() -> list[Workflow]:
    """Fixture to create a list of workflows"""
    now = datetime.now()
    return [
        Workflow(
            name="wf1",
            submitted_time=now - timedelta(minutes=10),
            steps=[Step(name="step1", action="test_action", node="test_node")],
        ),
        Workflow(
            name="wf2",
            submitted_time=now - timedelta(minutes=5),
            steps=[Step(name="step2", action="test_action", node="test_node")],
        ),
    ]


def test_fifo_prioritization(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that workflows are prioritized based on FIFO from their submission dates"""
    result = mock_scheduler.run_iteration(workflows)
    assert (
        result[workflows[0].workflow_id].priority
        > result[workflows[1].workflow_id].priority
    )
    workflows_reversed = [workflows[1], workflows[0]]
    result = mock_scheduler.run_iteration(workflows_reversed)
    assert (
        result[workflows[0].workflow_id].priority
        > result[workflows[1].workflow_id].priority
    )


def test_condition_checking_no_resource_info_for_location(
    mock_scheduler: Scheduler,
) -> None:
    """Test that conditions are evaluated correctly when no resource information is available for a location"""
    workflows: list[Workflow] = [
        Workflow(
            name="wf1",
            submitted_time=datetime.now(),
            steps=[
                Step(
                    name="step1",
                    action="test_action",
                    node="test_node",
                    conditions=[
                        ResourceInLocationCondition(location_name="loc1"),
                        NoResourceInLocationCondition(location_name="loc2"),
                    ],
                )
            ],
        )
    ]
    mock_scheduler.resource_client = MagicMock()
    mock_scheduler.resource_client.get_resource.return_value = None

    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    metadata = result[workflows[0].workflow_id]
    assert not metadata.ready_to_run
    assert len(metadata.reasons) > 0
    assert "does not have an attached container resource" in metadata.reasons[0]
    assert "does not have an attached container resource" in metadata.reasons[1]


def test_condition_checking_resource_presence(mock_scheduler: Scheduler) -> None:
    """Test that conditions are evaluated correctly when no resource information is available for a location"""
    workflows: list[Workflow] = [
        Workflow(
            name="wf1",
            submitted_time=datetime.now(),
            steps=[
                Step(
                    name="step1",
                    action="test_action",
                    node="test_node",
                    conditions=[
                        ResourceInLocationCondition(location_name="loc1"),
                        NoResourceInLocationCondition(location_name="loc2"),
                    ],
                )
            ],
        )
    ]
    mock_scheduler.resource_client = MagicMock()
    test_slot = Slot()
    mock_scheduler.resource_client.get_resource.return_value = test_slot
    mock_scheduler.state_handler.get_locations.return_value[
        0
    ].resource_id = test_slot.resource_id
    mock_scheduler.state_handler.get_locations.return_value[
        1
    ].resource_id = test_slot.resource_id

    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    metadata = result[workflows[0].workflow_id]
    assert not metadata.ready_to_run
    assert len(metadata.reasons) > 0
    assert "does not contain" in metadata.reasons[0]

    mock_scheduler.resource_client.get_resource.return_value = Resource()

    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    metadata = result[workflows[0].workflow_id]
    assert not metadata.ready_to_run
    assert len(metadata.reasons) > 0
    assert "is not a container." in metadata.reasons[0]
    assert "is not a container." in metadata.reasons[1]

    test_slot.children = [Resource()]
    mock_scheduler.resource_client.get_resource.return_value = test_slot

    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    metadata = result[workflows[0].workflow_id]
    assert not metadata.ready_to_run
    assert len(metadata.reasons) > 0
    assert "contains" in metadata.reasons[0]


def test_workflow_paused(mock_scheduler: Scheduler, workflows: list[Workflow]) -> None:
    """Test that paused workflows are marked as not ready to run"""
    workflows[0].status.paused = True
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert "Workflow is paused" in result[workflows[0].workflow_id].reasons


def test_workflow_running(mock_scheduler: Scheduler, workflows: list[Workflow]) -> None:
    """Test that running workflows are marked as not ready to run"""
    workflows[0].status.running = True
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert "Workflow is already running" in result[workflows[0].workflow_id].reasons


def test_workflow_status_failed(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that workflows with an error status are not ready to run"""
    workflows[0].status.failed = True
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert "Workflow must be active" in result[workflows[0].workflow_id].reasons[0]


def test_workflow_status_completed(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that completed workflows are not ready to run"""
    workflows[0].status.completed = True
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert "Workflow must be active" in result[workflows[0].workflow_id].reasons[0]


def test_workflow_status_cancelled(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that cancelled workflows are not ready to run"""
    workflows[0].status.cancelled = True
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert "Workflow must be active" in result[workflows[0].workflow_id].reasons[0]


def test_workflow_status_queued(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that queued workflows are ready to run"""
    workflows[0].status = WorkflowStatus()
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert result[workflows[0].workflow_id].ready_to_run


def test_node_status_abnormal(
    mock_scheduler: Scheduler, workflows: list[Workflow]
) -> None:
    """Test that workflows are not ready to run if the node is in an error state"""
    mock_scheduler.state_handler.get_node.return_value = Node(
        node_url="http://test_node",
        status=NodeStatus(errored=True),
        info=NodeInfo(
            node_name="test_node",
            module_name="test_module",
        ),
    )
    result: dict[str, SchedulerMetadata] = mock_scheduler.run_iteration(workflows)
    assert not result[workflows[0].workflow_id].ready_to_run
    assert (
        "Node test_node not ready: Node is in an error state"
        in result[workflows[0].workflow_id].reasons[0]
    )


# TODO: Test Location Reservation
# TODO: Test Node Reservation
