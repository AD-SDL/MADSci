"""Shared formatting utilities for MADSci CLI and TUI.

Provides centralised status styling, timestamp/duration formatting, and
text truncation helpers.  Used by both CLI commands and TUI screens to
ensure consistent visual presentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Centralised status -> (icon, colour) mapping
# ---------------------------------------------------------------------------

STATUS_STYLES: dict[str, tuple[str, str]] = {
    # Service health
    "healthy": ("\u25cf", "green"),
    "unhealthy": ("\u25cf", "yellow"),
    "offline": ("\u25cb", "red"),
    # Infrastructure connectivity
    "connected": ("\u25cf", "green"),
    "disconnected": ("\u25cb", "red"),
    "errored": ("\u25cf", "yellow"),
    # Workflow / run states
    "running": ("\u25cf", "blue"),
    "completed": ("\u25cf", "green"),
    "failed": ("\u25cf", "red"),
    "cancelled": ("\u25cb", "yellow"),
    "paused": ("\u25cf", "yellow"),
    "queued": ("\u25cb", "dim"),
    "pending": ("\u25cb", "dim"),
    # Catch-all
    "unknown": ("\u25cb", "dim"),
}


def get_status_style(status: str) -> tuple[str, str]:
    """Get the ``(icon, colour)`` tuple for a status string.

    Performs a case-insensitive lookup against :data:`STATUS_STYLES`.
    Returns the ``unknown`` entry for unrecognised statuses.

    Args:
        status: Status string (e.g. ``"healthy"``, ``"running"``).

    Returns:
        ``(icon_char, rich_colour_name)`` tuple.
    """
    return STATUS_STYLES.get(status.lower().strip(), STATUS_STYLES["unknown"])


def format_status_icon(status: str) -> str:
    """Return Rich markup for a status icon.

    Example output: ``"[green]\\u25cf[/green]"``.

    Args:
        status: Status string.

    Returns:
        Rich markup string.
    """
    icon, colour = get_status_style(status)
    return f"[{colour}]{icon}[/{colour}]"


def format_status_colored(status: str, text: str | None = None) -> str:
    """Return Rich markup for coloured status text.

    If *text* is ``None``, the *status* string itself is used as the
    display text.

    Args:
        status: Status string used for colour lookup.
        text: Optional override text to colour.

    Returns:
        Rich markup string.
    """
    _, colour = get_status_style(status)
    display = text if text is not None else status
    return f"[{colour}]{display}[/{colour}]"


# ---------------------------------------------------------------------------
# Timestamp / duration helpers
# ---------------------------------------------------------------------------


def format_timestamp(ts: Any, short: bool = False) -> str:
    """Format a timestamp for display.

    Handles ``datetime`` objects, ISO-format strings (with optional
    ``Z`` suffix), and arbitrary objects (via ``str()`` fallback).

    Args:
        ts: Timestamp value.
        short: If ``True``, use ``HH:MM:SS.mmm`` format.

    Returns:
        Formatted timestamp string or ``"-"`` for ``None`` inputs.
    """
    if ts is None:
        return "-"

    dt: datetime | None = None

    if isinstance(ts, datetime):
        dt = ts
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return ts[:12] if short else ts

    if dt is not None:
        if short:
            return dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    return str(ts)[:12] if short else str(ts)


def format_duration(seconds: float | None) -> str:
    """Format a duration in seconds as a human-readable string.

    Output forms:
    * ``Xh XXm XXs`` when hours > 0
    * ``XXm XXs`` otherwise
    * ``"-"`` for ``None`` or negative values

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string.
    """
    if seconds is None or seconds < 0:
        return "-"

    total = int(seconds)
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m {secs:02d}s"
    return f"{mins:02d}m {secs:02d}s"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate *text* with an ellipsis if it exceeds *max_len*.

    Args:
        text: Input text.
        max_len: Maximum allowed length (including the ellipsis).

    Returns:
        Truncated string.
    """
    if max_len <= 0:
        return ""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


# ---------------------------------------------------------------------------
# Ownership section helpers
# ---------------------------------------------------------------------------

_OWNERSHIP_KEYS: tuple[str, ...] = (
    "user_id",
    "experiment_id",
    "campaign_id",
    "workflow_id",
    "workflow_run_id",
    "step_id",
    "node_id",
)


def build_ownership_section(data: dict) -> list[tuple[str, str]]:
    """Build ownership detail section items from a data dict.

    Extracts ownership-related fields and formats them as (label, value) tuples
    suitable for a DetailPanel section.

    Args:
        data: Data dictionary that may contain an ``"ownership_info"`` key
            with a nested dict of ownership fields.

    Returns:
        List of ``(label, value)`` tuples for the non-empty ownership fields.
        Returns an empty list if no ownership info is present.
    """
    ownership_info = data.get("ownership_info", {})
    if not ownership_info:
        return []

    items: list[tuple[str, str]] = []
    for key in _OWNERSHIP_KEYS:
        value = ownership_info.get(key)
        if value:
            label = key.replace("_", " ").title()
            items.append((label, str(value)))
    return items
