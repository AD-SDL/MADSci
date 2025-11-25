"""Unified CLI for MADSci backup operations across all database types."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import click
from pydantic import AnyUrl

# Import backup tools - will be created in subsequent tasks
try:
    from .encryption import BackupEncryption  # type: ignore[attr-defined]
except ImportError:
    BackupEncryption = None  # type: ignore[assignment, misc]

try:
    from .registry import BackupRegistry  # type: ignore[attr-defined]
except ImportError:
    BackupRegistry = None  # type: ignore[assignment, misc]

from .mongodb_backup import MongoDBBackupSettings, MongoDBBackupTool

# Import PostgreSQL tools from resource_manager package
try:
    from madsci.resource_manager.backup_tools.postgres_backup import (
        PostgreSQLBackupSettings,
        PostgreSQLBackupTool,
    )
except ImportError:
    # Fallback for testing or when resource_manager not installed
    PostgreSQLBackupSettings = None  # type: ignore[assignment, misc]
    PostgreSQLBackupTool = None  # type: ignore[assignment, misc]


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
@click.option("--encrypt/--no-encrypt", default=False, help="Enable encryption")
@click.option("--encrypt-key", type=click.Path(exists=True), help="Encryption key file")
def create(
    db_url: str,
    backup_dir: str,
    db_type: Optional[str],
    name: Optional[str],
    encrypt: bool,
    encrypt_key: Optional[str],
) -> None:
    """Create a new database backup.

    Examples:
        madsci-backup create --db-url postgresql://localhost/mydb

        madsci-backup create --db-url mongodb://localhost/mydb --name pre-deploy

        madsci-backup create --db-url postgresql://localhost/mydb --encrypt --encrypt-key ~/.madsci/key
    """
    try:
        # Auto-detect database type if not specified
        if not db_type:
            db_type = detect_database_type(db_url)

        # Create appropriate backup tool
        backup_path: Path

        if db_type == "postgresql":
            if not PostgreSQLBackupTool or not PostgreSQLBackupSettings:
                click.echo(
                    "ERROR: PostgreSQL backup tools not available. "
                    "Please install with: pip install madsci-resource-manager",
                    err=True,
                )
                sys.exit(1)

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

        # Apply encryption if requested
        if encrypt:
            if not BackupEncryption:
                click.echo(
                    "ERROR: Encryption module not available. "
                    "Please install with: pip install madsci-common[encryption]",
                    err=True,
                )
                sys.exit(1)

            if not encrypt_key:
                click.echo(
                    "ERROR: --encrypt-key required when --encrypt is enabled", err=True
                )
                sys.exit(1)

            encryptor = BackupEncryption(Path(encrypt_key))
            encrypted_path = encryptor.encrypt_backup(backup_path)
            click.echo(f"✓ Backup created and encrypted: {encrypted_path}")
        else:
            click.echo(f"✓ Backup created: {backup_path}")

    except Exception as e:
        click.echo(f"✗ Backup failed: {e}", err=True)
        sys.exit(1)


@madsci_backup.command()
@click.option(
    "--type",
    "db_type",
    type=click.Choice(["postgresql", "mongodb"]),
    help="Filter by database type",
)
@click.option("--from", "date_from", help="Filter from date (YYYY-MM-DD)")
@click.option("--to", "date_to", help="Filter to date (YYYY-MM-DD)")
def list(
    db_type: Optional[str], date_from: Optional[str], date_to: Optional[str]
) -> None:
    """List available backups.

    Examples:
        madsci-backup list

        madsci-backup list --type postgresql

        madsci-backup list --from 2024-01-01 --to 2024-01-31
    """
    try:
        if not BackupRegistry:
            click.echo(
                "ERROR: Backup registry not available. "
                "Using registry requires additional setup.",
                err=True,
            )
            sys.exit(1)

        # Parse dates if provided
        parsed_date_from = datetime.fromisoformat(date_from) if date_from else None
        parsed_date_to = datetime.fromisoformat(date_to) if date_to else None

        # Get backups from registry
        registry = BackupRegistry()
        backups = registry.list_backups(
            database_type=db_type, date_from=parsed_date_from, date_to=parsed_date_to
        )

        if not backups:
            click.echo("No backups found matching criteria")
            return

        # Display backups
        click.echo(f"\nFound {len(backups)} backup(s):\n")
        for backup in backups:
            click.echo(f"  • {backup.backup_path}")
            click.echo(f"    Type: {backup.database_type}")
            click.echo(f"    Created: {backup.created_at}")
            click.echo(f"    Size: {backup.backup_size:,} bytes")
            click.echo(f"    Valid: {backup.validation_status}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ List failed: {e}", err=True)
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
@click.option(
    "--encrypt-key",
    type=click.Path(exists=True),
    help="Encryption key for encrypted backups",
)
def restore(
    backup: str, db_url: str, db_type: Optional[str], encrypt_key: Optional[str]
) -> None:
    """Restore from a backup.

    Examples:
        madsci-backup restore --backup /path/to/backup.dump --db-url postgresql://localhost/mydb

        madsci-backup restore --backup /path/to/backup.dump.enc --db-url postgresql://localhost/mydb --encrypt-key ~/.madsci/key
    """
    try:
        backup_path = Path(backup)

        # Handle encrypted backups
        if backup_path.suffix == ".enc":
            if not BackupEncryption:
                click.echo(
                    "ERROR: Encryption module not available for encrypted backups",
                    err=True,
                )
                sys.exit(1)

            if not encrypt_key:
                click.echo(
                    "ERROR: --encrypt-key required for encrypted backups", err=True
                )
                sys.exit(1)

            encryptor = BackupEncryption(Path(encrypt_key))
            backup_path = encryptor.decrypt_backup(backup_path)
            click.echo(f"✓ Backup decrypted: {backup_path}")

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
