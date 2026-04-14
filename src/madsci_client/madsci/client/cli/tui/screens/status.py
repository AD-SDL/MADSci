"""Status screen for MADSci TUI.

Provides detailed service status with health information.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import (
    AutoRefreshMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored, format_status_icon
from madsci.client.cli.utils.service_health import check_all_services_async
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.node_types import NodeStatus
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label

logger = logging.getLogger(__name__)

INFRASTRUCTURE_SERVICES = {
    "ferretdb": ("localhost", 27017),
    "postgresql": ("localhost", 5432),
    "valkey": ("localhost", 6379),
    "seaweedfs": ("localhost", 8333),
}


class StatusScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen showing detailed service status."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.service_status: dict[str, dict] = {}
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
        """Compose the status screen layout."""
        with VerticalScroll(id="main-content"):
            yield Label("[bold blue]Service Status[/bold blue]")
            yield Label("")

            with Vertical(id="managers-section"):
                yield Label("[bold]Managers[/bold]")
                yield DataTable(id="managers-table")

            yield Label("")

            with Vertical(id="infra-section"):
                yield Label("[bold]Infrastructure[/bold]")
                yield DataTable(id="infra-table")

            yield Label("")

            with Vertical(id="nodes-section"):
                yield Label("[bold]Nodes[/bold]")
                yield DataTable(id="nodes-table")

            yield Label("")
            yield DetailPanel(
                placeholder="Select a service from the table above",
                id="detail-panel",
            )

            yield Label("")
            yield Label(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]",
                id="status-footer",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up tables and load data."""
        managers_table = self.query_one("#managers-table", DataTable)
        managers_table.add_columns("Status", "Service", "URL", "State", "Version")
        managers_table.cursor_type = "row"

        infra_table = self.query_one("#infra-table", DataTable)
        infra_table.add_columns("Status", "Service", "Host", "Port", "State")
        infra_table.cursor_type = "row"

        nodes_table = self.query_one("#nodes-table", DataTable)
        nodes_table.add_columns("Status", "Node", "URL", "State")
        nodes_table.cursor_type = "row"

        await self.refresh_data()

    def _update_footer(self) -> None:
        """Update the footer label with current auto-refresh state."""
        footer = self.query_one("#status-footer", Label)
        if self.auto_refresh_enabled:
            footer.update(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )
        else:
            footer.update(
                "[dim]Auto-refresh: off | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )

    def watch_auto_refresh_enabled(self, _value: bool) -> None:
        """Update the footer when auto-refresh is toggled."""
        self._update_footer()

    async def refresh_data(self) -> None:
        """Refresh all service statuses concurrently."""
        await asyncio.gather(
            self._refresh_managers(),
            self._refresh_infrastructure(),
            self._refresh_nodes(),
        )

    async def _refresh_managers(self) -> None:
        """Refresh manager service statuses."""
        table = self.query_one("#managers-table", DataTable)

        service_urls = getattr(self.app, "service_urls", {})
        results = await check_all_services_async(service_urls)

        with preserve_cursor(table):
            table.clear()

            for name, result in results.items():
                status = (
                    "healthy"
                    if result.is_available
                    else (
                        "unhealthy"
                        if result.error and "HTTP" in (result.error or "")
                        else "offline"
                    )
                )
                self.service_status[name] = {
                    "status": status,
                    "url": result.url,
                    "version": result.version,
                    "error": result.error,
                }

                icon = format_status_icon(status)
                state = format_status_colored(status)

                table.add_row(
                    icon,
                    name,
                    result.url,
                    state,
                    result.version or "-",
                )

    async def _refresh_infrastructure(self) -> None:
        """Refresh infrastructure service statuses."""
        table = self.query_one("#infra-table", DataTable)

        infra_rows: list[tuple[str, str, str, str, str]] = []
        for name, (host, port) in INFRASTRUCTURE_SERVICES.items():
            # Check if port is reachable
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=1.0
                )
                writer.close()
                await writer.wait_closed()
                status = "connected"
            except (OSError, asyncio.TimeoutError):
                status = "disconnected"

            icon = format_status_icon(status)
            infra_rows.append((icon, name, host, str(port), status))

        with preserve_cursor(table):
            table.clear()
            for row in infra_rows:
                table.add_row(*row)

    async def _refresh_nodes(self) -> None:
        """Refresh node status from the workcell manager."""
        table = self.query_one("#nodes-table", DataTable)
        try:
            client = self._get_workcell_client()
            nodes = await client.async_get_nodes()
            with preserve_cursor(table):
                table.clear()
                for name, node in nodes.items():
                    node_status = node.status or NodeStatus()
                    if node_status.disconnected:
                        status_name = "disconnected"
                    elif node_status.errored:
                        status_name = "errored"
                    else:
                        status_name = "connected"
                    icon = format_status_icon(status_name)
                    url = str(node.node_url)
                    state = format_status_colored(status_name)
                    table.add_row(icon, name, url, state)
                if table.row_count == 0:
                    table.add_row(
                        format_status_icon("unknown"),
                        "[dim]No nodes[/dim]",
                        "-",
                        "-",
                    )
            return
        except Exception as exc:
            logger.debug("Refresh failed: %s", exc)
        with preserve_cursor(table):
            table.clear()
            table.add_row(
                format_status_icon("unknown"),
                "[dim]Workcell Manager not reachable[/dim]",
                "-",
                "-",
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        # Get the service name from the selected row
        table = event.data_table
        row_key = event.row_key

        if row_key and table.id == "managers-table":
            # Get the row data
            row = table.get_row(row_key)
            service_name = str(row[1])  # Service name is in column 1

            if service_name in self.service_status:
                data = self.service_status[service_name]
                detail_panel = self.query_one("#detail-panel", DetailPanel)

                status = data.get("status", "unknown")
                fields: dict[str, str] = {
                    "URL": data.get("url", "N/A"),
                    "Status": format_status_colored(status),
                    "Version": data.get("version") or "N/A",
                }
                if data.get("error"):
                    fields["Error"] = f"[red]{data['error']}[/red]"

                detail_panel.update_content(
                    title=service_name,
                    sections=[DetailSection("Service Info", fields)],
                )

        elif row_key and table.id == "nodes-table":
            row = table.get_row(row_key)
            node_name = str(row[1])
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            fields: dict[str, str] = {
                "Node": node_name,
                "URL": str(row[2]),
                "State": str(row[3]),
            }
            detail_panel.update_content(
                title=node_name,
                sections=[DetailSection("Node Info", fields)],
            )

    async def action_refresh(self) -> None:
        """Refresh status data."""
        await self.refresh_data()
        self.notify("Status refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
