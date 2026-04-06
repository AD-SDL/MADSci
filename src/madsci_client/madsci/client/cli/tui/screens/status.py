"""Status screen for MADSci TUI.

Provides detailed service status with health information.
"""

import socket
from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import (
    AutoRefreshMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored, format_status_icon
from madsci.client.cli.utils.service_health import check_all_services_async
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Label

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

    def compose(self) -> ComposeResult:
        """Compose the status screen layout."""
        with Container(id="main-content"):
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

    async def refresh_data(self) -> None:
        """Refresh all service statuses."""
        await self._refresh_managers()
        await self._refresh_infrastructure()

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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                status = "connected" if result == 0 else "disconnected"
            except Exception:
                status = "disconnected"

            icon = format_status_icon(status)
            infra_rows.append((icon, name, host, str(port), status))

        with preserve_cursor(table):
            table.clear()
            for row in infra_rows:
                table.add_row(*row)

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

    async def action_refresh(self) -> None:
        """Refresh status data."""
        await self.refresh_data()
        self.notify("Status refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
