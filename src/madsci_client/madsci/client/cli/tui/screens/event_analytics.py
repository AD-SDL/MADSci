"""Event analytics screen for MADSci TUI.

Provides a read-only analytics dashboard with utilization summary
data and a recent events table. Displays daily utilization periods
and the last 10 events for quick operational overview.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import ServiceURLMixin, preserve_cursor
from madsci.client.cli.tui.widgets import ActionBar, ActionDef
from madsci.client.cli.utils.formatting import format_timestamp, truncate
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Label


class EventAnalyticsScreen(ServiceURLMixin, Screen):
    """Screen showing event analytics and utilization summaries."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self._utilization_data: list[dict] = []
        self._recent_events: list[dict] = []

    def compose(self) -> ComposeResult:
        """Compose the event analytics screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Event Analytics[/bold blue]")
            yield Label("")

            with Vertical(id="utilization-section"):
                yield Label("[bold]Utilization Summary[/bold]")
                yield DataTable(id="utilization-table")

            yield Label("")

            with Vertical(id="recent-events-section"):
                yield Label("[bold]Recent Events[/bold]")
                yield DataTable(id="recent-events-table")

            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("r", "Refresh", "refresh"),
                ],
                id="analytics-action-bar",
            )

    async def on_mount(self) -> None:
        """Handle screen mount - set up tables and load data."""
        util_table = self.query_one("#utilization-table", DataTable)
        util_table.add_columns("Period", "Events", "Users", "Sessions")
        util_table.cursor_type = "row"

        events_table = self.query_one("#recent-events-table", DataTable)
        events_table.add_columns("Timestamp", "Level", "Source", "Message")
        events_table.cursor_type = "row"

        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh analytics data from the event manager."""
        await self._refresh_utilization()
        await self._refresh_recent_events()

    async def _refresh_utilization(self) -> None:
        """Refresh the utilization summary table."""
        util_table = self.query_one("#utilization-table", DataTable)
        self._utilization_data.clear()

        try:
            event_url = self.get_service_url("event_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{event_url.rstrip('/')}/utilization/periods",
                    params={"analysis_type": "daily"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self._utilization_data = data
                    elif isinstance(data, dict):
                        # Handle dict response (e.g., keyed by period)
                        periods = data.get("periods", [])
                        if isinstance(periods, list):
                            self._utilization_data = periods
                        else:
                            # Treat the entire dict as a single entry
                            self._utilization_data = [data]
        except Exception:  # noqa: S110
            pass

        with preserve_cursor(util_table):
            util_table.clear()
            if self._utilization_data:
                for period_data in self._utilization_data:
                    period = str(period_data.get("period", "-"))
                    events = str(
                        period_data.get("events", period_data.get("event_count", "-"))
                    )
                    users = str(
                        period_data.get("users", period_data.get("user_count", "-"))
                    )
                    sessions = str(
                        period_data.get(
                            "sessions", period_data.get("session_count", "-")
                        )
                    )
                    util_table.add_row(period, events, users, sessions)
            else:
                util_table.add_row("[dim]No utilization data[/dim]", "-", "-", "-")

    async def _refresh_recent_events(self) -> None:
        """Refresh the recent events table."""
        events_table = self.query_one("#recent-events-table", DataTable)
        self._recent_events.clear()

        try:
            event_url = self.get_service_url("event_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{event_url.rstrip('/')}/events",
                    params={"number": 10},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self._recent_events = data
                    elif isinstance(data, dict):
                        # Handle dict response (keyed by ID)
                        self._recent_events = list(data.values())
        except Exception:  # noqa: S110
            pass

        with preserve_cursor(events_table):
            events_table.clear()
            if self._recent_events:
                for event_data in self._recent_events:
                    timestamp = event_data.get("timestamp") or event_data.get(
                        "event_timestamp"
                    )
                    ts_str = (
                        format_timestamp(timestamp, short=True) if timestamp else "-"
                    )

                    level = str(
                        event_data.get("level", event_data.get("event_level", "-"))
                    )
                    source = str(
                        event_data.get("source", event_data.get("event_source", "-"))
                    )
                    message = event_data.get(
                        "message", event_data.get("event_message", "")
                    )
                    msg_str = truncate(str(message), 60) if message else "-"

                    events_table.add_row(ts_str, level, source, msg_str)
            else:
                events_table.add_row("[dim]No recent events[/dim]", "-", "-", "-")

    async def action_refresh(self) -> None:
        """Refresh analytics data."""
        await self.refresh_data()
        self.notify("Analytics refreshed", timeout=2)

    def action_go_back(self) -> None:
        """Go back to the dashboard."""
        self.app.switch_screen("dashboard")
