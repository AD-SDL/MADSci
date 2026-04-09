"""MADSci CLI logs command.

View and aggregate logs from MADSci services, using the shared utility layer
for timestamp formatting, level colouring, and output rendering.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from typing import Any

import click
from madsci.client.cli.utils.formatting import format_timestamp
from madsci.client.cli.utils.output import (
    OutputFormat,
    determine_output_format,
    get_console,
    output_result,
)
from madsci.client.event_client import EventClient

# Default Event Manager URL
DEFAULT_EVENT_MANAGER_URL = "http://localhost:8001/"

# Log level priority for filtering
LEVEL_PRIORITY = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "WARN": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}

# Map log levels to status-like keys so format_status_colored can colour them
_LEVEL_STATUS_MAP = {
    "DEBUG": "pending",  # dim
    "INFO": "running",  # blue
    "WARNING": "unhealthy",  # yellow
    "WARN": "unhealthy",  # yellow
    "ERROR": "failed",  # red
    "CRITICAL": "failed",  # red
}

# Map integer log levels to their name strings
_INT_TO_LEVEL_NAME: dict[int, str] = {
    10: "DEBUG",
    20: "INFO",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL",
}

# Map level name strings to Python logging int values
_LEVEL_NAME_TO_INT: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "warn": 30,
    "error": 40,
    "critical": 50,
}


def parse_duration(duration: str) -> timedelta:
    """Parse a duration string into a timedelta."""
    match = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not match:
        msg = f"Invalid duration: {duration}. Use format like '5m', '1h', '30s', '1d'"
        raise ValueError(msg)

    value = int(match.group(1))
    unit = match.group(2)

    unit_map = {
        "s": timedelta(seconds=value),
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
    }
    return unit_map[unit]


def _resolve_level_name(entry: dict[str, Any]) -> str:
    """Extract the log level name from an entry dict.

    Handles both string levels (``"INFO"``) and integer levels (``20``).

    Args:
        entry: A log entry dictionary.

    Returns:
        Uppercase level name string.
    """
    raw = entry.get("level", entry.get("log_level", "INFO"))
    if isinstance(raw, int):
        return _INT_TO_LEVEL_NAME.get(raw, str(raw))
    return str(raw).upper()


def _resolve_message(entry: dict[str, Any]) -> str:
    """Extract the message text from an entry dict.

    Supports both flat ``message``/``msg`` keys and nested
    ``event_data.message``.

    Args:
        entry: A log entry dictionary.

    Returns:
        Message string.
    """
    # Try top-level keys first
    message = entry.get("message", entry.get("msg"))
    if message is not None:
        return str(message)
    # Try nested event_data.message (from Event.model_dump)
    event_data = entry.get("event_data")
    if isinstance(event_data, dict):
        nested_msg = event_data.get("message")
        if nested_msg is not None:
            return str(nested_msg)
    return str(entry)


def format_log_entry(
    entry: dict[str, Any],
    show_timestamps: bool = True,
    no_color: bool = False,
) -> Any:
    """Format a log entry for display using shared formatting utilities."""
    from rich.text import Text

    text = Text()

    # Timestamp - use shared format_timestamp helper
    if show_timestamps:
        timestamp = entry.get(
            "timestamp",
            entry.get("logged_at", entry.get("event_timestamp", "")),
        )
        if timestamp:
            timestamp_str = format_timestamp(timestamp, short=True)
            if not no_color:
                text.append(timestamp_str, style="dim")
            else:
                text.append(timestamp_str)
            text.append("  ")

    # Level - use shared format_status_colored via level->status mapping
    level = _resolve_level_name(entry)
    level_str = f"{level:8}"
    if not no_color:
        status_key = _LEVEL_STATUS_MAP.get(level, "unknown")
        # Extract the Rich markup colour from format_status_colored
        # We need just the colour name, so use get_status_style directly
        from madsci.client.cli.utils.formatting import get_status_style

        _, colour = get_status_style(status_key)
        text.append(level_str, style=colour)
    else:
        text.append(level_str)
    text.append("  ")

    # Source
    source = entry.get("source", entry.get("service", entry.get("name", "")))
    if source:
        source_str = source if isinstance(source, str) else str(source)
        if not no_color:
            text.append(source_str, style="cyan")
        else:
            text.append(source_str)
        text.append("  ")

    # Message
    message = _resolve_message(entry)
    text.append(str(message))

    return text


def fetch_logs_from_event_manager(
    base_url: str,
    limit: int = 100,
    level: str | None = None,
    source: str | None = None,
    since: datetime | None = None,
    grep: str | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch logs from the Event Manager using EventClient.

    Args:
        base_url: Base URL for the Event Manager.
        limit: Maximum number of events to retrieve.
        level: Minimum log level name (e.g. ``"error"``). Passed to
            EventClient and also applied by the caller via ``filter_logs``.
        source: Source service name. Not supported server-side; the caller
            applies this filter after fetching.
        since: Only return events after this datetime. Applied client-side.
        grep: Search pattern. Applied client-side by the caller via
            ``filter_logs``.
        timeout: Request timeout in seconds.

    Returns:
        List of log entry dictionaries.
    """
    try:
        client = EventClient(
            name="cli-logs",
            event_server_url=base_url,
        )

        # Map the level name to an int for EventClient (-1 means no filter)
        level_int = _LEVEL_NAME_TO_INT.get(level.lower(), -1) if level else -1

        events = client.get_events(
            number=limit,
            level=level_int,
            timeout=timeout,
        )

        # Convert Event models to plain dicts for the existing display logic
        entries = [event.model_dump(mode="json") for event in events.values()]

        # Apply client-side filters not supported by EventClient
        if source:
            entries = [e for e in entries if _extract_source_name(e) == source]
        if since:
            since_iso = since.isoformat()
            entries = [
                e for e in entries if (e.get("event_timestamp") or "") >= since_iso
            ]
        if grep:
            grep_lower = grep.lower()
            entries = [e for e in entries if grep_lower in _resolve_message(e).lower()]

        return entries
    except Exception:
        return []


def _extract_source_name(entry: dict[str, Any]) -> str:
    """Extract the source name string from an entry dict.

    Handles both string ``source`` values and nested OwnershipInfo dicts.

    Args:
        entry: A log entry dictionary.

    Returns:
        Source name string, or empty string if unavailable.
    """
    raw = entry.get("source", entry.get("service", entry.get("name", "")))
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("name", raw.get("component_name", ""))
    return str(raw)


def filter_logs(
    logs: list[dict[str, Any]],
    level: str | None = None,
    grep: str | None = None,
) -> list[dict[str, Any]]:
    """Filter logs locally."""
    result = logs

    if level:
        min_priority = LEVEL_PRIORITY.get(level.upper(), 0)
        result = [
            log
            for log in result
            if LEVEL_PRIORITY.get(_resolve_level_name(log), 0) >= min_priority
        ]

    if grep:
        try:
            pattern = re.compile(grep, re.IGNORECASE)
        except re.error as e:
            raise click.ClickException(f"Invalid regex pattern '{grep}': {e}") from e
        result = [log for log in result if pattern.search(_resolve_message(log))]

    return result


@click.command()
@click.argument("services", nargs=-1)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output (live updates).",
)
@click.option(
    "--tail",
    type=int,
    default=100,
    help="Show last N lines (default: 100).",
)
@click.option(
    "--since",
    type=str,
    help="Show logs since duration (e.g., '5m', '1h', '30s').",
)
@click.option(
    "--level",
    type=click.Choice(
        ["debug", "info", "warning", "error", "critical"], case_sensitive=False
    ),
    default=None,
    help="Minimum log level to show.",
)
@click.option(
    "--grep",
    type=str,
    help="Filter logs by pattern (regex supported).",
)
@click.option(
    "--timestamps/--no-timestamps",
    default=True,
    help="Show/hide timestamps.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.pass_context
def logs(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    services: tuple[str, ...],
    follow: bool,
    tail: int,
    since: str | None,
    level: str | None,
    grep: str | None,
    timestamps: bool,
    as_json: bool,
) -> None:
    """View logs from MADSci services.

    \b
    Examples:
        madsci logs                          Show recent logs
        madsci logs -f                       Follow log output
        madsci logs --tail 50                Show last 50 lines
        madsci logs --since 5m               Logs from last 5 minutes
        madsci logs --level error            Only show errors
        madsci logs --grep "workflow"        Filter by pattern
        madsci logs workcell_manager         Logs from specific service
        madsci --yaml logs                   Output as YAML
    """
    from rich.panel import Panel

    console = get_console(ctx)
    no_color = ctx.obj.get("no_color", False)

    # Merge local --json flag into ctx.obj so determine_output_format sees it
    if as_json:
        ctx.ensure_object(dict)
        ctx.obj["json"] = True

    fmt = determine_output_format(ctx)

    since_dt = None
    if since:
        try:
            since_dt = datetime.now() - parse_duration(since)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)

    context = ctx.obj.get("context")
    event_manager_url = (
        str(context.event_server_url)
        if context and context.event_server_url
        else DEFAULT_EVENT_MANAGER_URL
    )

    log_entries = fetch_logs_from_event_manager(
        base_url=event_manager_url,
        limit=tail,
        level=level,
        source=services[0] if len(services) == 1 else None,
        since=since_dt,
        grep=grep,
    )

    if not log_entries:
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            payload = {"logs": [], "message": "No logs available"}
            if fmt == OutputFormat.JSON:
                console.print_json(json.dumps(payload))
            else:
                output_result(console, payload, format="yaml")
        elif fmt == OutputFormat.QUIET:
            console.print("No logs available")
        else:
            console.print(
                Panel(
                    "[yellow]No logs available.[/yellow]\n\n"
                    "Possible reasons:\n"
                    "  \u2022 Event Manager is not running\n"
                    "  \u2022 No events have been logged yet\n"
                    "  \u2022 Filter criteria too restrictive\n\n"
                    "[dim]Start services with: madsci start lab[/dim]",
                    title="Logs",
                    border_style="yellow",
                )
            )
        return

    if services and len(services) > 1:
        log_entries = [
            entry
            for entry in log_entries
            if entry.get("source", entry.get("service", "")) in services
        ]

    log_entries = filter_logs(log_entries, level=level, grep=grep)

    # --- Structured output modes ---
    if fmt == OutputFormat.JSON:
        console.print_json(json.dumps({"logs": log_entries}))
        return
    if fmt == OutputFormat.YAML:
        output_result(console, {"logs": log_entries}, format="yaml")
        return
    if fmt == OutputFormat.QUIET:
        for entry in log_entries:
            lvl = _resolve_level_name(entry)
            msg = _resolve_message(entry)
            console.print(f"{lvl}: {msg}")
        return

    # --- Follow mode ---
    if follow:
        seen_ids: set[str] = set()
        for entry in log_entries:
            entry_id = entry.get("event_id", entry.get("id", str(hash(str(entry)))))
            seen_ids.add(entry_id)
            console.print(format_log_entry(entry, timestamps, no_color))

        console.print("[dim]Following logs... (Ctrl+C to stop)[/dim]")

        try:
            while True:
                time.sleep(2)
                new_entries = fetch_logs_from_event_manager(
                    base_url=event_manager_url,
                    limit=50,
                    level=level,
                    source=services[0] if len(services) == 1 else None,
                    grep=grep,
                )
                new_entries = filter_logs(new_entries, level=level, grep=grep)

                for entry in new_entries:
                    entry_id = entry.get(
                        "event_id", entry.get("id", str(hash(str(entry))))
                    )
                    if entry_id not in seen_ids:
                        seen_ids.add(entry_id)
                        console.print(format_log_entry(entry, timestamps, no_color))
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped following logs.[/dim]")
            return

    # --- Default table output ---
    for entry in log_entries:
        console.print(format_log_entry(entry, timestamps, no_color))

    console.print(f"\n[dim]Showing {len(log_entries)} log entries.[/dim]")
