"""Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, workflow control actions, filtering,
and step detail inspection.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import (
    ActionBarMixin,
    AutoRefreshMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailSection,
    FilterBar,
    FilterDef,
)
from madsci.client.cli.utils.formatting import (
    format_duration,
    format_status_icon,
    format_timestamp,
)
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
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


def _build_timing_section(data: dict) -> DetailSection | None:
    """Build the timing section for a workflow detail panel.

    Args:
        data: Workflow data dictionary.

    Returns:
        DetailSection if any timing info exists, else None.
    """
    timing_fields: dict[str, str] = {}
    submitted_time = data.get("submitted_time")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    if submitted_time:
        timing_fields["Submitted"] = format_timestamp(submitted_time, short=True)
    if start_time:
        timing_fields["Started"] = format_timestamp(start_time, short=True)
    if end_time:
        timing_fields["Ended"] = format_timestamp(end_time, short=True)
    duration = data.get("duration_seconds")
    if duration is not None:
        timing_fields["Duration"] = format_duration(duration)
    if timing_fields:
        return DetailSection("Timing", timing_fields)
    return None


def _build_progress_section(data: dict, status: dict) -> DetailSection | None:
    """Build the progress section for a workflow detail panel.

    Args:
        data: Workflow data dictionary.
        status: Workflow status dictionary.

    Returns:
        DetailSection if steps exist, else None.
    """
    steps = data.get("steps", [])
    total_steps = len(steps)
    if total_steps == 0:
        return None

    completed_steps = data.get("completed_steps", 0)
    failed_steps = data.get("failed_steps", 0)
    skipped_steps = data.get("skipped_steps", 0)
    current_step = status.get("current_step_index", 0)

    progress = completed_steps / total_steps
    filled = int(progress * 20)
    empty = 20 - filled
    bar = "\u2588" * filled + "\u2591" * empty
    percent = int(progress * 100)

    progress_fields: dict[str, str] = {
        "Total": str(total_steps),
        "Completed": f"{completed_steps}/{total_steps}",
        "Progress": f"{bar} {percent}%",
        "Current Step": str(current_step),
    }
    if failed_steps:
        progress_fields["Failed"] = str(failed_steps)
    if skipped_steps:
        progress_fields["Skipped"] = str(skipped_steps)

    return DetailSection("Progress", progress_fields)


def _matches_filter(
    wf_data: dict,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether a workflow matches the current filter criteria.

    Args:
        wf_data: Workflow data dictionary.
        search: Search text (matched against name, case-insensitive).
        filters: Filter dict, currently supports ``"status"`` key.

    Returns:
        True if the workflow passes the filters.
    """
    # Status filter
    status_filter = filters.get("status", "all")
    if status_filter and status_filter != "all":
        status = wf_data.get("status", {})
        status_name = _get_workflow_status_name(status)
        if status_name != status_filter:
            return False

    # Search text filter (matches against name)
    if search:
        name = wf_data.get("name", "")
        if search.lower() not in name.lower():
            return False

    return True


class WorkflowsScreen(ActionBarMixin, AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing workflow visualization and management."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("p", "pause_workflow", "Pause"),
        ("u", "resume_workflow", "Resume"),
        ("c", "cancel_workflow", "Cancel"),
        ("t", "retry_workflow", "Retry"),
        ("s", "resubmit_workflow", "Resubmit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.workflows_data: dict[str, dict] = {}
        self.selected_workflow_id: str | None = None
        self._active_ids: list[str] = []
        self._archived_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the workflows screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Workflow Management[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Filter workflows...",
                filters=[
                    FilterDef(
                        "status",
                        "Status",
                        [
                            ("all", "All"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("paused", "Paused"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="all",
                    ),
                ],
                id="workflow-filter",
            )

            yield Label("")

            with Vertical(id="active-workflows-section"):
                yield Label("[bold]Active Workflows[/bold]")
                yield DataTable(id="workflows-table")

            yield Label("")

            with Vertical(id="archived-workflows-section"):
                yield Label("[bold]Archived Workflows[/bold]")
                yield DataTable(id="archived-table")

            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef("p", "Pause", "pause", variant="warning"),
                    ActionDef("u", "Resume", "resume", variant="success"),
                    ActionDef("c", "Cancel", "cancel", variant="error"),
                    ActionDef("t", "Retry", "retry", variant="warning"),
                    ActionDef("s", "Resubmit", "resubmit", variant="primary"),
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
        self._active_ids.clear()
        self._archived_ids.clear()
        await self._refresh_active_workflows()
        await self._refresh_archived_workflows()

    async def _refresh_active_workflows(self) -> None:
        """Refresh the active/queued workflows table."""
        table = self.query_one("#workflows-table", DataTable)

        active = await self._fetch_workflows("/workflows/active")
        queued = await self._fetch_workflows("/workflows/queue")

        active_ids: list[str] = []

        if isinstance(active, dict):
            for wf_id, wf_data in active.items():
                self.workflows_data[wf_id] = wf_data
                active_ids.append(wf_id)
        if isinstance(queued, list):
            for wf_data in queued:
                wf_id = wf_data.get("workflow_id", "unknown")
                if wf_id not in self.workflows_data:
                    self.workflows_data[wf_id] = wf_data
                    active_ids.append(wf_id)

        self._active_ids = active_ids

        # Apply filters and populate table
        filtered = [
            wf_id
            for wf_id in active_ids
            if _matches_filter(
                self.workflows_data[wf_id],
                self._current_search,
                self._current_filters,
            )
        ]

        with preserve_cursor(table):
            table.clear()
            for wf_id in filtered:
                _add_workflow_row(table, self.workflows_data[wf_id])

            if not filtered:
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

        archived = await self._fetch_workflows("/workflows/archived?number=20")
        rows = self._normalize_workflow_response(archived)

        archived_ids: list[str] = []
        for wf_id, wf_data in rows:
            if wf_id not in self.workflows_data:
                self.workflows_data[wf_id] = wf_data
            archived_ids.append(wf_id)

        self._archived_ids = archived_ids

        # Apply filters and populate table
        filtered = [
            wf_id
            for wf_id in archived_ids
            if _matches_filter(
                self.workflows_data[wf_id],
                self._current_search,
                self._current_filters,
            )
        ]

        with preserve_cursor(archived_table):
            archived_table.clear()
            for wf_id in filtered:
                _add_workflow_row(archived_table, self.workflows_data[wf_id])

            if not filtered:
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
            client = self.get_async_client(workcell_url)
            response = await client.get(f"{workcell_url.rstrip('/')}{path}")
            if response.status_code == 200:
                return response.json()
        except Exception:
            self.notify("Failed to reach Workcell Manager", timeout=3)
        return {}

    def on_filter_bar_filter_changed(self, event: FilterBar.FilterChanged) -> None:
        """Handle filter changes from the FilterBar.

        Args:
            event: The filter changed event with search and filters.
        """
        self._current_search = event.search
        self._current_filters = event.filters
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Re-populate both tables using current search and filter values."""
        # Active workflows table
        active_table = self.query_one("#workflows-table", DataTable)
        filtered_active = [
            wf_id
            for wf_id in self._active_ids
            if wf_id in self.workflows_data
            and _matches_filter(
                self.workflows_data[wf_id],
                self._current_search,
                self._current_filters,
            )
        ]
        with preserve_cursor(active_table):
            active_table.clear()
            for wf_id in filtered_active:
                _add_workflow_row(active_table, self.workflows_data[wf_id])
            if not filtered_active:
                active_table.add_row(
                    format_status_icon("unknown"),
                    "[dim]No active workflows[/dim]",
                    "-",
                    "-",
                    "-",
                    "-",
                )

        # Archived workflows table
        archived_table = self.query_one("#archived-table", DataTable)
        filtered_archived = [
            wf_id
            for wf_id in self._archived_ids
            if wf_id in self.workflows_data
            and _matches_filter(
                self.workflows_data[wf_id],
                self._current_search,
                self._current_filters,
            )
        ]
        with preserve_cursor(archived_table):
            archived_table.clear()
            for wf_id in filtered_archived:
                _add_workflow_row(archived_table, self.workflows_data[wf_id])
            if not filtered_archived:
                archived_table.add_row(
                    format_status_icon("unknown"),
                    "[dim]No archived workflows[/dim]",
                    "-",
                    "-",
                    "-",
                    "-",
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection — push workflow detail screen."""
        table = event.data_table
        row_key = event.row_key

        if not row_key:
            return

        if table.id not in ("workflows-table", "archived-table"):
            return

        row = table.get_row(row_key)
        workflow_id = str(row[0])  # ID is the first column

        wf_data = self.workflows_data.get(workflow_id)
        if wf_data is not None:
            self.selected_workflow_id = workflow_id
            from madsci.client.cli.tui.screens.workflow_detail import (
                WorkflowDetailScreen,
            )

            self.app.push_screen(
                WorkflowDetailScreen(
                    workflow_id=workflow_id,
                    workflow_data=wf_data,
                )
            )

    async def _send_workflow_command(self, command: str) -> None:
        """Send a control command to the selected workflow.

        Args:
            command: Command to send (pause, resume, cancel, retry, resubmit).
        """
        if not self.selected_workflow_id:
            self.notify("No workflow selected", timeout=2)
            return

        try:
            workcell_url = self.get_service_url("workcell_manager")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{workcell_url.rstrip('/')}/workflow/"
                    f"{self.selected_workflow_id}/{command}"
                )
                if response.status_code == 200:
                    self.notify(f"Workflow {command} successful", timeout=2)
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

    async def action_retry_workflow(self) -> None:
        """Retry the selected workflow from the beginning."""
        await self._send_workflow_command("retry")

    async def action_resubmit_workflow(self) -> None:
        """Resubmit the selected workflow as a new run."""
        await self._send_workflow_command("resubmit")

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "pause": self.action_pause_workflow,
            "resume": self.action_resume_workflow,
            "cancel": self.action_cancel_workflow,
            "retry": self.action_retry_workflow,
            "resubmit": self.action_resubmit_workflow,
        }

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
