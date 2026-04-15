"""Data browser screen for MADSci TUI.

Provides datapoint browsing with filtering by label and data type,
a type-aware detail panel for selected datapoints, and preview
information for JSON, file, and object storage types.
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
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
    format_timestamp,
    truncate,
)
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import DataPoint
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_data_type(datapoint: DataPoint) -> str:
    """Extract the data type from a datapoint.

    Args:
        datapoint: DataPoint model instance.

    Returns:
        Lowercase data type string.
    """
    data_type = datapoint.data_type
    if isinstance(data_type, str):
        return data_type.lower()
    return data_type.value.lower()


def _get_preview(datapoint: DataPoint) -> str:
    """Generate a preview string for a datapoint.

    Args:
        datapoint: DataPoint model instance.

    Returns:
        Short preview string for display in the table.
    """
    data_type = _get_data_type(datapoint)

    if data_type == "json":
        return _get_json_preview(datapoint)

    if data_type == "file":
        path = getattr(datapoint, "path", None)
        if path:
            return PurePosixPath(str(path)).name
        return "-"

    if data_type in ("object_storage", "object storage"):
        object_name = getattr(datapoint, "object_name", None)
        return truncate(str(object_name), 30) if object_name else "-"

    return "-"


def _get_json_preview(datapoint: DataPoint) -> str:
    """Generate a preview string for a JSON datapoint.

    Args:
        datapoint: DataPoint model instance.

    Returns:
        Truncated JSON value string.
    """
    value = getattr(datapoint, "value", None)
    if value is None:
        return "-"
    try:
        text = json.dumps(value) if not isinstance(value, str) else value
    except (TypeError, ValueError):
        text = str(value)
    return truncate(text, 30)


def _matches_filter(
    datapoint: DataPoint,
    search: str,
    filters: dict[str, Any],
) -> bool:
    """Check whether a datapoint matches the current filter criteria.

    Args:
        datapoint: DataPoint model instance.
        search: Search text (matched against label, case-insensitive).
        filters: Filter dict; supports ``"type"`` key.

    Returns:
        True if the datapoint passes the filters.
    """
    type_filter = filters.get("type", "all")
    if type_filter and type_filter != "all":
        data_type = _get_data_type(datapoint)
        if data_type != type_filter:
            return False

    if search:
        label = datapoint.label or ""
        if search.lower() not in label.lower():
            return False

    return True


def _build_general_section(datapoint: DataPoint) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        datapoint: DataPoint model instance.

    Returns:
        DetailSection with general fields.
    """
    fields: dict[str, str] = {
        "ID": datapoint.datapoint_id,
        "Label": datapoint.label or "Unknown",
        "Type": _get_data_type(datapoint),
    }
    if datapoint.data_timestamp:
        fields["Timestamp"] = format_timestamp(datapoint.data_timestamp, short=True)
    return DetailSection("General", fields)


def _build_json_section(datapoint: DataPoint) -> DetailSection | None:
    """Build the JSON value section for JSON-type datapoints.

    Args:
        datapoint: DataPoint model instance (expected to be a ValueDataPoint).

    Returns:
        DetailSection if value exists, else None.
    """
    value = getattr(datapoint, "value", None)
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


def _build_file_section(datapoint: DataPoint) -> DetailSection | None:
    """Build the file info section for file-type datapoints.

    Args:
        datapoint: DataPoint model instance (expected to be a FileDataPoint).

    Returns:
        DetailSection if file info exists, else None.
    """
    fields: dict[str, str] = {}
    path = getattr(datapoint, "path", None)
    if path:
        fields["Path"] = str(path)
    content_type = getattr(datapoint, "content_type", None)
    if content_type:
        fields["Content Type"] = str(content_type)
    size = getattr(datapoint, "size_bytes", None)
    if size is not None:
        fields["Size"] = str(size)
    if fields:
        return DetailSection("File", fields)
    return None


def _build_object_storage_section(datapoint: DataPoint) -> DetailSection | None:
    """Build the object storage section for object-storage-type datapoints.

    Args:
        datapoint: DataPoint model instance (expected to be an ObjectStorageDataPoint).

    Returns:
        DetailSection if object storage info exists, else None.
    """
    fields: dict[str, str] = {}
    endpoint = getattr(datapoint, "storage_endpoint", None)
    if endpoint:
        fields["Endpoint"] = str(endpoint)
    bucket = getattr(datapoint, "bucket_name", None)
    if bucket:
        fields["Bucket"] = str(bucket)
    object_name = getattr(datapoint, "object_name", None)
    if object_name:
        fields["Object Name"] = str(object_name)
    content_type = getattr(datapoint, "content_type", None)
    if content_type:
        fields["Content Type"] = str(content_type)
    size = getattr(datapoint, "size_bytes", None)
    if size is not None:
        fields["Size"] = str(size)
    url = getattr(datapoint, "url", None)
    if url:
        fields["URL"] = str(url)
    if fields:
        return DetailSection("Storage", fields)
    return None


class DataBrowserScreen(ActionBarMixin, AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing data browser with type-aware detail display."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.datapoints_data: dict[str, DataPoint] = {}
        self.selected_datapoint_id: str | None = None
        self._datapoint_ids: list[str] = []
        self._current_search: str = ""
        self._current_filters: dict[str, Any] = {}
        self._data_client: DataClient | None = None

    def _get_data_client(self) -> DataClient:
        """Get or create the DataClient instance."""
        if self._data_client is None:
            url = self.get_service_url("data_manager")
            self._data_client = DataClient(
                data_server_url=url,
            )
        return self._data_client

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
            client = self._get_data_client()
            datapoints = await client.async_get_datapoints(number=50)
            for datapoint in datapoints:
                self.datapoints_data[datapoint.datapoint_id] = datapoint
                self._datapoint_ids.append(datapoint.datapoint_id)
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
                label = dp.label or "-"
                data_type = _get_data_type(dp)
                ts_str = (
                    format_timestamp(dp.data_timestamp, short=True)
                    if dp.data_timestamp
                    else "-"
                )
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
        if row_id in self.datapoints_data:
            self.selected_datapoint_id = row_id
            self._update_detail_panel(self.datapoints_data[row_id])

    def _update_detail_panel(self, datapoint: DataPoint) -> None:
        """Update the detail panel with datapoint data.

        Args:
            datapoint: DataPoint model instance.
        """
        detail_panel = self.query_one("#data-detail-panel", DetailPanel)
        label = datapoint.label or "Datapoint"

        sections: list[DetailSection] = [
            _build_general_section(datapoint),
        ]

        ownership_items = build_ownership_section(
            datapoint.model_dump(mode="json"),
        )
        if ownership_items:
            sections.append(DetailSection("Ownership", dict(ownership_items)))

        # Type-specific sections
        data_type = _get_data_type(datapoint)
        if data_type == "json":
            json_section = _build_json_section(datapoint)
            if json_section:
                sections.append(json_section)
        elif data_type == "file":
            file_section = _build_file_section(datapoint)
            if file_section:
                sections.append(file_section)
        elif data_type in ("object_storage", "object storage"):
            storage_section = _build_object_storage_section(datapoint)
            if storage_section:
                sections.append(storage_section)

        detail_panel.update_content(title=label, sections=sections)

    async def action_refresh(self) -> None:
        """Refresh data."""
        await self.refresh_data()
        self.notify("Data refreshed", timeout=2)

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
        }

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
