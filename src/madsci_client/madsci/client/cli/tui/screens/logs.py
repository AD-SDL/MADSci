"""Logs screen for MADSci TUI.

Provides real-time log viewing with filtering capabilities.
"""

from typing import Any, ClassVar

import httpx
from madsci.client.cli.tui.mixins import AutoRefreshMixin, ServiceURLMixin
from madsci.client.cli.tui.widgets import FilterBar, FilterDef, LogViewer
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Label


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
                not log_viewer._seen_ids
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
        """Fetch logs from the Event Manager.

        Args:
            limit: Maximum number of logs to fetch.
            level: Minimum log level.
            search: Search pattern.

        Returns:
            List of log entries.
        """
        try:
            params: dict[str, str | int] = {"number": limit}
            if level:
                params["level"] = level.upper()
            if search:
                params["search"] = search

            event_url = self.get_service_url("event_manager")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{event_url.rstrip('/')}/events",
                    params=params,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        # The Event Manager returns Dict[str, Event]
                        return list(data.values())
                return []
        except Exception:
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

    def on_filter_bar_filter_changed(self, event: FilterBar.FilterChanged) -> None:  # noqa: ARG002
        """Handle filter changes from FilterBar."""
        log_viewer = self.query_one("#log-view", LogViewer)
        log_viewer.clear()
        self.run_worker(self.refresh_data())
