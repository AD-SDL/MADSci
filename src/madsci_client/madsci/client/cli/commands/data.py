"""MADSci CLI data command group.

Provides subcommands for managing datapoints: listing, viewing, submitting,
querying metadata, and downloading data from the Data Manager.
"""

from __future__ import annotations

import json
from pathlib import Path

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

_DATA_URL_OPTION = click.option(
    "--data-url",
    envvar="MADSCI_DATA_URL",
    default=None,
    help="Data manager URL (default: from config or http://localhost:8004/).",
)


def _get_data_url(ctx: click.Context, data_url: str | None) -> str:
    """Resolve the data URL from the option, context, or default."""
    return resolve_service_url(ctx, data_url, "data_server_url", 8004)


def _make_client(data_url: str, timeout: float) -> DataClient:  # noqa: F821 -- lazy import
    from madsci.client.data_client import DataClient
    from madsci.common.types.client_types import DataClientConfig

    config = DataClientConfig(timeout_default=timeout)
    return DataClient(data_server_url=data_url, config=config)


def _datapoint_to_row(dp) -> dict:  # noqa: ANN001
    """Convert a DataPoint to a dict for table rendering."""
    return {
        "id": dp.datapoint_id or "-",
        "label": getattr(dp, "label", None) or "-",
        "type": dp.data_type or "-",
        "timestamp": format_timestamp(getattr(dp, "data_timestamp", None)),
        "size": str(getattr(dp, "size_bytes", "-")),
    }


def _datapoint_to_dict(dp) -> dict:  # noqa: ANN001
    """Convert a DataPoint to a serialisable dict for JSON/YAML output."""
    return {
        "datapoint_id": dp.datapoint_id,
        "label": getattr(dp, "label", None),
        "data_type": dp.data_type,
        "data_timestamp": str(getattr(dp, "data_timestamp", None)),
        "size_bytes": getattr(dp, "size_bytes", None),
    }


_LIST_COLUMNS = [
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Label", "label", style="cyan"),
    ColumnDef("Type", "type"),
    ColumnDef("Timestamp", "timestamp", style="dim"),
    ColumnDef("Size", "size"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def data() -> None:
    """Manage datapoints.

    \b
    Examples:
        madsci data list                         List recent datapoints
        madsci data get <id>                     Get datapoint value
        madsci data metadata <id>                Show datapoint metadata
        madsci data submit --file ./results.csv  Submit a file datapoint
        madsci data submit --value '{"a": 1}'    Submit a JSON value
        madsci data query --selector '{"label": "test"}'
    """


# ---------------------------------------------------------------------------
# data list
# ---------------------------------------------------------------------------


@data.command("list")
@click.option(
    "--count",
    type=int,
    default=20,
    show_default=True,
    help="Number of datapoints to retrieve.",
)
@_DATA_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_datapoints(
    ctx: click.Context,
    count: int,
    data_url: str | None,
    timeout: float,
) -> None:
    """List recent datapoints.

    \b
    Examples:
        madsci data list
        madsci data list --count 50
        madsci data list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_data_url(ctx, data_url)
    client = _make_client(url, timeout)

    datapoints = client.get_datapoints(number=count)

    if not datapoints:
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            output_result(console, [], format=fmt.value)
        else:
            info(console, "No datapoints found.")
        return

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        rows = [_datapoint_to_dict(dp) for dp in datapoints]
        output_result(console, rows, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for dp in datapoints:
            console.print(f"{dp.datapoint_id} {dp.data_type}")
        return

    rows = [_datapoint_to_row(dp) for dp in datapoints]
    output_result(
        console, rows, format="text", title="Datapoints", columns=_LIST_COLUMNS
    )


# ---------------------------------------------------------------------------
# data get
# ---------------------------------------------------------------------------


@data.command("get")
@click.argument("datapoint_id")
@click.option(
    "--save-to",
    "save_to",
    type=click.Path(),
    default=None,
    help="Save datapoint value to a file instead of printing.",
)
@_DATA_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def get_datapoint(
    ctx: click.Context,
    datapoint_id: str,
    save_to: str | None,
    data_url: str | None,
    timeout: float,
) -> None:
    """Get a datapoint value.

    Prints the JSON value or downloads the file content. Use --save-to to
    write the value to a file.

    \b
    Examples:
        madsci data get 01J5ABCDEF12
        madsci data get 01J5ABCDEF12 --save-to ./output.json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_data_url(ctx, data_url)
    client = _make_client(url, timeout)

    if save_to:
        client.save_datapoint_value(datapoint_id, save_to)
        success(console, f"Datapoint saved to {save_to}")
        return

    value = client.get_datapoint_value(datapoint_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, value, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(str(value)[:200])
    # If it's a dict/list, print as JSON; otherwise print raw
    elif isinstance(value, (dict, list)):
        output_result(console, value, format="json")
    else:
        console.print(str(value))


# ---------------------------------------------------------------------------
# data metadata
# ---------------------------------------------------------------------------


@data.command("metadata")
@click.argument("datapoint_id")
@_DATA_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def datapoint_metadata(
    ctx: click.Context,
    datapoint_id: str,
    data_url: str | None,
    timeout: float,
) -> None:
    """Show metadata for a datapoint.

    Displays ID, label, type, timestamp, size, content_type, and ownership
    without fetching the full data content.

    \b
    Examples:
        madsci data metadata 01J5ABCDEF12
        madsci data metadata 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_data_url(ctx, data_url)
    client = _make_client(url, timeout)

    meta = client.get_datapoint_metadata(datapoint_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, meta, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{datapoint_id}")
    else:
        output_result(console, meta, format="text", title="Datapoint Metadata")


# ---------------------------------------------------------------------------
# data submit
# ---------------------------------------------------------------------------


@data.command("submit")
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a file to submit as a datapoint.",
)
@click.option(
    "--value",
    "json_value",
    default=None,
    help="JSON value to submit as a datapoint.",
)
@click.option("--label", default=None, help="Label for the datapoint.")
@_DATA_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def submit_datapoint(
    ctx: click.Context,
    file_path: str | None,
    json_value: str | None,
    label: str | None,
    data_url: str | None,
    timeout: float,
) -> None:
    """Submit a datapoint.

    Use --file to submit a file datapoint, or --value to submit a JSON value.
    These options are mutually exclusive.

    \b
    Examples:
        madsci data submit --file ./results.csv --label "experiment results"
        madsci data submit --value '{"temperature": 25.3}' --label "sensor reading"
    """
    from madsci.common.types.datapoint_types import DataPoint

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_data_url(ctx, data_url)
    client = _make_client(url, timeout)

    if file_path and json_value:
        raise click.ClickException("--file and --value are mutually exclusive.")
    if not file_path and not json_value:
        raise click.ClickException("Provide either --file or --value.")

    if file_path:
        dp = DataPoint.discriminate(
            {
                "data_type": "file",
                "path": str(Path(file_path).resolve()),
                "label": label,
            }
        )
    else:
        try:
            parsed_value = json.loads(json_value)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --value: {exc}") from exc
        dp = DataPoint.discriminate(
            {
                "data_type": "json",
                "value": parsed_value,
                "label": label,
            }
        )

    result = client.submit_datapoint(dp)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(result.datapoint_id)
    else:
        success(console, f"Datapoint submitted -- ID: {result.datapoint_id}")


# ---------------------------------------------------------------------------
# data query
# ---------------------------------------------------------------------------


@data.command("query")
@click.option(
    "--selector",
    required=True,
    help="MongoDB-style query selector as a JSON string.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of results.",
)
@_DATA_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def query_datapoints(
    ctx: click.Context,
    selector: str,
    limit: int | None,
    data_url: str | None,
    timeout: float,
) -> None:
    """Query datapoints with a MongoDB-style selector.

    \b
    Examples:
        madsci data query --selector '{"label": "temperature"}'
        madsci data query --selector '{"data_type": "file"}' --limit 10
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_data_url(ctx, data_url)
    client = _make_client(url, timeout)

    try:
        parsed_selector = json.loads(selector)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in --selector: {exc}") from exc

    results = client.query_datapoints(parsed_selector)

    # results is a dict[str, DataPoint]
    datapoints = list(results.values()) if isinstance(results, dict) else results
    if limit:
        datapoints = datapoints[:limit]

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        rows = [_datapoint_to_dict(dp) for dp in datapoints]
        output_result(console, rows, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for dp in datapoints:
            console.print(f"{dp.datapoint_id} {dp.data_type}")
        return

    if not datapoints:
        info(console, "No datapoints matched the query.")
        return

    rows = [_datapoint_to_row(dp) for dp in datapoints]
    output_result(
        console, rows, format="text", title="Query Results", columns=_LIST_COLUMNS
    )
