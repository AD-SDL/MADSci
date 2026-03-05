"""Node management screen for MADSci TUI.

Provides node discovery, status monitoring, and action display
by querying the Workcell Manager.
"""

from typing import Any, ClassVar

import httpx
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label, Static


class NodeDetailScreen(Screen):
    """Screen showing details for a single node, pushed on top of NodesScreen."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, node_name: str, node_data: dict, **kwargs: Any) -> None:
        """Initialize the detail screen.

        Args:
            node_name: Name of the node.
            node_data: Node data dictionary.
        """
        super().__init__(**kwargs)
        self.node_name = node_name
        self.node_data = node_data

    def compose(self) -> ComposeResult:
        """Compose the detail screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label(f"[bold blue]Node: {self.node_name}[/bold blue]")
            yield Label("")
            yield Static(id="node-detail-content")
            yield Label("")
            yield Label("[dim]'r' refresh | 'Esc' back[/dim]")

    def on_mount(self) -> None:
        """Render the detail content on mount."""
        self._render_details()

    def _render_details(self) -> None:
        """Render the node detail content."""
        content = self.query_one("#node-detail-content", Static)
        data = self.node_data
        node_status = data.get("status") or {}
        info = data.get("info") or {}

        lines = self._build_header_lines(data, node_status)
        lines.extend(self._build_action_lines(info))
        lines.extend(self._build_extra_lines(info, node_status, data))

        content.update("\n".join(lines))

    def _build_header_lines(self, data: dict, node_status: dict) -> list[str]:
        """Build header lines with name, URL, and status."""
        errored = node_status.get("errored", False)
        disconnected = node_status.get("disconnected", False)

        if disconnected:
            status_str = "[red]disconnected[/red]"
        elif errored:
            status_str = "[yellow]errored[/yellow]"
        else:
            status_str = "[green]connected[/green]"

        node_url = str(data.get("node_url", "N/A"))
        return [
            f"[bold]{self.node_name}[/bold]",
            "",
            f"  URL:      {node_url}",
            f"  Status:   {status_str}",
        ]

    @staticmethod
    def _build_action_lines(info: dict) -> list[str]:
        """Build action listing lines."""
        actions = info.get("actions", {})
        if not actions:
            return []
        lines = ["", "  [bold]Actions:[/bold]"]
        for action_name, action_def in actions.items():
            desc = ""
            if isinstance(action_def, dict) and action_def.get("description"):
                desc = f" - {action_def['description']}"
            lines.append(f"    - {action_name}{desc}")
        return lines

    @staticmethod
    def _build_extra_lines(info: dict, node_status: dict, data: dict) -> list[str]:
        """Build admin, errors, and state lines."""
        lines: list[str] = []

        capabilities = info.get("capabilities") or {}
        admin_commands = capabilities.get("admin_commands", [])
        if admin_commands:
            lines.extend(["", f"  [bold]Admin:[/bold] {', '.join(admin_commands)}"])

        errors = node_status.get("errors", [])
        if errors:
            lines.extend(["", "  [bold red]Errors:[/bold red]"])
            for error in errors[:5]:
                err_msg = (
                    error.get("message", str(error))
                    if isinstance(error, dict)
                    else str(error)
                )
                lines.append(f"    [red]{err_msg[:80]}[/red]")

        state = data.get("state")
        if state and isinstance(state, dict):
            lines.extend(["", "  [bold]State:[/bold]"])
            for key, value in state.items():
                lines.append(f"    {key}: {value}")

        return lines

    async def action_refresh(self) -> None:
        """Refresh node data by re-fetching from workcell manager."""
        try:
            workcell_url = self.app.service_urls.get(
                "workcell_manager", "http://localhost:8005/"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{workcell_url.rstrip('/')}/nodes")
                if response.status_code == 200:
                    nodes = response.json()
                    if isinstance(nodes, dict) and self.node_name in nodes:
                        self.node_data = nodes[self.node_name]
                        self._render_details()
                        self.notify("Node refreshed", timeout=2)
                        return
        except Exception:  # noqa: S110
            pass
        self.notify("Could not refresh node data", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the nodes list."""
        self.app.pop_screen()


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

    def compose(self) -> ComposeResult:
        """Compose the nodes screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Node Management[/bold blue]")
            yield Label("")

            with Vertical(id="nodes-section"):
                yield Label("[bold]Nodes[/bold]")
                yield DataTable(id="nodes-table")

            yield Label("")
            yield Label(
                "[dim]Select a node to view details | "
                "Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]",
                id="nodes-footer",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up table and load data."""
        nodes_table = self.query_one("#nodes-table", DataTable)
        nodes_table.add_columns("Status", "Node", "URL", "Actions", "State")
        nodes_table.cursor_type = "row"

        await self.refresh_data()

    def _update_footer(self) -> None:
        """Update the footer label with current auto-refresh state."""
        footer = self.query_one("#nodes-footer", Label)
        state = "on (5s)" if self.auto_refresh_enabled else "off"
        footer.update(
            f"[dim]Select a node to view details | "
            f"Auto-refresh: {state} | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
        )

    async def refresh_data(self) -> None:
        """Refresh node data from workcell manager."""
        table = self.query_one("#nodes-table", DataTable)
        table.clear()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                workcell_url = self.app.service_urls.get(
                    "workcell_manager", "http://localhost:8005/"
                )
                response = await client.get(f"{workcell_url.rstrip('/')}/nodes")
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
        info = node_data.get("info") or {}
        actions = info.get("actions", {})
        action_count = str(len(actions)) if actions else "0"

        table.add_row(icon, name, node_url, action_count, state)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - push detail screen."""
        table = event.data_table
        row_key = event.row_key

        if row_key and table.id == "nodes-table":
            row = table.get_row(row_key)
            node_name = str(row[1])

            if node_name in self.nodes_data:
                self.app.push_screen(
                    NodeDetailScreen(node_name, self.nodes_data[node_name])
                )

    async def action_refresh(self) -> None:
        """Refresh node data."""
        await self.refresh_data()
        self.notify("Nodes refreshed", timeout=2)

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        state = "enabled" if self.auto_refresh_enabled else "disabled"
        self.notify(f"Auto-refresh {state}", timeout=2)
        self._update_footer()

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
