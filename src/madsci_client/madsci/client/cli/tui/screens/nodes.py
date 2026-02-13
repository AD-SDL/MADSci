"""Node management screen for MADSci TUI.

Provides node discovery, status monitoring, and action display
by querying the Workcell Manager.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.constants import AUTO_REFRESH_INTERVAL, WORKCELL_MANAGER_URL
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Label, Static


class NodeDetailPanel(Static):
    """Panel showing details for a selected node."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the panel."""
        super().__init__(**kwargs)
        self.selected_node: str | None = None
        self.node_data: dict = {}

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Node Details[/bold]")
        yield Label(
            "[dim]Select a node from the table above[/dim]", id="node-detail-content"
        )

    def update_details(self, name: str, data: dict) -> None:
        """Update the detail display.

        Args:
            name: Node name.
            data: Node data dictionary.
        """
        self.selected_node = name
        self.node_data = data

        content = self.query_one("#node-detail-content", Label)

        # Determine status
        node_status = data.get("status", {})
        errored = node_status.get("errored", False)
        disconnected = node_status.get("disconnected", False)

        if disconnected:
            status_str = "[red]disconnected[/red]"
        elif errored:
            status_str = "[yellow]errored[/yellow]"
        else:
            status_str = "[green]connected[/green]"

        # Node info
        info = data.get("info", {})
        node_url = str(data.get("node_url", "N/A"))

        lines = [
            f"[bold]{name}[/bold]",
            "",
            f"  URL:      {node_url}",
            f"  Status:   {status_str}",
        ]

        # Available actions
        available_actions = info.get("available_actions", [])
        if available_actions:
            lines.append("")
            lines.append("  [bold]Actions:[/bold]")
            for action in available_actions:
                lines.append(f"    - {action}")

        # Admin capabilities
        capabilities = info.get("capabilities", {})
        admin_commands = capabilities.get("admin_commands", [])
        if admin_commands:
            lines.append("")
            lines.append(f"  [bold]Admin:[/bold] {', '.join(admin_commands)}")

        # Errors
        errors = node_status.get("errors", [])
        if errors:
            lines.append("")
            lines.append("  [bold red]Errors:[/bold red]")
            for error in errors[:3]:
                err_msg = (
                    error.get("message", str(error))
                    if isinstance(error, dict)
                    else str(error)
                )
                lines.append(f"    [red]{err_msg[:60]}[/red]")

        content.update("\n".join(lines))


class NodesScreen(Screen):
    """Screen showing node management and monitoring."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.nodes_data: dict[str, dict] = {}
        self.auto_refresh_enabled = True
        self._auto_refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        """Compose the nodes screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Node Management[/bold blue]")
            yield Label("")

            with Vertical(id="nodes-section"):
                yield Label("[bold]Nodes[/bold]")
                yield DataTable(id="nodes-table")

            yield Label("")
            yield NodeDetailPanel(id="node-detail-panel")

            yield Label("")
            yield Label(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]",
                id="nodes-footer",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        nodes_table = self.query_one("#nodes-table", DataTable)
        nodes_table.add_columns("Status", "Node", "URL", "Actions", "State")
        nodes_table.cursor_type = "row"

        await self.refresh_data()
        self._start_auto_refresh()

    def _start_auto_refresh(self) -> None:
        """Start the auto-refresh timer."""
        if self._auto_refresh_timer is None:
            self._auto_refresh_timer = self.set_interval(
                AUTO_REFRESH_INTERVAL, self._auto_refresh, name="nodes-auto-refresh"
            )

    def _stop_auto_refresh(self) -> None:
        """Stop the auto-refresh timer."""
        if self._auto_refresh_timer is not None:
            self._auto_refresh_timer.stop()
            self._auto_refresh_timer = None

    async def _auto_refresh(self) -> None:
        """Perform an auto-refresh cycle."""
        if self.auto_refresh_enabled:
            await self.refresh_data()

    def _update_footer(self) -> None:
        """Update the footer label with current auto-refresh state."""
        footer = self.query_one("#nodes-footer", Label)
        if self.auto_refresh_enabled:
            footer.update(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )
        else:
            footer.update(
                "[dim]Auto-refresh: off | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )

    async def refresh_data(self) -> None:
        """Refresh node data from workcell manager."""
        table = self.query_one("#nodes-table", DataTable)
        table.clear()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{WORKCELL_MANAGER_URL.rstrip('/')}/nodes")
                if response.status_code == 200:
                    nodes = response.json()
                    if isinstance(nodes, dict):
                        self.nodes_data = nodes
                        for name, node_data in nodes.items():
                            self._add_node_row(table, name, node_data)
                    return
        except Exception:  # noqa: S110
            pass

        # If we can't reach the workcell manager, show a message
        if not self.nodes_data:
            table.add_row(
                "[dim]\u25cb[/dim]",
                "[dim]No nodes available[/dim]",
                "[dim]Workcell Manager not reachable[/dim]",
                "-",
                "[dim]unknown[/dim]",
            )

    def _add_node_row(self, table: DataTable, name: str, node_data: dict) -> None:
        """Add a node row to the table.

        Args:
            table: The DataTable to add to.
            name: Node name.
            node_data: Node data dictionary.
        """
        node_status = node_data.get("status", {})
        errored = node_status.get("errored", False)
        disconnected = node_status.get("disconnected", False)

        if disconnected:
            icon = "[red]\u25cb[/red]"
            state = "[red]disconnected[/red]"
        elif errored:
            icon = "[yellow]\u25cf[/yellow]"
            state = "[yellow]errored[/yellow]"
        else:
            icon = "[green]\u25cf[/green]"
            state = "[green]connected[/green]"

        node_url = str(node_data.get("node_url", "N/A"))
        info = node_data.get("info", {})
        actions = info.get("available_actions", [])
        action_count = str(len(actions)) if actions else "0"

        table.add_row(icon, name, node_url, action_count, state)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        table = event.data_table
        row_key = event.row_key

        if row_key and table.id == "nodes-table":
            row = table.get_row(row_key)
            node_name = str(row[1])

            if node_name in self.nodes_data:
                detail_panel = self.query_one("#node-detail-panel", NodeDetailPanel)
                detail_panel.update_details(node_name, self.nodes_data[node_name])

    async def action_refresh(self) -> None:
        """Refresh node data."""
        await self.refresh_data()
        self.notify("Nodes refreshed", timeout=2)

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        if self.auto_refresh_enabled:
            self._start_auto_refresh()
            self.notify("Auto-refresh enabled", timeout=2)
        else:
            self._stop_auto_refresh()
            self.notify("Auto-refresh disabled", timeout=2)
        self._update_footer()

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self._stop_auto_refresh()
        self.app.switch_screen("dashboard")
