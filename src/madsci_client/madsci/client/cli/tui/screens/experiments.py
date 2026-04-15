"""Experiment management screen for MADSci TUI.

Provides experiment browsing with filtering by name and status,
a detail panel for selected experiments, and actions for pause,
continue, and cancel operations.
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
from madsci.client.experiment_client import ExperimentClient
from madsci.common.types.experiment_types import Experiment
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_experiment_name(experiment: Experiment) -> str:
    """Extract the experiment name from an Experiment model.

    Args:
        experiment: Experiment model instance.

    Returns:
        Experiment name string, or ``"Unknown"`` if not available.
    """
    if experiment.experiment_design and experiment.experiment_design.experiment_name:
        return experiment.experiment_design.experiment_name
    return "Unknown"


def _matches_filter(
    experiment: Experiment,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether an experiment matches the current filter criteria.

    Args:
        experiment: Experiment model instance.
        search: Search text (matched against experiment name, case-insensitive).
        filters: Filter dict; supports ``"status"`` key.

    Returns:
        True if the experiment passes the filters.
    """
    status_filter = filters.get("status", "all")
    if (
        status_filter not in {"", "all", None}
        and experiment.status.value != status_filter
    ):
        return False

    if search:
        name = _get_experiment_name(experiment)
        if search.lower() not in name.lower():
            return False

    return True


def _calculate_duration(experiment: Experiment) -> str:
    """Calculate duration from started_at and ended_at timestamps.

    Args:
        experiment: Experiment model instance.

    Returns:
        Formatted duration string.
    """
    if experiment.started_at and experiment.ended_at:
        delta = (experiment.ended_at - experiment.started_at).total_seconds()
        return format_duration(delta)
    return "-"


def _build_general_section(experiment: Experiment) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        experiment: Experiment model instance.

    Returns:
        DetailSection with general fields.
    """
    fields: dict[str, str] = {
        "ID": experiment.experiment_id,
        "Status": format_status_colored(experiment.status.value),
        "Name": _get_experiment_name(experiment),
    }
    return DetailSection("General", fields)


def _build_run_section(experiment: Experiment) -> DetailSection | None:
    """Build the run info section for the detail panel.

    Args:
        experiment: Experiment model instance.

    Returns:
        DetailSection if run info exists, else None.
    """
    fields: dict[str, str] = {}
    if experiment.run_name:
        fields["Run Name"] = experiment.run_name
    if experiment.run_description:
        fields["Description"] = truncate(experiment.run_description, 100)
    if fields:
        return DetailSection("Run", fields)
    return None


def _build_design_section(experiment: Experiment) -> DetailSection | None:
    """Build the design/description section for the detail panel.

    Args:
        experiment: Experiment model instance.

    Returns:
        DetailSection if design info exists, else None.
    """
    fields: dict[str, str] = {}
    if experiment.experiment_design:
        if experiment.experiment_design.experiment_description:
            fields["Description"] = truncate(
                experiment.experiment_design.experiment_description, 100
            )
        if experiment.experiment_design.resource_conditions:
            fields["Resource Conditions"] = str(
                len(experiment.experiment_design.resource_conditions)
            )
    if fields:
        return DetailSection("Design", fields)
    return None


def _build_timing_section(experiment: Experiment) -> DetailSection | None:
    """Build the timing section for the detail panel.

    Args:
        experiment: Experiment model instance.

    Returns:
        DetailSection if timing info exists, else None.
    """
    fields: dict[str, str] = {}
    if experiment.started_at:
        fields["Started"] = format_timestamp(experiment.started_at, short=True)
    if experiment.ended_at:
        fields["Ended"] = format_timestamp(experiment.ended_at, short=True)
    duration_str = _calculate_duration(experiment)
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
        self.experiments_data: dict[str, Experiment] = {}
        self.selected_experiment_id: str | None = None
        self._experiment_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}
        self._experiment_client: ExperimentClient | None = None

    def _get_experiment_client(self) -> ExperimentClient:
        """Get or create the ExperimentClient instance."""
        if self._experiment_client is None:
            url = self.get_service_url("experiment_manager")
            self._experiment_client = ExperimentClient(
                experiment_server_url=url,
            )
        return self._experiment_client

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
            client = self._get_experiment_client()
            experiments = await client.async_get_experiments(number=50)
            for experiment in experiments:
                self.experiments_data[experiment.experiment_id] = experiment
                self._experiment_ids.append(experiment.experiment_id)
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
                status = exp.status.value
                icon = format_status_icon(status)
                name = _get_experiment_name(exp)
                exp_id_str = exp_id or "-"
                run_name = exp.run_name or "-"
                started_str = (
                    format_timestamp(exp.started_at, short=True)
                    if exp.started_at
                    else "-"
                )
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
        if row_id in self.experiments_data:
            self.selected_experiment_id = row_id
            self._update_detail_panel(self.experiments_data[row_id])

    def _update_detail_panel(self, experiment: Experiment) -> None:
        """Update the detail panel with experiment data.

        Args:
            experiment: Experiment model instance.
        """
        detail_panel = self.query_one("#experiment-detail-panel", DetailPanel)
        name = _get_experiment_name(experiment)

        sections: list[DetailSection] = [
            _build_general_section(experiment),
        ]

        run_section = _build_run_section(experiment)
        if run_section:
            sections.append(run_section)

        design_section = _build_design_section(experiment)
        if design_section:
            sections.append(design_section)

        timing_section = _build_timing_section(experiment)
        if timing_section:
            sections.append(timing_section)

        ownership_items = build_ownership_section(
            experiment.model_dump(mode="json"),
        )
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
            client = self._get_experiment_client()
            command_methods = {
                "pause": client.async_pause_experiment,
                "continue": client.async_continue_experiment,
                "cancel": client.async_cancel_experiment,
            }
            method = command_methods.get(command)
            if method:
                await method(self.selected_experiment_id)
                self.notify(f"Experiment {command} successful", timeout=2)
                await self.refresh_data()
            else:
                self.notify(f"Unknown command: {command}", timeout=3)
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
