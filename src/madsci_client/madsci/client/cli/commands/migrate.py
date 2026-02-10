"""Migration CLI commands for MADSci.

This module provides commands for migrating from the old configuration
system (Definition files) to the new system (Settings + ID Registry).
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table


def _get_console(ctx: click.Context) -> Console:
    """Get console from Click context, respecting global --no-color and --quiet flags."""
    if ctx.obj and "console" in ctx.obj:
        return ctx.obj["console"]
    return Console()


@click.group()
def migrate() -> None:
    """Migration tools for upgrading configuration.

    The migration tool helps upgrade from definition files to the new
    Settings + ID Registry system.

    \b
    Migration workflow:
        1. madsci migrate scan          Find files needing migration
        2. madsci migrate convert --all Preview and apply migrations
        3. madsci migrate status        Check migration progress
        4. madsci migrate finalize      Remove deprecated files
    """


@migrate.command()
@click.argument("directory", default=".", type=click.Path(exists=True))
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed information about each file.",
)
@click.pass_context
def scan(ctx: click.Context, directory: str, json_output: bool, verbose: bool) -> None:
    """Scan for files that need migration."""
    from madsci.common.migration import MigrationScanner
    from madsci.common.types.migration_types import MigrationStatus

    console = _get_console(ctx)
    scanner = MigrationScanner(Path(directory))
    plan = scanner.scan()

    if json_output or ctx.obj.get("json"):
        console.print_json(json.dumps(plan.model_dump(mode="json"), default=str))
        return

    if not plan.files:
        console.print("[green]No files need migration.[/green]")
        return

    console.print(f"\nFound {len(plan.files)} files requiring migration:\n")

    # Group by type
    by_type: dict[str, list] = {}
    for migration in plan.files:
        by_type.setdefault(migration.file_type.value, []).append(migration)

    for file_type, migrations in by_type.items():
        console.print(f"[bold]{file_type.replace('_', ' ').title()}:[/bold]")

        for m in migrations:
            status_icon = {
                MigrationStatus.PENDING: "\u2717",
                MigrationStatus.MIGRATED: "\u2713",
                MigrationStatus.DEPRECATED: "\u25cb",
                MigrationStatus.FAILED: "\u2717",
            }.get(m.status, "?")

            status_color = {
                MigrationStatus.PENDING: "red",
                MigrationStatus.MIGRATED: "green",
                MigrationStatus.DEPRECATED: "yellow",
                MigrationStatus.FAILED: "red",
            }.get(m.status, "white")

            console.print(f"  [{status_color}]{status_icon}[/] {m.source_path}")

            if verbose:
                console.print(f"      Name: {m.name}")
                console.print(f"      ID: {m.component_id}")
                for action in m.actions:
                    console.print(f"      \u2192 {action.description}")

        console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Pending: {plan.pending_count}")
    console.print(f"  Migrated: {plan.migrated_count}")
    console.print()
    console.print("[bold]Next step:[/bold]")
    console.print("  madsci migrate convert --all --dry-run")


@migrate.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--all",
    "convert_all",
    is_flag=True,
    help="Convert all detected files.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without making changes.",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply the conversion.",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before converting.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output directory for generated files.",
)
@click.pass_context
def convert(  # noqa: C901, PLR0912
    ctx: click.Context,
    files: tuple[str, ...],
    convert_all: bool,
    dry_run: bool,
    apply: bool,
    backup: bool,
    output: Optional[str],
) -> None:
    """Convert definition files to new format."""
    from madsci.common.migration import (
        MigrationConverter,
        MigrationScanner,
    )
    from madsci.common.types.migration_types import MigrationStatus

    console = _get_console(ctx)

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        ctx.exit(1)
        return

    # Get files to convert
    if convert_all:
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [m for m in plan.files if m.status == MigrationStatus.PENDING]
    else:
        if not files:
            console.print("[red]Error: Specify files to convert or use --all[/red]")
            ctx.exit(1)
            return
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [
            m
            for m in plan.files
            if str(m.source_path) in files or m.source_path.name in files
        ]

    if not migrations:
        console.print("[yellow]No files to convert.[/yellow]")
        return

    converter = MigrationConverter(
        output_dir=Path(output) if output else None,
    )

    success_count = 0
    error_count = 0

    for migration in migrations:
        console.print(f"\n[bold]Migrating: {migration.source_path}[/bold]")
        console.print("\u2500" * 50)

        # Show actions
        for action in migration.actions:
            console.print(f"  \u2192 {action.description}")

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        else:
            result = converter.convert(migration, dry_run=False, create_backup=backup)

            if result.errors:
                for err in result.errors:
                    console.print(f"[red]Error: {err}[/red]")
                error_count += 1
            else:
                console.print("[green]\u2713 Migrated successfully[/green]")
                if result.backup_path:
                    console.print(f"  Backup: {result.backup_path}")
                for output_file in result.output_files:
                    console.print(f"  Output: {output_file}")
                success_count += 1

    if not dry_run:
        console.print("\n[bold]Results:[/bold]")
        console.print(f"  Successful: {success_count}")
        console.print(f"  Failed: {error_count}")


@migrate.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show migration status."""
    from madsci.common.migration import MigrationScanner

    console = _get_console(ctx)
    scanner = MigrationScanner(Path.cwd())
    plan = scanner.scan()

    total = plan.total_count
    if total == 0:
        console.print("[green]No definition files found. Migration complete![/green]")
        return

    console.print("\n[bold]MADSci Migration Status[/bold]")
    console.print("=" * 40)
    console.print(
        f"\nOverall: {plan.migrated_count}/{total} files migrated ({plan.progress_percent}%)\n"
    )

    # Progress bar
    bar_width = 30
    filled = int(bar_width * plan.migrated_count / total) if total > 0 else 0
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
    console.print(f"[{bar}]\n")

    # Show by status
    table = Table(show_header=True)
    table.add_column("Status")
    table.add_column("Count", justify="right")

    table.add_row("Pending", str(plan.pending_count))
    table.add_row("Migrated", str(plan.migrated_count))
    table.add_row("Deprecated", str(plan.deprecated_count))
    table.add_row("Failed", str(plan.failed_count))

    console.print(table)

    if plan.pending_count > 0:
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  madsci migrate convert --all --apply")


@migrate.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without making changes.",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply the finalization.",
)
@click.option(
    "--keep-backups",
    is_flag=True,
    help="Keep backup files.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@click.pass_context
def finalize(
    ctx: click.Context, dry_run: bool, apply: bool, keep_backups: bool, force: bool
) -> None:
    """Finalize migration by removing deprecated files."""
    from madsci.common.migration import MigrationScanner
    from madsci.common.types.migration_types import MigrationStatus

    console = _get_console(ctx)

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        ctx.exit(1)
        return

    scanner = MigrationScanner(Path.cwd())
    plan = scanner.scan()

    deprecated = [
        m
        for m in plan.files
        if m.status in (MigrationStatus.MIGRATED, MigrationStatus.DEPRECATED)
    ]

    if not deprecated:
        console.print("[yellow]No deprecated files to remove.[/yellow]")
        return

    console.print("\n[bold]Files to remove:[/bold]")
    for m in deprecated:
        console.print(f"  \u2717 {m.source_path}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        return

    if not force and not click.confirm("\nRemove these files?"):
        console.print("Cancelled.")
        return

    for m in deprecated:
        m.source_path.unlink()
        console.print(f"[green]\u2713[/green] Removed {m.source_path}")

        if not keep_backups and m.backup_path and m.backup_path.exists():
            m.backup_path.unlink()

    console.print("\n[green]Migration finalized.[/green]")


@migrate.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--all",
    "rollback_all",
    is_flag=True,
    help="Rollback all migrated files.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without making changes.",
)
@click.pass_context
def rollback(
    ctx: click.Context, files: tuple[str, ...], rollback_all: bool, dry_run: bool
) -> None:
    """Roll back a migration to restore original files."""
    from madsci.common.migration import (
        MigrationRollback,
        MigrationScanner,
    )
    from madsci.common.types.migration_types import MigrationStatus

    console = _get_console(ctx)

    # Get files to rollback
    if rollback_all:
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [
            m
            for m in plan.files
            if m.status in (MigrationStatus.MIGRATED, MigrationStatus.DEPRECATED)
        ]
    else:
        if not files:
            console.print("[red]Error: Specify files to rollback or use --all[/red]")
            ctx.exit(1)
            return
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [
            m
            for m in plan.files
            if str(m.source_path) in files or m.source_path.name in files
        ]

    if not migrations:
        console.print("[yellow]No files to rollback.[/yellow]")
        return

    rollback_handler = MigrationRollback()

    for migration in migrations:
        console.print(f"\n[bold]Rolling back: {migration.source_path}[/bold]")

        if dry_run:
            console.print("[yellow]Dry run - no changes made.[/yellow]")
            continue

        result = rollback_handler.rollback(migration)

        if result.errors:
            for err in result.errors:
                console.print(f"[red]Error: {err}[/red]")
        else:
            console.print("[green]\u2713 Rolled back successfully[/green]")
