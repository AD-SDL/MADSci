"""Logs screen for MADSci TUI.

Provides real-time log viewing with filtering capabilities.
"""

from datetime import datetime
from typing import Any, ClassVar

import httpx
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog, Select, Static

# Log level options
LOG_LEVELS = [
    ("All", "all"),
    ("Debug", "debug"),
    ("Info", "info"),
    ("Warning", "warning"),
    ("Error", "error"),
    ("Critical", "critical"),
]

# Level colors for display
LEVEL_COLORS = {
    "DEBUG": "dim",
    "INFO": "blue",
    "WARNING": "yellow",
    "WARN": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red",
}


class FilterPanel(Static):
    """Panel with log filters."""

    DEFAULT_CSS = """
    FilterPanel {
        height: 5;
        padding: 1 2;
        border: solid $primary;
    }

    FilterPanel Horizontal {
        height: 3;
    }

    FilterPanel Select {
        width: 20;
        margin-right: 2;
    }

    FilterPanel Input {
        width: 30;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the filter panel."""
        yield Label("[bold]Filters[/bold]")
        with Horizontal():
            yield Select(LOG_LEVELS, id="level-select", value="all")
            yield Input(placeholder="Search...", id="search-input")


class LogsScreen(Screen):
    """Screen for viewing logs."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("c", "clear", "Clear"),
        ("f", "toggle_follow", "Follow"),
        ("escape", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    LogsScreen #log-view {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.follow_mode = False
        self.seen_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        """Compose the logs screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Log Viewer[/bold blue]")
            yield Label("")

            yield FilterPanel(id="filter-panel")
            yield Label("")

            yield RichLog(id="log-view", highlight=True, markup=True)

            yield Label("")
            with Horizontal():
                yield Label("[dim]r[/dim] Refresh  ", id="help-refresh")
                yield Label("[dim]c[/dim] Clear  ", id="help-clear")
                yield Label("[dim]f[/dim] Follow  ", id="help-follow")
                yield Label("[dim]Esc[/dim] Back", id="help-back")

    async def on_mount(self) -> None:
        """Handle screen mount - load initial logs."""
        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Fetch and display logs."""
        log_view = self.query_one("#log-view", RichLog)

        # Get filter values
        level_select = self.query_one("#level-select", Select)
        search_input = self.query_one("#search-input", Input)

        level_value = level_select.value
        level = str(level_value) if level_value and level_value != "all" else None
        search = search_input.value or None

        # Fetch logs from Event Manager
        logs = await self._fetch_logs(level=level, search=search)

        if not logs:
            if not self.seen_ids:  # Only show message if no logs have been loaded
                log_view.write(
                    "[dim]No logs available. Event Manager may not be running.[/dim]"
                )
            return

        # Add new logs to display
        for entry in logs:
            entry_id = entry.get("event_id", entry.get("id", str(hash(str(entry)))))
            if entry_id not in self.seen_ids:
                self.seen_ids.add(entry_id)
                log_view.write(self._format_log_entry(entry))

    async def _fetch_logs(
        self,
        limit: int = 100,
        level: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Fetch logs from the Event Manager.

        Args:
            limit: Maximum number of logs to fetch.
            level: Minimum log level.
            search: Search pattern.

        Returns:
            List of log entries.
        """
        try:
            params: dict[str, str | int] = {"limit": limit}
            if level:
                params["min_level"] = level.upper()
            if search:
                params["search"] = search

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "http://localhost:8001/events",
                    params=params,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "events" in data:
                        return data["events"]
                return []
        except Exception:
            return []

    def _format_log_entry(self, entry: dict) -> str:
        """Format a log entry for display.

        Args:
            entry: Log entry dictionary.

        Returns:
            Formatted string.
        """
        # Timestamp
        timestamp = entry.get("timestamp", entry.get("logged_at", ""))
        if timestamp:
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp_str = dt.strftime("%H:%M:%S.%f")[:-3]
                except ValueError:
                    timestamp_str = timestamp[:12]
            else:
                timestamp_str = str(timestamp)[:12]
        else:
            timestamp_str = "????????????"

        # Level
        level = entry.get("level", entry.get("log_level", "INFO")).upper()
        level_color = LEVEL_COLORS.get(level, "")

        # Source
        source = entry.get("source", entry.get("service", entry.get("name", "")))[:12]

        # Message
        message = entry.get("message", entry.get("msg", str(entry)))

        return f"[dim]{timestamp_str}[/dim]  [{level_color}]{level:8}[/{level_color}]  [cyan]{source:12}[/cyan]  {message}"

    async def action_refresh(self) -> None:
        """Refresh logs."""
        await self.refresh_data()
        self.notify("Logs refreshed", timeout=2)

    def action_clear(self) -> None:
        """Clear the log view."""
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        self.seen_ids.clear()
        self.notify("Logs cleared", timeout=2)

    def action_toggle_follow(self) -> None:
        """Toggle follow mode."""
        self.follow_mode = not self.follow_mode
        if self.follow_mode:
            self.notify("Follow mode enabled", timeout=2)
            # Start a timer to periodically refresh
            self.set_interval(2.0, self._follow_refresh, name="follow-timer")
        else:
            self.notify("Follow mode disabled", timeout=2)

    async def _follow_refresh(self) -> None:
        """Refresh logs in follow mode."""
        if self.follow_mode:
            await self.refresh_data()

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.follow_mode = False
        self.app.switch_screen("dashboard")

    def on_select_changed(self, event: Select.Changed) -> None:  # noqa: ARG002
        """Handle filter changes."""
        # Clear and refresh when filters change
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        self.seen_ids.clear()
        self.run_worker(self.refresh_data())

    def on_input_submitted(self, event: Input.Submitted) -> None:  # noqa: ARG002
        """Handle search input submission."""
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        self.seen_ids.clear()
        self.run_worker(self.refresh_data())
