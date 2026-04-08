"""Experiment management screen for MADSci TUI.

Provides experiment browsing with filtering by name and status,
a detail panel for selected experiments, and actions for pause,
continue, and cancel operations.
"""

from datetime import datetime
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
    DetailPanel,
    DetailSection,
    FilterBar,
    FilterDef,
)
from madsci.client.cli.utils.formatting import (
    build_ownership_section,
    format_duration,
    format_status_colored,
    format_status_icon,
    format_timestamp,
    truncate,
)
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_experiment_status(data: dict) -> str:
    """Extract a canonical status name from experiment data.

    Args:
        data: Experiment data dictionary.

    Returns:
        Lowercase status name string.
    """
    status = data.get("status", "unknown")
    if isinstance(status, str):
        return status.lower()
    if isinstance(status, dict):
        for key in ("completed", "failed", "cancelled", "paused", "in_progress"):
            if status.get(key):
                return key
    return "unknown"


def _matches_filter(
    exp_data: dict,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether an experiment matches the current filter criteria.

    Args:
        exp_data: Experiment data dictionary.
        search: Search text (matched against experiment_name, case-insensitive).
        filters: Filter dict; supports ``"status"`` key.

    Returns:
        True if the experiment passes the filters.
    """
    status_filter = filters.get("status", "all")
    if status_filter and status_filter != "all":
        status = _get_experiment_status(exp_data)
        if status != status_filter:
            return False

    if search:
        name = exp_data.get("experiment_name", "")
        if search.lower() not in name.lower():
            return False

    return True


def _calculate_duration(data: dict) -> str:
    """Calculate duration from started_at and ended_at timestamps.

    Args:
        data: Experiment data dictionary.

    Returns:
        Formatted duration string.
    """
    duration = data.get("duration_seconds")
    if duration is not None:
        return format_duration(duration)

    started = data.get("started_at")
    ended = data.get("ended_at")
    if started and ended:
        try:
            start_dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
            delta = (end_dt - start_dt).total_seconds()
            return format_duration(delta)
        except (ValueError, TypeError):
            pass
    return "-"


def _build_general_section(exp_id: str, data: dict) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        exp_id: Experiment ID.
        data: Experiment data dictionary.

    Returns:
        DetailSection with general fields.
    """
    status = _get_experiment_status(data)
    fields: dict[str, str] = {
        "ID": exp_id,
        "Status": format_status_colored(status),
        "Name": data.get("experiment_name", "Unknown"),
    }
    return DetailSection("General", fields)


def _build_run_section(data: dict) -> DetailSection | None:
    """Build the run info section for the detail panel.

    Args:
        data: Experiment data dictionary.

    Returns:
        DetailSection if run info exists, else None.
    """
    fields: dict[str, str] = {}
    run_name = data.get("run_name")
    if run_name:
        fields["Run Name"] = str(run_name)
    run_desc = data.get("run_description")
    if run_desc:
        fields["Description"] = truncate(str(run_desc), 100)
    if fields:
        return DetailSection("Run", fields)
    return None


def _build_design_section(data: dict) -> DetailSection | None:
    """Build the design/description section for the detail panel.

    Args:
        data: Experiment data dictionary.

    Returns:
        DetailSection if design info exists, else None.
    """
    fields: dict[str, str] = {}
    desc = data.get("experiment_description")
    if desc:
        fields["Description"] = truncate(str(desc), 100)
    resource_conditions = data.get("resource_conditions")
    if isinstance(resource_conditions, (list, dict)):
        fields["Resource Conditions"] = str(len(resource_conditions))
    if fields:
        return DetailSection("Design", fields)
    return None


def _build_timing_section(data: dict) -> DetailSection | None:
    """Build the timing section for the detail panel.

    Args:
        data: Experiment data dictionary.

    Returns:
        DetailSection if timing info exists, else None.
    """
    fields: dict[str, str] = {}
    started = data.get("started_at")
    ended = data.get("ended_at")
    if started:
        fields["Started"] = format_timestamp(started, short=True)
    if ended:
        fields["Ended"] = format_timestamp(ended, short=True)
    duration_str = _calculate_duration(data)
    if duration_str != "-":
        fields["Duration"] = duration_str
    if fields:
        return DetailSection("Timing", fields)
    return None


class ExperimentsScreen(ActionBarMixin, AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing experiment management and monitoring."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("p", "pause_experiment", "Pause"),
        ("c", "continue_experiment", "Continue"),
        ("x", "cancel_experiment", "Cancel"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.experiments_data: dict[str, dict] = {}
        self.selected_experiment_id: str | None = None
        self._experiment_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the experiments screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Experiment Management[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Search experiments...",
                filters=[
                    FilterDef(
                        "status",
                        "Status",
                        [
                            ("all", "All"),
                            ("in_progress", "In Progress"),
                            ("paused", "Paused"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="all",
                    ),
                ],
                id="experiment-filter",
            )

            yield Label("")
            yield DataTable(id="experiments-table")
            yield Label("")
            yield DetailPanel(
                placeholder="Select an experiment from the table above",
                id="experiment-detail-panel",
            )
            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef("p", "Pause", "pause", variant="warning"),
                    ActionDef("c", "Continue", "continue", variant="success"),
                    ActionDef("x", "Cancel", "cancel", variant="error"),
                ],
                id="experiment-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        table = self.query_one("#experiments-table", DataTable)
        table.add_columns("Status", "Name", "ID", "Run Name", "Started", "Duration")
        table.cursor_type = "row"
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh experiment data from the experiment manager."""
        self.experiments_data.clear()
        self._experiment_ids.clear()

        try:
            experiment_url = self.get_service_url("experiment_manager")
            client = self.get_async_client(experiment_url)
            response = await client.get(
                f"{experiment_url.rstrip('/')}/experiments",
                params={"number": 50},
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    for exp_id, exp_data in data.items():
                        if isinstance(exp_data, dict):
                            self.experiments_data[exp_id] = exp_data
                            self._experiment_ids.append(exp_id)
                elif isinstance(data, list):
                    for exp_data in data:
                        exp_id = exp_data.get("experiment_id", "")
                        if exp_id:
                            self.experiments_data[exp_id] = exp_data
                            self._experiment_ids.append(exp_id)
        except Exception:
            self.notify("Failed to reach Experiment Manager", timeout=3)

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the experiments table with filtered data."""
        table = self.query_one("#experiments-table", DataTable)

        filtered = [
            exp_id
            for exp_id in self._experiment_ids
            if exp_id in self.experiments_data
            and _matches_filter(
                self.experiments_data[exp_id],
                self._current_search,
                self._current_filters,
            )
        ]

        with preserve_cursor(table):
            table.clear()

            for exp_id in filtered:
                exp = self.experiments_data[exp_id]
                status = _get_experiment_status(exp)
                icon = format_status_icon(status)
                name = exp.get("experiment_name", "Unknown")
                exp_id_str = exp_id or "-"
                run_name = exp.get("run_name", "-") or "-"
                started = exp.get("started_at")
                started_str = format_timestamp(started, short=True) if started else "-"
                duration_str = _calculate_duration(exp)
                table.add_row(
                    icon, name, exp_id_str, run_name, started_str, duration_str
                )

            if not filtered:
                table.add_row(
                    format_status_icon("unknown"),
                    "[dim]No experiments found[/dim]",
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
        self._populate_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the experiments table.

        Args:
            event: The row selected event.
        """
        table = event.data_table
        row_key = event.row_key
        if not row_key:
            return

        row = table.get_row(row_key)
        row_id = str(row[2])

        # Find experiment by matching full ID
        for exp_id, exp_data in self.experiments_data.items():
            if exp_id == row_id:
                self.selected_experiment_id = exp_id
                self._update_detail_panel(exp_id, exp_data)
                break

    def _update_detail_panel(self, experiment_id: str, data: dict) -> None:
        """Update the detail panel with experiment data.

        Args:
            experiment_id: Experiment ID.
            data: Experiment data dictionary.
        """
        detail_panel = self.query_one("#experiment-detail-panel", DetailPanel)
        name = data.get("experiment_name", "Unknown")

        sections: list[DetailSection] = [
            _build_general_section(experiment_id, data),
        ]

        run_section = _build_run_section(data)
        if run_section:
            sections.append(run_section)

        design_section = _build_design_section(data)
        if design_section:
            sections.append(design_section)

        timing_section = _build_timing_section(data)
        if timing_section:
            sections.append(timing_section)

        ownership_items = build_ownership_section(data)
        if ownership_items:
            sections.append(DetailSection("Ownership", dict(ownership_items)))

        detail_panel.update_content(title=name, sections=sections)

    async def _send_experiment_command(self, command: str) -> None:
        """Send a control command to the selected experiment.

        Args:
            command: Command to send (pause, continue, cancel).
        """
        if not self.selected_experiment_id:
            self.notify("No experiment selected", timeout=2)
            return

        try:
            experiment_url = self.get_service_url("experiment_manager")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{experiment_url.rstrip('/')}/experiment/"
                    f"{self.selected_experiment_id}/{command}"
                )
                if response.status_code == 200:
                    self.notify(f"Experiment {command} successful", timeout=2)
                    await self.refresh_data()
                else:
                    self.notify(
                        f"Failed to {command} experiment: HTTP {response.status_code}",
                        timeout=3,
                    )
        except Exception as e:
            self.notify(f"Error: {e}", timeout=3)

    async def action_refresh(self) -> None:
        """Refresh experiment data."""
        await self.refresh_data()
        self.notify("Experiments refreshed", timeout=2)

    async def action_pause_experiment(self) -> None:
        """Pause the selected experiment."""
        await self._send_experiment_command("pause")

    async def action_continue_experiment(self) -> None:
        """Continue the selected experiment."""
        await self._send_experiment_command("continue")

    async def action_cancel_experiment(self) -> None:
        """Cancel the selected experiment."""
        await self._send_experiment_command("cancel")

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "pause": self.action_pause_experiment,
            "continue": self.action_continue_experiment,
            "cancel": self.action_cancel_experiment,
        }

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
