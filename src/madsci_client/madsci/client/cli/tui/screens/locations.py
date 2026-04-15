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
from madsci.client.location_client import LocationClient
from madsci.common.types.location_types import Location
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _matches_filter(
    location: Location,
    search: str,
) -> bool:
    """Check whether a location matches the current search text.

    Args:
        location: Location model instance.
        search: Search text (matched against location_name, case-insensitive).

    Returns:
        True if the location passes the filter.
    """
    if search:
        name = location.location_name
        if search.lower() not in name.lower():
            return False
    return True


def _build_general_section(location: Location) -> DetailSection:
    """Build the general info section for the detail panel.

    Args:
        location: Location model instance.

    Returns:
        DetailSection with general fields.
    """
    fields: dict[str, str] = {
        "Name": location.location_name or "Unknown",
        "ID": location.location_id,
        "Allow Transfers": str(location.allow_transfers),
    }
    if location.location_template_name:
        fields["Template"] = str(location.location_template_name)
    if location.description:
        fields["Description"] = str(location.description)[:100]
    return DetailSection("General", fields)


def _build_resource_section(location: Location) -> DetailSection:
    """Build the resource section for the detail panel.

    Args:
        location: Location model instance.

    Returns:
        DetailSection with resource attachment info.
    """
    fields: dict[str, str] = {
        "Resource ID": str(location.resource_id) if location.resource_id else "None",
    }
    if location.resource_template_name:
        fields["Resource Template"] = str(location.resource_template_name)
    return DetailSection("Resource", fields)


def _build_representations_section(location: Location) -> DetailSection | None:
    """Build the representations section for the detail panel.

    Args:
        location: Location model instance.

    Returns:
        DetailSection if representations exist, else None.
    """
    representations = location.representations or {}
    if not isinstance(representations, dict) or not representations:
        return None
    fields: dict[str, str] = {}
    for node_name, value in representations.items():
        fields[str(node_name)] = str(value)[:80]
    return DetailSection("Representations", fields)


def _build_node_bindings_section(location: Location) -> DetailSection | None:
    """Build the node bindings section for the detail panel.

    Args:
        location: Location model instance.

    Returns:
        DetailSection if node bindings exist, else None.
    """
    bindings = location.node_bindings or {}
    if not isinstance(bindings, dict) or not bindings:
        return None
    fields: dict[str, str] = {str(role): str(node) for role, node in bindings.items()}
    return DetailSection("Node Bindings", fields)


def _build_reservation_section(location: Location) -> DetailSection | None:
    """Build the reservation section for the detail panel.

    Args:
        location: Location model instance.

    Returns:
        DetailSection if a reservation exists, else None.
    """
    reservation = location.reservation
    if not reservation:
        return None
    fields: dict[str, str] = {}
    owned_by = reservation.owned_by
    if owned_by:
        for key in ("user_id", "experiment_id", "campaign_id"):
            value = getattr(owned_by, key, None)
            if value:
                fields[key.replace("_", " ").title()] = str(value)
    created = reservation.created
    if created:
        fields["Created"] = format_timestamp(created, short=True)
    expires = reservation.expires
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
        self.locations_data: dict[str, Location] = {}
        self.selected_location_id: str | None = None
        self._location_ids: list[str] = []
        self._current_search: str = ""
        self._location_client: LocationClient | None = None

    def _get_location_client(self) -> LocationClient:
        """Get or create the LocationClient instance."""
        if self._location_client is None:
            url = self.get_service_url("location_manager")
            self._location_client = LocationClient(
                location_server_url=url,
            )
        return self._location_client

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
            "Name", "ID", "Template", "Resource", "Transfers", "Reservation"
        )
        table.cursor_type = "row"
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh location data from the location manager."""
        self.locations_data.clear()
        self._location_ids.clear()

        try:
            client = self._get_location_client()
            locations = await client.async_get_locations()
            for location in locations:
                self.locations_data[location.location_id] = location
                self._location_ids.append(location.location_id)
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
                name = loc.location_name or "Unknown"
                loc_id_str = loc_id or "-"
                template = loc.location_template_name or "-"
                resource = loc.resource_id
                resource_display = resource or "None"
                transfers = "Yes" if loc.allow_transfers else "No"
                reservation = "Reserved" if loc.reservation else "-"
                table.add_row(
                    name, loc_id_str, template, resource_display, transfers, reservation
                )

            if not filtered:
                table.add_row("[dim]No locations found[/dim]", "-", "-", "-", "-", "-")

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
        row_id = str(row[1])

        # Find location by matching full ID
        if row_id in self.locations_data:
            self.selected_location_id = row_id
            self._update_detail_panel(self.locations_data[row_id])

    def _update_detail_panel(self, location: Location) -> None:
        """Update the detail panel with location data.

        Args:
            location: Location model instance.
        """
        detail_panel = self.query_one("#location-detail-panel", DetailPanel)
        name = location.location_name or "Unknown"

        sections: list[DetailSection] = [_build_general_section(location)]
        sections.append(_build_resource_section(location))

        representations_section = _build_representations_section(location)
        if representations_section:
            sections.append(representations_section)

        bindings_section = _build_node_bindings_section(location)
        if bindings_section:
            sections.append(bindings_section)

        reservation_section = _build_reservation_section(location)
        if reservation_section:
            sections.append(reservation_section)

        detail_panel.update_content(title=name, sections=sections)

    async def action_refresh(self) -> None:
        """Refresh location data."""
        await self.refresh_data()
        self.notify("Locations refreshed", timeout=2)

    def action_show_transfer_graph(self) -> None:
        """Show the transfer graph screen."""
        client = self._get_location_client()
        self.app.push_screen(TransferGraphScreen(location_client=client))

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "show_transfer_graph": self.action_show_transfer_graph,
        }

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
