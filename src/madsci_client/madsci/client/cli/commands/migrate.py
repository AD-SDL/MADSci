"""Migration CLI commands for MADSci.

This module provides commands for migrating from the old configuration
system (Definition files) to the new system (Settings + ID Registry),
and for migrating data from the proprietary stack (MongoDB, Redis, MinIO)
to the FOSS stack (FerretDB, Valkey, SeaweedFS).
"""

import json
from pathlib import Path
from typing import Optional

import click
from madsci.client.cli.utils.output import get_console as _get_console
from rich.table import Table


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
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "env"]),
    default="yaml",
    help="Output format for generated config files (default: yaml).",
)
@click.pass_context
def convert(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    files: tuple[str, ...],
    convert_all: bool,
    dry_run: bool,
    apply: bool,
    backup: bool,
    output: Optional[str],
    output_format: str,
) -> None:
    """Convert definition files to new format."""
    from madsci.common.migration import (
        MigrationConverter,
        MigrationScanner,
    )
    from madsci.common.types.migration_types import MigrationStatus, OutputFormat

    console = _get_console(ctx)

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        ctx.exit(1)
        return

    fmt = OutputFormat(output_format)

    # Get files to convert
    if convert_all:
        scanner = MigrationScanner(Path.cwd(), output_format=fmt)
        plan = scanner.scan()
        migrations = [m for m in plan.files if m.status == MigrationStatus.PENDING]
    else:
        if not files:
            console.print("[red]Error: Specify files to convert or use --all[/red]")
            ctx.exit(1)
            return
        scanner = MigrationScanner(Path.cwd(), output_format=fmt)
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

        if success_count > 0:
            console.print("\n[bold]Next steps:[/bold]")
            console.print(
                "  Settings files have been generated alongside your definition files."
            )
            console.print(
                "  Managers and nodes resolve settings via walk-up file discovery"
            )
            console.print("  from the working directory. To ensure settings are found:")
            console.print("    1. Start managers/nodes from your project directory, or")
            console.print(
                "    2. Set [bold]MADSCI_SETTINGS_DIR[/bold] to your project path, or"
            )
            console.print(
                "    3. Use [bold]--settings-dir[/bold] with [bold]madsci start[/bold]"
            )
            console.print("\n  Consider merging generated settings into your shared")
            console.print(
                "  [bold]settings.yaml[/bold] for a single-file configuration."
            )
            console.print(
                "\n  Run [bold]madsci migrate status[/bold] to check progress."
            )


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


# ---------------------------------------------------------------------------
# FOSS stack migration
# ---------------------------------------------------------------------------

_FOSS_STEP_CHOICES = ["document-db", "postgresql", "redis", "object-storage", "all"]


@migrate.command("foss")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without making changes.",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply the FOSS migration.",
)
@click.option(
    "--step",
    type=click.Choice(_FOSS_STEP_CHOICES),
    default="all",
    help="Run a single migration step instead of all steps.",
)
@click.option(
    "--skip-backup",
    is_flag=True,
    help="Skip creating a pre-migration backup.",
)
@click.option(
    "--skip-docker",
    is_flag=True,
    help="Skip starting/stopping old containers (assume already running).",
)
@click.option(
    "--compose-dir",
    type=click.Path(exists=True),
    default=None,
    help="Directory containing Docker Compose files.",
)
@click.option(
    "--old-mongo-url",
    default=None,
    help="Override old MongoDB URL.",
)
@click.option(
    "--new-mongo-url",
    default=None,
    help="Override new FerretDB URL.",
)
@click.option(
    "--old-postgres-url",
    default=None,
    help="Override old PostgreSQL URL.",
)
@click.option(
    "--new-postgres-url",
    default=None,
    help="Override new PostgreSQL URL.",
)
@click.pass_context
def foss(  # noqa: C901, PLR0912, PLR0915
    ctx: click.Context,
    dry_run: bool,
    apply: bool,
    step: str,
    skip_backup: bool,
    skip_docker: bool,
    compose_dir: Optional[str],
    old_mongo_url: Optional[str],
    new_mongo_url: Optional[str],
    old_postgres_url: Optional[str],
    new_postgres_url: Optional[str],
) -> None:
    """Migrate data from MongoDB/Redis/MinIO to FerretDB/Valkey/SeaweedFS.

    \b
    Workflow:
        1. madsci migrate foss --dry-run          Preview migration plan
        2. madsci migrate foss --apply             Run full migration
        3. madsci migrate foss --apply --step X    Run a single step
    """
    from madsci.common.foss_migration import FossMigrationSettings, FossMigrationTool
    from rich.table import Table as RichTable

    console = _get_console(ctx)

    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        ctx.exit(1)
        return

    # Build settings overrides
    overrides: dict = {}
    if compose_dir:
        overrides["compose_dir"] = compose_dir
    if old_mongo_url:
        overrides["old_document_db_url"] = old_mongo_url
    if new_mongo_url:
        overrides["new_document_db_url"] = new_mongo_url
    if old_postgres_url:
        overrides["old_postgres_url"] = old_postgres_url
    if new_postgres_url:
        overrides["new_postgres_url"] = new_postgres_url

    settings = FossMigrationSettings(**overrides)
    tool = FossMigrationTool(settings=settings)

    # --- Dry run ---
    if dry_run:
        console.print("\n[bold]FOSS Stack Migration Plan[/bold]")
        console.print("=" * 50)

        # Detection
        detected = tool.detect_old_data()
        det_table = RichTable(title="Detected Old Data")
        det_table.add_column("Component")
        det_table.add_column("Found")
        for component, found in detected.items():
            style = "green" if found else "dim"
            det_table.add_row(component, str(found), style=style)
        console.print(det_table)

        # Prerequisites
        prereq = tool.check_prerequisites()
        if prereq.success:
            console.print("\n[green]\u2713[/green] All prerequisite tools found")
        else:
            console.print(f"\n[red]\u2717[/red] {prereq.error}")

        # Steps
        steps_to_run = list(tool.STEP_METHODS.keys()) if step == "all" else [step]
        console.print("\n[bold]Steps to execute:[/bold]")
        for s in steps_to_run:
            console.print(f"  \u2022 {s}")
        if not skip_backup:
            console.print(f"\n  Backup dir: {settings.backup_dir}")
        if not skip_docker:
            console.print(f"  Compose dir: {settings.compose_dir}")

        console.print("\n[yellow]Dry run \u2014 no changes made.[/yellow]")
        console.print("Run with [bold]--apply[/bold] to execute.")
        return

    # --- Apply ---
    steps_filter = None if step == "all" else [step]

    report = tool.run_full_migration(
        skip_backup=skip_backup,
        skip_docker=skip_docker,
        steps=steps_filter,
    )

    # Display results
    console.print("\n[bold]FOSS Migration Results[/bold]")
    console.print("=" * 50)

    results_table = RichTable()
    results_table.add_column("Step")
    results_table.add_column("Status")
    results_table.add_column("Duration")
    results_table.add_column("Message")

    for s in report.steps:
        status = "[green]\u2713[/green]" if s.success else "[red]\u2717[/red]"
        duration = f"{s.duration_seconds:.1f}s"
        msg = s.message
        if s.error:
            msg += f"\n[dim]{s.error}[/dim]"
        results_table.add_row(s.step, status, duration, msg)

    console.print(results_table)

    total = report.total_duration_seconds
    if report.all_succeeded:
        console.print(
            f"\n[green]\u2713 Migration completed successfully in {total:.1f}s[/green]"
        )
    else:
        console.print(
            f"\n[red]\u2717 Migration completed with errors in {total:.1f}s[/red]"
        )
        ctx.exit(1)
