"""Tests for the TUI step detail screen.

The screen takes a typed ``Step`` model (issue #279).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from madsci.client.cli.tui.screens.step_detail import StepDetailScreen
from madsci.client.cli.tui.screens.workflow_detail import WorkflowDetailScreen
from madsci.client.cli.tui.widgets import DetailPanel
from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.base_types import Error
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import Workflow
from textual.app import App

START = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


class StepDetailHostApp(App):
    """Test app that pushes one StepDetailScreen on mount."""

    def __init__(self, step: Step, step_index: int = 0) -> None:
        """Keep the step to show."""
        super().__init__()
        self._step = step
        self._step_index = step_index

    def on_mount(self) -> None:
        """Push the step detail screen."""
        self.push_screen(
            StepDetailScreen(
                workflow_id="wf-1",
                step_data=self._step,
                step_index=self._step_index,
            )
        )


async def _render_text(step: Step, step_index: int = 0) -> str:
    """Render the screen for a step and return the panel text."""
    async with StepDetailHostApp(step, step_index).run_test() as pilot:
        await pilot.pause()
        panel = pilot.app.screen.query_one("#step-detail", DetailPanel)
        return str(panel.query_one("#detail-panel-content").render())


class TestStepDetailScreen:
    """Tests for StepDetailScreen with a typed Step."""

    @pytest.mark.asyncio
    async def test_full_step(self) -> None:
        """All sections render from the typed model."""
        step = Step(
            name="Transfer plate",
            key="transfer_1",
            description="Move the plate to the reader",
            action="transfer",
            node="robot_arm",
            args={"speed": 5},
            locations={"source": "deck_1"},
            data_labels={"image": "plate_image"},
            status=ActionStatus.FAILED,
            start_time=START,
            end_time=START + timedelta(seconds=5),
            duration=timedelta(seconds=5),
            result=ActionResult(
                status=ActionStatus.FAILED,
                json_result={"reading": 0.42},
                errors=[Error(message="Gripper jammed")],
            ),
        )

        text = await _render_text(step)

        assert "Transfer plate" in text
        assert "transfer_1" in text
        assert "robot_arm" in text
        assert "failed" in text
        assert step.step_id in text
        assert "Move the plate to the reader" in text
        assert "speed" in text
        assert "deck_1" in text
        assert "plate_image" in text
        assert "Data: reading" in text
        assert "0.42" in text
        assert "Gripper jammed" in text
        assert "0:00:05" in text
        assert str(START) in text

    @pytest.mark.asyncio
    async def test_minimal_step(self) -> None:
        """A step with only an action shows the General section only."""
        step = Step(action="measure")

        text = await _render_text(step, step_index=2)

        assert "measure" in text
        assert "not_started" in text
        assert "Timing" not in text
        assert "Result" not in text
        assert "Arguments" not in text

    @pytest.mark.asyncio
    async def test_result_with_status_only(self) -> None:
        """A result with only a status shows that status."""
        step = Step(
            action="measure",
            result=ActionResult(status=ActionStatus.SUCCEEDED),
        )

        text = await _render_text(step)

        assert "Result" in text
        assert "succeeded" in text


class TestWorkflowDetailStepSelection:
    """WorkflowDetailScreen passes the typed Step to StepDetailScreen."""

    def test_row_selection_pushes_typed_step(self) -> None:
        """Selecting a step row pushes a screen with the Step model."""
        step = Step(name="Step A", action="transfer")
        workflow = Workflow(name="wf", steps=[step])
        screen = WorkflowDetailScreen(workflow_id="wf-1", workflow_data=workflow)

        table = MagicMock()
        table.id = "steps-table"
        table.get_row.return_value = ["1", "Step A"]
        event = MagicMock(data_table=table, row_key="row-1")
        app = MagicMock()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(type(screen), "app", property(lambda _self: app))
            screen.on_data_table_row_selected(event)

        app.push_screen.assert_called_once()
        pushed = app.push_screen.call_args.args[0]
        assert isinstance(pushed, StepDetailScreen)
        assert isinstance(pushed.step_data, Step)
        assert pushed.step_data.step_id == step.step_id
        assert pushed.step_index == 0
