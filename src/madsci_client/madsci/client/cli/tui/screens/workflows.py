"""Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, and workflow control actions.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailPanel,
    DetailSection,
)
from madsci.client.cli.utils.formatting import (
    format_duration,
    format_status_colored,
    format_status_icon,
    format_timestamp,
)
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_workflow_status_name(status: dict) -> str:
    """Get a canonical status name from a workflow status dict.

    Args:
        status: Workflow status dictionary with boolean flags.

    Returns:
        Status name string.
    """
    for key in ("completed", "failed", "cancelled", "running", "paused"):
        if status.get(key):
            return key
    return "unknown"


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


def _add_workflow_row(table: DataTable, data: dict) -> None:
    """Add a workflow row to a table.

    Args:
        table: The DataTable to add to.
        data: Workflow data dictionary.
    """
    status = data.get("status", {})
    name = data.get("name", "Unknown")
    status_name = _get_workflow_status_name(status)
    icon = format_status_icon(status_name)

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

    # Timing - use shared formatting utilities
    start_time = data.get("start_time")
    started_str = format_timestamp(start_time, short=True) if start_time else "-"

    duration = data.get("duration_seconds")
    duration_str = format_duration(duration)

    table.add_row(icon, name, progress, step_name, started_str, duration_str)


class WorkflowsScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
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

    def compose(self) -> ComposeResult:
        """Compose the workflows screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Workflow Management[/bold blue]")
            yield Label("")

            with Vertical(id="active-workflows-section"):
                yield Label("[bold]Active Workflows[/bold]")
                yield DataTable(id="workflows-table")

            yield Label("")

            with Vertical(id="archived-workflows-section"):
                yield Label("[bold]Archived Workflows[/bold]")
                yield DataTable(id="archived-table")

            yield Label("")
            yield DetailPanel(
                placeholder="Select a workflow from the table above",
                id="workflow-detail-panel",
            )

            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef("p", "Pause", "pause", variant="warning"),
                    ActionDef("u", "Resume", "resume", variant="success"),
                    ActionDef("c", "Cancel", "cancel", variant="error"),
                ],
                id="workflows-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up tables and load data."""
        workflows_table = self.query_one("#workflows-table", DataTable)
        workflows_table.add_columns(
            "Status", "Name", "Progress", "Step", "Started", "Duration"
        )
        workflows_table.cursor_type = "row"

        archived_table = self.query_one("#archived-table", DataTable)
        archived_table.add_columns(
            "Status", "Name", "Progress", "Step", "Started", "Duration"
        )
        archived_table.cursor_type = "row"

        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh workflow data from workcell manager."""
        self.workflows_data.clear()
        await self._refresh_active_workflows()
        await self._refresh_archived_workflows()

    async def _refresh_active_workflows(self) -> None:
        """Refresh the active/queued workflows table."""
        table = self.query_one("#workflows-table", DataTable)
        table.clear()

        active = await self._fetch_workflows("/workflows/active")
        queued = await self._fetch_workflows("/workflows/queue")

        if isinstance(active, dict):
            for wf_id, wf_data in active.items():
                self.workflows_data[wf_id] = wf_data
                _add_workflow_row(table, wf_data)
        if isinstance(queued, list):
            for wf_data in queued:
                wf_id = wf_data.get("workflow_id", "unknown")
                if wf_id not in self.workflows_data:
                    self.workflows_data[wf_id] = wf_data
                    _add_workflow_row(table, wf_data)

        if not self.workflows_data:
            table.add_row(
                format_status_icon("unknown"),
                "[dim]No active workflows[/dim]",
                "-",
                "-",
                "-",
                "-",
            )

    async def _refresh_archived_workflows(self) -> None:
        """Refresh the archived workflows table."""
        archived_table = self.query_one("#archived-table", DataTable)
        archived_table.clear()

        archived = await self._fetch_workflows("/workflows/archived?number=20")
        rows = self._normalize_workflow_response(archived)

        for wf_id, wf_data in rows:
            if wf_id not in self.workflows_data:
                self.workflows_data[wf_id] = wf_data
            _add_workflow_row(archived_table, wf_data)

        if not rows:
            archived_table.add_row(
                format_status_icon("unknown"),
                "[dim]No archived workflows[/dim]",
                "-",
                "-",
                "-",
                "-",
            )

    @staticmethod
    def _normalize_workflow_response(data: dict | list) -> list[tuple[str, dict]]:
        """Normalize a workflow API response to a list of (id, data) pairs."""
        if isinstance(data, dict):
            return list(data.items())
        if isinstance(data, list):
            return [(d.get("workflow_id", "unknown"), d) for d in data]
        return []

    async def _fetch_workflows(self, path: str) -> dict | list:
        """Fetch workflows from the workcell manager.

        Args:
            path: API path to fetch.

        Returns:
            Workflow data (dict or list depending on endpoint).
        """
        try:
            workcell_url = self.get_service_url("workcell_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{workcell_url.rstrip('/')}{path}")
                if response.status_code == 200:
                    return response.json()
        except Exception:  # noqa: S110
            pass
        return {}

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the workflows table."""
        table = event.data_table
        row_key = event.row_key

        if row_key and table.id in ("workflows-table", "archived-table"):
            row = table.get_row(row_key)
            workflow_name = str(row[1])

            # Find workflow by name match
            for wf_id, wf_data in self.workflows_data.items():
                if wf_data.get("name", "") == workflow_name:
                    self.selected_workflow_id = wf_id
                    self._update_detail_panel(wf_id, wf_data)
                    break

    def _update_detail_panel(self, workflow_id: str, data: dict) -> None:
        """Update the detail panel with workflow data.

        Args:
            workflow_id: Workflow ID.
            data: Workflow data dictionary.
        """
        detail_panel = self.query_one("#workflow-detail-panel", DetailPanel)
        status = data.get("status", {})
        status_name = _get_workflow_status_name(status)
        name = data.get("name", "Unknown")

        # General section
        general_fields: dict[str, str] = {
            "ID": f"{workflow_id[:20]}...",
            "Status": format_status_colored(
                status_name, status.get("description", status_name)
            ),
        }

        # Timing section
        timing_fields: dict[str, str] = {}
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if start_time:
            timing_fields["Started"] = format_timestamp(start_time, short=True)
        if end_time:
            timing_fields["Ended"] = format_timestamp(end_time, short=True)
        duration = data.get("duration_seconds")
        if duration is not None:
            timing_fields["Duration"] = format_duration(duration)

        sections = [DetailSection("General", general_fields)]
        if timing_fields:
            sections.append(DetailSection("Timing", timing_fields))

        # Progress section
        steps = data.get("steps", [])
        total_steps = len(steps)
        if total_steps > 0:
            completed_steps = data.get("completed_steps", 0)
            failed_steps = data.get("failed_steps", 0)
            current_step = status.get("current_step_index", 0)

            progress = completed_steps / total_steps
            filled = int(progress * 20)
            empty = 20 - filled
            bar = "\u2588" * filled + "\u2591" * empty
            percent = int(progress * 100)

            progress_fields: dict[str, str] = {
                "Completed": f"{completed_steps}/{total_steps}",
                "Progress": f"{bar} {percent}%",
            }
            if failed_steps:
                progress_fields["Failed"] = str(failed_steps)

            sections.append(DetailSection("Steps", progress_fields))

            # Build step lines as a separate section
            step_lines = _build_step_lines(
                steps, current_step, bool(status.get("running"))
            )
            if step_lines:
                step_fields = {line.strip(): "" for line in step_lines}
                sections.append(DetailSection("Step List", step_fields))

        detail_panel.update_content(title=name, sections=sections)

    async def _send_workflow_command(self, command: str) -> None:
        """Send a control command to the selected workflow.

        Args:
            command: Command to send (pause, resume, cancel).
        """
        if not self.selected_workflow_id:
            self.notify("No workflow selected", timeout=2)
            return

        try:
            workcell_url = self.get_service_url("workcell_manager")
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
        self.app.switch_screen("dashboard")
