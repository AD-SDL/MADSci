"""Registry CLI commands for MADSci.

This module provides commands for managing the ID Registry.
"""

import json
from pathlib import Path
from typing import Optional

import click
from madsci.client.cli.utils.output import get_console as _get_console
from rich.table import Table


@click.group()
@click.option(
    "--registry-path",
    "-r",
    "registry_path",
    type=click.Path(),
    envvar="MADSCI_REGISTRY_PATH",
    default=None,
    help=(
        "Path to the registry JSON file. "
        "Overrides MADSCI_REGISTRY_PATH and walk-up auto-detection."
    ),
)
@click.pass_context
def registry(ctx: click.Context, registry_path: Optional[str]) -> None:
    """ID Registry management commands.

    The registry maps component names to unique IDs (ULIDs) and tracks
    which components are currently active.

    \b
    Examples:
        madsci registry list              List all registered components
        madsci registry resolve mynode    Get ID for a component name
        madsci registry clean             Remove stale entries
    """
    ctx.ensure_object(dict)
    ctx.obj["registry_path"] = (
        Path(registry_path).expanduser() if registry_path else None
    )


@registry.command("list")
@click.option(
    "--type",
    "-t",
    "component_type",
    type=click.Choice(["node", "module", "manager", "experiment", "workcell"]),
    default=None,
    help="Filter by component type.",
)
@click.option(
    "--include-stale",
    is_flag=True,
    help="Include entries with expired locks.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format.",
)
@click.pass_context
def list_entries(
    ctx: click.Context,
    component_type: Optional[str],
    include_stale: bool,
    json_output: bool,
) -> None:
    """List all registered components."""
    from madsci.common.registry import LocalRegistryManager

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))
    entries = registry_mgr.list_entries(
        component_type=component_type,  # type: ignore[arg-type]
        include_stale=include_stale,
    )

    if json_output or ctx.obj.get("json"):
        output = [
            {
                "name": name,
                "id": entry.id,
                "type": entry.component_type,
                "last_seen": entry.last_seen.isoformat(),
                "locked": entry.is_locked(),
            }
            for name, entry in entries
        ]
        console.print_json(json.dumps(output))
        return

    if not entries:
        console.print("[yellow]No registry entries found.[/yellow]")
        return

    table = Table(title="Registry Entries")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Last Seen")

    for name, entry in entries:
        status = "[green]Active[/green]" if entry.is_locked() else "[dim]Inactive[/dim]"

        table.add_row(
            name,
            entry.id[:12] + "...",  # Truncate ULID
            entry.component_type,
            status,
            entry.last_seen.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@registry.command()
@click.argument("name")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format.",
)
@click.pass_context
def resolve(ctx: click.Context, name: str, json_output: bool) -> None:
    """Resolve a component name to its ID."""
    from madsci.common.registry import LocalRegistryManager

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))
    entry = registry_mgr.get_entry(name)

    if entry is None:
        if json_output or ctx.obj.get("json"):
            console.print_json(json.dumps({"error": f"Name '{name}' not found"}))
        else:
            console.print(f"[red]Name '{name}' not found in registry[/red]")
        ctx.exit(1)
        return

    if json_output or ctx.obj.get("json"):
        console.print_json(
            json.dumps(
                {
                    "name": name,
                    "id": entry.id,
                    "type": entry.component_type,
                    "locked": entry.is_locked(),
                }
            )
        )
    else:
        console.print(f"[cyan]{name}[/cyan] \u2192 [green]{entry.id}[/green]")
        console.print(f"  Type: {entry.component_type}")
        console.print(f"  Locked: {entry.is_locked()}")
        if entry.metadata:
            console.print(f"  Metadata: {entry.metadata}")


@registry.command()
@click.argument("old_name")
@click.argument("new_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force rename even if locked.",
)
@click.pass_context
def rename(ctx: click.Context, old_name: str, new_name: str, force: bool) -> None:
    """Rename a registry entry."""
    # Lazy imports to improve CLI startup time
    from madsci.common.registry import LocalRegistryManager
    from madsci.common.registry.local_registry import RegistryError
    from madsci.common.registry.lock_manager import RegistryLockError

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))

    try:
        component_id = registry_mgr.rename(old_name, new_name, force=force)
        console.print(
            f"[green]\u2713[/green] Renamed [cyan]{old_name}[/cyan] \u2192 [cyan]{new_name}[/cyan]"
        )
        console.print(f"  ID: {component_id}")
    except RegistryLockError as e:
        console.print(f"[red]Cannot rename: {e}[/red]")
        console.print("Use --force to override the lock.")
        ctx.exit(1)
    except RegistryError as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)


@registry.command()
@click.option(
    "--older-than",
    type=int,
    default=7,
    help="Remove entries not seen in this many days (default: 7).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be removed.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@click.pass_context
def clean(ctx: click.Context, older_than: int, dry_run: bool, force: bool) -> None:
    """Remove stale registry entries."""
    from madsci.common.registry import LocalRegistryManager

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))

    # First, preview
    stale = registry_mgr.clean_stale(older_than_days=older_than, dry_run=True)

    if not stale:
        console.print("[green]No stale entries to clean.[/green]")
        return

    console.print(f"Found {len(stale)} stale entries:")
    for name in stale:
        console.print(f"  \u2022 {name}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        return

    if not force and not click.confirm("\nRemove these entries?"):
        console.print("Cancelled.")
        return

    registry_mgr.clean_stale(older_than_days=older_than, dry_run=False)
    console.print(f"[green]\u2713 Removed {len(stale)} stale entries.[/green]")


@registry.command("export")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout).",
)
@click.pass_context
def export_registry(ctx: click.Context, output: Optional[str]) -> None:
    """Export registry to JSON file."""
    from madsci.common.registry import LocalRegistryManager

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))
    data = registry_mgr.export()

    if output:
        with Path(output).open("w") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"[green]\u2713 Exported registry to {output}[/green]")
    else:
        console.print_json(json.dumps(data, default=str))


@registry.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--merge/--replace",
    default=True,
    help="Merge with existing or replace (default: merge).",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@click.pass_context
def import_registry(ctx: click.Context, file: str, merge: bool, force: bool) -> None:
    """Import registry from JSON file."""
    from madsci.common.registry import LocalRegistryManager

    console = _get_console(ctx)
    registry_mgr = LocalRegistryManager(registry_path=ctx.obj.get("registry_path"))

    with Path(file).open() as f:
        data = json.load(f)

    entry_count = len(data.get("entries", {}))
    console.print(f"Found {entry_count} entries in {file}")

    if not force:
        action = "merge with" if merge else "replace"
        if not click.confirm(f"\n{action.capitalize()} existing registry?"):
            console.print("Cancelled.")
            return

    registry_mgr.import_entries(data, merge=merge)
    console.print(f"[green]\u2713 Imported {entry_count} entries.[/green]")
