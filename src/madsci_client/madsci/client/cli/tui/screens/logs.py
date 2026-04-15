"""Logs screen for MADSci TUI.

Provides real-time log viewing with filtering capabilities.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import FilterBar, FilterDef, LogViewer
from madsci.client.event_client import EventClient
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Label

logger = logging.getLogger(__name__)

# Map level name strings to Python logging int values.
_LEVEL_NAME_MAP: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}


def _level_name_to_int(name: str | None) -> int:
    """Convert a level name string to the corresponding integer.

    Args:
        name: Level name (e.g. ``"info"``, ``"error"``). ``None`` or
            ``"all"`` returns ``-1`` so EventClient fetches all levels.

    Returns:
        Integer log level, or ``-1`` for no filtering.
    """
    if name is None or name.lower() in {"all", ""}:
        return -1
    return _LEVEL_NAME_MAP.get(name.lower(), -1)


def _matches_search(event_dict: dict[str, Any], search: str) -> bool:
    """Check whether an event dict matches a search string.

    Searches in the ``event_data.message`` field (case-insensitive).

    Args:
        event_dict: A serialized Event dictionary.
        search: The search text.

    Returns:
        True if the event matches.
    """
    event_data = event_dict.get("event_data", {})
    if isinstance(event_data, dict):
        message = str(event_data.get("message", ""))
    else:
        message = str(event_data)
    return search.lower() in message.lower()


class LogsScreen(AutoRefreshMixin, ServiceURLMixin, Screen):
    """Screen for viewing logs."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("c", "clear", "Clear"),
        ("f", "toggle_follow", "Follow"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(**kwargs)
        self._follow_timer: Any = None
        self._event_client: EventClient | None = None

    def _get_event_client(self) -> EventClient:
        """Get or create the EventClient instance."""
        if self._event_client is None:
            url = self.get_service_url("event_manager")
            self._event_client = EventClient(
                name="tui-logs",
                event_server_url=url,
            )
        return self._event_client

    def compose(self) -> ComposeResult:
        """Compose the logs screen layout."""
        with Container(id="main-content"):
            yield Label("[bold blue]Log Viewer[/bold blue]")
            yield Label("")

            yield FilterBar(
                search_placeholder="Search...",
                filters=[
                    FilterDef(
                        name="level",
                        label="Level",
                        options=[
                            ("all", "All"),
                            ("debug", "Debug"),
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("critical", "Critical"),
                        ],
                        default="all",
                    ),
                ],
                id="filter-panel",
            )
            yield Label("")

            yield LogViewer(id="log-view")

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
        log_viewer = self.query_one("#log-view", LogViewer)

        # Get filter values from FilterBar
        filter_bar = self.query_one("#filter-panel", FilterBar)
        filter_values = filter_bar.get_filter_values()
        search_text = filter_bar.get_search_text()

        level_value = filter_values.get("level", "all")
        level = level_value if level_value and level_value != "all" else None
        search = search_text or None

        # Fetch logs from Event Manager
        logs = await self._fetch_logs(level=level, search=search)

        if not logs:
            if (
                log_viewer.entry_count == 0
            ):  # Only show message if no logs have been loaded
                log_viewer.append_entries(
                    [
                        {
                            "event_id": "__no_logs__",
                            "log_level": 20,
                            "event_data": {
                                "message": "No logs available. Event Manager may not be running."
                            },
                        }
                    ]
                )
            return

        # Add new logs to display (dedup handled by LogViewer)
        log_viewer.append_entries(logs)

    async def _fetch_logs(
        self,
        limit: int = 100,
        level: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Fetch logs from the Event Manager using EventClient.

        Args:
            limit: Maximum number of logs to fetch.
            level: Minimum log level name (e.g. ``"info"``).
            search: Search pattern applied client-side.

        Returns:
            List of log entry dictionaries.
        """
        try:
            client = self._get_event_client()
            level_int = _level_name_to_int(level)
            events = await client.async_get_events(
                number=limit,
                level=level_int,
            )

            # Convert Event models to dicts for LogViewer.append_entries
            entries = [event.model_dump(mode="json") for event in events.values()]

            # Apply search filtering client-side (EventClient doesn't support search)
            if search:
                entries = [e for e in entries if _matches_search(e, search)]

            return entries
        except Exception as exc:
            logger.debug("Failed to fetch logs: %s", exc)
            return []

    async def action_refresh(self) -> None:
        """Refresh logs."""
        await self.refresh_data()
        self.notify("Logs refreshed", timeout=2)

    def action_clear(self) -> None:
        """Clear the log view."""
        log_viewer = self.query_one("#log-view", LogViewer)
        log_viewer.clear()
        self.notify("Logs cleared", timeout=2)

    def action_toggle_follow(self) -> None:
        """Toggle follow mode."""
        log_viewer = self.query_one("#log-view", LogViewer)
        log_viewer.follow_mode = not log_viewer.follow_mode

        if log_viewer.follow_mode:
            self.notify("Follow mode enabled", timeout=2)
            self._follow_timer = self.set_interval(
                2.0, self._follow_refresh, name="follow-timer"
            )
        else:
            if self._follow_timer is not None:
                self._follow_timer.stop()
                self._follow_timer = None
            self.notify("Follow mode disabled", timeout=2)

    async def _follow_refresh(self) -> None:
        """Refresh logs in follow mode."""
        log_viewer = self.query_one("#log-view", LogViewer)
        if log_viewer.follow_mode:
            await self.refresh_data()

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        log_viewer = self.query_one("#log-view", LogViewer)
        log_viewer.follow_mode = False
        if self._follow_timer is not None:
            self._follow_timer.stop()
            self._follow_timer = None
        self.app.switch_screen("dashboard")

    def on_screen_suspend(self) -> None:
        """Pause the follow timer when the screen is suspended."""
        if self._follow_timer is not None:
            self._follow_timer.stop()
            self._follow_timer = None

    def on_screen_resume(self) -> None:
        """Restart the follow timer when the screen is resumed, if follow mode is active."""
        log_viewer = self.query_one("#log-view", LogViewer)
        if log_viewer.follow_mode and self._follow_timer is None:
            self._follow_timer = self.set_interval(
                2.0, self._follow_refresh, name="follow-timer"
            )

    def on_filter_bar_filter_changed(self, event: FilterBar.FilterChanged) -> None:  # noqa: ARG002
        """Handle filter changes from FilterBar."""
        log_viewer = self.query_one("#log-view", LogViewer)
        log_viewer.clear()
        self.run_worker(self.refresh_data())
