"""Location management screen for MADSci TUI.

Provides location browsing with search filtering, a detail panel for
selected locations, and an action to view the transfer adjacency graph.
"""

from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import (
    ActionBarMixin,
    AutoRefreshMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.screens.transfer_graph import TransferGraphScreen
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailPanel,
    DetailSection,
    FilterBar,
)
from madsci.client.cli.utils.formatting import format_timestamp
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _matches_filter(
    loc_data: dict,
    search: str,
) -> bool:
    """Check whether a location matches the current search text.

    Args:
        loc_data: Location data dictionary.
        search: Search text (matched against location_name, case-insensitive).

    Returns:
        True if the location passes the filter.
    """
    if search:
        name = loc_data.get("location_name", "")
        if search.lower() not in name.lower():
            return False
    return True


def _build_general_section(loc_id: str, data: dict) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        loc_id: Location ID.
        data: Location data dictionary.

    Returns:
        DetailSection with general fields.
    """
    managed_by_raw = data.get("managed_by", "lab")
    managed_by_str = str(managed_by_raw).upper() if managed_by_raw else "LAB"

    owner = data.get("owner")
    if owner and isinstance(owner, dict):
        node_id = owner.get("node_id")
        owner_str = str(node_id) if node_id else "N/A"
    else:
        owner_str = "N/A"

    fields: dict[str, str] = {
        "Name": data.get("location_name", "Unknown"),
        "ID": loc_id,
        "Managed By": managed_by_str,
        "Owner": owner_str,
        "Allow Transfers": str(data.get("allow_transfers", True)),
    }
    template_name = data.get("location_template_name")
    if template_name:
        fields["Template"] = str(template_name)
    desc = data.get("description")
    if desc:
        fields["Description"] = str(desc)[:100]
    return DetailSection("General", fields)


def _build_resource_section(data: dict) -> DetailSection:
    """Build the resource section for the detail panel.

    Args:
        data: Location data dictionary.

    Returns:
        DetailSection with resource attachment info.
    """
    resource_id = data.get("resource_id")
    fields: dict[str, str] = {
        "Resource ID": str(resource_id) if resource_id else "None",
    }
    resource_template = data.get("resource_template_name")
    if resource_template:
        fields["Resource Template"] = str(resource_template)
    return DetailSection("Resource", fields)


def _build_representations_section(data: dict) -> DetailSection | None:
    """Build the representations section for the detail panel.

    Args:
        data: Location data dictionary.

    Returns:
        DetailSection if representations exist, else None.
    """
    representations = data.get("representations") or {}
    if not isinstance(representations, dict) or not representations:
        return None
    fields: dict[str, str] = {}
    for node_name, value in representations.items():
        fields[str(node_name)] = str(value)[:80]
    return DetailSection("Representations", fields)


def _build_node_bindings_section(data: dict) -> DetailSection | None:
    """Build the node bindings section for the detail panel.

    Args:
        data: Location data dictionary.

    Returns:
        DetailSection if node bindings exist, else None.
    """
    bindings = data.get("node_bindings") or {}
    if not isinstance(bindings, dict) or not bindings:
        return None
    fields: dict[str, str] = {str(role): str(node) for role, node in bindings.items()}
    return DetailSection("Node Bindings", fields)


def _build_reservation_section(data: dict) -> DetailSection | None:
    """Build the reservation section for the detail panel.

    Args:
        data: Location data dictionary.

    Returns:
        DetailSection if a reservation exists, else None.
    """
    reservation = data.get("reservation")
    if not reservation or not isinstance(reservation, dict):
        return None
    fields: dict[str, str] = {}
    owned_by = reservation.get("owned_by")
    if owned_by and isinstance(owned_by, dict):
        for key in ("user_id", "experiment_id", "campaign_id"):
            value = owned_by.get(key)
            if value:
                fields[key.replace("_", " ").title()] = str(value)
    created = reservation.get("created")
    if created:
        fields["Created"] = format_timestamp(created, short=True)
    expires = reservation.get("expires")
    if expires:
        fields["Expires"] = format_timestamp(expires, short=True)
    if fields:
        return DetailSection("Reservation", fields)
    return None


class LocationsScreen(ActionBarMixin, AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing location inventory and management."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("g", "show_transfer_graph", "Transfer Graph"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.locations_data: dict[str, dict] = {}
        self.selected_location_id: str | None = None
        self._location_ids: list[str] = []
        self._current_search: str = ""

    def compose(self) -> ComposeResult:
        """Compose the locations screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Location Inventory[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Search locations...",
                filters=[],
                id="location-filter",
            )

            yield Label("")
            yield DataTable(id="locations-table")
            yield Label("")
            yield DetailPanel(
                placeholder="Select a location from the table above",
                id="location-detail-panel",
            )
            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef(
                        "g", "Transfer Graph", "show_transfer_graph", variant="primary"
                    ),
                ],
                id="location-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        table = self.query_one("#locations-table", DataTable)
        table.add_columns(
            "Name",
            "Managed By",
            "ID",
            "Template",
            "Resource",
            "Transfers",
            "Reservation",
        )
        table.cursor_type = "row"
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh location data from the location manager."""
        self.locations_data.clear()
        self._location_ids.clear()

        try:
            location_url = self.get_service_url("location_manager")
            client = self.get_async_client(location_url)
            response = await client.get(
                f"{location_url.rstrip('/')}/locations",
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for loc in data:
                        loc_id = loc.get("location_id", "")
                        if loc_id:
                            self.locations_data[loc_id] = loc
                            self._location_ids.append(loc_id)
        except Exception:
            self.notify("Failed to reach Location Manager", timeout=3)

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the locations table with filtered data."""
        table = self.query_one("#locations-table", DataTable)

        filtered = [
            loc_id
            for loc_id in self._location_ids
            if loc_id in self.locations_data
            and _matches_filter(
                self.locations_data[loc_id],
                self._current_search,
            )
        ]

        with preserve_cursor(table):
            table.clear()

            for loc_id in filtered:
                loc = self.locations_data[loc_id]
                name = loc.get("location_name", "Unknown")
                managed_by_raw = loc.get("managed_by", "lab")
                managed_by_str = (
                    str(managed_by_raw).upper() if managed_by_raw else "LAB"
                )
                loc_id_str = loc_id or "-"
                template = loc.get("location_template_name", "-") or "-"
                resource = loc.get("resource_id", "")
                resource_display = resource or "None"
                transfers = "Yes" if loc.get("allow_transfers", True) else "No"
                reservation = "Reserved" if loc.get("reservation") else "-"
                table.add_row(
                    name,
                    managed_by_str,
                    loc_id_str,
                    template,
                    resource_display,
                    transfers,
                    reservation,
                )

            if not filtered:
                table.add_row(
                    "[dim]No locations found[/dim]",
                    "-",
                    "-",
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
        self._populate_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the locations table.

        Args:
            event: The row selected event.
        """
        table = event.data_table
        row_key = event.row_key
        if not row_key:
            return

        row = table.get_row(row_key)
        row_id = str(row[2])

        # Find location by matching full ID
        for loc_id, loc_data in self.locations_data.items():
            if loc_id == row_id:
                self.selected_location_id = loc_id
                self._update_detail_panel(loc_id, loc_data)
                break

    def _update_detail_panel(self, location_id: str, data: dict) -> None:
        """Update the detail panel with location data.

        Args:
            location_id: Location ID.
            data: Location data dictionary.
        """
        detail_panel = self.query_one("#location-detail-panel", DetailPanel)
        name = data.get("location_name", "Unknown")

        sections: list[DetailSection] = [_build_general_section(location_id, data)]
        sections.append(_build_resource_section(data))

        representations_section = _build_representations_section(data)
        if representations_section:
            sections.append(representations_section)

        bindings_section = _build_node_bindings_section(data)
        if bindings_section:
            sections.append(bindings_section)

        reservation_section = _build_reservation_section(data)
        if reservation_section:
            sections.append(reservation_section)

        detail_panel.update_content(title=name, sections=sections)

    async def action_refresh(self) -> None:
        """Refresh location data."""
        await self.refresh_data()
        self.notify("Locations refreshed", timeout=2)

    def action_show_transfer_graph(self) -> None:
        """Show the transfer graph screen."""
        location_url = self.get_service_url("location_manager")
        self.app.push_screen(TransferGraphScreen(location_url=location_url))

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "show_transfer_graph": self.action_show_transfer_graph,
        }

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
