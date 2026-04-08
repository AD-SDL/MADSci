"""MADSci CLI resource command group.

Provides subcommands for full resource lifecycle management: listing, showing,
creating, deleting, restoring, locking, unlocking, quantity management,
template management, hierarchy display, and history querying.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from madsci.client.resource_client import ResourceClient

import click
from madsci.client.cli.utils.cli_decorators import (
    resolve_service_url,
    timeout_option,
    with_service_error_handling,
)
from madsci.client.cli.utils.formatting import (
    format_timestamp,
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

_RESOURCE_URL_OPTION = click.option(
    "--resource-url",
    envvar="MADSCI_RESOURCE_URL",
    default=None,
    help="Resource manager URL (default: from config or http://localhost:8003/).",
)


def _get_resource_url(ctx: click.Context, resource_url: str | None) -> str:
    """Resolve the resource URL from the option, context, or default."""
    return resolve_service_url(ctx, resource_url, "resource_server_url", 8003)


def _make_client(resource_url: str, timeout: float) -> ResourceClient:
    from madsci.client.resource_client import ResourceClient
    from madsci.common.types.client_types import ResourceClientConfig

    config = ResourceClientConfig(timeout_default=timeout)
    return ResourceClient(resource_server_url=resource_url, config=config)


def _resource_to_row(r: Any) -> dict:
    """Convert a resource (possibly wrapped) to a dict suitable for table rendering."""
    # Handle ResourceWrapper transparently
    name = getattr(r, "resource_name", "-") or "-"
    rid = getattr(r, "resource_id", "-") or "-"
    base_type = getattr(r, "base_type", "-")
    if hasattr(base_type, "value"):
        base_type = base_type.value
    quantity = getattr(r, "quantity", None)
    capacity = getattr(r, "capacity", None)
    parent_id = getattr(r, "parent_id", None)

    return {
        "name": truncate(str(name), 30),
        "id": str(rid),
        "type": str(base_type),
        "quantity": str(quantity) if quantity is not None else "-",
        "capacity": str(capacity) if capacity is not None else "-",
        "parent": str(parent_id) if parent_id else "-",
    }


def _resource_to_dict(r: Any) -> dict:
    """Convert a resource to a serialisable dict for JSON/YAML output."""
    if hasattr(r, "model_dump"):
        return r.model_dump(mode="json")
    return dict(r) if hasattr(r, "__iter__") else {"resource": str(r)}


_LIST_COLUMNS = [
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("ID", "id", style="dim"),
    ColumnDef("Type", "type"),
    ColumnDef("Quantity", "quantity"),
    ColumnDef("Capacity", "capacity"),
    ColumnDef("Parent", "parent", style="dim"),
]

_HISTORY_COLUMNS = [
    ColumnDef("Version", "version"),
    ColumnDef("Change", "change_type"),
    ColumnDef("Timestamp", "timestamp", style="dim"),
    ColumnDef("Details", "details"),
]


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group()
def resource() -> None:
    """Manage resources.

    \b
    Examples:
        madsci resource list                     List resources
        madsci resource get <id>                 Show resource details
        madsci resource create --template <t>    Create from template
        madsci resource delete <id>              Soft-delete a resource
        madsci resource restore <id>             Restore deleted resource
        madsci resource tree <id>                Show resource hierarchy
        madsci resource lock <id>                Acquire a lock
        madsci resource unlock <id>              Release a lock
        madsci resource quantity set <id> <val>  Set quantity
        madsci resource quantity adjust <id> <d> Adjust quantity
        madsci resource template list            List templates
        madsci resource history <id>             Show change history
    """


# ---------------------------------------------------------------------------
# resource list
# ---------------------------------------------------------------------------


@resource.command("list")
@click.option(
    "--type",
    "base_type",
    default=None,
    help="Filter by base type (e.g. asset, consumable, container, stack, queue, slot, collection, row, grid, pool).",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    show_default=True,
    help="Limit number of results returned.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def list_resources(
    ctx: click.Context,
    base_type: str | None,
    limit: int,
    resource_url: str | None,
    timeout: float,
) -> None:
    """List resources.

    By default lists all non-deleted resources, optionally filtered by type.

    \b
    Examples:
        madsci resource list
        madsci resource list --type asset
        madsci resource list --type stack --limit 10
        madsci resource list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    resources = client.query_resource(
        base_type=base_type,
        multiple=True,
    )

    # Ensure we always have a list
    if not isinstance(resources, list):
        resources = [resources] if resources else []

    # Apply limit
    resources = resources[:limit]

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_resource_to_dict(r) for r in resources]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for r in resources:
            rid = getattr(r, "resource_id", "-")
            name = getattr(r, "resource_name", "-")
            console.print(f"{rid} {name}")
        return

    if not resources:
        info(console, "No resources found.")
        return

    rows = [_resource_to_row(r) for r in resources]
    output_result(
        console, rows, format="text", title="Resources", columns=_LIST_COLUMNS
    )


# ---------------------------------------------------------------------------
# resource get
# ---------------------------------------------------------------------------


@resource.command("get")
@click.argument("resource_id")
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def get_resource(
    ctx: click.Context,
    resource_id: str,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Show detailed information about a resource.

    \b
    Examples:
        madsci resource get 01J5ABCDEF12
        madsci resource get 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    r = client.get_resource(resource_id)
    if r is None:
        raise click.ClickException(f"Resource {resource_id} not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        rid = getattr(r, "resource_id", "-")
        name = getattr(r, "resource_name", "-")
        console.print(f"{rid} {name}")
        return

    # Rich detail display
    name = getattr(r, "resource_name", "Unnamed Resource")
    console.print()
    console.print(f"[bold]{name}[/bold]")
    console.print(f"  ID:          {getattr(r, 'resource_id', '-')}")
    bt = getattr(r, "base_type", "-")
    if hasattr(bt, "value"):
        bt = bt.value
    console.print(f"  Type:        {bt}")
    console.print(f"  Class:       {getattr(r, 'resource_class', '-')}")
    parent = getattr(r, "parent_id", None)
    console.print(f"  Parent:      {parent or '-'}")

    quantity = getattr(r, "quantity", None)
    capacity = getattr(r, "capacity", None)
    if quantity is not None:
        console.print(f"  Quantity:    {quantity}")
    if capacity is not None:
        console.print(f"  Capacity:    {capacity}")

    locked_by = getattr(r, "locked_by", None)
    if locked_by:
        console.print(f"  Locked by:   {locked_by}")

    desc = getattr(r, "resource_description", None)
    if desc:
        console.print(f"  Description: {desc}")

    console.print()


# ---------------------------------------------------------------------------
# resource create
# ---------------------------------------------------------------------------


@resource.command("create")
@click.option(
    "--template",
    "template_name",
    required=True,
    help="Template name to create the resource from.",
)
@click.option(
    "--name",
    "resource_name",
    default=None,
    help="Name for the new resource.",
)
@click.option(
    "--params",
    "params_json",
    default=None,
    help="Override parameters as a JSON string.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def create_resource(
    ctx: click.Context,
    template_name: str,
    resource_name: str | None,
    params_json: str | None,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Create a resource from a template.

    \b
    Examples:
        madsci resource create --template my_plate --name "Plate 1"
        madsci resource create --template my_tube --params '{"quantity": 10}'
        madsci resource create --template rack --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    overrides: dict | None = None
    if params_json:
        try:
            overrides = json.loads(params_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in --params: {exc}") from exc

    r = client.create_resource_from_template(
        template_name=template_name,
        resource_name=resource_name or template_name,
        overrides=overrides,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(getattr(r, "resource_id", ""))
    else:
        rid = getattr(r, "resource_id", "unknown")
        success(console, f"Resource created -- ID: {rid}")


# ---------------------------------------------------------------------------
# resource delete
# ---------------------------------------------------------------------------


@resource.command("delete")
@click.argument("resource_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def delete_resource(
    ctx: click.Context,
    resource_id: str,
    yes: bool,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Soft-delete a resource.

    The resource is moved to history and can be restored later.

    \b
    Examples:
        madsci resource delete 01J5ABCDEF12
        madsci resource delete 01J5ABCDEF12 --yes
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)

    if not yes:
        click.confirm(f"Delete resource {resource_id}?", abort=True)

    client = _make_client(url, timeout)
    r = client.remove_resource(resource_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{resource_id} deleted")
    else:
        success(console, f"Resource {resource_id} deleted.")


# ---------------------------------------------------------------------------
# resource restore
# ---------------------------------------------------------------------------


@resource.command("restore")
@click.argument("resource_id")
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def restore_resource(
    ctx: click.Context,
    resource_id: str,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Restore a soft-deleted resource from history.

    \b
    Examples:
        madsci resource restore 01J5ABCDEF12
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    r = client.restore_deleted_resource(resource_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{resource_id} restored")
    else:
        success(console, f"Resource {resource_id} restored.")


# ---------------------------------------------------------------------------
# resource tree
# ---------------------------------------------------------------------------


@resource.command("tree")
@click.argument("resource_id")
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def tree_resource(
    ctx: click.Context,
    resource_id: str,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Show the hierarchy of a resource as a tree.

    Displays ancestors and descendants of the specified resource.

    \b
    Examples:
        madsci resource tree 01J5ABCDEF12
        madsci resource tree 01J5ABCDEF12 --json
    """
    from rich.tree import Tree

    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    hierarchy = client.query_resource_hierarchy(resource_id)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, hierarchy, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(resource_id)
        for parent_id, children in hierarchy.descendant_ids.items():
            for child_id in children:
                console.print(f"  {parent_id} -> {child_id}")
        return

    # Build a Rich Tree
    # Show ancestors as a chain leading to the resource
    if hierarchy.ancestor_ids:
        root_label = f"[dim]{hierarchy.ancestor_ids[-1]}[/dim]"
    else:
        root_label = f"[bold cyan]{resource_id}[/bold cyan] (root)"

    tree = Tree(root_label)

    if hierarchy.ancestor_ids:
        # Build ancestor chain from furthest to closest
        current = tree
        for anc_id in reversed(
            hierarchy.ancestor_ids[:-1] if len(hierarchy.ancestor_ids) > 1 else []
        ):
            current = current.add(f"[dim]{anc_id}[/dim]")

        # Add the target resource as a highlighted node
        target_node = current.add(f"[bold cyan]{resource_id}[/bold cyan] (target)")
    else:
        target_node = tree

    # Add descendants recursively
    def _add_descendants(parent_node: Any, parent_id: str) -> None:
        children = hierarchy.descendant_ids.get(parent_id, [])
        for child_id in children:
            child_node = parent_node.add(f"{child_id}")
            _add_descendants(child_node, child_id)

    _add_descendants(target_node, resource_id)

    console.print()
    console.print("[bold]Resource Hierarchy[/bold]")
    console.print(tree)
    console.print()


# ---------------------------------------------------------------------------
# resource lock
# ---------------------------------------------------------------------------


@resource.command("lock")
@click.argument("resource_id")
@click.option(
    "--owner",
    "owner_id",
    default=None,
    help="Owner/client ID for the lock.",
)
@click.option(
    "--duration",
    type=float,
    default=300.0,
    show_default=True,
    help="Lock duration in seconds.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def lock_resource(
    ctx: click.Context,
    resource_id: str,
    owner_id: str | None,
    duration: float,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Acquire a lock on a resource.

    \b
    Examples:
        madsci resource lock 01J5ABCDEF12
        madsci resource lock 01J5ABCDEF12 --owner my-client
        madsci resource lock 01J5ABCDEF12 --duration 600
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    result = client.acquire_lock(
        resource_id,
        lock_duration=duration,
        client_id=owner_id,
    )

    if result is None:
        raise click.ClickException(f"Failed to acquire lock on resource {resource_id}.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{resource_id} locked")
    else:
        success(console, f"Lock acquired on resource {resource_id}.")


# ---------------------------------------------------------------------------
# resource unlock
# ---------------------------------------------------------------------------


@resource.command("unlock")
@click.argument("resource_id")
@click.option(
    "--owner",
    "owner_id",
    default=None,
    help="Owner/client ID that holds the lock.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def unlock_resource(
    ctx: click.Context,
    resource_id: str,
    owner_id: str | None,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Release a lock on a resource.

    \b
    Examples:
        madsci resource unlock 01J5ABCDEF12
        madsci resource unlock 01J5ABCDEF12 --owner my-client
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    result = client.release_lock(
        resource_id,
        client_id=owner_id,
    )

    if result is None:
        raise click.ClickException(f"Failed to release lock on resource {resource_id}.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{resource_id} unlocked")
    else:
        success(console, f"Lock released on resource {resource_id}.")


# ---------------------------------------------------------------------------
# resource quantity (subgroup)
# ---------------------------------------------------------------------------


@resource.group("quantity")
def quantity_group() -> None:
    """Manage resource quantities.

    \b
    Examples:
        madsci resource quantity set <id> <value>      Set absolute quantity
        madsci resource quantity adjust <id> <delta>    Relative change
    """


@quantity_group.command("set")
@click.argument("resource_id")
@click.argument("value", type=float)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def quantity_set(
    ctx: click.Context,
    resource_id: str,
    value: float,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Set the absolute quantity of a resource.

    \b
    Examples:
        madsci resource quantity set 01J5ABCDEF12 100
        madsci resource quantity set 01J5ABCDEF12 0
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    r = client.set_quantity(resource_id, value)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(f"{resource_id} quantity={value}")
    else:
        success(console, f"Resource {resource_id} quantity set to {value}.")


@quantity_group.command("adjust")
@click.argument("resource_id")
@click.argument("delta", type=float)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def quantity_adjust(
    ctx: click.Context,
    resource_id: str,
    delta: float,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Adjust the quantity of a resource by a relative amount.

    \b
    Examples:
        madsci resource quantity adjust 01J5ABCDEF12 5      # increase by 5
        madsci resource quantity adjust 01J5ABCDEF12 -3     # decrease by 3
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    r = client.change_quantity_by(resource_id, delta)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(r), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        sign = "+" if delta >= 0 else ""
        console.print(f"{resource_id} quantity{sign}{delta}")
    else:
        sign = "+" if delta >= 0 else ""
        new_qty = getattr(r, "quantity", "?")
        success(
            console,
            f"Resource {resource_id} quantity adjusted by {sign}{delta} (now {new_qty}).",
        )


# ---------------------------------------------------------------------------
# resource template (subgroup)
# ---------------------------------------------------------------------------


@resource.group("template")
def template_group() -> None:
    """Manage resource templates.

    \b
    Examples:
        madsci resource template list              List all templates
        madsci resource template get <name>        Show template details
        madsci resource template create ...        Create template from resource
    """


_TEMPLATE_LIST_COLUMNS = [
    ColumnDef("Name", "name", style="cyan"),
    ColumnDef("Type", "type"),
    ColumnDef("Description", "description"),
    ColumnDef("Version", "version"),
]


@template_group.command("list")
@click.option(
    "--type",
    "base_type",
    default=None,
    help="Filter templates by base type.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def template_list(
    ctx: click.Context,
    base_type: str | None,
    resource_url: str | None,
    timeout: float,
) -> None:
    """List resource templates.

    \b
    Examples:
        madsci resource template list
        madsci resource template list --type asset
        madsci resource template list --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    templates = client.query_templates(base_type=base_type)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        data = [_resource_to_dict(t) for t in templates]
        output_result(console, data, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for t in templates:
            console.print(getattr(t, "resource_name", "-"))
        return

    if not templates:
        info(console, "No templates found.")
        return

    rows = []
    for t in templates:
        bt = getattr(t, "base_type", "-")
        if hasattr(bt, "value"):
            bt = bt.value
        rows.append(
            {
                "name": getattr(t, "resource_name", "-"),
                "type": str(bt),
                "description": truncate(
                    getattr(t, "resource_description", "") or "", 40
                ),
                "version": getattr(t, "version", "-"),
            }
        )

    output_result(
        console,
        rows,
        format="text",
        title="Resource Templates",
        columns=_TEMPLATE_LIST_COLUMNS,
    )


@template_group.command("get")
@click.argument("template_name")
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def template_get(
    ctx: click.Context,
    template_name: str,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Show details of a resource template.

    \b
    Examples:
        madsci resource template get my_plate
        madsci resource template get my_plate --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    template_info = client.get_template_info(template_name)
    if template_info is None:
        raise click.ClickException(f"Template '{template_name}' not found.")

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, template_info, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        console.print(template_name)
        return

    output_result(
        console, template_info, format="text", title=f"Template: {template_name}"
    )


@template_group.command("create")
@click.option(
    "--from",
    "from_resource_id",
    required=True,
    help="Resource ID to create the template from.",
)
@click.option(
    "--name",
    "template_name",
    required=True,
    help="Unique name for the template.",
)
@click.option(
    "--description",
    default="",
    help="Description of the template.",
)
@click.option(
    "--version",
    default="1.0.0",
    show_default=True,
    help="Template version.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def template_create(
    ctx: click.Context,
    from_resource_id: str,
    template_name: str,
    description: str,
    version: str,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Create a resource template from an existing resource.

    \b
    Examples:
        madsci resource template create --from 01J5ABCDEF12 --name my_plate
        madsci resource template create --from 01J5ABCDEF12 --name my_tube --description "Standard tube"
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    # Fetch the source resource first
    source = client.get_resource(from_resource_id)
    if source is None:
        raise click.ClickException(f"Resource {from_resource_id} not found.")

    result = client.create_template(
        resource=source,
        template_name=template_name,
        description=description,
        version=version,
    )

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, _resource_to_dict(result), format=fmt.value)
    elif fmt == OutputFormat.QUIET:
        console.print(template_name)
    else:
        success(console, f"Template '{template_name}' created.")


# ---------------------------------------------------------------------------
# resource history
# ---------------------------------------------------------------------------


@resource.command("history")
@click.argument("resource_id")
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Limit number of history entries returned.",
)
@_RESOURCE_URL_OPTION
@timeout_option(default=10.0)
@click.pass_context
@with_service_error_handling
def history_resource(
    ctx: click.Context,
    resource_id: str,
    limit: int,
    resource_url: str | None,
    timeout: float,
) -> None:
    """Show the change history of a resource.

    \b
    Examples:
        madsci resource history 01J5ABCDEF12
        madsci resource history 01J5ABCDEF12 --limit 50
        madsci resource history 01J5ABCDEF12 --json
    """
    console = get_console(ctx)
    fmt = determine_output_format(ctx)
    url = _get_resource_url(ctx, resource_url)
    client = _make_client(url, timeout)

    entries = client.query_history(resource=resource_id, limit=limit)

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        output_result(console, entries, format=fmt.value)
        return

    if fmt == OutputFormat.QUIET:
        for entry in entries:
            console.print(str(entry.get("history_id", entry.get("id", "-"))))
        return

    if not entries:
        info(console, f"No history found for resource {resource_id}.")
        return

    rows = []
    for entry in entries:
        rows.append(
            {
                "version": str(entry.get("version", "-")),
                "change_type": str(entry.get("change_type", "-")),
                "timestamp": format_timestamp(
                    entry.get("changed_at", entry.get("timestamp"))
                ),
                "details": truncate(str(entry.get("change_description", "")), 50),
            }
        )

    output_result(
        console,
        rows,
        format="text",
        title=f"History for {resource_id}",
        columns=_HISTORY_COLUMNS,
    )
