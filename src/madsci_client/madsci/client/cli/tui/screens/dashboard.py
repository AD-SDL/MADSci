"""Dashboard screen for MADSci TUI.

Provides an overview of the lab status including services, nodes,
active workflows, and recent events.
"""

import asyncio
import logging
from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import StatusBadge
from madsci.client.cli.utils.formatting import truncate
from madsci.client.cli.utils.service_health import check_all_services_async
from madsci.client.event_client import EventClient
from madsci.common.types.event_types import Event
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

logger = logging.getLogger(__name__)


class ServicesPanel(Static):
    """Panel showing all service statuses using StatusBadge widgets."""

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Services[/bold]")
        for name in self.app.service_urls:
            yield StatusBadge("unknown", id=f"svc-badge-{name}")
            yield Label(f" {name}", id=f"svc-label-{name}")

    async def refresh_data(self) -> None:
        """Refresh all service statuses using shared health check."""
        service_urls = getattr(self.app, "service_urls", {})
        results = await check_all_services_async(service_urls)

        for name, result in results.items():
            try:
                badge = self.query_one(f"#svc-badge-{name}", StatusBadge)
                if result.is_available:
                    badge.status = "healthy"
                else:
                    badge.status = "offline"
            except Exception as exc:
                logger.debug("Refresh failed: %s", exc)


class QuickActionsPanel(Static):
    """Panel showing quick action shortcuts."""

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Quick Actions[/bold]")
        yield Button("(s) Status", id="action-status", variant="default")
        yield Button("(l) Logs", id="action-logs", variant="default")
        yield Button("(n) Nodes", id="action-nodes", variant="default")
        yield Button("(w) Workflows", id="action-workflows", variant="default")
        yield Button("(e) Experiments", id="action-experiments", variant="default")
        yield Button("(i) Resource Inventory", id="action-resources", variant="default")
        yield Button("(b) Data Browser", id="action-data", variant="default")
        yield Button("(o) Locations", id="action-locations", variant="default")
        yield Button("(r) Refresh", id="action-refresh", variant="default")
        yield Button("(q) Quit", id="action-quit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle quick action button presses."""
        action_map = {
            "action-status": "status",
            "action-logs": "logs",
            "action-nodes": "nodes",
            "action-workflows": "workflows",
            "action-experiments": "experiments",
            "action-resources": "resources",
            "action-data": "data",
            "action-locations": "locations",
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


def _extract_message(event: Event) -> str:
    """Extract the message string from an Event model instance."""
    event_data = event.event_data
    if isinstance(event_data, dict):
        return truncate(event_data.get("message", str(event_data)), max_len=50)
    return truncate(str(event_data), max_len=50)


class RecentEventsPanel(Static):
    """Panel showing recent events."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the panel."""
        super().__init__(**kwargs)
        self._event_client: EventClient | None = None

    def _get_event_client(self) -> EventClient:
        """Get or create the EventClient instance."""
        if self._event_client is None:
            url = self.app.service_urls.get("event_manager", "http://localhost:8001/")
            self._event_client = EventClient(
                name="tui-dashboard",
                event_server_url=url,
            )
        return self._event_client

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Label("[bold]Recent Events[/bold]")
        yield Label(
            "[dim]No events loaded. Press 'r' to refresh.[/dim]", id="events-content"
        )

    async def on_unmount(self) -> None:
        """Clean up client connections when panel is unmounted."""
        for attr_name in list(vars(self)):
            if attr_name.endswith("_client"):
                client = getattr(self, attr_name, None)
                if client is not None and hasattr(client, "close"):
                    client.close()

    async def refresh_data(self) -> None:
        """Refresh recent events."""
        content = self.query_one("#events-content", Label)
        try:
            client = self._get_event_client()
            events_dict = await client.async_get_events(number=5)
            events = list(events_dict.values())
            if events:
                lines = []
                for event in events[:5]:
                    msg = _extract_message(event)
                    level = _format_level(event.log_level)
                    lines.append(f"  [{level}] {msg}")
                content.update("\n".join(lines))
            else:
                content.update("[dim]No recent events[/dim]")
        except Exception as exc:
            logger.debug("Refresh failed: %s", exc)
            content.update("[dim]Event Manager not available[/dim]")


class DashboardScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
    """Main dashboard screen showing lab overview."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("a", "toggle_auto_refresh", "Auto-refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with VerticalScroll(id="main-content"):
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

    def watch_auto_refresh_enabled(self, _value: bool) -> None:
        """React to auto_refresh_enabled changes by updating the footer."""
        self._update_footer()

    async def refresh_data(self) -> None:
        """Refresh all dashboard data."""
        services_panel = self.query_one("#services-panel", ServicesPanel)
        events_panel = self.query_one("#events-panel", RecentEventsPanel)

        await asyncio.gather(
            services_panel.refresh_data(),
            events_panel.refresh_data(),
        )

    async def action_refresh(self) -> None:
        """Refresh dashboard data."""
        await self.refresh_data()
        self.notify("Dashboard refreshed", timeout=2)
