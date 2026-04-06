"""Step detail screen for MADSci TUI.

Provides a detailed view of a single workflow step, pushed on top of
the WorkflowsScreen when a step row is selected.
"""

from typing import Any, ClassVar

from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Label


def _step_status_name(status: Any) -> str:
    """Derive a display name from a step status value.

    Handles both string statuses (e.g. ``"succeeded"``) and dict
    representations.

    Args:
        status: Step status, either a string or a dict with status flags.

    Returns:
        Lowercase status name string.
    """
    if isinstance(status, str):
        return status.lower()
    if isinstance(status, dict):
        for key in ("succeeded", "failed", "cancelled", "running", "paused"):
            if status.get(key):
                return key
    return "unknown"


def _build_general_section(step: dict) -> DetailSection:
    """Build the General section for a step.

    Args:
        step: Step data dictionary.

    Returns:
        DetailSection with general step info.
    """
    general: dict[str, str] = {
        "Name": step.get("name") or step.get("action") or "Unknown",
        "Key": step.get("key") or "-",
        "Action": step.get("action") or "-",
        "Node": step.get("node") or "-",
        "Status": format_status_colored(
            _step_status_name(step.get("status", "unknown"))
        ),
    }
    step_id = step.get("step_id")
    if step_id:
        general["Step ID"] = str(step_id)
    return DetailSection("General", general)


def _build_result_section(result: dict) -> DetailSection | None:
    """Build the Result section from a step result dict.

    Args:
        result: Step result dictionary.

    Returns:
        DetailSection if any result fields exist, else None.
    """
    result_fields: dict[str, str] = {}
    if result.get("status"):
        result_fields["Status"] = str(result["status"])
    if result.get("action_msg"):
        result_fields["Message"] = str(result["action_msg"])

    json_result = result.get("json_result")
    if json_result and isinstance(json_result, dict):
        for k, v in json_result.items():
            result_fields[f"Data: {k}"] = str(v)[:200]

    errors = result.get("errors")
    if errors and isinstance(errors, list):
        for i, err in enumerate(errors):
            err_msg = (
                err.get("message", str(err)) if isinstance(err, dict) else str(err)
            )
            result_fields[f"Error {i + 1}"] = str(err_msg)[:200]

    if result_fields:
        return DetailSection("Result", result_fields)
    return None


def _build_timing_section(step: dict) -> DetailSection | None:
    """Build the Timing section for a step.

    Args:
        step: Step data dictionary.

    Returns:
        DetailSection if any timing info exists, else None.
    """
    timing: dict[str, str] = {}
    start_time = step.get("start_time")
    end_time = step.get("end_time")
    duration = step.get("duration")
    if start_time:
        timing["Started"] = str(start_time)
    if end_time:
        timing["Ended"] = str(end_time)
    if duration:
        timing["Duration"] = str(duration)
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
        step_data: dict,
        step_index: int,
        **kwargs: Any,
    ) -> None:
        """Initialize the step detail screen.

        Args:
            workflow_id: Parent workflow ID.
            step_data: Step data dictionary.
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

        # Description
        description = step.get("description")
        if description:
            sections.append(DetailSection("Description", {"": str(description)}))

        # Arguments
        args = step.get("args") or {}
        if args:
            sections.append(
                DetailSection("Arguments", {str(k): str(v) for k, v in args.items()})
            )

        # Locations
        locations = step.get("locations") or {}
        if locations:
            sections.append(
                DetailSection(
                    "Locations", {str(k): str(v) for k, v in locations.items()}
                )
            )

        # Timing
        timing_section = _build_timing_section(step)
        if timing_section:
            sections.append(timing_section)

        # Result
        result = step.get("result")
        if result and isinstance(result, dict):
            result_section = _build_result_section(result)
            if result_section:
                sections.append(result_section)

        # Data labels
        data_labels = step.get("data_labels") or {}
        if data_labels:
            sections.append(
                DetailSection(
                    "Data Labels", {str(k): str(v) for k, v in data_labels.items()}
                )
            )

        # Conditions
        conditions = step.get("conditions") or []
        if conditions:
            cond_fields = {
                f"Condition {i + 1}": str(cond)[:200]
                for i, cond in enumerate(conditions)
            }
            sections.append(DetailSection("Conditions", cond_fields))

        title = step.get("name") or step.get("action") or f"Step {self.step_index + 1}"
        panel.update_content(title=title, sections=sections)

    def action_go_back(self) -> None:
        """Go back to the workflows screen."""
        self.app.pop_screen()
