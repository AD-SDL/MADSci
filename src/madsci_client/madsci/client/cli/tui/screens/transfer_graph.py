"""Transfer graph visualization screen for MADSci TUI.

A pushed screen that shows the transfer adjacency list from the
Location Manager as a DataTable.
"""

from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import preserve_cursor
from madsci.client.location_client import LocationClient
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Label


class TransferGraphScreen(Screen):
    """Screen showing the transfer adjacency graph."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "go_back", "Back"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        location_client: LocationClient,
        **kwargs: Any,
    ) -> None:
        """Initialize the transfer graph screen.

        Args:
            location_client: LocationClient instance for fetching data.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self._location_client = location_client

    def compose(self) -> ComposeResult:
        """Compose the transfer graph screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Transfer Graph[/bold blue]")
            yield Label("")
            yield DataTable(id="graph-table")

    async def on_mount(self) -> None:
        """Handle mount - set up table and fetch graph data."""
        table = self.query_one("#graph-table", DataTable)
        table.add_columns("Source", "Connected Targets")
        await self._refresh_graph()

    async def _fetch_location_names(self) -> dict[str, str]:
        """Fetch a mapping of location IDs to names.

        Returns:
            Dict mapping location_id to location_name.
        """
        try:
            locations = await self._location_client.async_get_locations()
            return {loc.location_id: loc.location_name for loc in locations}
        except Exception:
            return {}

    def _resolve_name(self, loc_id: str, names: dict[str, str]) -> str:
        """Resolve a location ID to a display string with name.

        Args:
            loc_id: Location ID.
            names: Mapping of location IDs to names.

        Returns:
            Display string like "name (id)" or just the ID if no name found.
        """
        name = names.get(loc_id)
        if name and name != loc_id:
            return f"{name} ({loc_id})"
        return loc_id

    async def _refresh_graph(self) -> None:
        """Fetch and display the transfer adjacency graph."""
        table = self.query_one("#graph-table", DataTable)
        try:
            graph = await self._location_client.async_get_transfer_graph()
            names = await self._fetch_location_names()
            with preserve_cursor(table):
                table.clear()
                if isinstance(graph, dict):
                    for source, targets in graph.items():
                        source_display = self._resolve_name(source, names)
                        if isinstance(targets, list):
                            targets_str = (
                                ", ".join(self._resolve_name(t, names) for t in targets)
                                if targets
                                else "[dim]none[/dim]"
                            )
                        else:
                            targets_str = self._resolve_name(str(targets), names)
                        table.add_row(source_display, targets_str)
                if not graph:
                    table.add_row("[dim]No transfer edges found[/dim]", "")
        except Exception:
            with preserve_cursor(table):
                table.clear()
                table.add_row("[dim]Error loading graph[/dim]", "")

    def action_go_back(self) -> None:
        """Go back to the locations screen."""
        self.app.pop_screen()

    async def action_refresh(self) -> None:
        """Refresh the transfer graph."""
        await self._refresh_graph()
        self.notify("Transfer graph refreshed", timeout=2)
