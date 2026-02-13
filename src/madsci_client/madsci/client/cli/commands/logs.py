"""MADSci CLI logs command.

View and aggregate logs from MADSci services.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from typing import Any

import click

# Default Event Manager URL
DEFAULT_EVENT_MANAGER_URL = "http://localhost:8001/"

# Log level colors
LEVEL_COLORS = {
    "DEBUG": "dim",
    "INFO": "blue",
    "WARNING": "yellow",
    "WARN": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red",
}

# Log level priority for filtering
LEVEL_PRIORITY = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "WARN": 2,
    "ERROR": 3,
    "CRITICAL": 4,
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


def format_log_entry(
    entry: dict[str, Any],
    show_timestamps: bool = True,
    no_color: bool = False,
) -> Any:
    """Format a log entry for display."""
    from rich.text import Text

    text = Text()

    if show_timestamps:
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

            if not no_color:
                text.append(timestamp_str, style="dim")
            else:
                text.append(timestamp_str)
            text.append("  ")

    level = entry.get("level", entry.get("log_level", "INFO")).upper()
    level_str = f"{level:8}"
    if not no_color:
        level_style = LEVEL_COLORS.get(level, "")
        text.append(level_str, style=level_style)
    else:
        text.append(level_str)
    text.append("  ")

    source = entry.get("source", entry.get("service", entry.get("name", "")))
    if source:
        source_str = f"{source[:12]:12}"
        if not no_color:
            text.append(source_str, style="cyan")
        else:
            text.append(source_str)
        text.append("  ")

    message = entry.get("message", entry.get("msg", str(entry)))
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
    """Fetch logs from the Event Manager."""
    import httpx

    url = base_url.rstrip("/") + "/events"
    params: dict[str, Any] = {"limit": limit}

    if level:
        params["min_level"] = level.upper()
    if source:
        params["source"] = source
    if since:
        params["since"] = since.isoformat()
    if grep:
        params["search"] = grep

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "events" in data:
                    return data["events"]
                return []
            return []
    except Exception:
        return []


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
            if LEVEL_PRIORITY.get(
                log.get("level", log.get("log_level", "INFO")).upper(), 0
            )
            >= min_priority
        ]

    if grep:
        try:
            pattern = re.compile(grep, re.IGNORECASE)
        except re.error as e:
            raise click.ClickException(f"Invalid regex pattern '{grep}': {e}") from e
        result = [
            log
            for log in result
            if pattern.search(log.get("message", log.get("msg", str(log))))
        ]

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
def logs(  # noqa: C901, PLR0912
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
    """
    from madsci.client.cli.utils.output import get_console
    from rich.panel import Panel

    console = get_console(ctx)
    no_color = ctx.obj.get("no_color", False)

    since_dt = None
    if since:
        try:
            since_dt = datetime.now() - parse_duration(since)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            ctx.exit(1)

    cli_config = ctx.obj.get("config")
    event_manager_url = (
        str(cli_config.event_manager_url)
        if cli_config
        else ctx.obj.get("event_manager_url", DEFAULT_EVENT_MANAGER_URL)
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
        if as_json or ctx.obj.get("json"):
            console.print_json(json.dumps({"logs": [], "message": "No logs available"}))
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

    if as_json or ctx.obj.get("json"):
        console.print_json(json.dumps({"logs": log_entries}))
        return

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

    for entry in log_entries:
        console.print(format_log_entry(entry, timestamps, no_color))

    console.print(f"\n[dim]Showing {len(log_entries)} log entries.[/dim]")
