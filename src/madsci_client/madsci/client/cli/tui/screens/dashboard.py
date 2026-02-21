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
from textual.widgets import Button, Label, Static


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

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Services[/bold]")
        for name, url in self.app.service_urls.items():
            yield ServiceStatusWidget(name, url)

    async def refresh_data(self) -> None:
        """Refresh all service statuses."""
        for widget in self.query(ServiceStatusWidget):
            await widget.check_health()


class QuickActionsPanel(Static):
    """Panel showing quick action shortcuts."""

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Quick Actions[/bold]")
        yield Button("(s) Status", id="action-status", variant="default")
        yield Button("(l) Logs", id="action-logs", variant="default")
        yield Button("(n) Nodes", id="action-nodes", variant="default")
        yield Button("(w) Workflows", id="action-workflows", variant="default")
        yield Button("(r) Refresh", id="action-refresh", variant="default")
        yield Button("(q) Quit", id="action-quit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle quick action button presses."""
        action_map = {
            "action-status": "status",
            "action-logs": "logs",
            "action-nodes": "nodes",
            "action-workflows": "workflows",
        }
        button_id = event.button.id
        if button_id in action_map:
            self.app.switch_screen(action_map[button_id])
        elif button_id == "action-refresh":
            self.app.run_worker(self.app.action_refresh())
        elif button_id == "action-quit":
            self.app.exit()


_LOG_LEVEL_NAMES = {
    0: "NOTSET",
    10: "DEBUG",
    20: "INFO",
    30: "WARN",
    40: "ERROR",
    50: "CRIT",
}


def _format_level(level: object) -> str:
    """Convert a log_level (int enum or string) to a short display name."""
    if isinstance(level, int):
        return _LOG_LEVEL_NAMES.get(level, str(level))
    return str(level)[:5]


def _extract_message(event: dict) -> str:
    """Extract the message string from an Event dict."""
    event_data = event.get("event_data", {})
    if isinstance(event_data, dict):
        return event_data.get("message", str(event_data))[:50]
    return str(event_data)[:50]


class RecentEventsPanel(Static):
    """Panel showing recent events."""

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
                event_url = self.app.service_urls.get(
                    "event_manager", "http://localhost:8001/"
                )
                response = await client.get(
                    f"{event_url.rstrip('/')}/events",
                    params={"number": 5},
                )
                if response.status_code == 200:
                    data = response.json()
                    # Event Manager returns Dict[str, Event]
                    if isinstance(data, dict) and data:
                        events = list(data.values())
                    elif isinstance(data, list):
                        events = data
                    else:
                        events = []
                    if events:
                        lines = []
                        for event in events[:5]:
                            msg = _extract_message(event)
                            level = _format_level(event.get("log_level", 20))
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
        ("a", "toggle_auto_refresh", "Auto-refresh"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the dashboard screen."""
        super().__init__(**kwargs)
        self.auto_refresh_enabled = True

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
            yield Label(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | '?' help[/dim]",
                id="dashboard-footer",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - initial data load."""
        await self.refresh_data()

    def _update_footer(self) -> None:
        """Update the footer label with current auto-refresh state."""
        footer = self.query_one("#dashboard-footer", Label)
        if self.auto_refresh_enabled:
            footer.update(
                "[dim]Auto-refresh: on (5s) | 'a' toggle | 'r' manual | '?' help[/dim]"
            )
        else:
            footer.update(
                "[dim]Auto-refresh: off | 'a' toggle | 'r' manual | '?' help[/dim]"
            )

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

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        state = "enabled" if self.auto_refresh_enabled else "disabled"
        self.notify(f"Auto-refresh {state}", timeout=2)
        self._update_footer()
