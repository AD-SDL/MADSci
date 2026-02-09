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

console = Console()


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
def scan(directory: str, json_output: bool, verbose: bool) -> None:
    """Scan for files that need migration."""
    from madsci.common.migration import MigrationScanner  # noqa: PLC0415
    from madsci.common.types.migration_types import MigrationStatus  # noqa: PLC0415

    scanner = MigrationScanner(Path(directory))
    plan = scanner.scan()

    if json_output:
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
                MigrationStatus.PENDING: "✗",
                MigrationStatus.MIGRATED: "✓",
                MigrationStatus.DEPRECATED: "○",
                MigrationStatus.FAILED: "✗",
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
                    console.print(f"      → {action.description}")

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
def convert(  # noqa: C901, PLR0912
    files: tuple[str, ...],
    convert_all: bool,
    dry_run: bool,
    apply: bool,
    backup: bool,
    output: Optional[str],
) -> None:
    """Convert definition files to new format."""
    from madsci.common.migration import (  # noqa: PLC0415
        MigrationConverter,
        MigrationScanner,
    )
    from madsci.common.types.migration_types import MigrationStatus  # noqa: PLC0415

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        raise SystemExit(1)

    # Get files to convert
    if convert_all:
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [m for m in plan.files if m.status == MigrationStatus.PENDING]
    else:
        if not files:
            console.print("[red]Error: Specify files to convert or use --all[/red]")
            raise SystemExit(1)
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
        console.print("─" * 50)

        # Show actions
        for action in migration.actions:
            console.print(f"  → {action.description}")

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        else:
            result = converter.convert(migration, dry_run=False, create_backup=backup)

            if result.errors:
                for error in result.errors:
                    console.print(f"[red]Error: {error}[/red]")
                error_count += 1
            else:
                console.print("[green]✓ Migrated successfully[/green]")
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
def status() -> None:
    """Show migration status."""
    from madsci.common.migration import MigrationScanner  # noqa: PLC0415

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
    bar = "█" * filled + "░" * (bar_width - filled)
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
def finalize(dry_run: bool, apply: bool, keep_backups: bool, force: bool) -> None:
    """Finalize migration by removing deprecated files."""
    from madsci.common.migration import MigrationScanner  # noqa: PLC0415
    from madsci.common.types.migration_types import MigrationStatus  # noqa: PLC0415

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        raise SystemExit(1)

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
        console.print(f"  ✗ {m.source_path}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        return

    if not force and not click.confirm("\nRemove these files?"):
        console.print("Cancelled.")
        return

    for m in deprecated:
        m.source_path.unlink()
        console.print(f"[green]✓[/green] Removed {m.source_path}")

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
def rollback(files: tuple[str, ...], rollback_all: bool, dry_run: bool) -> None:
    """Roll back a migration to restore original files."""
    from madsci.common.migration import (  # noqa: PLC0415
        MigrationRollback,
        MigrationScanner,
    )
    from madsci.common.types.migration_types import MigrationStatus  # noqa: PLC0415

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
            raise SystemExit(1)
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
            for error in result.errors:
                console.print(f"[red]Error: {error}[/red]")
        else:
            console.print("[green]✓ Rolled back successfully[/green]")
