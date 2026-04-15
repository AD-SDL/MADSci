"""Node management screen for MADSci TUI.

Provides node discovery, status monitoring, admin command actions,
enhanced detail display, and action execution by querying the
Workcell Manager and communicating with nodes directly.
"""

from __future__ import annotations

import logging
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
)
from madsci.client.cli.utils.formatting import format_status_colored, format_status_icon
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.action_types import ActionDefinition
from madsci.common.types.admin_command_types import AdminCommands
from madsci.common.types.node_types import Node, NodeInfo, NodeStatus
from pydantic import AnyUrl
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label

logger = logging.getLogger(__name__)


def _get_node_status_name(node_status: NodeStatus) -> str:
    """Derive a status name string from a NodeStatus model.

    Args:
        node_status: NodeStatus model instance.

    Returns:
        Status name: "disconnected", "errored", or "connected".
    """
    if node_status.disconnected:
        return "disconnected"
    if node_status.errored:
        return "errored"
    return "connected"


def _format_bool_indicator(value: bool) -> str:
    """Format a boolean flag as a colored Yes/No indicator.

    Args:
        value: Boolean flag value.

    Returns:
        Rich markup string with colored indicator.
    """
    if value:
        return "[red]Yes[/red]"
    return "[green]No[/green]"


def _build_general_section(
    node: Node, info: NodeInfo | None, node_status: NodeStatus | None
) -> DetailSection:
    """Build the general info section for the node detail panel.

    Args:
        node: Node model instance.
        info: NodeInfo model instance, or None.
        node_status: NodeStatus model instance, or None.

    Returns:
        DetailSection with general node information.
    """
    status_name = _get_node_status_name(node_status) if node_status else "unknown"
    general_fields: dict[str, str] = {
        "URL": str(node.node_url),
        "Status": format_status_colored(status_name),
    }
    if info is not None:
        for attr, label in (
            ("node_id", "Node ID"),
            ("module_name", "Module"),
            ("module_version", "Version"),
            ("node_type", "Type"),
        ):
            value = getattr(info, attr, None)
            if value is not None:
                general_fields[label] = str(value)
    return DetailSection("General", general_fields)


def _build_status_flags_section(node_status: NodeStatus) -> DetailSection:
    """Build the status flags section for the node detail panel.

    Args:
        node_status: NodeStatus model instance.

    Returns:
        DetailSection with all status flag indicators.
    """
    status_fields: dict[str, str] = {}
    description = node_status.description
    if description:
        status_fields["Description"] = str(description)
    ready = node_status.ready
    # Ready is inverted: True = good (green), False = bad (red)
    status_fields["Ready"] = "[green]Yes[/green]" if ready else "[red]No[/red]"
    for flag_name in (
        "busy",
        "paused",
        "locked",
        "stopped",
        "errored",
        "disconnected",
        "initializing",
    ):
        value = getattr(node_status, flag_name, False)
        status_fields[flag_name.capitalize()] = _format_bool_indicator(value)
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


def _build_errors_section(node_status: NodeStatus) -> DetailSection | None:
    """Build the errors section for the node detail panel.

    Args:
        node_status: NodeStatus model instance.

    Returns:
        DetailSection with error information, or None if no errors.
    """
    if not node_status.errors:
        return None
    error_fields: dict[str, str] = {}
    for i, error in enumerate(node_status.errors[:5]):
        err_msg = error.message or str(error)
        error_fields[f"Error {i + 1}"] = f"[red]{err_msg[:80]}[/red]"
    return DetailSection("Errors", error_fields)


def _build_config_section(info: NodeInfo) -> DetailSection | None:
    """Build the configuration section for the node detail panel.

    Args:
        info: NodeInfo model instance.

    Returns:
        DetailSection with config information, or None if no config.
    """
    config = info.config
    if config is None or not isinstance(config, dict):
        return None
    config_fields = {str(k): str(v)[:100] for k, v in list(config.items())[:20]}
    return DetailSection("Configuration", config_fields)


def _build_actions_section(
    actions: dict[str, ActionDefinition | Any],
) -> DetailSection:
    """Build the actions section with parameter details.

    Args:
        actions: Dict mapping action names to ActionDefinition models or dicts.

    Returns:
        DetailSection with action descriptions and parameter info.
    """
    action_fields: dict[str, str] = {}
    for action_name, action_def in actions.items():
        if isinstance(action_def, ActionDefinition):
            parts: list[str] = []
            if action_def.description:
                parts.append(action_def.description)
            param_names = _extract_param_names(action_def.args)
            if param_names:
                parts.append(f"[dim]params: {', '.join(param_names)}[/dim]")
            action_fields[action_name] = " | ".join(parts) if parts else "-"
        elif isinstance(action_def, dict):
            desc = action_def.get("description", "")
            args = action_def.get("args", {})
            parts = []
            if desc:
                parts.append(desc)
            param_names = _extract_param_names(args)
            if param_names:
                parts.append(f"[dim]params: {', '.join(param_names)}[/dim]")
            action_fields[action_name] = " | ".join(parts) if parts else "-"
        else:
            action_fields[action_name] = "-"
    return DetailSection("Actions", action_fields)


class NodeDetailScreen(ServiceURLMixin, Screen):
    """Screen showing details for a single node, pushed on top of NodesScreen."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, node_name: str, node_data: Node, **kwargs: Any) -> None:
        """Initialize the detail screen.

        Args:
            node_name: Name of the node.
            node_data: Node model instance.
        """
        super().__init__(**kwargs)
        self.node_name = node_name
        self.node_data = node_data
        self._workcell_client: WorkcellClient | None = None

    def _get_workcell_client(self) -> WorkcellClient:
        """Get or create the WorkcellClient instance."""
        if self._workcell_client is None:
            workcell_url = self.get_service_url("workcell_manager")
            self._workcell_client = WorkcellClient(
                workcell_server_url=workcell_url,
            )
        return self._workcell_client

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
        node = self.node_data
        node_status = node.status
        info = node.info

        sections: list[DetailSection] = [
            _build_general_section(node, info, node_status),
        ]
        if node_status is not None:
            sections.append(_build_status_flags_section(node_status))
            self._append_running_actions(sections, node_status)

        self._append_info_sections(sections, info)

        if node_status is not None:
            errors_section = _build_errors_section(node_status)
            if errors_section is not None:
                sections.append(errors_section)

        # State
        if node.state and isinstance(node.state, dict):
            sections.append(
                DetailSection("State", {k: str(v) for k, v in node.state.items()})
            )

        panel.update_content(title=self.node_name, sections=sections)

    @staticmethod
    def _append_running_actions(
        sections: list[DetailSection], node_status: NodeStatus
    ) -> None:
        """Append running actions section if any exist."""
        if node_status.running_actions:
            running_fields = {
                f"Action {i + 1}": str(aid)
                for i, aid in enumerate(list(node_status.running_actions)[:10])
            }
            sections.append(DetailSection("Running Actions", running_fields))

    @staticmethod
    def _append_info_sections(
        sections: list[DetailSection], info: NodeInfo | None
    ) -> None:
        """Append action definitions, admin commands, and config sections."""
        if info is None:
            return

        if info.actions:
            sections.append(_build_actions_section(info.actions))

        if info.capabilities is not None and info.capabilities.admin_commands:
            cmd_str = ", ".join(
                str(c) for c in sorted(info.capabilities.admin_commands)
            )
            sections.append(DetailSection("Admin Commands", {"Supported": cmd_str}))

        config_section = _build_config_section(info)
        if config_section is not None:
            sections.append(config_section)

    async def action_refresh(self) -> None:
        """Refresh node data by re-fetching from workcell manager."""
        try:
            client = self._get_workcell_client()
            node = await client.async_get_node(self.node_name)
            self.node_data = node
            self._render_details()
            self.notify("Node refreshed", timeout=2)
            return
        except Exception as exc:
            logger.debug("Refresh failed: %s", exc)
        self.notify("Could not refresh node data", timeout=2)

    async def on_unmount(self) -> None:
        """Clean up client connections when screen is unmounted."""
        for attr_name in list(vars(self)):
            if attr_name.endswith("_client"):
                client = getattr(self, attr_name, None)
                if client is not None and hasattr(client, "aclose"):
                    await client.aclose()
                elif client is not None and hasattr(client, "close"):
                    client.close()

    def action_go_back(self) -> None:
        """Go back to the nodes list."""
        self.app.pop_screen()


class NodesScreen(ActionBarMixin, AutoRefreshMixin, ServiceURLMixin, Screen):
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
        self.nodes_data: dict[str, Node] = {}
        self._workcell_client: WorkcellClient | None = None

    def _get_workcell_client(self) -> WorkcellClient:
        """Get or create the WorkcellClient instance."""
        if self._workcell_client is None:
            url = self.get_service_url("workcell_manager")
            self._workcell_client = WorkcellClient(
                workcell_server_url=url,
            )
        return self._workcell_client

    def compose(self) -> ComposeResult:
        """Compose the nodes screen layout."""
        with VerticalScroll(id="main-content"):
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

    def watch_auto_refresh_enabled(self, _value: bool) -> None:
        """React to auto_refresh_enabled changes by updating the footer."""
        self._update_footer()

    async def refresh_data(self) -> None:
        """Refresh node data from workcell manager."""
        table = self.query_one("#nodes-table", DataTable)

        try:
            client = self._get_workcell_client()
            nodes = await client.async_get_nodes()
            self.nodes_data = nodes
            with preserve_cursor(table):
                table.clear()
                for name, node in nodes.items():
                    self._add_node_row(table, name, node)
            return
        except Exception as exc:
            logger.debug("Refresh failed: %s", exc)
            self.notify("Failed to reach Workcell Manager", timeout=3)

        # If we can't reach the workcell manager, show a message
        if not self.nodes_data:
            with preserve_cursor(table):
                table.clear()
                table.add_row(
                    format_status_icon("unknown"),
                    "[dim]No nodes available[/dim]",
                    "[dim]Workcell Manager not reachable[/dim]",
                    "-",
                    "[dim]unknown[/dim]",
                )

    def _add_node_row(self, table: DataTable, name: str, node: Node) -> None:
        """Add a node row to the table.

        Args:
            table: The DataTable to add to.
            name: Node name.
            node: Node model instance.
        """
        node_status = node.status or NodeStatus()
        status_name = _get_node_status_name(node_status)

        icon = format_status_icon(status_name)
        state = format_status_colored(status_name)

        node_url = str(node.node_url)
        info = node.info
        actions = info.actions if info is not None else {}
        action_count = str(len(actions)) if actions else "0"

        table.add_row(icon, name, node_url, action_count, state)

    def _get_selected_node(self) -> tuple[str, Node] | None:
        """Get the currently selected node name and data.

        Returns:
            Tuple of (node_name, Node) or None if no valid selection.
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

        node_name, node = selected
        node_url = str(node.node_url)
        if not node_url:
            self.notify(f"No URL for node {node_name}", timeout=2)
            return

        node_client = RestNodeClient(url=AnyUrl(node_url))
        try:
            await node_client.async_send_admin_command(AdminCommands(command))
            self.notify(
                f"Admin command '{command}' sent to {node_name}",
                timeout=2,
            )
            await self.refresh_data()
        except Exception as e:
            logger.debug("Admin command error", exc_info=True)
            self.notify(f"Error sending '{command}' to {node_name}: {e}", timeout=3)
        finally:
            await node_client.aclose()

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

        _node_name, node = selected
        node_status = node.status or NodeStatus()
        is_locked = node_status.locked
        command = "unlock" if is_locked else "lock"
        await self._send_admin_command(command)

    async def action_execute_action(self) -> None:
        """Open the action executor screen for the selected node."""
        selected = self._get_selected_node()
        if selected is None:
            self.notify("No node selected", timeout=2)
            return

        node_name, node = selected
        node_url = str(node.node_url)
        if not node_url:
            self.notify(f"No URL for node {node_name}", timeout=2)
            return

        info = node.info
        actions = info.actions if info is not None else {}
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

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "toggle_auto_refresh": self.action_toggle_auto_refresh,
            "pause": self.action_pause_node,
            "resume": self.action_resume_node,
            "reset": self.action_reset_node,
            "toggle_lock": self.action_toggle_lock_node,
            "execute": self.action_execute_action,
        }

    async def on_unmount(self) -> None:
        """Clean up client connections when screen is unmounted."""
        for attr_name in list(vars(self)):
            if attr_name.endswith("_client"):
                client = getattr(self, attr_name, None)
                if client is not None and hasattr(client, "aclose"):
                    await client.aclose()
                elif client is not None and hasattr(client, "close"):
                    client.close()

    async def action_refresh(self) -> None:
        """Refresh node data."""
        await self.refresh_data()
        self.notify("Nodes refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
