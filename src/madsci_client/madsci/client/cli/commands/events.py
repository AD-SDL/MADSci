"""MADSci CLI events command group.

Provides subcommands for event management: querying, viewing, archiving,
purging, and backup operations.
"""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from madsci.client.event_client import EventClient

import click
from madsci.client.cli.utils.cli_decorators import (
    resolve_service_url,
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import format_timestamp
from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    get_console,
    info,
    output_result,
    success,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_EVENT_URL_OPTION = click.option(
    "--event-url",
    envvar="MADSCI_EVENT_URL",
    default=None,
    help="Event manager URL (default: from config or http://localhost:8001/).",
)


def _get_event_url(ctx: click.Context, event_url: str | None) -> str:
    """Resolve the event URL from the option, context, or default."""
    return resolve_service_url(ctx, event_url, "event_server_url", 8001)


@contextlib.contextmanager
def _make_client(event_url: str, timeout: float) -> Iterator[EventClient]:
    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import EventClientConfig

    config = EventClientConfig(timeout_default=timeout)
    client = EventClient(event_server_url=event_url, config=config)
    try:
        yield client
    finally:
        client.close()


def _event_to_row(event) -> dict:  # noqa: ANN001
    """Convert an Event to a dict for table rendering."""
    source_name = ""
    if event.source:
        source_name = getattr(event.source, "component_name", None) or ""
    return {
        "timestamp": format_timestamp(event.event_timestamp),
        "level": event.log_level.name
        if hasattr(event.log_level, "name")
        else str(event.log_level),
        "source": source_name or "-",
        "message": str(event.event_data)[:80] if event.event_data else "-",
    }


def _event_to_dict(event) -> dict:  # noqa: ANN001
    """Convert an Event to a serialisable dict for JSON/YAML output."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value
        if hasattr(event.event_type, "value")
        else str(event.event_type),
        "log_level": event.log_level.name
        if hasattr(event.log_level, "name")
        else str(event.log_level),
        "event_timestamp": str(event.event_timestamp),
        "event_data": event.event_data,
        "archived": event.archived,
    }


_LIST_COLUMNS = [
    ColumnDef("Timestamp", "timestamp", style="dim"),
    ColumnDef("Level", "level"),
    ColumnDef("Source", "source", style="cyan"),
    ColumnDef("Message", "message", max_width=80),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def events() -> None:
    """Manage events.

    \b
    Examples:
        madsci events query                     Query recent events
        madsci events get <id>                  Show event details
        madsci events archive --ids <id1,id2>   Archive specific events
        madsci events purge --older-than-days 30
        madsci events backup --create           Create event backup
    """


# ---------------------------------------------------------------------------
# events query
# ---------------------------------------------------------------------------


@events.command("query")
@click.option(
    "--selector",
    default=None,
    help="MongoDB-style query selector as a JSON string.",
)
@click.option(
    "--count",
    type=int,
    default=100,
    show_default=True,
    help="Number of events to retrieve.",
)
@click.option(
    "--level",
    default=None,
    help="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
)
@_EVENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def query_events(
    ctx: click.Context,
    selector: str | None,
    count: int,
    level: str | None,
    event_url: str | None,
    timeout: float,
) -> None:
    """Query events from the event manager.

    Without --selector, retrieves recent events. With --selector, runs
    a MongoDB-style query.

    \b
    Examples:
        madsci events query
        madsci events query --count 50
        madsci events query --level ERROR
        madsci events query --selector '{"event_type": "WORKFLOW_START"}'
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_event_url(ctx, event_url)

    with _make_client(url, timeout) as client:
        if selector:
            try:
                parsed_selector = json.loads(selector)
            except json.JSONDecodeError as exc:
                raise click.ClickException(
                    f"Invalid JSON in --selector: {exc}"
                ) from exc
            results = client.query_events(parsed_selector)
        else:
            level_int = -1
            if level:
                import logging

                level_int = getattr(logging, level.upper(), -1)
            results = client.get_events(number=count, level=level_int)

    # results is a dict[str, Event]
    event_list = list(results.values()) if isinstance(results, dict) else results

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_event_to_dict(e) for e in event_list]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for e in event_list:
            console.print(f"{e.event_id}")
        return

    if not event_list:
        info(console, "No events found.")
        return

    rows = [_event_to_row(e) for e in event_list]
    output_result(console, rows, format="text", title="Events", columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# events get
# ---------------------------------------------------------------------------


@events.command("get")
@click.argument("event_id")
@_EVENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def get_event(
    ctx: click.Context,
    event_id: str,
    event_url: str | None,
    timeout: float,
) -> None:
    """Show details of a single event.

    \b
    Examples:
        madsci events get 01J5ABCDEF12
        madsci events get 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_event_url(ctx, event_url)

    with _make_client(url, timeout) as client:
        event = client.get_event(event_id)
        if event is None:
            raise click.ClickException(f"Event {event_id} not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, event, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{event.event_id}")
    else:
        output_result(console, _event_to_dict(event), format="text", title="Event")


# ---------------------------------------------------------------------------
# events archive
# ---------------------------------------------------------------------------


@events.command("archive")
@click.option(
    "--before-date",
    default=None,
    help="Archive events before this date (ISO format, e.g. 2026-01-01).",
)
@click.option(
    "--ids",
    default=None,
    help="Comma-separated list of event IDs to archive.",
)
@_EVENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def archive_events(
    ctx: click.Context,
    before_date: str | None,
    ids: str | None,
    event_url: str | None,
    timeout: float,
) -> None:
    """Archive events.

    Archive events by date or by specific IDs. Archived events are
    soft-deleted and can be purged later.

    \b
    Examples:
        madsci events archive --before-date 2026-01-01
        madsci events archive --ids "id1,id2,id3"
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_event_url(ctx, event_url)

    if not before_date and not ids:
        raise click.ClickException("Provide --before-date or --ids.")

    event_ids_list = [i.strip() for i in ids.split(",")] if ids else None

    with _make_client(url, timeout) as client:
        result = client.archive_events(
            before_date=before_date,
            event_ids=event_ids_list,
            timeout=timeout,
        )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    else:
        archived_count = (
            result.get("archived_count", 0) if isinstance(result, dict) else 0
        )
        success(console, f"Archived {archived_count} event(s).")


# ---------------------------------------------------------------------------
# events purge
# ---------------------------------------------------------------------------


@events.command("purge")
@click.option(
    "--older-than-days",
    type=int,
    default=30,
    show_default=True,
    help="Purge archived events older than this many days.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@_EVENT_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def purge_events(
    ctx: click.Context,
    older_than_days: int,
    yes: bool,
    event_url: str | None,
    timeout: float,
) -> None:
    """Purge archived events.

    Permanently deletes archived events older than the specified number of days.

    \b
    Examples:
        madsci events purge
        madsci events purge --older-than-days 7
        madsci events purge --older-than-days 90 --yes
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_event_url(ctx, event_url)

    if not yes:
        click.confirm(
            f"Permanently delete archived events older than {older_than_days} days?",
            abort=True,
        )

    with _make_client(url, timeout) as client:
        result = client.purge_events(older_than_days=older_than_days, timeout=timeout)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    else:
        purged_count = result.get("purged_count", 0) if isinstance(result, dict) else 0
        success(console, f"Purged {purged_count} archived event(s).")


# ---------------------------------------------------------------------------
# events backup
# ---------------------------------------------------------------------------


@events.command("backup")
@click.option("--create", "do_create", is_flag=True, help="Create a new event backup.")
@click.option("--status", "show_status", is_flag=True, help="Show backup status.")
@_EVENT_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def backup_events(
    ctx: click.Context,
    do_create: bool,
    show_status: bool,
    event_url: str | None,
    timeout: float,
) -> None:
    """Manage event backups.

    \b
    Examples:
        madsci events backup --create
        madsci events backup --status
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_event_url(ctx, event_url)

    if not do_create and not show_status:
        raise click.ClickException("Provide --create or --status.")

    with _make_client(url, timeout) as client:
        if show_status:
            result = client.get_backup_status(timeout=timeout)
            if fmt in (OutputFormat.JSON, OutputFormat.YAML):
                output_result(console, result, format=fmt.value)
            else:
                output_result(console, result, format="text", title="Backup Status")
            return

        if do_create:
            result = client.create_backup(timeout=timeout)
            if fmt in (OutputFormat.JSON, OutputFormat.YAML):
                output_result(console, result, format=fmt.value)
            else:
                success(console, "Event backup created.")
