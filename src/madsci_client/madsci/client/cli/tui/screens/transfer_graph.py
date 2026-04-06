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

    async def _refresh_graph(self) -> None:
        """Fetch and display the transfer adjacency graph."""
        table = self.query_one("#graph-table", DataTable)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.location_url.rstrip('/')}/transfer/graph"
                )
                if response.status_code == 200:
                    graph = response.json()
                    with preserve_cursor(table):
                        table.clear()
                        if isinstance(graph, dict):
                            for source, targets in graph.items():
                                if isinstance(targets, list):
                                    targets_str = (
                                        ", ".join(str(t) for t in targets)
                                        if targets
                                        else "[dim]none[/dim]"
                                    )
                                else:
                                    targets_str = str(targets)
                                table.add_row(source, targets_str)
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
