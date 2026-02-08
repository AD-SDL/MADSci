"""Dashboard screen for MADSci TUI.

Provides an overview of the lab status including services, nodes,
active workflows, and recent events.
"""

from typing import Any, ClassVar

import httpx
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label, Static

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


class ServiceStatusWidget(Static):
    """Widget displaying status of a single service."""

    def __init__(self, name: str, url: str, **kwargs: Any) -> None:
        """Initialize the service status widget.

        Args:
            name: Service name.
            url: Service URL.
        """
        super().__init__(**kwargs)
        self.service_name = name
        self.service_url = url
        self.status = "unknown"

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Label(f"\u25cb {self.service_name}", id=f"status-{self.service_name}")

    async def check_health(self) -> None:
        """Check service health and update display."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url.rstrip('/')}/health")
                if response.status_code == 200:
                    self.status = "healthy"
                    icon = "[green]\u25cf[/green]"
                else:
                    self.status = "unhealthy"
                    icon = "[yellow]\u25cf[/yellow]"
        except Exception:
            self.status = "offline"
            icon = "[red]\u25cb[/red]"

        label = self.query_one(f"#status-{self.service_name}", Label)
        label.update(f"{icon} {self.service_name}")


class ServicesPanel(Static):
    """Panel showing all service statuses."""

    DEFAULT_CSS = """
    ServicesPanel {
        border: solid $primary;
        padding: 1 2;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Services[/bold]")
        for name, url in DEFAULT_SERVICES.items():
            yield ServiceStatusWidget(name, url)

    async def refresh_data(self) -> None:
        """Refresh all service statuses."""
        for widget in self.query(ServiceStatusWidget):
            await widget.check_health()


class QuickActionsPanel(Static):
    """Panel showing quick action shortcuts."""

    DEFAULT_CSS = """
    QuickActionsPanel {
        border: solid $primary;
        padding: 1 2;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Quick Actions[/bold]")
        yield Label("  [dim]s[/dim] View Status")
        yield Label("  [dim]l[/dim] View Logs")
        yield Label("  [dim]r[/dim] Refresh")
        yield Label("  [dim]q[/dim] Quit")


class RecentEventsPanel(Static):
    """Panel showing recent events."""

    DEFAULT_CSS = """
    RecentEventsPanel {
        border: solid $primary;
        padding: 1 2;
        height: auto;
        max-height: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Recent Events[/bold]")
        yield Label(
            "[dim]No events loaded. Press 'r' to refresh.[/dim]", id="events-content"
        )

    async def refresh_data(self) -> None:
        """Refresh recent events."""
        content = self.query_one("#events-content", Label)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "http://localhost:8001/events",
                    params={"limit": 5},
                )
                if response.status_code == 200:
                    events = response.json()
                    if isinstance(events, list) and events:
                        lines = []
                        for event in events[:5]:
                            msg = event.get("message", str(event))[:50]
                            level = event.get("level", "INFO")[:5]
                            lines.append(f"  [{level}] {msg}")
                        content.update("\n".join(lines))
                    else:
                        content.update("[dim]No recent events[/dim]")
                else:
                    content.update("[dim]Could not load events[/dim]")
        except Exception:
            content.update("[dim]Event Manager not available[/dim]")


class DashboardScreen(Screen):
    """Main dashboard screen showing lab overview."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]MADSci Lab Dashboard[/bold blue]")
            yield Label("")

            with Horizontal():
                with Vertical(id="left-column"):
                    yield ServicesPanel(id="services-panel")
                with Vertical(id="right-column"):
                    yield QuickActionsPanel(id="actions-panel")

            yield RecentEventsPanel(id="events-panel")
            yield Label("")
            yield Label("[dim]Press 'r' to refresh, '?' for help[/dim]")

    async def on_mount(self) -> None:
        """Handle screen mount - initial data load."""
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh all dashboard data."""
        services_panel = self.query_one("#services-panel", ServicesPanel)
        events_panel = self.query_one("#events-panel", RecentEventsPanel)

        await services_panel.refresh_data()
        await events_panel.refresh_data()

    async def action_refresh(self) -> None:
        """Refresh dashboard data."""
        await self.refresh_data()
        self.notify("Dashboard refreshed", timeout=2)
