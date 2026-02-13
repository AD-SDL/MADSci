"""Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, and workflow control actions.
"""

from datetime import datetime
from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.constants import AUTO_REFRESH_INTERVAL, DEFAULT_SERVICES
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Label, Static

# Status-to-color mapping used across the module
_STATUS_COLORS = {
    "completed": "green",
    "failed": "red",
    "cancelled": "yellow",
    "running": "blue",
    "paused": "yellow",
}

# Status-to-icon mapping for table rows
_STATUS_ICONS = {
    "completed": "[green]\u25cf[/green]",
    "failed": "[red]\u25cf[/red]",
    "cancelled": "[yellow]\u25cb[/yellow]",
    "running": "[blue]\u25cf[/blue]",
    "paused": "[yellow]\u25cf[/yellow]",
}


def _get_status_color(status: dict) -> str:
    """Get the display color for a workflow status.

    Args:
        status: Workflow status dictionary.

    Returns:
        Color name string.
    """
    for key, color in _STATUS_COLORS.items():
        if status.get(key):
            return color
    return "dim"


def _get_status_icon(status: dict) -> str:
    """Get the display icon for a workflow status.

    Args:
        status: Workflow status dictionary.

    Returns:
        Rich markup icon string.
    """
    for key, icon in _STATUS_ICONS.items():
        if status.get(key):
            return icon
    return "[dim]\u25cb[/dim]"


def _format_timestamp(ts: Any) -> str:
    """Format a timestamp for display.

    Args:
        ts: Timestamp value (string or datetime).

    Returns:
        Formatted time string.
    """
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except ValueError:
            return ts[:8]
    return str(ts)[:8]


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string.
    """
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes:02d}m {secs:02d}s"


def _build_step_lines(steps: list, current_step: int, is_running: bool) -> list[str]:
    """Build display lines for workflow steps.

    Args:
        steps: List of step dictionaries.
        current_step: Current step index.
        is_running: Whether the workflow is currently running.

    Returns:
        List of formatted step lines.
    """
    lines = []
    for i, step in enumerate(steps[:10]):
        step_name = step.get("name", step.get("action", f"Step {i + 1}"))
        step_node = step.get("node", "")

        if i < current_step:
            icon = "[green]\u2713[/green]"
        elif i == current_step and is_running:
            icon = "[blue]\u25ba[/blue]"
        else:
            icon = "[dim]\u25cb[/dim]"

        step_line = f"    {icon} {i + 1}. {step_name}"
        if step_node:
            step_line += f" [dim]({step_node})[/dim]"
        lines.append(step_line)

    total_steps = len(steps)
    if total_steps > 10:
        lines.append(f"    ... and {total_steps - 10} more steps")
    return lines


class WorkflowDetailPanel(Static):
    """Panel showing details for a selected workflow."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the panel."""
        super().__init__(**kwargs)
        self.selected_workflow: str | None = None
        self.workflow_data: dict = {}

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Workflow Details[/bold]")
        yield Label(
            "[dim]Select a workflow from the table above[/dim]",
            id="workflow-detail-content",
        )

    def update_details(self, workflow_id: str, data: dict) -> None:
        """Update the detail display.

        Args:
            workflow_id: Workflow ID.
            data: Workflow data dictionary.
        """
        self.selected_workflow = workflow_id
        self.workflow_data = data

        content = self.query_one("#workflow-detail-content", Label)
        status = data.get("status", {})
        status_color = _get_status_color(status)

        lines = self._build_header_lines(workflow_id, data, status, status_color)
        lines.extend(self._build_timing_lines(data))
        lines.extend(self._build_progress_lines(data, status, status_color))

        content.update("\n".join(lines))

    def _build_header_lines(
        self, workflow_id: str, data: dict, status: dict, status_color: str
    ) -> list[str]:
        """Build the header section of the detail display."""
        name = data.get("name", "Unknown")
        status_desc = status.get("description", "Unknown")
        return [
            f"[bold]{name}[/bold]",
            "",
            f"  ID:       {workflow_id[:20]}...",
            f"  Status:   [{status_color}]{status_desc}[/{status_color}]",
        ]

    def _build_timing_lines(self, data: dict) -> list[str]:
        """Build the timing section of the detail display."""
        lines: list[str] = []
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if start_time:
            lines.append(f"  Started:  {_format_timestamp(start_time)}")
        if end_time:
            lines.append(f"  Ended:    {_format_timestamp(end_time)}")
        duration = data.get("duration_seconds")
        if duration is not None:
            lines.append(f"  Duration: {_format_duration(duration)}")
        return lines

    def _build_progress_lines(
        self, data: dict, status: dict, status_color: str
    ) -> list[str]:
        """Build the step progress section of the detail display."""
        steps = data.get("steps", [])
        total_steps = len(steps)
        if total_steps == 0:
            return []

        completed_steps = data.get("completed_steps", 0)
        failed_steps = data.get("failed_steps", 0)
        current_step = status.get("current_step_index", 0)

        lines = [""]
        summary = f"  [bold]Steps:[/bold] {completed_steps}/{total_steps} completed"
        if failed_steps:
            summary += f", {failed_steps} failed"
        lines.append(summary)

        # Progress bar
        progress = completed_steps / total_steps
        filled = int(progress * 20)
        empty = 20 - filled
        bar = "\u2588" * filled + "\u2591" * empty
        percent = int(progress * 100)
        lines.append(f"  [{status_color}]{bar}[/{status_color}] {percent}%")

        # Step list
        lines.append("")
        lines.extend(
            _build_step_lines(steps, current_step, bool(status.get("running")))
        )

        return lines


class WorkflowsScreen(Screen):
    """Screen showing workflow visualization and management."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("p", "pause_workflow", "Pause"),
        ("u", "resume_workflow", "Resume"),
        ("c", "cancel_workflow", "Cancel"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.workflows_data: dict[str, dict] = {}
        self.selected_workflow_id: str | None = None
        self.auto_refresh_enabled = True
        self._auto_refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        """Compose the workflows screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Workflow Management[/bold blue]")
            yield Label("")

            with Vertical(id="active-workflows-section"):
                yield Label("[bold]Active Workflows[/bold]")
                yield DataTable(id="workflows-table")

            yield Label("")
            yield WorkflowDetailPanel(id="workflow-detail-panel")

            yield Label("")
            yield Label(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'p' pause | "
                "'u' resume | 'c' cancel | 'Esc' back[/dim]",
                id="workflows-footer",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up tables and load data."""
        workflows_table = self.query_one("#workflows-table", DataTable)
        workflows_table.add_columns(
            "Status", "Name", "Progress", "Step", "Started", "Duration"
        )
        workflows_table.cursor_type = "row"

        await self.refresh_data()
        self._start_auto_refresh()

    def _start_auto_refresh(self) -> None:
        """Start the auto-refresh timer."""
        if self._auto_refresh_timer is None:
            self._auto_refresh_timer = self.set_interval(
                AUTO_REFRESH_INTERVAL,
                self._auto_refresh,
                name="workflows-auto-refresh",
            )

    def _stop_auto_refresh(self) -> None:
        """Stop the auto-refresh timer."""
        if self._auto_refresh_timer is not None:
            self._auto_refresh_timer.stop()
            self._auto_refresh_timer = None

    async def _auto_refresh(self) -> None:
        """Perform an auto-refresh cycle."""
        if self.auto_refresh_enabled:
            await self.refresh_data()

    def _update_footer(self) -> None:
        """Update the footer label with current auto-refresh state."""
        footer = self.query_one("#workflows-footer", Label)
        if self.auto_refresh_enabled:
            footer.update(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'p' pause | "
                "'u' resume | 'c' cancel | 'Esc' back[/dim]"
            )
        else:
            footer.update(
                "[dim]Auto-refresh: off | 'a' toggle | 'p' pause | "
                "'u' resume | 'c' cancel | 'Esc' back[/dim]"
            )

    async def refresh_data(self) -> None:
        """Refresh workflow data from workcell manager."""
        table = self.query_one("#workflows-table", DataTable)
        table.clear()
        self.workflows_data.clear()

        # Fetch active workflows
        active = await self._fetch_workflows("/workflows/active")
        # Fetch queued workflows
        queued = await self._fetch_workflows("/workflows/queue")

        # Merge: active is dict, queued is list
        if isinstance(active, dict):
            for wf_id, wf_data in active.items():
                self.workflows_data[wf_id] = wf_data
                self._add_workflow_row(table, wf_data)
        if isinstance(queued, list):
            for wf_data in queued:
                wf_id = wf_data.get("workflow_id", "unknown")
                if wf_id not in self.workflows_data:
                    self.workflows_data[wf_id] = wf_data
                    self._add_workflow_row(table, wf_data)

        if not self.workflows_data:
            table.add_row(
                "[dim]\u25cb[/dim]",
                "[dim]No active workflows[/dim]",
                "-",
                "-",
                "-",
                "-",
            )

    async def _fetch_workflows(self, path: str) -> dict | list:
        """Fetch workflows from the workcell manager.

        Args:
            path: API path to fetch.

        Returns:
            Workflow data (dict or list depending on endpoint).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                workcell_url = self.app.service_urls.get(
                    "workcell_manager",
                    DEFAULT_SERVICES["workcell_manager"],
                )
                response = await client.get(f"{workcell_url.rstrip('/')}{path}")
                if response.status_code == 200:
                    return response.json()
        except Exception:  # noqa: S110
            pass
        return {}

    def _add_workflow_row(self, table: DataTable, data: dict) -> None:
        """Add a workflow row to the table.

        Args:
            table: The DataTable to add to.
            data: Workflow data dictionary.
        """
        status = data.get("status", {})
        name = data.get("name", "Unknown")
        icon = _get_status_icon(status)

        # Progress
        steps = data.get("steps", [])
        total_steps = len(steps)
        completed = data.get("completed_steps", 0)
        progress = f"{completed}/{total_steps}" if total_steps > 0 else "-"

        # Current step
        current_index = status.get("current_step_index", 0)
        if steps and 0 <= current_index < total_steps:
            current_step = steps[current_index]
            step_name = current_step.get("name", current_step.get("action", "-"))
        else:
            step_name = "-"

        # Timing
        start_time = data.get("start_time")
        started_str = _format_timestamp(start_time) if start_time else "-"

        duration = data.get("duration_seconds")
        duration_str = _format_duration(duration) if duration is not None else "-"

        table.add_row(icon, name, progress, step_name, started_str, duration_str)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the workflows table."""
        table = event.data_table
        row_key = event.row_key

        if row_key and table.id == "workflows-table":
            row = table.get_row(row_key)
            workflow_name = str(row[1])

            # Find workflow by name match
            for wf_id, wf_data in self.workflows_data.items():
                if wf_data.get("name", "") == workflow_name:
                    self.selected_workflow_id = wf_id
                    detail_panel = self.query_one(
                        "#workflow-detail-panel", WorkflowDetailPanel
                    )
                    detail_panel.update_details(wf_id, wf_data)
                    break

    async def _send_workflow_command(self, command: str) -> None:
        """Send a control command to the selected workflow.

        Args:
            command: Command to send (pause, resume, cancel).
        """
        if not self.selected_workflow_id:
            self.notify("No workflow selected", timeout=2)
            return

        try:
            workcell_url = self.app.service_urls.get(
                "workcell_manager", DEFAULT_SERVICES["workcell_manager"]
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{workcell_url.rstrip('/')}/workflow/"
                    f"{self.selected_workflow_id}/{command}"
                )
                if response.status_code == 200:
                    self.notify(f"Workflow {command}d successfully", timeout=2)
                    await self.refresh_data()
                else:
                    self.notify(
                        f"Failed to {command} workflow: HTTP {response.status_code}",
                        timeout=3,
                    )
        except Exception as e:
            self.notify(f"Error: {e}", timeout=3)

    async def action_refresh(self) -> None:
        """Refresh workflow data."""
        await self.refresh_data()
        self.notify("Workflows refreshed", timeout=2)

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        if self.auto_refresh_enabled:
            self._start_auto_refresh()
            self.notify("Auto-refresh enabled", timeout=2)
        else:
            self._stop_auto_refresh()
            self.notify("Auto-refresh disabled", timeout=2)
        self._update_footer()

    async def action_pause_workflow(self) -> None:
        """Pause the selected workflow."""
        await self._send_workflow_command("pause")

    async def action_resume_workflow(self) -> None:
        """Resume the selected workflow."""
        await self._send_workflow_command("resume")

    async def action_cancel_workflow(self) -> None:
        """Cancel the selected workflow."""
        await self._send_workflow_command("cancel")

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self._stop_auto_refresh()
        self.app.switch_screen("dashboard")
