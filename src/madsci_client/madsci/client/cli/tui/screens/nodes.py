"""Node management screen for MADSci TUI.

Provides node discovery, status monitoring, admin command actions,
enhanced detail display, and action execution by querying the
Workcell Manager and communicating with nodes directly.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailPanel,
    DetailSection,
)
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


def _format_bool_indicator(value: bool, label: str) -> str:
    """Format a boolean flag as a colored indicator.

    Args:
        value: Boolean flag value.
        label: Display label for the flag.

    Returns:
        Rich markup string with colored indicator.
    """
    if value:
        return f"[red]{label}[/red]"
    return f"[green]{label}[/green]"


def _build_general_section(data: dict, info: dict, node_status: dict) -> DetailSection:
    """Build the general info section for the node detail panel.

    Args:
        data: Full node data dictionary.
        info: Node info dictionary.
        node_status: Node status dictionary.

    Returns:
        DetailSection with general node information.
    """
    status_name = _get_node_status_name(node_status)
    general_fields: dict[str, str] = {
        "URL": str(data.get("node_url", "N/A")),
        "Status": format_status_colored(status_name),
    }
    for key, label in (
        ("node_id", "Node ID"),
        ("module_name", "Module"),
        ("module_version", "Version"),
        ("node_type", "Type"),
    ):
        if info.get(key):
            general_fields[label] = str(info[key])
    return DetailSection("General", general_fields)


def _build_status_flags_section(node_status: dict) -> DetailSection:
    """Build the status flags section for the node detail panel.

    Args:
        node_status: Node status dictionary.

    Returns:
        DetailSection with all status flag indicators.
    """
    status_fields: dict[str, str] = {}
    ready = node_status.get("ready", not node_status.get("errored", False))
    status_fields["Ready"] = _format_bool_indicator(not ready, "ready")
    for flag_name in (
        "busy",
        "paused",
        "locked",
        "stopped",
        "errored",
        "disconnected",
        "initializing",
    ):
        value = node_status.get(flag_name, False)
        status_fields[flag_name.capitalize()] = _format_bool_indicator(value, flag_name)
    return DetailSection("Status Flags", status_fields)


def _extract_param_names(args: Any) -> list[str]:
    """Extract parameter names from an action's args definition.

    Args:
        args: Action arguments -- may be a dict, list, or other type.

    Returns:
        List of parameter name strings.
    """
    if isinstance(args, dict):
        return list(args.keys())
    if isinstance(args, list):
        return [
            a.get("name", f"arg{i}") if isinstance(a, dict) else str(a)
            for i, a in enumerate(args)
        ]
    return []


def _build_actions_section(actions: dict) -> DetailSection:
    """Build the actions section with parameter details.

    Args:
        actions: Dict mapping action names to action definitions.

    Returns:
        DetailSection with action descriptions and parameter info.
    """
    action_fields: dict[str, str] = {}
    for action_name, action_def in actions.items():
        if not isinstance(action_def, dict):
            action_fields[action_name] = "-"
            continue
        desc = action_def.get("description", "")
        args = action_def.get("args", {})
        parts: list[str] = []
        if desc:
            parts.append(desc)
        param_names = _extract_param_names(args)
        if param_names:
            parts.append(f"[dim]params: {', '.join(param_names)}[/dim]")
        action_fields[action_name] = " | ".join(parts) if parts else "-"
    return DetailSection("Actions", action_fields)


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

        sections: list[DetailSection] = [
            _build_general_section(data, info, node_status),
            _build_status_flags_section(node_status),
        ]

        # Running actions
        running_actions = node_status.get("running_actions", [])
        if running_actions:
            running_fields = {
                f"Action {i + 1}": str(aid)
                for i, aid in enumerate(list(running_actions)[:10])
            }
            sections.append(DetailSection("Running Actions", running_fields))

        # Action definitions with parameter details
        actions = info.get("actions", {})
        if actions:
            sections.append(_build_actions_section(actions))

        # Admin commands
        capabilities = info.get("capabilities") or {}
        admin_commands = capabilities.get("admin_commands", [])
        if admin_commands:
            cmd_str = ", ".join(str(c) for c in admin_commands)
            sections.append(DetailSection("Admin Commands", {"Supported": cmd_str}))

        # Configuration
        config = info.get("config")
        if config and isinstance(config, dict):
            config_fields = {str(k): str(v)[:100] for k, v in list(config.items())[:20]}
            sections.append(DetailSection("Configuration", config_fields))

        # Errors
        errors = node_status.get("errors", [])
        if errors:
            error_fields = {}
            for i, error in enumerate(errors[:5]):
                err_msg = (
                    error.get("message", str(error))
                    if isinstance(error, dict)
                    else str(error)
                )
                error_fields[f"Error {i + 1}"] = f"[red]{err_msg[:80]}[/red]"
            sections.append(DetailSection("Errors", error_fields))

        # State
        state = data.get("state")
        if state and isinstance(state, dict):
            sections.append(
                DetailSection("State", {k: str(v) for k, v in state.items()})
            )

        panel.update_content(title=self.node_name, sections=sections)

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
        ("p", "pause_node", "Pause"),
        ("u", "resume_node", "Resume"),
        ("x", "reset_node", "Reset"),
        ("k", "toggle_lock_node", "Lock/Unlock"),
        ("e", "execute_action", "Execute Action"),
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
            yield ActionBar(
                actions=[
                    ActionDef("a", "Auto-refresh", "toggle_auto_refresh"),
                    ActionDef("p", "Pause", "pause", variant="warning"),
                    ActionDef("u", "Resume", "resume", variant="success"),
                    ActionDef("x", "Reset", "reset", variant="warning"),
                    ActionDef("k", "Lock/Unlock", "toggle_lock", variant="warning"),
                    ActionDef("e", "Execute", "execute", variant="primary"),
                ],
                id="nodes-action-bar",
            )
            yield Label("")
            yield Label(
                "[dim]Select a node and use actions above | "
                "Auto-refresh: on (5s) | 'r' manual | 'Esc' back[/dim]",
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
            f"[dim]Select a node and use actions above | "
            f"Auto-refresh: {state} | 'r' manual | 'Esc' back[/dim]"
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

    def _get_selected_node(self) -> tuple[str, dict] | None:
        """Get the currently selected node name and data.

        Returns:
            Tuple of (node_name, node_data) or None if no valid selection.
        """
        table = self.query_one("#nodes-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return None

        if row_key is None:
            return None

        try:
            row = table.get_row(row_key)
        except Exception:
            return None

        node_name = str(row[1])
        if node_name not in self.nodes_data:
            return None

        return node_name, self.nodes_data[node_name]

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

    async def _send_admin_command(self, command: str) -> None:
        """Send an admin command to the selected node.

        Args:
            command: Admin command to send (pause, resume, reset, lock, unlock).
        """
        selected = self._get_selected_node()
        if selected is None:
            self.notify("No node selected", timeout=2)
            return

        node_name, node_data = selected
        node_url = str(node_data.get("node_url", ""))
        if not node_url:
            self.notify(f"No URL for node {node_name}", timeout=2)
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{node_url.rstrip('/')}/admin/{command}")
                if response.status_code == 200:
                    self.notify(
                        f"Admin command '{command}' sent to {node_name}",
                        timeout=2,
                    )
                    await self.refresh_data()
                else:
                    self.notify(
                        f"Failed to send '{command}' to {node_name}: "
                        f"HTTP {response.status_code}",
                        timeout=3,
                    )
        except Exception as e:
            self.notify(f"Error sending '{command}' to {node_name}: {e}", timeout=3)

    async def action_pause_node(self) -> None:
        """Pause the selected node."""
        await self._send_admin_command("pause")

    async def action_resume_node(self) -> None:
        """Resume the selected node."""
        await self._send_admin_command("resume")

    async def action_reset_node(self) -> None:
        """Reset the selected node (clear errors)."""
        await self._send_admin_command("reset")

    async def action_toggle_lock_node(self) -> None:
        """Toggle lock/unlock on the selected node."""
        selected = self._get_selected_node()
        if selected is None:
            self.notify("No node selected", timeout=2)
            return

        _node_name, node_data = selected
        node_status = node_data.get("status") or {}
        is_locked = node_status.get("locked", False)
        command = "unlock" if is_locked else "lock"
        await self._send_admin_command(command)

    async def action_execute_action(self) -> None:
        """Open the action executor screen for the selected node."""
        selected = self._get_selected_node()
        if selected is None:
            self.notify("No node selected", timeout=2)
            return

        node_name, node_data = selected
        node_url = str(node_data.get("node_url", ""))
        if not node_url:
            self.notify(f"No URL for node {node_name}", timeout=2)
            return

        info = node_data.get("info") or {}
        actions = info.get("actions", {})
        if not actions:
            self.notify(f"Node {node_name} has no actions", timeout=2)
            return

        from madsci.client.cli.tui.screens.action_executor import (
            ActionExecutorScreen,
        )

        self.app.push_screen(
            ActionExecutorScreen(
                node_name=node_name,
                node_url=node_url,
                actions=actions,
            )
        )

    async def action_refresh(self) -> None:
        """Refresh node data."""
        await self.refresh_data()
        self.notify("Nodes refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
