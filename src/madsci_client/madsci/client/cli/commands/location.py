"""MADSci CLI location command group.

Provides subcommands for full location lifecycle management: listing, showing,
creating, deleting, resource attachment/detachment, representation management,
transfer graph/planning, import/export, and template management.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from madsci.client.location_client import LocationClient

import click
from madsci.client.cli.utils.cli_decorators import (
    resolve_service_url,
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import (
    truncate,
)
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

_LOCATION_URL_OPTION = click.option(
    "--location-url",
    envvar="MADSCI_LOCATION_URL",
    default=None,
    help="Location manager URL (default: from config or http://localhost:8006/).",
)


def _get_location_url(ctx: click.Context, location_url: str | None) -> str:
    """Resolve the location URL from the option, context, or default."""
    return resolve_service_url(ctx, location_url, "location_server_url", 8006)


def _make_client(location_url: str, timeout: float) -> LocationClient:
    from madsci.client.location_client import LocationClient
    from madsci.common.types.client_types import LocationClientConfig

    config = LocationClientConfig(timeout_default=timeout)
    return LocationClient(location_server_url=location_url, config=config)


def _location_to_row(loc: Any) -> dict:
    """Convert a Location to a dict suitable for table rendering."""
    name = getattr(loc, "location_name", "-") or "-"
    lid = getattr(loc, "location_id", "-") or "-"
    template = getattr(loc, "location_template_name", None) or "-"
    resource_id = getattr(loc, "resource_id", None) or "-"
    transfers = getattr(loc, "allow_transfers", True)
    reservation = getattr(loc, "reservation", None)
    managed_by = getattr(loc, "managed_by", None)
    managed_by_str = managed_by.value.upper() if managed_by else "LAB"

    return {
        "name": truncate(str(name), 30),
        "managed_by": managed_by_str,
        "id": str(lid),
        "template": truncate(str(template), 20),
        "resource": str(resource_id) if resource_id != "-" else "-",
        "transfers": "yes" if transfers else "no",
        "reservation": "reserved" if reservation else "-",
    }


def _location_to_dict(loc: Any) -> dict:
    """Convert a Location to a serialisable dict for JSON/YAML output."""
    if hasattr(loc, "model_dump"):
        return loc.model_dump(mode="json")
    return dict(loc) if hasattr(loc, "__iter__") else {"location": str(loc)}


_LIST_COLUMNS = [
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("Managed By", "managed_by"),
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Template", "template"),
    ColumnDef("Resource", "resource", style="dim"),
    ColumnDef("Transfers", "transfers"),
    ColumnDef("Reservation", "reservation"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def location() -> None:
    """Manage locations.

    \b
    Examples:
        madsci location list                         List locations
        madsci location list -m node                 List node-managed locations
        madsci location get <name>                   Show location details
        madsci location create --name <name>         Create a location
        madsci location create-from-template <t>     Create from template
        madsci location delete <name>                Delete a location
        madsci location resources <name>             Show attached resources
        madsci location attach <name> <resource_id>  Attach resource
        madsci location detach <name>                Detach resource
        madsci location train <loc> <node>           Train location for a node
        madsci location set-repr <loc> <node>        Set representation
        madsci location remove-repr <loc> <node>     Remove representation
        madsci location transfer-graph               Show transfer graph
        madsci location plan-transfer <src> <tgt>    Plan a transfer
        madsci location export                       Export locations
        madsci location import <file>                Import locations
        madsci location template list                List location templates
        madsci location rep-template list             List repr templates
    """


# ---------------------------------------------------------------------------
# location list
# ---------------------------------------------------------------------------


@location.command("list")
@click.option(
    "--managed-by",
    "-m",
    "managed_by",
    default=None,
    type=click.Choice(["node", "lab"], case_sensitive=False),
    help="Filter by management type (node or lab).",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_locations(
    ctx: click.Context,
    managed_by: str | None,
    location_url: str | None,
    timeout: float,
) -> None:
    """List all locations.

    \b
    Examples:
        madsci location list
        madsci location list --managed-by node
        madsci location list -m lab
        madsci location list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    locations = client.get_locations(managed_by=managed_by)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_location_to_dict(loc) for loc in locations]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for loc in locations:
            lid = getattr(loc, "location_id", "-")
            name = getattr(loc, "location_name", "-")
            console.print(f"{lid} {name}")
        return

    if not locations:
        info(console, "No locations found.")
        return

    rows = [_location_to_row(loc) for loc in locations]
    output_result(
        console, rows, format="text", title="Locations", columns=_LIST_COLUMNS
    )


# ---------------------------------------------------------------------------
# location get
# ---------------------------------------------------------------------------


@location.command("get")
@click.argument("location_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def get_location(
    ctx: click.Context,
    location_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Show detailed information about a location.

    \b
    Examples:
        madsci location get deck_slot_1
        madsci location get deck_slot_1 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    loc = client.get_location_by_name(location_name)
    if loc is None:
        raise click.ClickException(f"Location '{location_name}' not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(loc), format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        lid = getattr(loc, "location_id", "-")
        name = getattr(loc, "location_name", "-")
        console.print(f"{lid} {name}")
        return

    # Rich detail display
    name = getattr(loc, "location_name", "Unnamed Location")
    managed_by = getattr(loc, "managed_by", None)
    managed_by_str = managed_by.value.upper() if managed_by else "LAB"
    owner = getattr(loc, "owner", None)
    owner_str = (
        str(owner.node_id) if owner and getattr(owner, "node_id", None) else "N/A"
    )

    console.print()
    console.print(f"[bold]{name}[/bold]")
    console.print(f"  ID:          {getattr(loc, 'location_id', '-')}")
    console.print(f"  Managed By:  {managed_by_str}")
    console.print(f"  Owner:       {owner_str}")
    console.print(
        f"  Template:    {getattr(loc, 'location_template_name', None) or '-'}"
    )
    console.print(f"  Resource:    {getattr(loc, 'resource_id', None) or '-'}")
    console.print(
        f"  Transfers:   {'yes' if getattr(loc, 'allow_transfers', True) else 'no'}"
    )

    node_bindings = getattr(loc, "node_bindings", None)
    if node_bindings:
        console.print(f"  Bindings:    {node_bindings}")

    representations = getattr(loc, "representations", {})
    if representations:
        console.print(f"  Repr keys:   {list(representations.keys())}")

    reservation = getattr(loc, "reservation", None)
    if reservation:
        console.print(f"  Reservation: {reservation}")

    desc = getattr(loc, "description", None)
    if desc:
        console.print(f"  Description: {desc}")

    console.print()


# ---------------------------------------------------------------------------
# location create
# ---------------------------------------------------------------------------


@location.command("create")
@click.option(
    "--name",
    "location_name",
    required=True,
    help="Name for the new location.",
)
@click.option(
    "--description",
    default=None,
    help="Description of the location.",
)
@click.option(
    "--allow-transfers/--no-transfers",
    default=True,
    show_default=True,
    help="Whether the location can be used in transfers.",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def create_location(
    ctx: click.Context,
    location_name: str,
    description: str | None,
    allow_transfers: bool,
    location_url: str | None,
    timeout: float,
) -> None:
    """Create a new location.

    \b
    Examples:
        madsci location create --name deck_slot_1
        madsci location create --name deck_slot_1 --description "Slot 1"
        madsci location create --name storage --no-transfers
    """
    from madsci.common.types.location_types import Location

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    loc = Location(
        location_name=location_name,
        description=description,
        allow_transfers=allow_transfers,
    )
    result = client.add_location(loc)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(getattr(result, "location_id", ""))
    else:
        lid = getattr(result, "location_id", "unknown")
        success(console, f"Location created -- ID: {lid}")


# ---------------------------------------------------------------------------
# location create-from-template
# ---------------------------------------------------------------------------


@location.command("create-from-template")
@click.argument("template_name")
@click.option(
    "--name",
    "location_name",
    required=True,
    help="Name for the new location.",
)
@click.option(
    "--bindings",
    "bindings_json",
    default=None,
    help="Node bindings as a JSON string (role->node name mapping).",
)
@click.option(
    "--repr-overrides",
    "repr_overrides_json",
    default=None,
    help="Representation overrides as a JSON string.",
)
@click.option(
    "--description",
    default=None,
    help="Description of the location.",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def create_from_template(
    ctx: click.Context,
    template_name: str,
    location_name: str,
    bindings_json: str | None,
    repr_overrides_json: str | None,
    description: str | None,
    location_url: str | None,
    timeout: float,
) -> None:
    """Create a location from a location template.

    \b
    Examples:
        madsci location create-from-template ot2_deck_slot --name slot_1
        madsci location create-from-template ot2_deck_slot --name slot_1 \\
            --bindings '{"deck_controller": "ot2_node"}'
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    bindings: dict[str, str] | None = None
    if bindings_json:
        try:
            bindings = json.loads(bindings_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --bindings: {exc}") from exc

    repr_overrides: dict[str, dict[str, Any]] | None = None
    if repr_overrides_json:
        try:
            repr_overrides = json.loads(repr_overrides_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(
                f"Invalid JSON in --repr-overrides: {exc}"
            ) from exc

    result = client.create_location_from_template(
        location_name=location_name,
        template_name=template_name,
        node_bindings=bindings,
        representation_overrides=repr_overrides,
        description=description,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(getattr(result, "location_id", ""))
    else:
        lid = getattr(result, "location_id", "unknown")
        success(
            console,
            f"Location created from template '{template_name}' -- ID: {lid}",
        )


# ---------------------------------------------------------------------------
# location delete
# ---------------------------------------------------------------------------


@location.command("delete")
@click.argument("location_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def delete_location(
    ctx: click.Context,
    location_name: str,
    yes: bool,
    location_url: str | None,
    timeout: float,
) -> None:
    """Delete a location.

    \b
    Examples:
        madsci location delete deck_slot_1
        madsci location delete deck_slot_1 --yes
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)

    if not yes:
        click.confirm(f"Delete location '{location_name}'?", abort=True)

    client = _make_client(url, timeout)
    result = client.delete_location(location_name)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, result, format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} deleted")
    else:
        success(console, f"Location '{location_name}' deleted.")


# ---------------------------------------------------------------------------
# location resources
# ---------------------------------------------------------------------------


@location.command("resources")
@click.argument("location_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def location_resources(
    ctx: click.Context,
    location_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Show resource hierarchy attached to a location.

    \b
    Examples:
        madsci location resources deck_slot_1
        madsci location resources deck_slot_1 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    hierarchy = client.get_location_resources(location_name)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            hierarchy.model_dump(mode="json")
            if hasattr(hierarchy, "model_dump")
            else hierarchy
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        rid = getattr(hierarchy, "resource_id", "-")
        console.print(str(rid))
        return

    rid = getattr(hierarchy, "resource_id", None)
    if not rid:
        info(console, f"No resources attached to location '{location_name}'.")
        return

    console.print()
    console.print(f"[bold]Resources at '{location_name}'[/bold]")
    console.print(f"  Root resource: {rid}")
    descendants = getattr(hierarchy, "descendant_ids", {})
    if descendants:
        for parent_id, children in descendants.items():
            for child_id in children:
                console.print(f"    {parent_id} -> {child_id}")
    console.print()


# ---------------------------------------------------------------------------
# location attach
# ---------------------------------------------------------------------------


@location.command("attach")
@click.argument("location_name")
@click.argument("resource_id")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def attach_resource(
    ctx: click.Context,
    location_name: str,
    resource_id: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Attach a resource to a location.

    \b
    Examples:
        madsci location attach deck_slot_1 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    result = client.attach_resource(location_name, resource_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} attached {resource_id}")
    else:
        success(console, f"Resource {resource_id} attached to '{location_name}'.")


# ---------------------------------------------------------------------------
# location detach
# ---------------------------------------------------------------------------


@location.command("detach")
@click.argument("location_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def detach_resource(
    ctx: click.Context,
    location_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Detach the resource from a location.

    \b
    Examples:
        madsci location detach deck_slot_1
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    result = client.detach_resource(location_name)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} detached")
    else:
        success(console, f"Resource detached from '{location_name}'.")


# ---------------------------------------------------------------------------
# location set-repr
# ---------------------------------------------------------------------------


@location.command("set-repr")
@click.argument("location_name")
@click.argument("node_name")
@click.option(
    "--data",
    "data_json",
    required=True,
    help="Representation data as a JSON string.",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def set_repr(
    ctx: click.Context,
    location_name: str,
    node_name: str,
    data_json: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Set a node-specific representation for a location.

    \b
    Examples:
        madsci location set-repr deck_slot_1 robot_arm --data '{"x": 1, "y": 2}'
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in --data: {exc}") from exc

    result = client.set_representation(location_name, node_name, data)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} repr set for {node_name}")
    else:
        success(
            console, f"Representation set for node '{node_name}' on '{location_name}'."
        )


# ---------------------------------------------------------------------------
# location remove-repr
# ---------------------------------------------------------------------------


@location.command("remove-repr")
@click.argument("location_name")
@click.argument("node_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def remove_repr(
    ctx: click.Context,
    location_name: str,
    node_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Remove a node-specific representation from a location.

    \b
    Examples:
        madsci location remove-repr deck_slot_1 robot_arm
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    result = client.remove_representation(location_name, node_name)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} repr removed for {node_name}")
    else:
        success(
            console,
            f"Representation removed for node '{node_name}' from '{location_name}'.",
        )


# ---------------------------------------------------------------------------
# location transfer-graph
# ---------------------------------------------------------------------------

_GRAPH_COLUMNS = [
    ColumnDef("Source", "source", style="cyan"),
    ColumnDef("Connected Targets", "targets"),
]


@location.command("transfer-graph")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def transfer_graph(
    ctx: click.Context,
    location_url: str | None,
    timeout: float,
) -> None:
    """Display the transfer graph as an adjacency list.

    \b
    Examples:
        madsci location transfer-graph
        madsci location transfer-graph --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    graph = client.get_transfer_graph()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, graph, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for src, targets in graph.items():
            console.print(f"{src} -> {', '.join(targets)}")
        return

    if not graph:
        info(console, "Transfer graph is empty.")
        return

    rows = []
    for src, targets in graph.items():
        rows.append(
            {
                "source": str(src),
                "targets": ", ".join(str(t) for t in targets) if targets else "-",
            }
        )

    output_result(
        console, rows, format="text", title="Transfer Graph", columns=_GRAPH_COLUMNS
    )


# ---------------------------------------------------------------------------
# location plan-transfer
# ---------------------------------------------------------------------------


@location.command("plan-transfer")
@click.argument("source")
@click.argument("target")
@click.option(
    "--resource-id",
    default=None,
    help="Resource ID to transfer.",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def plan_transfer(
    ctx: click.Context,
    source: str,
    target: str,
    resource_id: str | None,
    location_url: str | None,
    timeout: float,
) -> None:
    """Plan a transfer between two locations.

    Generates a WorkflowDefinition for the transfer.

    \b
    Examples:
        madsci location plan-transfer slot_1 slot_2
        madsci location plan-transfer slot_1 slot_2 --resource-id 01J5ABCDEF12
        madsci location plan-transfer slot_1 slot_2 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    workflow = client.plan_transfer(source, target, resource_id=resource_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            workflow.model_dump(mode="json")
            if hasattr(workflow, "model_dump")
            else workflow
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        wf_name = getattr(workflow, "name", "-")
        console.print(str(wf_name))
        return

    # Rich detail display
    console.print()
    console.print("[bold]Transfer Plan[/bold]")
    console.print(f"  Source: {source}")
    console.print(f"  Target: {target}")
    if resource_id:
        console.print(f"  Resource: {resource_id}")

    wf_name = getattr(workflow, "name", None)
    if wf_name:
        console.print(f"  Workflow: {wf_name}")

    steps = getattr(workflow, "steps", [])
    if steps:
        console.print(f"  Steps: {len(steps)}")
        for i, step in enumerate(steps):
            step_name = getattr(step, "name", f"step_{i}")
            console.print(f"    {i + 1}. {step_name}")

    console.print()


# ---------------------------------------------------------------------------
# location train
# ---------------------------------------------------------------------------


@location.command("train")
@click.argument("location_name")
@click.argument("node_name")
@click.option(
    "--template",
    "template_name",
    default=None,
    help="Name of a representation template whose defaults to use.",
)
@click.option(
    "--overrides",
    "overrides_json",
    default=None,
    help="Representation data overrides as a JSON string.",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def train_location(
    ctx: click.Context,
    location_name: str,
    node_name: str,
    template_name: str | None,
    overrides_json: str | None,
    location_url: str | None,
    timeout: float,
) -> None:
    """Train a location by setting a node's representation.

    Adds (or updates) a node-specific representation for a location. If
    ``--template`` is given, the template's defaults are fetched and merged
    with any ``--overrides``. At least one of ``--template`` or
    ``--overrides`` must be provided.

    \b
    Examples:
        madsci location train deck_slot_1 robot_arm --overrides '{"x": 1, "y": 2}'
        madsci location train deck_slot_1 robot_arm --template arm_template
        madsci location train deck_slot_1 robot_arm --template arm_template \\
            --overrides '{"gripper": "wide"}'
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    # Parse overrides
    overrides: dict[str, Any] | None = None
    if overrides_json:
        try:
            overrides = json.loads(overrides_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --overrides: {exc}") from exc

    if not template_name and not overrides:
        raise click.ClickException(
            "At least one of --template or --overrides must be provided."
        )

    # Build the representation data
    data: dict[str, Any] = {}
    if template_name:
        template = client.get_representation_template(template_name)
        data = dict(getattr(template, "default_values", {}) or {})

    if overrides:
        data.update(overrides)

    result = client.set_representation(location_name, node_name, data)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _location_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{location_name} trained for {node_name}")
    else:
        success(
            console,
            f"Location '{location_name}' trained for node '{node_name}'.",
        )


# ---------------------------------------------------------------------------
# location export
# ---------------------------------------------------------------------------


@location.command("export")
@click.option(
    "--output",
    "output_file",
    default=None,
    type=click.Path(),
    help="Output file path (default: stdout).",
)
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def export_locations(
    ctx: click.Context,
    output_file: str | None,
    location_url: str | None,
    timeout: float,
) -> None:
    """Export all locations to YAML.

    \b
    Examples:
        madsci location export
        madsci location export --output locations.yaml
        madsci location export --json
    """
    import yaml

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    locations = client.export_locations()
    data = [_location_to_dict(loc) for loc in locations]

    if output_file:
        with Path(output_file).open("w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        success(console, f"Exported {len(locations)} locations to {output_file}.")
        return

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, data, format=fmt.value)
    else:
        # Default to YAML for export
        output_result(console, data, format="yaml")


# ---------------------------------------------------------------------------
# location import
# ---------------------------------------------------------------------------


@location.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--overwrite", is_flag=True, help="Overwrite existing locations.")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def import_locations(
    ctx: click.Context,
    file: str,
    overwrite: bool,
    location_url: str | None,
    timeout: float,
) -> None:
    """Import locations from a YAML/JSON file.

    \b
    Examples:
        madsci location import locations.yaml
        madsci location import locations.yaml --overwrite
        madsci location import locations.json --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    result = client.import_locations(
        location_file_path=Path(file),
        overwrite=overwrite,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(f"{result.imported} imported")
        return

    success(
        console,
        f"Import complete: {result.imported} imported, {result.skipped} skipped, {len(result.errors)} errors.",
    )
    if result.errors:
        for err in result.errors:
            console.print(f"  [red]{err}[/red]")


# ---------------------------------------------------------------------------
# location template (subgroup)
# ---------------------------------------------------------------------------


@location.group("template")
def template_group() -> None:
    """Manage location templates.

    \b
    Examples:
        madsci location template list              List all templates
        madsci location template get <name>        Show template details
    """


_TEMPLATE_LIST_COLUMNS = [
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("Description", "description"),
    ColumnDef("Version", "version"),
    ColumnDef("Transfers", "transfers"),
]


@template_group.command("list")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def template_list(
    ctx: click.Context,
    location_url: str | None,
    timeout: float,
) -> None:
    """List location templates.

    \b
    Examples:
        madsci location template list
        madsci location template list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    templates = client.get_location_templates()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_location_to_dict(t) for t in templates]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for t in templates:
            console.print(getattr(t, "template_name", "-"))
        return

    if not templates:
        info(console, "No location templates found.")
        return

    rows = []
    for t in templates:
        rows.append(
            {
                "name": getattr(t, "template_name", "-"),
                "description": truncate(getattr(t, "description", "") or "", 40),
                "version": getattr(t, "version", "-"),
                "transfers": "yes"
                if getattr(t, "default_allow_transfers", True)
                else "no",
            }
        )

    output_result(
        console,
        rows,
        format="text",
        title="Location Templates",
        columns=_TEMPLATE_LIST_COLUMNS,
    )


@template_group.command("get")
@click.argument("template_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def template_get(
    ctx: click.Context,
    template_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Show details of a location template.

    \b
    Examples:
        madsci location template get ot2_deck_slot
        madsci location template get ot2_deck_slot --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    template_info = client.get_location_template(template_name)
    if template_info is None:
        raise click.ClickException(f"Location template '{template_name}' not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = _location_to_dict(template_info)
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(template_name)
        return

    data = _location_to_dict(template_info)
    output_result(
        console, data, format="text", title=f"Location Template: {template_name}"
    )


# ---------------------------------------------------------------------------
# location rep-template (subgroup)
# ---------------------------------------------------------------------------


@location.group("rep-template")
def rep_template_group() -> None:
    """Manage representation templates.

    \b
    Examples:
        madsci location rep-template list              List all repr templates
        madsci location rep-template get <name>        Show repr template details
    """


_REP_TEMPLATE_LIST_COLUMNS = [
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("Description", "description"),
    ColumnDef("Version", "version"),
    ColumnDef("Created By", "created_by", style="dim"),
]


@rep_template_group.command("list")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def rep_template_list(
    ctx: click.Context,
    location_url: str | None,
    timeout: float,
) -> None:
    """List representation templates.

    \b
    Examples:
        madsci location rep-template list
        madsci location rep-template list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    templates = client.get_representation_templates()

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_location_to_dict(t) for t in templates]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for t in templates:
            console.print(getattr(t, "template_name", "-"))
        return

    if not templates:
        info(console, "No representation templates found.")
        return

    rows = []
    for t in templates:
        rows.append(
            {
                "name": getattr(t, "template_name", "-"),
                "description": truncate(getattr(t, "description", "") or "", 40),
                "version": getattr(t, "version", "-"),
                "created_by": getattr(t, "created_by", None) or "-",
            }
        )

    output_result(
        console,
        rows,
        format="text",
        title="Representation Templates",
        columns=_REP_TEMPLATE_LIST_COLUMNS,
    )


@rep_template_group.command("get")
@click.argument("template_name")
@_LOCATION_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def rep_template_get(
    ctx: click.Context,
    template_name: str,
    location_url: str | None,
    timeout: float,
) -> None:
    """Show details of a representation template.

    \b
    Examples:
        madsci location rep-template get robotarm_deck_access
        madsci location rep-template get robotarm_deck_access --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_location_url(ctx, location_url)
    client = _make_client(url, timeout)

    template_info = client.get_representation_template(template_name)
    if template_info is None:
        raise click.ClickException(
            f"Representation template '{template_name}' not found."
        )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = _location_to_dict(template_info)
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(template_name)
        return

    data = _location_to_dict(template_info)
    output_result(
        console, data, format="text", title=f"Representation Template: {template_name}"
    )
