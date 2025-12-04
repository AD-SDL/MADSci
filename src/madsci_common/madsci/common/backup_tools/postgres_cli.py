"""Command-line interface for PostgreSQL backup management."""

import sys
from pathlib import Path
from typing import Any

import click
from madsci.common.types.backup_types import PostgreSQLBackupSettings

from .postgres_backup import PostgreSQLBackupTool


@click.group()
@click.option(
    "--db-url",
    required=True,
    help="PostgreSQL connection URL (e.g., postgresql://user:pass@localhost:5432/db)",
)
@click.option(
    "--backup-dir",
    default=".madsci/postgresql/backups",
    help="Backup directory (default: .madsci/postgresql/backups)",
    type=click.Path(),
)
@click.option(
    "--format",
    type=click.Choice(["custom", "plain", "directory", "tar"]),
    default="custom",
    help="Backup format (default: custom)",
)
@click.option(
    "--max-backups",
    type=int,
    default=10,
    help="Maximum number of backups to retain (default: 10)",
)
@click.option("--no-compression", is_flag=True, help="Disable compression")
@click.pass_context
def postgres_backup(
    ctx: Any,
    db_url: str,
    backup_dir: str,
    format: str,
    max_backups: int,
    no_compression: bool,
) -> None:
    """PostgreSQL backup management commands."""
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store common settings for subcommands
    ctx.obj["settings"] = PostgreSQLBackupSettings(
        db_url=db_url,
        backup_dir=Path(backup_dir),
        backup_format=format,
        max_backups=max_backups,
        validate_integrity=True,  # Default to validating
        compression=not no_compression,
    )


@postgres_backup.command()
@click.option("--name-suffix", help="Optional backup name suffix")
@click.option("--no-validate", is_flag=True, help="Skip integrity validation")
@click.pass_context
def create(ctx: Any, name_suffix: str, no_validate: bool) -> None:
    """Create a new PostgreSQL backup."""
    settings = ctx.obj["settings"]

    # Override validation setting if requested
    if no_validate:
        settings.validate_integrity = False

    try:
        tool = PostgreSQLBackupTool(settings)
        backup_path = tool.create_backup(name_suffix)
        click.echo(f"Backup created successfully: {backup_path}")

    except Exception as e:
        click.echo(f"Backup failed: {e}", err=True)
        sys.exit(1)


@postgres_backup.command()
@click.pass_context
def list(ctx: Any) -> None:
    """List available PostgreSQL backups."""
    settings = ctx.obj["settings"]

    try:
        tool = PostgreSQLBackupTool(settings)
        backups = tool.list_available_backups()

        if not backups:
            click.echo("No backups found in backup directory.")
            return

        # Display backup information in a table format
        click.echo(f"{'Backup File':<50} {'Created':<20} {'Size (bytes)':<12} {'Type'}")
        click.echo("-" * 90)

        for backup in backups:
            created = backup.created_at.strftime("%Y-%m-%d %H:%M:%S")
            backup_name = backup.backup_path.name
            click.echo(
                f"{backup_name:<50} {created:<20} {backup.backup_size:<12} {backup.backup_type}"
            )

    except Exception as e:
        click.echo(f"Failed to list backups: {e}", err=True)
        sys.exit(1)


@postgres_backup.command()
@click.argument("backup_path", type=click.Path())
@click.option(
    "--target-db", help="Target database name (defaults to original database)"
)
@click.pass_context
def restore(ctx: Any, backup_path: str, target_db: str) -> None:
    """Restore database from backup."""
    settings = ctx.obj["settings"]
    backup_path = Path(backup_path)

    # Check if backup file exists
    if not backup_path.exists():
        click.echo(f"Backup file does not exist: {backup_path}", err=True)
        sys.exit(1)

    try:
        tool = PostgreSQLBackupTool(settings)
        tool.restore_from_backup(backup_path, target_db)
        click.echo(f"Backup restored successfully from: {backup_path}")

        if target_db:
            click.echo(f"Restored to database: {target_db}")

    except Exception as e:
        click.echo(f"Restore failed: {e}", err=True)
        sys.exit(1)


@postgres_backup.command()
@click.argument("backup_path", type=click.Path())
@click.pass_context
def validate(ctx: Any, backup_path: str) -> None:
    """Validate backup integrity."""
    settings = ctx.obj["settings"]
    backup_path = Path(backup_path)

    try:
        tool = PostgreSQLBackupTool(settings)
        is_valid = tool.validate_backup_integrity(backup_path)

        if is_valid:
            click.echo(f"Backup is valid: {backup_path}")
        else:
            click.echo(f"Backup is invalid: {backup_path}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)


@postgres_backup.command()
@click.argument("backup_path", type=click.Path())
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx: Any, backup_path: str, confirm: bool) -> None:
    """Delete a backup."""
    settings = ctx.obj["settings"]
    backup_path = Path(backup_path)

    # Confirmation prompt unless --confirm flag is used
    if not confirm and not click.confirm(
        f"Are you sure you want to delete backup: {backup_path}?"
    ):
        click.echo("Delete cancelled.")
        return

    try:
        tool = PostgreSQLBackupTool(settings)
        tool.delete_backup(backup_path)
        click.echo(f"Backup deleted successfully: {backup_path}")

    except Exception as e:
        click.echo(f"Delete failed: {e}", err=True)
        sys.exit(1)


def main_postgres_backup() -> None:
    """Entry point for PostgreSQL backup CLI."""
    postgres_backup()
