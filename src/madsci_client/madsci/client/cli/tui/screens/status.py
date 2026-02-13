"""Status screen for MADSci TUI.

Provides detailed service status with health information.
"""

import socket
from typing import Any, ClassVar

import httpx
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Label, Static

# Default auto-refresh interval in seconds
AUTO_REFRESH_INTERVAL = 5.0

# Default service URLs
DEFAULT_SERVICES = {
    "lab_manager": "http://localhost:8000/",
    "event_manager": "http://localhost:8001/",
    "experiment_manager": "http://localhost:8002/",
    "resource_manager": "http://localhost:8003/",
    "data_manager": "http://localhost:8004/",
    "workcell_manager": "http://localhost:8005/",
    "location_manager": "http://localhost:8006/",
}

INFRASTRUCTURE_SERVICES = {
    "mongodb": ("localhost", 27017),
    "postgresql": ("localhost", 5432),
    "redis": ("localhost", 6379),
    "minio": ("localhost", 9000),
}


class ServiceDetailPanel(Static):
    """Panel showing details for a selected service."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the panel."""
        super().__init__(**kwargs)
        self.selected_service = None
        self.service_data = {}

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Service Details[/bold]")
        yield Label(
            "[dim]Select a service from the table above[/dim]", id="detail-content"
        )

    def update_details(self, name: str, data: dict) -> None:
        """Update the detail display.

        Args:
            name: Service name.
            data: Service data dictionary.
        """
        self.selected_service = name
        self.service_data = data

        content = self.query_one("#detail-content", Label)

        status = data.get("status", "unknown")
        status_color = {
            "healthy": "green",
            "unhealthy": "yellow",
            "offline": "red",
        }.get(status, "dim")

        lines = [
            f"[bold]{name}[/bold]",
            "",
            f"  URL:     {data.get('url', 'N/A')}",
            f"  Status:  [{status_color}]{status}[/{status_color}]",
            f"  Version: {data.get('version', 'N/A')}",
        ]

        if data.get("error"):
            lines.append(f"  Error:   [red]{data.get('error')}[/red]")

        content.update("\n".join(lines))


class StatusScreen(Screen):
    """Screen showing detailed service status."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.service_status = {}
        self.auto_refresh_enabled = True
        self._auto_refresh_timer: Timer | None = None

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
            yield ServiceDetailPanel(id="detail-panel")

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
        self._start_auto_refresh()

    def _start_auto_refresh(self) -> None:
        """Start the auto-refresh timer."""
        if self._auto_refresh_timer is None:
            self._auto_refresh_timer = self.set_interval(
                AUTO_REFRESH_INTERVAL, self._auto_refresh, name="status-auto-refresh"
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
        footer = self.query_one("#status-footer", Label)
        if self.auto_refresh_enabled:
            footer.update(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )
        else:
            footer.update(
                "[dim]Auto-refresh: off | 'a' toggle | 'r' manual | 'Esc' back[/dim]"
            )

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

    async def refresh_data(self) -> None:
        """Refresh all service statuses."""
        await self._refresh_managers()
        await self._refresh_infrastructure()

    async def _refresh_managers(self) -> None:
        """Refresh manager service statuses."""
        table = self.query_one("#managers-table", DataTable)
        table.clear()

        for name, url in DEFAULT_SERVICES.items():
            status_data = await self._check_service(name, url)
            self.service_status[name] = status_data

            status = status_data.get("status", "unknown")
            icon = {
                "healthy": "\u25cf",
                "unhealthy": "\u25cf",
                "offline": "\u25cb",
            }.get(status, "\u25cb")

            status_style = {
                "healthy": "green",
                "unhealthy": "yellow",
                "offline": "red",
            }.get(status, "dim")

            table.add_row(
                f"[{status_style}]{icon}[/{status_style}]",
                name,
                url,
                f"[{status_style}]{status}[/{status_style}]",
                status_data.get("version", "-"),
            )

    async def _refresh_infrastructure(self) -> None:
        """Refresh infrastructure service statuses."""
        table = self.query_one("#infra-table", DataTable)
        table.clear()

        for name, (host, port) in INFRASTRUCTURE_SERVICES.items():
            # Check if port is reachable
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    status = "connected"
                    icon = "[green]\u25cf[/green]"
                else:
                    status = "unavailable"
                    icon = "[red]\u25cb[/red]"
            except Exception:
                status = "error"
                icon = "[red]\u25cb[/red]"

            table.add_row(icon, name, host, str(port), status)

    async def _check_service(self, name: str, url: str) -> dict:  # noqa: ARG002
        """Check a service's health.

        Args:
            name: Service name.
            url: Service URL.

        Returns:
            Dictionary with status information.
        """
        health_url = url.rstrip("/") + "/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    data = response.json() if response.text else {}
                    return {
                        "status": "healthy",
                        "url": url,
                        "version": data.get("version"),
                        "details": data,
                    }
                return {
                    "status": "unhealthy",
                    "url": url,
                    "error": f"HTTP {response.status_code}",
                }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "url": url,
                "error": "Connection refused",
            }
        except httpx.TimeoutException:
            return {
                "status": "offline",
                "url": url,
                "error": "Timeout",
            }
        except Exception as e:
            return {
                "status": "offline",
                "url": url,
                "error": str(e),
            }

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
                detail_panel = self.query_one("#detail-panel", ServiceDetailPanel)
                detail_panel.update_details(
                    service_name, self.service_status[service_name]
                )

    async def action_refresh(self) -> None:
        """Refresh status data."""
        await self.refresh_data()
        self.notify("Status refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.switch_screen("dashboard")
