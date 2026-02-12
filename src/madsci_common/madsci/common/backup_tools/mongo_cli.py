"""MongoDB backup management commands."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from madsci.common.backup_tools.mongodb_backup import MongoDBBackupTool
from madsci.common.types.backup_types import MongoDBBackupSettings


def load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with Path(config_path).open() as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Error loading config file: {e}") from e


@click.group()
@click.option(
    "--config-file", help="Configuration file path", type=click.Path(exists=True)
)
@click.option("--mongo-url", help="MongoDB connection URL")
@click.option("--database", help="Database name")
@click.option(
    "--backup-dir", default=".madsci/mongodb/backups", help="Backup directory"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def mongodb_backup(
    ctx: click.Context,
    config_file: Optional[str],
    mongo_url: Optional[str],
    database: Optional[str],
    backup_dir: str,
    verbose: bool,
) -> None:
    """MongoDB backup management commands."""
    ctx.ensure_object(dict)

    # Load configuration from file if provided
    if config_file:
        config_data = load_config_file(config_file)
        ctx.obj["config"] = config_data
        # Use config file values as defaults
        mongo_url = mongo_url or config_data.get("mongo_db_url")
        database = database or config_data.get("database")
        backup_dir = config_data.get("backup_dir", backup_dir)

    # Validate required parameters
    if not mongo_url:
        raise click.ClickException(
            "MongoDB URL is required (use --mongo-url or config file)"
        )
    if not database:
        raise click.ClickException(
            "Database name is required (use --database or config file)"
        )

    ctx.obj["mongo_url"] = mongo_url
    ctx.obj["database"] = database
    ctx.obj["backup_dir"] = Path(backup_dir)
    ctx.obj["verbose"] = verbose


@mongodb_backup.command()
@click.option("--name-suffix", help="Optional backup name suffix")
@click.option("--no-validate", is_flag=True, help="Skip integrity validation")
@click.option("--no-compression", is_flag=True, help="Disable backup compression")
@click.option("--collections", help="Comma-separated list of collections to backup")
@click.pass_context
def create(
    ctx: click.Context,
    name_suffix: Optional[str],
    no_validate: bool,
    no_compression: bool,
    collections: Optional[str],
) -> None:
    """Create a new MongoDB backup."""
    try:
        # Parse collections list
        collections_list = None
        if collections:
            collections_list = [c.strip() for c in collections.split(",")]

        # Create settings
        settings = MongoDBBackupSettings(
            mongo_db_url=ctx.obj["mongo_url"],
            database=ctx.obj["database"],
            backup_dir=ctx.obj["backup_dir"],
            validate_integrity=not no_validate,
            compression=not no_compression,
            collections=collections_list,
        )

        # Create backup tool
        tool = MongoDBBackupTool(settings)

        # Create backup
        backup_path = tool.create_backup(name_suffix)
        click.echo(f"Backup created successfully: {backup_path}")

    except Exception as e:
        click.echo(f"Backup failed: {e}", err=True)
        sys.exit(1)


@mongodb_backup.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List available MongoDB backups."""
    try:
        # Create settings
        settings = MongoDBBackupSettings(
            mongo_db_url=ctx.obj["mongo_url"],
            database=ctx.obj["database"],
            backup_dir=ctx.obj["backup_dir"],
        )

        # Create backup tool
        tool = MongoDBBackupTool(settings)

        # List backups
        backups = tool.list_available_backups()

        if not backups:
            click.echo("No backups found")
            return

        click.echo(f"Found {len(backups)} backup(s):")
        click.echo()

        # Display backups in a table format
        header = f"{'Backup Path':<50} {'Created':<20} {'Size':<15} {'Valid':<8}"
        click.echo(header)
        click.echo("-" * len(header))

        for backup in backups:
            size_mb = backup.backup_size / (1024 * 1024)
            click.echo(
                f"{backup.backup_path.name:<50} "
                f"{backup.created_at.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                f"{size_mb:.1f} MB{'':<8} "
                f"{'✓' if backup.is_valid else '✗':<8}"
            )

    except Exception as e:
        click.echo(f"List failed: {e}", err=True)
        sys.exit(1)


@mongodb_backup.command()
@click.argument("backup_path", type=click.Path())
@click.option(
    "--target-database", help="Target database name (defaults to original database)"
)
@click.pass_context
def restore(
    ctx: click.Context, backup_path: str, target_database: Optional[str]
) -> None:
    """Restore from MongoDB backup."""
    try:
        backup_path_obj = Path(backup_path)

        if not backup_path_obj.exists():
            click.echo(f"Backup path does not exist: {backup_path}", err=True)
            sys.exit(1)

        # Create settings
        settings = MongoDBBackupSettings(
            mongo_db_url=ctx.obj["mongo_url"],
            database=ctx.obj["database"],
            backup_dir=ctx.obj["backup_dir"],
        )

        # Create backup tool
        tool = MongoDBBackupTool(settings)

        # Restore backup
        tool.restore_from_backup(backup_path_obj, target_database)

        target_name = target_database or ctx.obj["database"]
        click.echo(f"Restore completed successfully to database: {target_name}")

    except Exception as e:
        click.echo(f"Restore failed: {e}", err=True)
        sys.exit(1)


@mongodb_backup.command()
@click.argument("backup_path", type=click.Path())
@click.pass_context
def validate(ctx: click.Context, backup_path: str) -> None:
    """Validate MongoDB backup integrity."""
    try:
        backup_path_obj = Path(backup_path)

        if not backup_path_obj.exists():
            click.echo(f"Backup path does not exist: {backup_path}", err=True)
            sys.exit(1)

        # Create settings
        settings = MongoDBBackupSettings(
            mongo_db_url=ctx.obj["mongo_url"],
            database=ctx.obj["database"],
            backup_dir=ctx.obj["backup_dir"],
        )

        # Create backup tool
        tool = MongoDBBackupTool(settings)

        # Validate backup
        is_valid = tool.validate_backup_integrity(backup_path_obj)

        if is_valid:
            click.echo("Backup validation successful")
        else:
            click.echo("Backup validation failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)


@mongodb_backup.command()
@click.argument("backup_path", type=click.Path())
@click.option("--force", is_flag=True, help="Delete without confirmation")
@click.pass_context
def delete(ctx: click.Context, backup_path: str, force: bool) -> None:
    """Delete MongoDB backup."""
    try:
        backup_path_obj = Path(backup_path)

        if not backup_path_obj.exists():
            click.echo(f"Backup path does not exist: {backup_path}", err=True)
            sys.exit(1)

        if not force and not click.confirm(
            f"Are you sure you want to delete backup '{backup_path}'?"
        ):
            click.echo("Deletion cancelled")
            return

        # Create settings
        settings = MongoDBBackupSettings(
            mongo_db_url=ctx.obj["mongo_url"],
            database=ctx.obj["database"],
            backup_dir=ctx.obj["backup_dir"],
        )

        # Create backup tool
        tool = MongoDBBackupTool(settings)

        # Delete backup
        tool.delete_backup(backup_path_obj)
        click.echo("Backup deleted successfully")

    except Exception as e:
        click.echo(f"Delete failed: {e}", err=True)
        sys.exit(1)


def main_mongodb_backup() -> None:
    """Entry point for MongoDB backup CLI."""
    mongodb_backup()


if __name__ == "__main__":
    main_mongodb_backup()
