"""Transfer graph visualization screen for MADSci TUI.

A pushed screen that shows the transfer adjacency list from the
Location Manager as a DataTable.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import preserve_cursor
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
        location_url: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the transfer graph screen.

        Args:
            location_url: Base URL of the location manager.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self.location_url = location_url

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

    async def _fetch_location_names(self, client: httpx.AsyncClient) -> dict[str, str]:
        """Fetch a mapping of location IDs to names.

        Args:
            client: httpx async client to use.

        Returns:
            Dict mapping location_id to location_name.
        """
        try:
            response = await client.get(f"{self.location_url.rstrip('/')}/locations")
            if response.status_code == 200:
                data = response.json()
                names: dict[str, str] = {}
                if isinstance(data, dict):
                    for loc_id, loc_data in data.items():
                        if isinstance(loc_data, dict):
                            names[loc_id] = loc_data.get("location_name", loc_id)
                        else:
                            names[loc_id] = str(loc_id)
                elif isinstance(data, list):
                    for loc in data:
                        lid = loc.get("location_id", "")
                        if lid:
                            names[lid] = loc.get("location_name", lid)
                return names
        except Exception:  # noqa: S110
            pass
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
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Fetch both graph and location names
                response = await client.get(
                    f"{self.location_url.rstrip('/')}/transfer/graph"
                )
                if response.status_code == 200:
                    graph = response.json()
                    names = await self._fetch_location_names(client)
                    with preserve_cursor(table):
                        table.clear()
                        if isinstance(graph, dict):
                            for source, targets in graph.items():
                                source_display = self._resolve_name(source, names)
                                if isinstance(targets, list):
                                    targets_str = (
                                        ", ".join(
                                            self._resolve_name(t, names)
                                            for t in targets
                                        )
                                        if targets
                                        else "[dim]none[/dim]"
                                    )
                                else:
                                    targets_str = self._resolve_name(
                                        str(targets), names
                                    )
                                table.add_row(source_display, targets_str)
                        if not graph:
                            table.add_row("[dim]No transfer edges found[/dim]", "")
                else:
                    with preserve_cursor(table):
                        table.clear()
                        table.add_row(
                            f"[dim]Error: HTTP {response.status_code}[/dim]", ""
                        )
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
