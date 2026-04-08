"""Data browser screen for MADSci TUI.

Provides datapoint browsing with filtering by label and data type,
a type-aware detail panel for selected datapoints, and preview
information for JSON, file, and object storage types.
"""

import asyncio
import json
from pathlib import PurePosixPath
from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import (
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
from madsci.client.cli.utils.formatting import format_timestamp, truncate
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_data_type(data: dict) -> str:
    """Extract the data type from a datapoint.

    Args:
        data: Datapoint data dictionary.

    Returns:
        Lowercase data type string.
    """
    data_type = data.get("data_type", "unknown")
    if isinstance(data_type, str):
        return data_type.lower()
    return "unknown"


def _get_preview(data: dict) -> str:
    """Generate a preview string for a datapoint.

    Args:
        data: Datapoint data dictionary.

    Returns:
        Short preview string for display in the table.
    """
    data_type = _get_data_type(data)

    if data_type == "json":
        return _get_json_preview(data)

    if data_type == "file":
        path = data.get("path") or data.get("file_path", "")
        if path:
            return PurePosixPath(str(path)).name
        return "-"

    if data_type in ("object_storage", "object storage"):
        object_name = data.get("object_name", "")
        return truncate(str(object_name), 30) if object_name else "-"

    return "-"


def _get_json_preview(data: dict) -> str:
    """Generate a preview string for a JSON datapoint.

    Args:
        data: Datapoint data dictionary.

    Returns:
        Truncated JSON value string.
    """
    value = data.get("value")
    if value is None:
        return "-"
    try:
        text = json.dumps(value) if not isinstance(value, str) else value
    except (TypeError, ValueError):
        text = str(value)
    return truncate(text, 30)


def _matches_filter(
    dp_data: dict,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether a datapoint matches the current filter criteria.

    Args:
        dp_data: Datapoint data dictionary.
        search: Search text (matched against label, case-insensitive).
        filters: Filter dict; supports ``"type"`` key.

    Returns:
        True if the datapoint passes the filters.
    """
    type_filter = filters.get("type", "all")
    if type_filter and type_filter != "all":
        data_type = _get_data_type(dp_data)
        if data_type != type_filter:
            return False

    if search:
        label = dp_data.get("label", "")
        if search.lower() not in label.lower():
            return False

    return True


def _build_general_section(dp_id: str, data: dict) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        dp_id: Datapoint ID.
        data: Datapoint data dictionary.

    Returns:
        DetailSection with general fields.
    """
    fields: dict[str, str] = {
        "ID": dp_id,
        "Label": data.get("label", "Unknown"),
        "Type": _get_data_type(data),
    }
    timestamp = data.get("data_timestamp")
    if timestamp:
        fields["Timestamp"] = format_timestamp(timestamp, short=True)
    return DetailSection("General", fields)


def _build_ownership_section(data: dict) -> DetailSection | None:
    """Build the ownership section for the detail panel.

    Args:
        data: Datapoint data dictionary.

    Returns:
        DetailSection if ownership info exists, else None.
    """
    ownership_info = data.get("ownership_info") or {}
    if not isinstance(ownership_info, dict):
        return None
    fields: dict[str, str] = {}
    for key in ("user_id", "experiment_id", "workflow_id"):
        value = ownership_info.get(key)
        if value:
            fields[key.replace("_", " ").title()] = str(value)
    if fields:
        return DetailSection("Ownership", fields)
    return None


def _build_json_section(data: dict) -> DetailSection | None:
    """Build the JSON value section for JSON-type datapoints.

    Args:
        data: Datapoint data dictionary.

    Returns:
        DetailSection if value exists, else None.
    """
    value = data.get("value")
    if value is None:
        return None
    try:
        if isinstance(value, str):
            formatted = truncate(value, 200)
        else:
            formatted = truncate(json.dumps(value, indent=2), 200)
    except (TypeError, ValueError):
        formatted = truncate(str(value), 200)
    return DetailSection("Value", {"Data": formatted})


def _build_file_section(data: dict) -> DetailSection | None:
    """Build the file info section for file-type datapoints.

    Args:
        data: Datapoint data dictionary.

    Returns:
        DetailSection if file info exists, else None.
    """
    fields: dict[str, str] = {}
    path = data.get("path") or data.get("file_path")
    if path:
        fields["Path"] = str(path)
    content_type = data.get("content_type")
    if content_type:
        fields["Content Type"] = str(content_type)
    size = data.get("size") or data.get("file_size")
    if size is not None:
        fields["Size"] = str(size)
    if fields:
        return DetailSection("File", fields)
    return None


def _build_object_storage_section(data: dict) -> DetailSection | None:
    """Build the object storage section for object-storage-type datapoints.

    Args:
        data: Datapoint data dictionary.

    Returns:
        DetailSection if object storage info exists, else None.
    """
    fields: dict[str, str] = {}
    endpoint = data.get("endpoint")
    if endpoint:
        fields["Endpoint"] = str(endpoint)
    bucket = data.get("bucket")
    if bucket:
        fields["Bucket"] = str(bucket)
    object_name = data.get("object_name")
    if object_name:
        fields["Object Name"] = str(object_name)
    content_type = data.get("content_type")
    if content_type:
        fields["Content Type"] = str(content_type)
    size = data.get("size") or data.get("object_size")
    if size is not None:
        fields["Size"] = str(size)
    url = data.get("url") or data.get("object_url")
    if url:
        fields["URL"] = str(url)
    if fields:
        return DetailSection("Storage", fields)
    return None


class DataBrowserScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing data browser with type-aware detail display."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.datapoints_data: dict[str, dict] = {}
        self.selected_datapoint_id: str | None = None
        self._datapoint_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the data browser screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Data Browser[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Search by label...",
                filters=[
                    FilterDef(
                        "type",
                        "Type",
                        [
                            ("all", "All"),
                            ("json", "JSON"),
                            ("file", "File"),
                            ("object_storage", "Object Storage"),
                        ],
                        default="all",
                    ),
                ],
                id="data-filter",
            )

            yield Label("")
            yield DataTable(id="data-table")
            yield Label("")
            yield DetailPanel(
                placeholder="Select a datapoint from the table above",
                id="data-detail-panel",
            )
            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                ],
                id="data-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        table = self.query_one("#data-table", DataTable)
        table.add_columns("ID", "Label", "Type", "Timestamp", "Preview")
        table.cursor_type = "row"
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh datapoint data from the data manager."""
        self.datapoints_data.clear()
        self._datapoint_ids.clear()

        try:
            data_url = self.get_service_url("data_manager")
            client = self.get_async_client(data_url)
            response = await client.get(
                f"{data_url.rstrip('/')}/datapoints",
                params={"number": 50},
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    for dp_id, dp_data in data.items():
                        if isinstance(dp_data, dict):
                            self.datapoints_data[dp_id] = dp_data
                            self._datapoint_ids.append(dp_id)
                elif isinstance(data, list):
                    for dp_data in data:
                        dp_id = dp_data.get("datapoint_id", "")
                        if dp_id:
                            self.datapoints_data[dp_id] = dp_data
                            self._datapoint_ids.append(dp_id)
        except Exception:
            self.notify("Failed to reach Data Manager", timeout=3)

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the data table with filtered datapoints."""
        table = self.query_one("#data-table", DataTable)

        filtered = [
            dp_id
            for dp_id in self._datapoint_ids
            if dp_id in self.datapoints_data
            and _matches_filter(
                self.datapoints_data[dp_id],
                self._current_search,
                self._current_filters,
            )
        ]

        with preserve_cursor(table):
            table.clear()

            for dp_id in filtered:
                dp = self.datapoints_data[dp_id]
                dp_id_str = dp_id or "-"
                label = dp.get("label", "-") or "-"
                data_type = _get_data_type(dp)
                timestamp = dp.get("data_timestamp")
                ts_str = format_timestamp(timestamp, short=True) if timestamp else "-"
                preview = _get_preview(dp)
                table.add_row(dp_id_str, label, data_type, ts_str, preview)

            if not filtered:
                table.add_row(
                    "-",
                    "[dim]No datapoints found[/dim]",
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
        """Handle row selection in the data table.

        Args:
            event: The row selected event.
        """
        table = event.data_table
        row_key = event.row_key
        if not row_key:
            return

        row = table.get_row(row_key)
        row_id = str(row[0])

        # Find datapoint by matching full ID
        for dp_id, dp_data in self.datapoints_data.items():
            if dp_id == row_id:
                self.selected_datapoint_id = dp_id
                self._update_detail_panel(dp_id, dp_data)
                break

    def _update_detail_panel(self, datapoint_id: str, data: dict) -> None:
        """Update the detail panel with datapoint data.

        Args:
            datapoint_id: Datapoint ID.
            data: Datapoint data dictionary.
        """
        detail_panel = self.query_one("#data-detail-panel", DetailPanel)
        label = data.get("label", "Datapoint")

        sections: list[DetailSection] = [
            _build_general_section(datapoint_id, data),
        ]

        ownership_section = _build_ownership_section(data)
        if ownership_section:
            sections.append(ownership_section)

        # Type-specific sections
        data_type = _get_data_type(data)
        if data_type == "json":
            json_section = _build_json_section(data)
            if json_section:
                sections.append(json_section)
        elif data_type == "file":
            file_section = _build_file_section(data)
            if file_section:
                sections.append(file_section)
        elif data_type in ("object_storage", "object storage"):
            storage_section = _build_object_storage_section(data)
            if storage_section:
                sections.append(storage_section)

        detail_panel.update_content(title=label, sections=sections)

    async def action_refresh(self) -> None:
        """Refresh data."""
        await self.refresh_data()
        self.notify("Data refreshed", timeout=2)

    def on_action_bar_action_triggered(self, event: ActionBar.ActionTriggered) -> None:
        """Route ActionBar button triggers to screen actions."""
        action_map = {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
        }
        handler = action_map.get(event.action)
        if handler is not None:
            if asyncio.iscoroutinefunction(handler):
                self.run_worker(handler())
            else:
                handler()

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
