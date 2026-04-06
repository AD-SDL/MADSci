"""Node management screen for MADSci TUI.

Provides node discovery, status monitoring, and action display
by querying the Workcell Manager.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored, format_status_icon
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


def _get_node_status_name(node_status: dict) -> str:
    """Derive a status name string from node status dict.

    Args:
        node_status: Node status dictionary with errored/disconnected flags.

    Returns:
        Status name: "disconnected", "errored", or "connected".
    """
    if node_status.get("disconnected", False):
        return "disconnected"
    if node_status.get("errored", False):
        return "errored"
    return "connected"


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
            yield DetailPanel(
                placeholder="Loading node details...",
                id="node-detail-panel",
            )
            yield Label("")
            yield Label("[dim]'r' refresh | 'Esc' back[/dim]")

    def on_mount(self) -> None:
        """Render the detail content on mount."""
        self._render_details()

    def _render_details(self) -> None:
        """Render the node detail content using DetailPanel."""
        panel = self.query_one("#node-detail-panel", DetailPanel)
        data = self.node_data
        node_status = data.get("status") or {}
        info = data.get("info") or {}

        sections: list[DetailSection] = []

        # General section
        status_name = _get_node_status_name(node_status)
        general_fields: dict[str, str] = {
            "URL": str(data.get("node_url", "N/A")),
            "Status": format_status_colored(status_name),
        }
        sections.append(DetailSection("General", general_fields))

        # Actions section
        actions = info.get("actions", {})
        if actions:
            action_fields: dict[str, str] = {}
            for action_name, action_def in actions.items():
                desc = ""
                if isinstance(action_def, dict) and action_def.get("description"):
                    desc = action_def["description"]
                action_fields[action_name] = desc or "-"
            sections.append(DetailSection("Actions", action_fields))

        # Admin commands section
        capabilities = info.get("capabilities") or {}
        admin_commands = capabilities.get("admin_commands", [])
        if admin_commands:
            sections.append(
                DetailSection("Admin", {"Commands": ", ".join(admin_commands)})
            )

        # Errors section
        errors = node_status.get("errors", [])
        if errors:
            error_fields: dict[str, str] = {}
            for i, error in enumerate(errors[:5]):
                err_msg = (
                    error.get("message", str(error))
                    if isinstance(error, dict)
                    else str(error)
                )
                error_fields[f"Error {i + 1}"] = f"[red]{err_msg[:80]}[/red]"
            sections.append(DetailSection("Errors", error_fields))

        # State section
        state = data.get("state")
        if state and isinstance(state, dict):
            state_fields = {k: str(v) for k, v in state.items()}
            sections.append(DetailSection("State", state_fields))

        panel.update_content(
            title=self.node_name,
            sections=sections,
        )

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


class NodesScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
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
            workcell_url = self.get_service_url("workcell_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
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
                format_status_icon("unknown"),
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
        status_name = _get_node_status_name(node_status)

        icon = format_status_icon(status_name)
        state = format_status_colored(status_name)

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

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
