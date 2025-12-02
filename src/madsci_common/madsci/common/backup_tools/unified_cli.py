"""Unified CLI for MADSci backup operations across all database types."""

import json
import sys
from pathlib import Path
from typing import Literal, Optional

import click
from madsci.common.types.backup_types import PostgreSQLBackupSettings
from pydantic import AnyUrl

from .mongodb_backup import MongoDBBackupSettings, MongoDBBackupTool
from .postgres_backup import PostgreSQLBackupTool


def detect_database_type(db_url: str) -> Literal["postgresql", "mongodb"]:
    """Auto-detect database type from connection URL.

    Args:
        db_url: Database connection URL

    Returns:
        Database type: "postgresql" or "mongodb"

    Raises:
        ValueError: If database type cannot be detected
    """
    db_url_lower = db_url.lower()

    if db_url_lower.startswith(("postgresql://", "postgres://")):
        return "postgresql"
    if db_url_lower.startswith(("mongodb://", "mongodb+srv://")):
        return "mongodb"
    raise ValueError(
        f"Unable to detect database type from URL: {db_url}. "
        "Supported prefixes: postgresql://, postgres://, mongodb://, mongodb+srv://"
    )


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    with Path(config_path).open() as f:
        return json.load(f)


@click.group()
@click.option(
    "--config", type=click.Path(exists=True), help="Configuration file (JSON)"
)
@click.pass_context
def madsci_backup(ctx: click.Context, config: Optional[str]) -> None:
    """MADSci unified backup management tool.

    Supports PostgreSQL and MongoDB backups with automatic database type detection.
    """
    ctx.ensure_object(dict)
    if config:
        ctx.obj["config"] = load_config(config)


@madsci_backup.command()
@click.option("--db-url", required=True, help="Database connection URL")
@click.option("--backup-dir", default=".madsci/backups", help="Backup directory")
@click.option(
    "--type",
    "db_type",
    type=click.Choice(["postgresql", "mongodb"]),
    help="Database type (auto-detected if omitted)",
)
@click.option("--name", help="Backup name suffix")
def create(
    db_url: str,
    backup_dir: str,
    db_type: Optional[str],
    name: Optional[str],
) -> None:
    """Create a new database backup.

    Examples:
        madsci-backup create --db-url postgresql://localhost/mydb

        madsci-backup create --db-url mongodb://localhost/mydb --name pre-deploy
    """
    try:
        # Auto-detect database type if not specified
        if not db_type:
            db_type = detect_database_type(db_url)

        # Create appropriate backup tool
        backup_path: Path

        if db_type == "postgresql":
            settings = PostgreSQLBackupSettings(
                db_url=db_url, backup_dir=Path(backup_dir)
            )
            tool = PostgreSQLBackupTool(settings)
            backup_path = tool.create_backup(name)

        else:  # mongodb
            # Parse database name from URL
            database = db_url.rstrip("/").split("/")[-1]
            if not database or database.startswith("mongodb"):
                database = "default"

            settings = MongoDBBackupSettings(
                mongo_db_url=AnyUrl(db_url),
                database=database,
                backup_dir=Path(backup_dir),
            )
            tool = MongoDBBackupTool(settings)
            backup_path = tool.create_backup(name)

        click.echo(f"✓ Backup created: {backup_path}")

    except Exception as e:
        click.echo(f"✗ Backup failed: {e}", err=True)
        sys.exit(1)


@madsci_backup.command()
@click.option(
    "--backup", required=True, type=click.Path(exists=True), help="Backup file path"
)
@click.option("--db-url", required=True, help="Target database URL")
@click.option(
    "--type",
    "db_type",
    type=click.Choice(["postgresql", "mongodb"]),
    help="Database type (auto-detected if omitted)",
)
def restore(backup: str, db_url: str, db_type: Optional[str]) -> None:
    """Restore from a backup.

    Examples:
        madsci-backup restore --backup /path/to/backup.dump --db-url postgresql://localhost/mydb
    """
    try:
        backup_path = Path(backup)

        # Auto-detect database type if not specified
        if not db_type:
            db_type = detect_database_type(db_url)

        # Restore using appropriate tool
        if db_type == "postgresql":
            settings = PostgreSQLBackupSettings(
                db_url=db_url, backup_dir=backup_path.parent
            )
            tool = PostgreSQLBackupTool(settings)
            tool.restore_from_backup(backup_path)

        else:  # mongodb
            database = db_url.rstrip("/").split("/")[-1]
            if not database or database.startswith("mongodb"):
                database = "default"

            settings = MongoDBBackupSettings(
                mongo_db_url=AnyUrl(db_url),
                database=database,
                backup_dir=backup_path.parent,
            )
            tool = MongoDBBackupTool(settings)
            tool.restore_from_backup(backup_path)

        click.echo(f"✓ Backup restored successfully to {db_url}")

    except Exception as e:
        click.echo(f"✗ Restore failed: {e}", err=True)
        sys.exit(1)


@madsci_backup.command()
@click.option(
    "--backup", required=True, type=click.Path(exists=True), help="Backup file path"
)
@click.option("--db-url", required=True, help="Database URL for validation context")
@click.option(
    "--type",
    "db_type",
    type=click.Choice(["postgresql", "mongodb"]),
    help="Database type (auto-detected if omitted)",
)
def validate(backup: str, db_url: str, db_type: Optional[str]) -> None:
    """Validate backup integrity.

    Examples:
        madsci-backup validate --backup /path/to/backup.dump --db-url postgresql://localhost/mydb
    """
    try:
        backup_path = Path(backup)

        # Auto-detect database type if not specified
        if not db_type:
            db_type = detect_database_type(db_url)

        # Validate using appropriate tool
        is_valid = False

        if db_type == "postgresql":
            settings = PostgreSQLBackupSettings(
                db_url=db_url, backup_dir=backup_path.parent
            )
            tool = PostgreSQLBackupTool(settings)
            is_valid = tool.validate_backup_integrity(backup_path)

        else:  # mongodb
            database = db_url.rstrip("/").split("/")[-1]
            if not database or database.startswith("mongodb"):
                database = "default"

            settings = MongoDBBackupSettings(
                mongo_db_url=AnyUrl(db_url),
                database=database,
                backup_dir=backup_path.parent,
            )
            tool = MongoDBBackupTool(settings)
            is_valid = tool.validate_backup_integrity(backup_path)

        if is_valid:
            click.echo(f"✓ Backup is valid: {backup_path}")
        else:
            click.echo(f"✗ Backup is INVALID: {backup_path}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for madsci-backup CLI."""
    madsci_backup()


if __name__ == "__main__":
    main()
