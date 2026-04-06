"""MADSci CLI node command group.

Provides subcommands for node inspection, control, and interaction:
listing, info, status, state, log, admin commands, action execution,
action results, action history, config management, adding nodes, and
an interactive shell.
"""

from __future__ import annotations

import cmd
import json
from typing import Any, Callable

import click
from madsci.client.cli.utils.cli_decorators import (
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import (
    format_status_colored,
    format_status_icon,
    format_timestamp,
    truncate,
)
from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    error,
    get_console,
    info,
    output_result,
    success,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_WORKCELL_URL_OPTION = click.option(
    "--workcell-url",
    envvar="MADSCI_WORKCELL_URL",
    default=None,
    help="Workcell manager URL (default: from config or http://localhost:8005/).",
)


def _get_workcell_url(ctx: click.Context, workcell_url: str | None) -> str:
    """Resolve the workcell URL from the option, context, or default."""
    if workcell_url:
        return workcell_url
    context = ctx.obj.get("context") if ctx.obj else None
    if context and context.workcell_server_url:
        return str(context.workcell_server_url)
    return "http://localhost:8005/"


def _make_workcell_client(workcell_url: str, timeout: float) -> Any:
    """Create a WorkcellClient configured with the given URL and timeout."""
    from madsci.client.workcell_client import WorkcellClient
    from madsci.common.types.client_types import WorkcellClientConfig

    config = WorkcellClientConfig(timeout_default=timeout)
    return WorkcellClient(workcell_server_url=workcell_url, config=config)


def _get_node_client(
    workcell_url: str, node_name: str, timeout: float
) -> tuple[Any, dict]:
    """Discover node via workcell and return (RestNodeClient, node_data).

    The node data returned by ``WorkcellClient.get_node`` may be a dict
    or a Pydantic model -- callers should handle both.
    """
    from madsci.client.node.rest_node_client import RestNodeClient

    wc = _make_workcell_client(workcell_url, timeout)
    node = wc.get_node(node_name)
    if node is None:
        raise click.ClickException(f"Node '{node_name}' not found.")

    # Extract node_url from dict or model
    if hasattr(node, "node_url"):
        node_url = str(node.node_url)
    elif isinstance(node, dict):
        node_url = str(node.get("node_url", ""))
    else:
        raise click.ClickException(f"Unable to determine URL for node '{node_name}'.")

    if not node_url:
        raise click.ClickException(f"Node '{node_name}' has no URL configured.")

    return RestNodeClient(url=node_url), node


def _node_to_dict(node: Any) -> dict:
    """Convert a node to a serialisable dict for JSON/YAML output."""
    if hasattr(node, "model_dump"):
        return node.model_dump(mode="json")
    if isinstance(node, dict):
        return node
    return {"node": str(node)}


def _flag_badge(flag: bool) -> str:
    """Return a coloured yes/no indicator for a boolean flag."""
    if flag:
        return "[green]yes[/green]"
    return "[dim]no[/dim]"


def _extract_attr(obj: Any, key: str, default: Any = "-") -> Any:
    """Extract a value from a dict or model attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _node_to_row(name: str, n: Any) -> dict:
    """Convert a node entry (dict or model) into a table row dict."""
    n_url = _extract_attr(n, "node_url", "-")
    status = _extract_attr(n, "status", None) or {}
    node_info = _extract_attr(n, "info", None)

    is_ready = _extract_attr(status, "ready", False)
    is_errored = _extract_attr(status, "errored", False)
    is_disconnected = _extract_attr(status, "disconnected", False)

    status_label = _derive_status_label(is_ready, is_errored, is_disconnected)
    action_count = _count_actions(node_info)

    return {
        "status": f"{format_status_icon(status_label)} {format_status_colored(status_label)}",
        "name": truncate(str(name), 30),
        "url": truncate(str(n_url), 40),
        "actions": str(action_count),
        "ready": "yes" if is_ready else "no",
    }


def _derive_status_label(
    is_ready: bool, is_errored: bool, is_disconnected: bool
) -> str:
    """Derive a human-friendly status label from node flags."""
    if is_disconnected:
        return "disconnected"
    if is_errored:
        return "errored"
    if is_ready:
        return "healthy"
    return "unhealthy"


def _count_actions(node_info: Any) -> int:
    """Count the actions available on a node from its info."""
    if node_info is None:
        return 0
    actions = _extract_attr(node_info, "actions", {}) or {}
    return len(actions)


def _extract_info_fields(node_data: Any, name: str) -> dict:
    """Extract key info fields from node_data (dict or model) for display."""
    node_info = _extract_attr(node_data, "info", None) or {}
    node_url = _extract_attr(node_data, "node_url", "-")

    node_name = _extract_attr(node_info, "node_name", name)
    node_id = _extract_attr(node_info, "node_id", "-")
    node_type = _extract_attr(node_info, "node_type", "-")
    if hasattr(node_type, "value"):
        node_type = node_type.value
    module_name = _extract_attr(node_info, "module_name", "-")
    module_version = _extract_attr(node_info, "module_version", "-")
    actions = _extract_attr(node_info, "actions", {}) or {}
    capabilities = _extract_attr(node_info, "capabilities", None)

    return {
        "node_name": node_name,
        "node_id": node_id,
        "node_type": node_type,
        "module_name": module_name,
        "module_version": module_version,
        "node_url": node_url,
        "actions": actions,
        "capabilities": capabilities,
    }


# ---------------------------------------------------------------------------
# Column definitions (module-level)
# ---------------------------------------------------------------------------

_LIST_COLUMNS = [
    ColumnDef("Status", "status"),
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("URL", "url"),
    ColumnDef("Actions", "actions"),
    ColumnDef("Ready", "ready"),
]

_LOG_COLUMNS = [
    ColumnDef("Time", "time", style="dim"),
    ColumnDef("Level", "level"),
    ColumnDef("Message", "message"),
]

_HISTORY_COLUMNS = [
    ColumnDef("Action", "action"),
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Status", "status"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def node() -> None:
    """Manage nodes.

    \b
    Examples:
        madsci node list                         List all nodes
        madsci node info <name>                  Show node details
        madsci node status <name>                Show node status
        madsci node state <name>                 Show node state
        madsci node log <name>                   Show node events
        madsci node admin <name> <command>       Send admin command
        madsci node action <name> <action>       Execute an action
        madsci node action-result <name> <id>    Get action result
        madsci node action-history <name>        Show action history
        madsci node config <name>                Show node config
        madsci node set-config <name> --data {}  Update node config
        madsci node add <name> <url>             Add node to workcell
        madsci node shell <name>                 Interactive REPL
    """


# ---------------------------------------------------------------------------
# node list
# ---------------------------------------------------------------------------


@node.command("list")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_nodes(
    ctx: click.Context,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """List all nodes in the workcell.

    \b
    Examples:
        madsci node list
        madsci node list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    client = _make_workcell_client(url, timeout)

    nodes = client.get_nodes()
    if not isinstance(nodes, dict):
        nodes = {}

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, nodes, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for name in nodes:
            console.print(name)
        return

    if not nodes:
        info(console, "No nodes found.")
        return

    rows = [_node_to_row(name, n) for name, n in nodes.items()]
    output_result(console, rows, format="text", title="Nodes", columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# node info
# ---------------------------------------------------------------------------


def _render_info_detail(console: Any, fields: dict) -> None:
    """Render the detailed info section for a node."""
    console.print()
    console.print(f"[bold]{fields['node_name']}[/bold]")
    console.print(f"  ID:             {fields['node_id']}")
    console.print(f"  Type:           {fields['node_type']}")
    console.print(f"  Module:         {fields['module_name']}")
    console.print(f"  Version:        {fields['module_version']}")
    console.print(f"  URL:            {fields['node_url']}")

    actions = fields.get("actions", {})
    if actions and isinstance(actions, dict):
        console.print()
        console.print("[bold]Actions:[/bold]")
        for action_name, action_def in actions.items():
            desc = _extract_attr(action_def, "description", "")
            desc_str = f" -- {desc}" if desc else ""
            console.print(f"  {action_name}{desc_str}")

    capabilities = fields.get("capabilities")
    if capabilities:
        console.print()
        console.print("[bold]Capabilities:[/bold]")
        cap_dict = (
            capabilities.model_dump(mode="json")
            if hasattr(capabilities, "model_dump")
            else capabilities
        )
        if isinstance(cap_dict, dict):
            for cap_name, cap_val in cap_dict.items():
                if cap_val is not None:
                    console.print(f"  {cap_name}: {_flag_badge(bool(cap_val))}")

    console.print()


@node.command("info")
@click.argument("name")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def info_node(
    ctx: click.Context,
    name: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show detailed information about a node.

    \b
    Examples:
        madsci node info my_robot
        madsci node info my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    wc = _make_workcell_client(url, timeout)

    node_data = wc.get_node(name)
    if node_data is None:
        raise click.ClickException(f"Node '{name}' not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _node_to_dict(node_data), format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(name)
        return

    fields = _extract_info_fields(node_data, name)
    _render_info_detail(console, fields)


# ---------------------------------------------------------------------------
# node status
# ---------------------------------------------------------------------------


@node.command("status")
@click.argument("name")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def status_node(
    ctx: click.Context,
    name: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show the current status of a node.

    Displays status flags: ready, busy, paused, locked, stopped, errored,
    disconnected, along with running actions and errors.

    \b
    Examples:
        madsci node status my_robot
        madsci node status my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    status = node_client.get_status()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            status.model_dump(mode="json") if hasattr(status, "model_dump") else status
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        ready = getattr(status, "ready", False)
        console.print(f"{name} {'ready' if ready else 'not_ready'}")
        return

    console.print()
    console.print(f"[bold]Status: {name}[/bold]")

    flags = [
        ("ready", getattr(status, "ready", False)),
        ("busy", getattr(status, "busy", False)),
        ("paused", getattr(status, "paused", False)),
        ("locked", getattr(status, "locked", False)),
        ("stopped", getattr(status, "stopped", False)),
        ("errored", getattr(status, "errored", False)),
        ("disconnected", getattr(status, "disconnected", False)),
        ("initializing", getattr(status, "initializing", False)),
    ]

    for label, flag in flags:
        console.print(f"  {label:15s} {_flag_badge(flag)}")

    # Running actions
    running = getattr(status, "running_actions", set())
    if running:
        console.print()
        console.print("[bold]Running Actions:[/bold]")
        for action_id in running:
            console.print(f"  {action_id}")

    # Errors
    errors = getattr(status, "errors", [])
    if errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for err in errors:
            err_str = str(err)
            console.print(f"  [red]{err_str}[/red]")

    # Description
    desc = getattr(status, "description", None)
    if desc:
        console.print()
        console.print(f"  [dim]{desc}[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# node state
# ---------------------------------------------------------------------------


@node.command("state")
@click.argument("name")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def state_node(
    ctx: click.Context,
    name: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show the custom state dict of a node.

    \b
    Examples:
        madsci node state my_robot
        madsci node state my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    state = node_client.get_state()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, state, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(json.dumps(state, default=str))
        return

    if not state:
        info(console, f"Node '{name}' has no state data.")
        return

    console.print()
    console.print(f"[bold]State: {name}[/bold]")
    output_result(console, state, format="text", title=f"State: {name}")
    console.print()


# ---------------------------------------------------------------------------
# node log
# ---------------------------------------------------------------------------


def _log_entry_to_row(entry: Any) -> dict:
    """Convert a single log entry to a table row dict."""
    if isinstance(entry, dict):
        return {
            "time": format_timestamp(
                entry.get("timestamp", entry.get("event_timestamp"))
            ),
            "level": entry.get("event_type", entry.get("level", "-")),
            "message": truncate(
                str(entry.get("message", entry.get("event_message", "-"))), 80
            ),
        }
    return {"time": "-", "level": "-", "message": truncate(str(entry), 80)}


@node.command("log")
@click.argument("name")
@click.option(
    "--tail",
    "tail_count",
    type=int,
    default=20,
    show_default=True,
    help="Number of recent log entries to show.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def log_node(
    ctx: click.Context,
    name: str,
    tail_count: int,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show node event log.

    \b
    Examples:
        madsci node log my_robot
        madsci node log my_robot --tail 50
        madsci node log my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    log_data = node_client.get_log()

    # Log may be a dict of {id: event} or a list
    if isinstance(log_data, dict):
        entries = list(log_data.values())
    elif isinstance(log_data, list):
        entries = log_data
    else:
        entries = []

    entries = entries[-tail_count:]

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, entries, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for entry in entries:
            msg = (
                entry.get("message", str(entry))
                if isinstance(entry, dict)
                else str(entry)
            )
            console.print(msg)
        return

    if not entries:
        info(console, f"No log entries for node '{name}'.")
        return

    rows = [_log_entry_to_row(entry) for entry in entries]
    output_result(
        console, rows, format="text", title=f"Log: {name}", columns=_LOG_COLUMNS
    )


# ---------------------------------------------------------------------------
# node admin
# ---------------------------------------------------------------------------


@node.command("admin")
@click.argument("name")
@click.argument(
    "command",
    type=click.Choice(
        [
            "safety_stop",
            "reset",
            "pause",
            "resume",
            "cancel",
            "shutdown",
            "lock",
            "unlock",
        ],
        case_sensitive=False,
    ),
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def admin_node(
    ctx: click.Context,
    name: str,
    command: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Send an admin command to a node.

    \b
    Valid commands: safety_stop, reset, pause, resume, cancel,
                    shutdown, lock, unlock

    \b
    Examples:
        madsci node admin my_robot pause
        madsci node admin my_robot reset
        madsci node admin my_robot safety_stop
    """
    from madsci.common.types.admin_command_types import AdminCommands

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    admin_cmd = AdminCommands(command)
    response = node_client.send_admin_command(admin_cmd)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else response
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        ok = getattr(response, "success", True)
        console.print(f"{name} {command} {'ok' if ok else 'failed'}")
        return

    ok = getattr(response, "success", True)
    if ok:
        success(console, f"Admin command '{command}' sent to node '{name}'.")
    else:
        errors_list = getattr(response, "errors", [])
        error(console, f"Admin command '{command}' failed on node '{name}'.")
        for err in errors_list:
            console.print(f"  [red]{err}[/red]")


# ---------------------------------------------------------------------------
# node action
# ---------------------------------------------------------------------------


def _render_action_result(
    console: Any, fmt: OutputFormat, result: Any, action_name: str
) -> None:
    """Render an action result in the requested output format."""
    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        action_id = getattr(result, "action_id", "-")
        status_val = getattr(result, "status", "-")
        console.print(f"{action_id} {status_val}")
        return

    action_id = getattr(result, "action_id", "-")
    status_val = getattr(result, "status", "-")
    if hasattr(status_val, "value"):
        status_val = status_val.value

    success(
        console,
        f"Action '{action_name}' -- ID: {action_id}, status: {status_val}",
    )

    json_result = getattr(result, "json_result", None)
    if json_result is not None:
        console.print()
        console.print("[bold]Result Data:[/bold]")
        console.print_json(json.dumps(json_result, default=str))

    result_errors = getattr(result, "errors", [])
    if result_errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for err in result_errors:
            console.print(f"  [red]{err}[/red]")


@node.command("action")
@click.argument("name")
@click.argument("action_name")
@click.option(
    "--args",
    "args_json",
    default=None,
    help="Action arguments as a JSON string.",
)
@click.option(
    "--file",
    "files",
    multiple=True,
    help="File arguments as param=path (can be repeated).",
)
@click.option(
    "--no-wait",
    is_flag=True,
    help="Submit action and return immediately.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=30.0)
@click.pass_context
@with_service_error_handling
def action_node(
    ctx: click.Context,
    name: str,
    action_name: str,
    args_json: str | None,
    files: tuple[str, ...],
    no_wait: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Execute an action on a node.

    \b
    Examples:
        madsci node action my_robot pick --args '{"plate_id": "p1"}'
        madsci node action my_robot transfer --file input=/path/to/file.csv
        madsci node action my_robot measure --no-wait
    """
    from madsci.common.types.action_types import ActionRequest

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    # Parse args
    action_args: dict = {}
    if args_json:
        try:
            action_args = json.loads(args_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --args: {exc}") from exc

    # Parse file arguments
    action_files: dict = {}
    for file_spec in files:
        if "=" not in file_spec:
            raise click.ClickException(
                f"Invalid --file format: '{file_spec}'. Expected param=path."
            )
        param, path = file_spec.split("=", 1)
        action_files[param] = path

    request = ActionRequest(
        action_name=action_name,
        args=action_args,
        files=action_files,
    )

    if not no_wait:
        console.print(f"Executing action '{action_name}' on node '{name}'...")

    result = node_client.send_action(request, await_result=not no_wait)
    _render_action_result(console, fmt, result, action_name)


# ---------------------------------------------------------------------------
# node action-result
# ---------------------------------------------------------------------------


@node.command("action-result")
@click.argument("name")
@click.argument("action_id")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def action_result_node(
    ctx: click.Context,
    name: str,
    action_id: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Get the result of a previous action.

    \b
    Examples:
        madsci node action-result my_robot 01J5ABCDEF12
        madsci node action-result my_robot 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    result = node_client.get_action_result(action_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        status_val = getattr(result, "status", "-")
        console.print(f"{action_id} {status_val}")
        return

    status_val = getattr(result, "status", "-")
    if hasattr(status_val, "value"):
        status_val = status_val.value

    console.print()
    console.print(f"[bold]Action Result: {action_id}[/bold]")
    console.print(f"  Status: {status_val}")

    json_result = getattr(result, "json_result", None)
    if json_result is not None:
        console.print()
        console.print("[bold]Result Data:[/bold]")
        console.print_json(json.dumps(json_result, default=str))

    result_errors = getattr(result, "errors", [])
    if result_errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for err in result_errors:
            console.print(f"  [red]{err}[/red]")

    console.print()


# ---------------------------------------------------------------------------
# node action-history
# ---------------------------------------------------------------------------


def _history_to_rows(history: dict) -> list[dict]:
    """Convert action history dict to a list of table rows."""
    rows = []
    for action_name_key, results in history.items():
        result_list = results if isinstance(results, list) else [results]
        for r in result_list:
            rid = str(_extract_attr(r, "action_id", "-"))[:12]
            st = str(_extract_attr(r, "status", "-"))
            rows.append({"action": action_name_key, "id": rid, "status": st})
    return rows


@node.command("action-history")
@click.argument("name")
@click.option(
    "--action",
    "action_filter",
    default=None,
    help="Filter by action name.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def action_history_node(
    ctx: click.Context,
    name: str,
    action_filter: str | None,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show action history for a node.

    \b
    Examples:
        madsci node action-history my_robot
        madsci node action-history my_robot --action pick
        madsci node action-history my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    history = node_client.get_action_history(action_id=action_filter)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, history, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        if isinstance(history, dict):
            for action_name_key, results in history.items():
                for r in results if isinstance(results, list) else [results]:
                    rid = _extract_attr(r, "action_id", "-")
                    console.print(f"{action_name_key} {rid}")
        return

    if not history:
        info(console, f"No action history for node '{name}'.")
        return

    rows = _history_to_rows(history) if isinstance(history, dict) else []
    output_result(
        console,
        rows,
        format="text",
        title=f"Action History: {name}",
        columns=_HISTORY_COLUMNS,
    )


# ---------------------------------------------------------------------------
# node config
# ---------------------------------------------------------------------------


@node.command("config")
@click.argument("name")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def config_node(
    ctx: click.Context,
    name: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Show the current configuration of a node.

    \b
    Examples:
        madsci node config my_robot
        madsci node config my_robot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    wc = _make_workcell_client(url, timeout)

    node_data = wc.get_node(name)
    if node_data is None:
        raise click.ClickException(f"Node '{name}' not found.")

    # Extract config from node info
    node_info = _extract_attr(node_data, "info", None) or {}
    config = _extract_attr(node_info, "config", None)

    if config is None:
        info(console, f"No configuration available for node '{name}'.")
        return

    # Serialize config
    if hasattr(config, "model_dump"):
        config_data = config.model_dump(mode="json")
    elif isinstance(config, dict):
        config_data = config
    else:
        config_data = {"config": str(config)}

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, config_data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(json.dumps(config_data, default=str))
        return

    output_result(console, config_data, format="text", title=f"Config: {name}")


# ---------------------------------------------------------------------------
# node set-config
# ---------------------------------------------------------------------------


@node.command("set-config")
@click.argument("name")
@click.option(
    "--data",
    "data_json",
    required=True,
    help="Configuration data as a JSON string.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def set_config_node(
    ctx: click.Context,
    name: str,
    data_json: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Update the configuration of a node.

    \b
    Examples:
        madsci node set-config my_robot --data '{"speed": 100}'
        madsci node set-config my_robot --data '{"timeout": 30}' --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_workcell_url(ctx, workcell_url)
    node_client, _node_data = _get_node_client(url, name, timeout)

    try:
        config_dict = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in --data: {exc}") from exc

    response = node_client.set_config(config_dict)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else response
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        ok = getattr(response, "success", True)
        console.print(f"{name} set-config {'ok' if ok else 'failed'}")
        return

    ok = getattr(response, "success", True)
    if ok:
        success(console, f"Configuration updated for node '{name}'.")
    else:
        error(console, f"Failed to update configuration for node '{name}'.")


# ---------------------------------------------------------------------------
# node add
# ---------------------------------------------------------------------------


@node.command("add")
@click.argument("name")
@click.argument("url_arg", metavar="URL")
@click.option(
    "--description",
    default="A Node",
    show_default=True,
    help="Description of the node.",
)
@click.option(
    "--permanent",
    is_flag=True,
    help="Add the node permanently to the workcell.",
)
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def add_node(
    ctx: click.Context,
    name: str,
    url_arg: str,
    description: str,
    permanent: bool,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Add a node to the workcell.

    \b
    Examples:
        madsci node add my_robot http://localhost:2000
        madsci node add my_robot http://localhost:2000 --permanent
        madsci node add my_robot http://localhost:2000 --description "Robot arm"
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    wc_url = _get_workcell_url(ctx, workcell_url)
    client = _make_workcell_client(wc_url, timeout)

    result = client.add_node(
        node_name=name,
        node_url=url_arg,
        node_description=description,
        permanent=permanent,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _node_to_dict(result), format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(f"{name} added")
        return

    perm_label = " (permanent)" if permanent else ""
    success(console, f"Node '{name}' added to workcell{perm_label}.")


# ---------------------------------------------------------------------------
# node shell
# ---------------------------------------------------------------------------


class NodeShell(cmd.Cmd):
    """Interactive REPL for a MADSci node."""

    def __init__(
        self,
        node_name: str,
        node_client: Any,
        node_data: Any,
    ) -> None:
        """Initialize the NodeShell.

        Args:
            node_name: Name of the node.
            node_client: RestNodeClient instance.
            node_data: Raw node data from workcell.
        """
        super().__init__()
        self.node_name = node_name
        self.node_client = node_client
        self.node_data = node_data
        self.prompt = f"node:{node_name}> "
        self.intro = (
            f"Interactive shell for node '{node_name}'. "
            "Type 'help' for available commands, 'exit' to quit."
        )

    def _safe_call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a function and handle errors gracefully."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.stdout.write(f"Error: {e}\n")
            return None

    def do_status(self, _arg: str) -> None:
        """Show the current status of the node."""
        status = self._safe_call(self.node_client.get_status)
        if status is None:
            return
        data = (
            status.model_dump(mode="json") if hasattr(status, "model_dump") else status
        )
        self.stdout.write(json.dumps(data, indent=2, default=str) + "\n")

    def do_state(self, _arg: str) -> None:
        """Show the current state of the node."""
        state = self._safe_call(self.node_client.get_state)
        if state is None:
            return
        self.stdout.write(json.dumps(state, indent=2, default=str) + "\n")

    def do_info(self, _arg: str) -> None:
        """Show node information."""
        node_info = self._safe_call(self.node_client.get_info)
        if node_info is None:
            return
        data = (
            node_info.model_dump(mode="json")
            if hasattr(node_info, "model_dump")
            else node_info
        )
        self.stdout.write(json.dumps(data, indent=2, default=str) + "\n")

    def do_actions(self, _arg: str) -> None:
        """List available actions."""
        node_info = self._safe_call(self.node_client.get_info)
        if node_info is None:
            return
        actions = getattr(node_info, "actions", {}) or {}
        if not actions:
            self.stdout.write("No actions available.\n")
            return
        for act_name, action_def in actions.items():
            desc = _extract_attr(action_def, "description", "")
            desc_str = f" -- {desc}" if desc else ""
            self.stdout.write(f"  {act_name}{desc_str}\n")

    def do_run(self, arg: str) -> None:
        """Run an action: run <action_name> [json_args]."""
        from madsci.common.types.action_types import ActionRequest

        parts = arg.strip().split(None, 1)
        if not parts:
            self.stdout.write("Usage: run <action_name> [json_args]\n")
            return

        act_name = parts[0]
        action_args = {}
        if len(parts) > 1:
            try:
                action_args = json.loads(parts[1])
            except json.JSONDecodeError as exc:
                self.stdout.write(f"Invalid JSON args: {exc}\n")
                return

        request = ActionRequest(action_name=act_name, args=action_args)
        self.stdout.write(f"Executing '{act_name}'...\n")
        result = self._safe_call(
            self.node_client.send_action, request, await_result=True
        )
        if result is None:
            return
        data = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        self.stdout.write(json.dumps(data, indent=2, default=str) + "\n")

    def do_admin(self, arg: str) -> None:
        """Send admin command: admin <command>."""
        from madsci.common.types.admin_command_types import AdminCommands

        command = arg.strip()
        if not command:
            self.stdout.write("Usage: admin <command>\n")
            self.stdout.write(
                f"  Valid commands: {', '.join(c.value for c in AdminCommands)}\n"
            )
            return

        try:
            admin_cmd = AdminCommands(command)
        except ValueError:
            self.stdout.write(f"Unknown admin command: {command}\n")
            self.stdout.write(
                f"  Valid commands: {', '.join(c.value for c in AdminCommands)}\n"
            )
            return

        response = self._safe_call(self.node_client.send_admin_command, admin_cmd)
        if response is None:
            return
        data = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else response
        )
        self.stdout.write(json.dumps(data, indent=2, default=str) + "\n")

    def do_config(self, _arg: str) -> None:
        """Show current node configuration."""
        node_info = self._safe_call(self.node_client.get_info)
        if node_info is None:
            return
        config = getattr(node_info, "config", None)
        if config is None:
            self.stdout.write("No configuration available.\n")
            return
        if hasattr(config, "model_dump"):
            config = config.model_dump(mode="json")
        self.stdout.write(json.dumps(config, indent=2, default=str) + "\n")

    def do_log(self, arg: str) -> None:
        """Show node log: log [N]  (default: last 20 entries)."""
        tail = 20
        if arg.strip():
            try:
                tail = int(arg.strip())
            except ValueError:
                self.stdout.write(f"Invalid number: {arg}\n")
                return

        log_data = self._safe_call(self.node_client.get_log)
        if log_data is None:
            return

        if isinstance(log_data, dict):
            entries = list(log_data.values())
        elif isinstance(log_data, list):
            entries = log_data
        else:
            entries = []

        entries = entries[-tail:]
        if not entries:
            self.stdout.write("No log entries.\n")
            return

        for entry in entries:
            if isinstance(entry, dict):
                ts = entry.get("timestamp", entry.get("event_timestamp", ""))
                msg = entry.get("message", entry.get("event_message", ""))
                level = entry.get("event_type", entry.get("level", ""))
                self.stdout.write(f"[{ts}] {level}: {msg}\n")
            else:
                self.stdout.write(str(entry) + "\n")

    def do_exit(self, _arg: str) -> bool:
        """Exit the shell."""
        return True

    def do_quit(self, _arg: str) -> bool:
        """Exit the shell."""
        return True

    do_EOF = do_exit  # noqa: N815

    def emptyline(self) -> None:
        """Do nothing on empty line."""


@node.command("shell")
@click.argument("name")
@_WORKCELL_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def shell_node(
    ctx: click.Context,
    name: str,
    workcell_url: str | None,
    timeout: float,
) -> None:
    """Open an interactive REPL shell for a node.

    Provides commands for status, state, info, actions, run, admin,
    config, log, and more.

    \b
    Examples:
        madsci node shell my_robot
    """
    url = _get_workcell_url(ctx, workcell_url)
    node_client, node_data = _get_node_client(url, name, timeout)

    shell = NodeShell(name, node_client, node_data)
    shell.cmdloop()
