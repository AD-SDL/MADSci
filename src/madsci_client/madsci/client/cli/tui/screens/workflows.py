"""Workflow visualization screen for MADSci TUI.

Provides workflow monitoring with step progress visualization,
active/queued workflow display, workflow control actions, filtering,
and step detail inspection.
"""

from __future__ import annotations

from typing import Any, ClassVar

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
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.workflow_types import Workflow, WorkflowStatus
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_workflow_status_name(status: WorkflowStatus) -> str:
    """Get a canonical status name from a WorkflowStatus model.

    Args:
        status: WorkflowStatus model instance with boolean flags.

    Returns:
        Status name string.
    """
    for key in ("completed", "failed", "cancelled", "running", "paused"):
        if getattr(status, key, False):
            return key
    return "unknown"


def _add_workflow_row(table: DataTable, workflow: Workflow) -> None:
    """Add a workflow row to a table.

    Args:
        table: The DataTable to add to.
        workflow: Workflow model instance.
    """
    status_name = _get_workflow_status_name(workflow.status)
    icon = format_status_icon(status_name)

    # Progress
    total_steps = len(workflow.steps)
    completed = workflow.completed_steps
    progress = f"{completed}/{total_steps}" if total_steps > 0 else "-"

    # Current step
    current_index = workflow.status.current_step_index
    if workflow.steps and 0 <= current_index < total_steps:
        current_step = workflow.steps[current_index]
        step_name = current_step.name or current_step.action or "-"
    else:
        step_name = "-"

    # Timing - use shared formatting utilities
    started_str = (
        format_timestamp(workflow.start_time, short=True)
        if workflow.start_time
        else "-"
    )

    duration_str = format_duration(workflow.duration_seconds)

    table.add_row(icon, workflow.name, progress, step_name, started_str, duration_str)


def _build_timing_section(workflow: Workflow) -> DetailSection | None:
    """Build the timing section for a workflow detail panel.

    Args:
        workflow: Workflow model instance.

    Returns:
        DetailSection if any timing info exists, else None.
    """
    timing_fields: dict[str, str] = {}
    if workflow.submitted_time:
        timing_fields["Submitted"] = format_timestamp(
            workflow.submitted_time, short=True
        )
    if workflow.start_time:
        timing_fields["Started"] = format_timestamp(workflow.start_time, short=True)
    if workflow.end_time:
        timing_fields["Ended"] = format_timestamp(workflow.end_time, short=True)
    if workflow.duration_seconds is not None:
        timing_fields["Duration"] = format_duration(workflow.duration_seconds)
    if timing_fields:
        return DetailSection("Timing", timing_fields)
    return None


def _build_progress_section(workflow: Workflow) -> DetailSection | None:
    """Build the progress section for a workflow detail panel.

    Args:
        workflow: Workflow model instance.

    Returns:
        DetailSection if steps exist, else None.
    """
    total_steps = len(workflow.steps)
    if total_steps == 0:
        return None

    completed_steps = workflow.completed_steps
    failed_steps = workflow.failed_steps
    skipped_steps = workflow.skipped_steps
    current_step = workflow.status.current_step_index

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
    workflow: Workflow,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether a workflow matches the current filter criteria.

    Args:
        workflow: Workflow model instance.
        search: Search text (matched against name, case-insensitive).
        filters: Filter dict, currently supports ``"status"`` key.

    Returns:
        True if the workflow passes the filters.
    """
    # Status filter
    status_filter = filters.get("status", "all")
    if status_filter and status_filter != "all":
        status_name = _get_workflow_status_name(workflow.status)
        if status_name != status_filter:
            return False

    # Search text filter (matches against name)
    if search:
        name = workflow.name or ""
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
        self.workflows_data: dict[str, Workflow] = {}
        self.selected_workflow_id: str | None = None
        self._active_ids: list[str] = []
        self._archived_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}
        self._workcell_client: WorkcellClient | None = None

    def _get_workcell_client(self) -> WorkcellClient:
        """Get or create the WorkcellClient instance."""
        if self._workcell_client is None:
            url = self.get_service_url("workcell_manager")
            self._workcell_client = WorkcellClient(
                workcell_server_url=url,
            )
        return self._workcell_client

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

        active_ids: list[str] = []

        try:
            client = self._get_workcell_client()
            active = await client.async_get_active_workflows()
            for wf_id, wf in active.items():
                self.workflows_data[wf_id] = wf
                active_ids.append(wf_id)

            queued = await client.async_get_workflow_queue()
            for wf in queued:
                wf_id = wf.workflow_id
                if wf_id not in self.workflows_data:
                    self.workflows_data[wf_id] = wf
                    active_ids.append(wf_id)
        except Exception:
            self.notify("Failed to reach Workcell Manager", timeout=3)

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

        archived_ids: list[str] = []

        try:
            client = self._get_workcell_client()
            archived = await client.async_get_archived_workflows(number=20)
            for wf_id, wf in archived.items():
                if wf_id not in self.workflows_data:
                    self.workflows_data[wf_id] = wf
                archived_ids.append(wf_id)
        except Exception:
            self.notify("Failed to reach Workcell Manager", timeout=3)

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
        """Handle row selection -- push workflow detail screen."""
        table = event.data_table
        row_key = event.row_key

        if not row_key:
            return

        if table.id not in ("workflows-table", "archived-table"):
            return

        row = table.get_row(row_key)
        workflow_name = str(row[1])

        # Find workflow by matching name in the appropriate ID list
        source_ids = (
            self._active_ids if table.id == "workflows-table" else self._archived_ids
        )
        for wf_id in source_ids:
            wf = self.workflows_data.get(wf_id)
            if wf is not None and wf.name == workflow_name:
                self.selected_workflow_id = wf_id
                from madsci.client.cli.tui.screens.workflow_detail import (
                    WorkflowDetailScreen,
                )

                self.app.push_screen(
                    WorkflowDetailScreen(
                        workflow_id=wf_id,
                        workflow_data=wf,
                    )
                )
                return

    async def _send_workflow_command(self, command: str) -> None:
        """Send a control command to the selected workflow.

        Args:
            command: Command to send (pause, resume, cancel, retry, resubmit).
        """
        if not self.selected_workflow_id:
            self.notify("No workflow selected", timeout=2)
            return

        try:
            client = self._get_workcell_client()
            command_methods = {
                "pause": client.async_pause_workflow,
                "resume": client.async_resume_workflow,
                "cancel": client.async_cancel_workflow,
                "retry": client.async_retry_workflow,
                "resubmit": client.async_resubmit_workflow,
            }
            method = command_methods.get(command)
            if method:
                await method(self.selected_workflow_id)
                self.notify(f"Workflow {command} successful", timeout=2)
                await self.refresh_data()
            else:
                self.notify(f"Unknown command: {command}", timeout=3)
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
