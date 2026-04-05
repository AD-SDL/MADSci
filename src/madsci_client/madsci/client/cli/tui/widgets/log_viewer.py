"""LogViewer widget for MADSci TUI.

Rich log viewer with follow mode, deduplication, and pluggable
formatting. Extracts the log display pattern from the Logs screen.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import RichLog

# Level colours matching the Logs screen convention.
_LEVEL_COLOURS: dict[str, str] = {
    "DEBUG": "dim",
    "INFO": "blue",
    "WARNING": "yellow",
    "WARN": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red",
}

# Numeric level -> name mapping (MADSci Event model uses int enum).
_LEVEL_NAMES: dict[int, str] = {
    0: "NOTSET",
    10: "DEBUG",
    20: "INFO",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL",
}


def _format_entry_timestamp(entry: dict[str, Any]) -> str:
    """Extract and format the timestamp from a log entry."""
    timestamp = entry.get("event_timestamp", entry.get("timestamp", ""))
    if not timestamp:
        return "????????????"
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S.%f")[:-3]
        except ValueError:
            return timestamp[:12]
    return str(timestamp)[:12]


def _extract_source(source_data: object) -> str:
    """Extract a display-friendly source name from ownership info."""
    if isinstance(source_data, dict):
        for key in ("node_id", "manager_id", "workcell_id", "experiment_id"):
            val = source_data.get(key)
            if val:
                return str(val)[:12]
        return ""
    return str(source_data)[:12]


def _extract_message(entry: dict[str, Any]) -> str:
    """Extract the message string from an event entry."""
    event_data = entry.get("event_data", {})
    if isinstance(event_data, dict):
        return event_data.get("message", str(event_data) if event_data else "")
    return str(event_data) if event_data else str(entry.get("event_type", ""))


def _default_formatter(entry: dict[str, Any]) -> str:
    """Format a log entry using the standard MADSci event layout.

    Produces output like:
        ``12:34:56.789  INFO      source_id   Message text``

    Args:
        entry: Log entry dictionary (MADSci Event format).

    Returns:
        Rich-formatted log line.
    """
    ts_str = _format_entry_timestamp(entry)

    log_level = entry.get("log_level", entry.get("level", 20))
    if isinstance(log_level, int):
        level = _LEVEL_NAMES.get(log_level, str(log_level))
    else:
        level = str(log_level).upper()
    level_colour = _LEVEL_COLOURS.get(level, "")

    source = _extract_source(entry.get("source", {}))
    message = _extract_message(entry)

    return (
        f"[dim]{ts_str}[/dim]  "
        f"[{level_colour}]{level:8}[/{level_colour}]  "
        f"[cyan]{source:12}[/cyan]  "
        f"{message}"
    )


class LogViewer(Widget):
    """Rich log viewer with follow mode and deduplication.

    Features:
    - Level-based colouring via a pluggable formatter.
    - Follow mode: auto-scroll to the latest entry.
    - Deduplication: bounded ``OrderedDict`` of seen IDs (default 10k).
    - Pluggable formatter via :meth:`set_formatter`.

    Usage::

        viewer = LogViewer()
        count = viewer.append_entries(entries, id_key="event_id")
        viewer.follow_mode = True
        viewer.clear()
    """

    follow_mode: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    LogViewer {
        height: 1fr;
    }
    LogViewer RichLog {
        height: 1fr;
    }
    """

    def __init__(self, *, max_seen: int = 10_000, **kwargs: Any) -> None:
        """Initialize the log viewer.

        Args:
            max_seen: Maximum number of entry IDs to track for
                deduplication. Oldest entries are evicted when this
                limit is reached.
            **kwargs: Additional keyword arguments forwarded to ``Widget``.
        """
        super().__init__(**kwargs)
        self._max_seen = max_seen
        self._seen_ids: OrderedDict[str, None] = OrderedDict()
        self._formatter: Callable[[dict[str, Any]], str] = _default_formatter

    def compose(self) -> ComposeResult:
        """Compose the log viewer."""
        yield RichLog(id="log-viewer-richlog", highlight=True, markup=True)

    def append_entries(
        self,
        entries: list[dict[str, Any]],
        id_key: str = "event_id",
    ) -> int:
        """Append new log entries with deduplication.

        Args:
            entries: List of log entry dictionaries.
            id_key: Key used to extract unique IDs from entries. Falls
                back to ``"_id"`` then ``hash(str(entry))`` if the key
                is missing.

        Returns:
            Number of *new* (non-duplicate) entries that were appended.
        """
        rich_log = self.query_one("#log-viewer-richlog", RichLog)
        new_count = 0

        for entry in entries:
            entry_id = str(entry.get(id_key, entry.get("_id", hash(str(entry)))))
            if entry_id in self._seen_ids:
                continue

            self._seen_ids[entry_id] = None
            # Evict oldest entries when exceeding the bound
            while len(self._seen_ids) > self._max_seen:
                self._seen_ids.popitem(last=False)

            rich_log.write(self._formatter(entry))
            new_count += 1

        if self.follow_mode and new_count > 0:
            rich_log.scroll_end(animate=False)

        return new_count

    def clear(self) -> None:
        """Clear all displayed log entries and the dedup cache."""
        rich_log = self.query_one("#log-viewer-richlog", RichLog)
        rich_log.clear()
        self._seen_ids.clear()

    def set_formatter(self, formatter: Callable[[dict[str, Any]], str]) -> None:
        """Set a custom entry formatter.

        Args:
            formatter: Callable that takes an entry dict and returns a
                Rich-formatted string.
        """
        self._formatter = formatter

    def watch_follow_mode(self, value: bool) -> None:
        """Scroll to end when follow mode is enabled."""
        if value:
            try:
                rich_log = self.query_one("#log-viewer-richlog", RichLog)
                rich_log.scroll_end(animate=False)
            except Exception:  # noqa: S110
                pass  # Widget may not be mounted yet
