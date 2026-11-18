"""Step detail screen for MADSci TUI.

Provides a detailed view of a single workflow step, pushed on top of
the WorkflowsScreen when a step row is selected.
"""

from typing import Any, ClassVar

from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored
from madsci.common.types.action_types import ActionResult
from madsci.common.types.step_types import Step
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Label


def _build_general_section(step: Step) -> DetailSection:
    """Build the General section for a step.

    Args:
        step: The workflow step.

    Returns:
        DetailSection with general step info.
    """
    return DetailSection(
        "General",
        {
            "Name": step.name or step.action or "Unknown",
            "Key": step.key or "-",
            "Action": step.action or "-",
            "Node": step.node or "-",
            "Status": format_status_colored(step.status.value),
            "Step ID": step.step_id,
        },
    )


def _build_result_section(result: ActionResult) -> DetailSection:
    """Build the Result section from a step result.

    Args:
        result: The latest action result of the step.

    Returns:
        DetailSection with the result status, data and errors.
    """
    result_fields: dict[str, str] = {"Status": result.status.value}

    if isinstance(result.json_result, dict):
        for k, v in result.json_result.items():
            result_fields[f"Data: {k}"] = str(v)[:200]

    for i, err in enumerate(result.errors):
        result_fields[f"Error {i + 1}"] = str(err.message or err)[:200]

    return DetailSection("Result", result_fields)


def _build_timing_section(step: Step) -> DetailSection | None:
    """Build the Timing section for a step.

    Args:
        step: The workflow step.

    Returns:
        DetailSection if any timing info exists, else None.
    """
    timing: dict[str, str] = {}
    if step.start_time:
        timing["Started"] = str(step.start_time)
    if step.end_time:
        timing["Ended"] = str(step.end_time)
    if step.duration:
        timing["Duration"] = str(step.duration)
    if timing:
        return DetailSection("Timing", timing)
    return None


class StepDetailScreen(Screen):
    """Detailed view of a single workflow step."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        workflow_id: str,
        step_data: Step,
        step_index: int,
        **kwargs: Any,
    ) -> None:
        """Initialize the step detail screen.

        Args:
            workflow_id: Parent workflow ID.
            step_data: The workflow step to show.
            step_index: Zero-based index of this step within the workflow.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self.workflow_id = workflow_id
        self.step_data = step_data
        self.step_index = step_index

    def compose(self) -> ComposeResult:
        """Compose the step detail screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label(f"[bold blue]Step {self.step_index + 1} Detail[/bold blue]")
            yield Label("")
            yield DetailPanel(
                placeholder="Loading step details...",
                id="step-detail",
            )
            yield Label("")
            yield Label("[dim]'Esc' back[/dim]")

    def on_mount(self) -> None:
        """Render the step detail content on mount."""
        self._render_step_detail()

    def _render_step_detail(self) -> None:
        """Render step data into the detail panel."""
        panel = self.query_one("#step-detail", DetailPanel)
        step = self.step_data

        sections: list[DetailSection] = [_build_general_section(step)]

        if step.description:
            sections.append(DetailSection("Description", {"": step.description}))

        if step.args:
            sections.append(
                DetailSection(
                    "Arguments", {str(k): str(v) for k, v in step.args.items()}
                )
            )

        if step.locations:
            sections.append(
                DetailSection(
                    "Locations",
                    {str(k): str(v) for k, v in step.locations.items()},
                )
            )

        timing_section = _build_timing_section(step)
        if timing_section:
            sections.append(timing_section)

        if step.result:
            sections.append(_build_result_section(step.result))

        if step.data_labels:
            sections.append(
                DetailSection(
                    "Data Labels",
                    {str(k): str(v) for k, v in step.data_labels.items()},
                )
            )

        if step.conditions:
            cond_fields = {
                f"Condition {i + 1}": str(cond)[:200]
                for i, cond in enumerate(step.conditions)
            }
            sections.append(DetailSection("Conditions", cond_fields))

        title = step.name or step.action or f"Step {self.step_index + 1}"
        panel.update_content(title=title, sections=sections)

    def action_go_back(self) -> None:
        """Go back to the workflows screen."""
        self.app.pop_screen()
