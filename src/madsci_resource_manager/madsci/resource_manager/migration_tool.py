"""Database migration tool for MADSci resources using Alembic with automatic type conversion handling."""

import argparse
import os
import re
import subprocess
import sys
import traceback
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from madsci.client.event_client import EventClient
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.resource_tables import ResourceTable, SchemaVersionTable
from psycopg2 import sql
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select


class DatabaseMigrator:
    """Handles database schema migrations for MADSci using Alembic with automatic type conversion handling."""

    def __init__(
        self, db_url: Optional[str] = None, logger: Optional[EventClient] = None
    ) -> None:
        """Initialize the migrator with database URL and logger."""
        # If no db_url provided, try to get from environment
        if db_url is None:
            db_url = self._get_database_url_from_env()

        self.db_url = db_url
        self.logger = logger or EventClient()
        self.engine = create_engine(db_url)
        self.version_checker = DatabaseVersionChecker(db_url, logger)

        # Get the package root directory for consistent file paths
        self.package_root = self._get_package_root()

        # Parse database connection details for backup
        self.backup_dir = self._get_backup_directory()

        # Setup Alembic configuration
        self.alembic_cfg = self._setup_alembic_config()

    def _get_package_root(self) -> Path:
        """Get the root directory of the madsci.resource_manager package."""
        try:
            # Get the directory where this migration_tool.py file is located
            current_file = Path(__file__).resolve()

            # Navigate up to find the package root
            # This should be the directory containing alembic.ini
            package_root = current_file.parent

            # Look for alembic.ini to confirm we have the right directory
            alembic_ini = package_root / "alembic.ini"

            if not alembic_ini.exists():
                # If not found, check parent directories
                for parent in package_root.parents:
                    potential_ini = parent / "alembic.ini"
                    if potential_ini.exists():
                        package_root = parent
                        break
                else:
                    # Fall back to current working directory
                    package_root = Path.cwd()

            self.logger.info(f"Using package root: {package_root}")
            return package_root

        except Exception as e:
            self.logger.warning(f"Could not determine package root: {e}")
            return Path.cwd()

    def _get_backup_directory(self) -> Path:
        """Get the backup directory path in the current working directory."""
        # Create backup directory in the current working directory where the command was run
        current_dir = Path.cwd()
        backup_dir = current_dir / ".madsci" / "postgres" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Using backup directory: {backup_dir}")
        return backup_dir

    def _get_database_url_from_env(self) -> str:
        """Get database URL from environment variables as fallback."""
        # Try to get from environment variable
        db_url = os.getenv("RESOURCES_DB_URL")
        if db_url:
            return db_url

        # If no URL found, raise an error with helpful message
        raise RuntimeError(
            "No database URL provided and RESOURCES_DB_URL environment variable not found. "
            "Please either:\n"
            "1. Provide --db-url argument, or\n"
            "2. Set RESOURCES_DB_URL in your environment/.env file\n"
            "Example: RESOURCES_DB_URL=postgresql://user:pass@localhost:5432/resources"
        )

    def _setup_alembic_config(self) -> Config:
        """Setup Alembic configuration with proper paths."""
        # Look for alembic.ini in the package root
        alembic_ini_path = self.package_root / "alembic.ini"

        if not alembic_ini_path.exists():
            raise FileNotFoundError(
                f"alembic.ini not found at {alembic_ini_path}. "
                f"Please ensure the file exists in the package directory or run 'alembic init alembic' first."
            )

        # Create Alembic config with absolute path
        alembic_cfg = Config(str(alembic_ini_path))

        # Set the database URL for Alembic
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)

        # Ensure Alembic script location is set to absolute path
        script_location = self.package_root / "alembic"
        alembic_cfg.set_main_option("script_location", str(script_location))

        # Set prepend_sys_path to ensure imports work
        alembic_cfg.set_main_option("prepend_sys_path", str(self.package_root))

        self.logger.info(
            f"Alembic config: ini={alembic_ini_path}, script_location={script_location}"
        )

        return alembic_cfg

    def _parse_db_url(self) -> dict:
        """Parse PostgreSQL connection details from database URL."""

        parsed = urlparse.urlparse(self.db_url)
        return {
            "host": parsed.hostname,
            "port": parsed.port,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/") if parsed.path else "resources",
        }

    def create_backup(self) -> Path:
        """Create a backup of the current database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_info = self._parse_db_url()

        backup_filename = f"madsci_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename

        # Set PGPASSWORD environment variable for pg_dump
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        pg_dump_cmd = [
            "pg_dump",
            "-h",
            db_info["host"],
            "-p",
            str(db_info["port"]),
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "--no-password",
            "--verbose",
            "--file",
            str(backup_path),
        ]

        try:
            self.logger.log_info(f"Creating database backup: {backup_path}")
            result = subprocess.run(  # noqa: S603
                pg_dump_cmd, env=env, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database backup completed successfully: {backup_path}"
                )
                return backup_path
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e.stderr}")
            raise RuntimeError(f"Database backup failed: {e}") from e
        except FileNotFoundError as fe:
            raise RuntimeError(
                "pg_dump command not found. Please ensure PostgreSQL client tools are installed. {fe}"
            ) from fe

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore database from a backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        db_info = self._parse_db_url()

        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        # First, drop and recreate the database
        self._recreate_database(db_info)

        psql_cmd = [
            "psql",
            "-h",
            db_info["host"],
            "-p",
            str(db_info["port"]),
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "--no-password",
            "--file",
            str(backup_path),
        ]

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")
            result = subprocess.run(  # noqa: S603
                psql_cmd, env=env, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
            else:
                raise RuntimeError(f"psql restore failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            raise RuntimeError(f"Database restore failed: {e}") from e

    def _recreate_database(self, db_info: dict) -> None:
        """Drop and recreate the database for restore."""
        # Connect to postgres database to drop/create target database
        postgres_url = self.db_url.replace(f"/{db_info['database']}", "/postgres")
        postgres_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")

        # Get raw connection properly
        raw_conn = postgres_engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            try:
                # Terminate existing connections to the target database
                # Use parameterized query to avoid SQL injection warnings
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                    AND pid <> pg_backend_pid()
                """,
                    (db_info["database"],),
                )

                # For DROP/CREATE DATABASE, we need to use identifier quoting
                # Since these can't be parameterized, we'll validate the database name first
                db_name = db_info["database"]

                # Basic validation: ensure database name contains only safe characters

                if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
                    raise ValueError(
                        f"Database name contains unsafe characters: {db_name}"
                    )

                # Use quoted identifiers for DROP/CREATE (these operations can't use parameters)

                # Drop and recreate database using sql.Identifier for safe quoting
                cursor.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(db_name)
                    )
                )
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
                )

            finally:
                cursor.close()
        finally:
            raw_conn.close()
            postgres_engine.dispose()

    def apply_schema_migrations(self) -> None:
        """Apply schema migrations using Alembic with automatic migration generation."""
        try:
            self.logger.info("Applying schema migrations using Alembic...")

            # Set environment variable for Alembic to use
            os.environ["RESOURCES_DB_URL"] = self.db_url

            # Change to the package root directory for Alembic operations
            original_cwd = Path.cwd()
            os.chdir(self.package_root)

            try:
                # Initialize Alembic if this is the first run
                self._ensure_alembic_initialized()

                # Auto-generate migration if there are model changes
                if self._has_pending_model_changes():
                    self.logger.info("Detected model changes, generating migration...")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    migration_message = f"Auto-generated migration {timestamp}"
                    command.revision(
                        self.alembic_cfg, message=migration_message, autogenerate=True
                    )

                    # Post-process the generated migration file
                    versions_dir = self.package_root / "alembic" / "versions"
                    if versions_dir.exists():
                        migration_files = list(versions_dir.glob("*.py"))
                        if migration_files:
                            latest_migration = max(
                                migration_files, key=lambda p: p.stat().st_mtime
                            )
                            self._post_process_migration_file(latest_migration)

                    self.logger.info(
                        f"Generated and processed migration: {migration_message}"
                    )
                else:
                    self.logger.info("No model changes detected")

                # Run Alembic upgrade to head
                command.upgrade(self.alembic_cfg, "head")

                # Ensure our version tracking table exists (separate from Alembic)
                SchemaVersionTable.metadata.create_all(self.engine)

                self.logger.info("Alembic migrations applied successfully")

            finally:
                # Always restore the original working directory
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"Alembic migration failed: {traceback.format_exc()}")
            raise RuntimeError(f"Schema migration failed: {e}") from e

    def _post_process_migration_file(self, migration_file_path: Path) -> None:
        """Post-process generated migration files to handle common type conversions."""
        try:
            with open(migration_file_path) as f:  # noqa: PTH123
                content = f.read()

            # Pattern to find VARCHAR to Float conversions

            # Replace basic alter_column operations with safe conversions
            varchar_to_float_pattern = r"op\.alter_column\('(\w+)', '(\w+)',\s*existing_type=sa\.VARCHAR\(\),\s*type_=sa\.Float\(\),\s*existing_nullable=True\)"

            def replace_varchar_to_float(match: Any) -> str:
                table_name = match.group(1)
                column_name = match.group(2)
                # Use triple quotes with raw string to avoid escape issues
                return rf'''op.execute(r"""
                            ALTER TABLE {table_name}
                            ALTER COLUMN {column_name} TYPE FLOAT
                            USING CASE
                                WHEN {column_name} IS NULL THEN NULL
                                WHEN {column_name} ~ '^-?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$' THEN {column_name}::float
                                ELSE NULL
                            END
                        """)'''

            # Apply the replacement
            new_content = re.sub(
                varchar_to_float_pattern, replace_varchar_to_float, content
            )

            # Also handle VARCHAR to Integer conversions
            varchar_to_int_pattern = r"op\.alter_column\('(\w+)', '(\w+)',\s*existing_type=sa\.VARCHAR\(\),\s*type_=sa\.Integer\(\),\s*existing_nullable=True\)"

            def replace_varchar_to_int(match: Any) -> str:
                table_name = match.group(1)
                column_name = match.group(2)
                # Use triple quotes with raw string to avoid escape issues
                return f'''op.execute(r"""
                            ALTER TABLE {table_name}
                            ALTER COLUMN {column_name} TYPE INTEGER
                            USING CASE
                                WHEN {column_name} IS NULL THEN NULL
                                WHEN {column_name} ~ '^-?[0-9]+$' THEN {column_name}::integer
                                ELSE NULL
                            END
                        """)'''

            new_content = re.sub(
                varchar_to_int_pattern, replace_varchar_to_int, new_content
            )

            # Only write back if changes were made
            if new_content != content:
                with open(migration_file_path, "w") as f:  # noqa: PTH123
                    f.write(new_content)
                self.logger.info(
                    f"Post-processed migration file for safe type conversions: {migration_file_path}"
                )
            else:
                self.logger.info("No type conversion post-processing needed")

        except Exception as e:
            self.logger.warning(f"Could not post-process migration file: {e}")

    def _has_pending_model_changes(self) -> bool:
        """Check if there are pending model changes by comparing current schema with models."""
        try:
            # Get current database metadata and compare with model metadata
            with self.engine.connect() as connection:
                context = MigrationContext.configure(connection)

                # Compare database schema with model metadata
                diff = compare_metadata(context, ResourceTable.metadata)

                # Count ALL differences, don't filter too aggressively
                relevant_changes = []
                for change in diff:
                    # Convert change to string to check for alembic_version table
                    change_str = str(change)
                    if "alembic_version" not in change_str:
                        relevant_changes.append(change)

                has_changes = len(relevant_changes) > 0

                if has_changes:
                    self.logger.info(
                        f"Found {len(relevant_changes)} relevant schema differences"
                    )
                    for change in relevant_changes[:5]:  # Log first 5 changes
                        self.logger.info(f"  - {change}")

                return has_changes

        except Exception as e:
            self.logger.warning(f"Could not check for model changes: {e}")
            return False

    def _ensure_alembic_initialized(self) -> None:
        """Ensure Alembic is properly initialized."""
        try:
            inspector = inspect(self.engine)

            if "alembic_version" not in inspector.get_table_names():
                self.logger.info("Initializing Alembic version tracking...")
                # Stamp the database with the current revision
                command.stamp(self.alembic_cfg, "head")

        except Exception as e:
            self.logger.warning(f"Could not initialize Alembic: {e}")
            # This might be the first migration, which is OK

    def generate_migration(self, message: str) -> None:
        """Generate a new Alembic migration based on model changes."""
        try:
            self.logger.info(f"Generating new migration: {message}")
            os.environ["RESOURCES_DB_URL"] = self.db_url

            # Change to package root for generation
            original_cwd = Path.cwd()
            os.chdir(self.package_root)

            try:
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
                self.logger.info("Migration file generated successfully")
            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"Migration generation failed: {e}")
            raise

    def run_migration(self, target_version: Optional[str] = None) -> None:
        """Run the complete migration process using Alembic."""
        try:
            # Determine target version
            if target_version is None:
                target_version = self.version_checker.get_current_madsci_version()

            current_db_version = self.version_checker.get_database_version()

            self.logger.info(f"Starting migration to version {target_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # Check if this is actually a downgrade scenario
            if current_db_version and current_db_version != target_version:
                # Check if we already have a record for the target version
                existing_target_record = self._check_for_existing_version_record(
                    target_version
                )

                if existing_target_record:
                    self.logger.info(
                        f"Found existing database record for version {target_version}"
                    )
                    self.logger.info(
                        "This appears to be a downgrade - updating version tracking to match current MADSci version"
                    )

                    # Update the version record to mark the target version as current
                    self._mark_version_as_current(target_version)

                    self.logger.info(
                        f"Version tracking updated to {target_version} (no schema changes needed)"
                    )
                    return

            # Regular migration process for upgrades or first-time setups
            # Create backup
            backup_path = self.create_backup()

            try:
                # Apply Alembic migrations
                self.apply_schema_migrations(target_version)

                # Record new version in our tracking system
                migration_notes = f"Alembic migration from {current_db_version or 'unversioned'} to {target_version}"
                self.version_checker.record_version(target_version, migration_notes)

                self.logger.info(
                    f"Migration completed successfully to version {target_version}"
                )

            except Exception as migration_error:
                self.logger.error(f"Migration failed: {migration_error}")
                self.logger.info("Attempting to restore from backup...")

                try:
                    self.restore_from_backup(backup_path)
                    self.logger.info("Database restored from backup successfully")
                except Exception as restore_error:
                    self.logger.error(
                        f"CRITICAL: Backup restore also failed: {restore_error}"
                    )
                    self.logger.error("Manual intervention required!")

                raise migration_error

        except Exception as e:
            self.logger.error(f"Migration process failed: {e}")
            raise

    def _check_for_existing_version_record(self, version: str) -> bool:
        """Check if a version record already exists in the database."""
        try:
            with Session(self.engine) as session:
                statement = select(SchemaVersionTable).where(
                    SchemaVersionTable.version == version
                )
                result = session.exec(statement).first()
                return result is not None
        except Exception as e:
            self.logger.warning(f"Could not check for existing version record: {e}")
            return False

    def _mark_version_as_current(self, version: str) -> None:
        """Update the version record to mark it as the current version."""
        try:
            with Session(self.engine) as session:
                # Find the existing record for this version
                statement = select(SchemaVersionTable).where(
                    SchemaVersionTable.version == version
                )
                existing_record = session.exec(statement).first()

                if existing_record:
                    # Update the timestamp to make it the "current" version

                    existing_record.applied_at = datetime.now()
                    existing_record.migration_notes = (
                        f"Version synchronized with MADSci package version {version}"
                    )
                    session.add(existing_record)
                    session.commit()
                    self.logger.info(
                        f"Updated version record for {version} to current timestamp"
                    )
                else:
                    # Create a new record if none exists
                    self.version_checker.record_version(
                        version,
                        f"Version synchronized with MADSci package version {version}",
                    )
                    self.logger.info(f"Created new version record for {version}")

        except Exception as e:
            self.logger.error(f"Could not mark version as current: {e}")
            raise


def main() -> None:
    """Command line interface for the migration tool."""

    parser = argparse.ArgumentParser(
        description="MADSci Database Migration Tool with Alembic"
    )
    parser.add_argument(
        "--db-url",
        help="Database URL (e.g., postgresql://user:pass@localhost:5432/resources). "
        "If not provided, will try to read RESOURCES_DB_URL from environment.",
    )
    parser.add_argument(
        "--target-version",
        help="Target version to migrate to (defaults to current MADSci version)",
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only create a backup, do not run migration",
    )
    parser.add_argument(
        "--restore-from", help="Restore from specified backup file instead of migrating"
    )
    parser.add_argument(
        "--generate-migration",
        help="Generate a new migration file with the given message",
    )

    args = parser.parse_args()

    logger = EventClient()

    try:
        migrator = DatabaseMigrator(args.db_url, logger)

        if args.generate_migration:
            migrator.generate_migration(args.generate_migration)
        elif args.restore_from:
            backup_path = Path(args.restore_from)
            migrator.restore_from_backup(backup_path)
        elif args.backup_only:
            backup_path = migrator.create_backup()
            logger.log_info(f"Backup created: {backup_path}")
        else:
            migrator.run_migration(args.target_version)

    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        logger.log_error(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
