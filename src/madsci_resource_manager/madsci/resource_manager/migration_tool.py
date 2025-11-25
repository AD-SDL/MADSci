"""Database migration tool for MADSci resources using Alembic with automatic type conversion handling."""

import fcntl
import os
import re
import sys
import tempfile
import time
import traceback
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from madsci.client.event_client import EventClient
from madsci.common.backup_tools.postgres_backup import PostgreSQLBackupTool
from madsci.common.types.backup_types import PostgreSQLBackupSettings
from madsci.common.types.base_types import MadsciBaseSettings, PathLike
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.resource_tables import ResourceTable, SchemaVersionTable
from pydantic import Field
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select


class DatabaseMigrationSettings(
    MadsciBaseSettings,
    env_file=(".env", "resources.env", "migration.env"),
    toml_file=("settings.toml", "resources.settings.toml", "migration.settings.toml"),
    yaml_file=("settings.yaml", "resources.settings.yaml", "migration.settings.yaml"),
    json_file=("settings.json", "resources.settings.json", "migration.settings.json"),
    env_prefix="RESOURCES_MIGRATION_",
):
    """Configuration settings for PostgreSQL database migration operations."""

    db_url: Optional[str] = Field(
        default=None,
        title="Database URL",
        description="PostgreSQL connection URL (e.g., postgresql://user:pass@localhost:5432/resources). "
        "If not provided, will try RESOURCES_DB_URL environment variable.",
    )
    target_version: Optional[str] = Field(
        default=None,
        title="Target Version",
        description="Target version to migrate to (defaults to current MADSci version)",
    )
    backup_dir: PathLike = Field(
        default=Path(".madsci/postgres/backups"),
        title="Backup Directory",
        description="Directory where database backups will be stored. "
        "Relative to the current working directory unless absolute.",
    )
    backup_only: bool = Field(
        default=False,
        title="Backup Only",
        description="Only create a backup, do not run migration",
    )
    restore_from: Optional[PathLike] = Field(
        default=None,
        title="Restore From",
        description="Restore from specified backup file instead of migrating",
    )
    generate_migration: Optional[str] = Field(
        default=None,
        title="Generate Migration",
        description="Generate a new migration file with the given message",
    )

    def get_effective_db_url(self) -> str:
        """Get the effective database URL, trying fallback environment variables if needed."""
        if self.db_url:
            return self.db_url

        # Try environment variable
        db_url = os.getenv("RESOURCES_DB_URL")
        if db_url:
            return db_url

        raise RuntimeError(
            "No database URL provided and RESOURCES_DB_URL environment variable not found. "
            "Please either:\n"
            "1. Provide --db-url argument, or\n"
            "2. Set RESOURCES_DB_URL in your environment/.env file\n"
            "Example: RESOURCES_DB_URL=postgresql://user:pass@localhost:5432/resources"
        )


class DatabaseMigrator:
    """Handles database schema migrations for MADSci using Alembic with automatic type conversion handling."""

    def __init__(
        self, settings: DatabaseMigrationSettings, logger: Optional[EventClient] = None
    ) -> None:
        """Initialize the migrator with settings and logger."""
        self.settings = settings
        self.db_url = settings.get_effective_db_url()
        self.logger = logger or EventClient()
        self.engine = create_engine(self.db_url)
        self.version_checker = DatabaseVersionChecker(self.db_url, self.logger)

        # Get the package root directory for consistent file paths
        self.package_root = self._get_package_root()

        raw_backup = Path(self.settings.backup_dir)
        self.backup_dir = (
            raw_backup if raw_backup.is_absolute() else (Path.cwd() / raw_backup)
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using backup directory: {self.backup_dir}")

        # Create backup tool instance with migration-appropriate settings
        backup_settings = PostgreSQLBackupSettings(
            db_url=self.db_url,
            backup_dir=self.backup_dir,
            max_backups=10,  # Migration-specific default
            validate_integrity=True,  # Always validate for migrations
            backup_format="custom",  # Use custom format for faster restore
        )
        self.backup_tool = PostgreSQLBackupTool(backup_settings, logger=self.logger)

        # Setup Alembic configuration
        self.alembic_cfg = self._setup_alembic_config()

        # Migration locking attributes
        self.lock_file: Optional[Path] = None
        self.lock_fd: Optional[int] = None

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

    def _acquire_migration_lock(self) -> None:
        """Acquire exclusive lock for migration operations."""
        db_info = self._parse_db_url()
        database_name = db_info["database"]

        # Create lock file in system temp directory
        temp_dir = Path(tempfile.gettempdir())
        self.lock_file = temp_dir / f"madsci_migration_{database_name}.lock"

        try:
            # Open lock file for writing
            self.lock_fd = os.open(
                str(self.lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644
            )

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write process info to lock file
            lock_info = f"pid={os.getpid()}\ntimestamp={time.time()}\ndatabase={database_name}\n"
            os.write(self.lock_fd, lock_info.encode())

            self.logger.info(f"Acquired migration lock: {self.lock_file}")

        except BlockingIOError:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
                self.lock_fd = None
            raise RuntimeError(
                f"Another migration is already in progress for database '{database_name}'. "
                f"Lock file: {self.lock_file}"
            ) from None
        except Exception as e:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
                self.lock_fd = None
            raise RuntimeError(f"Failed to acquire migration lock: {e}") from e

    def _release_migration_lock(self) -> None:
        """Release migration lock."""
        if self.lock_fd is not None:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                self.logger.info("Released migration lock")
            except Exception as e:
                self.logger.warning(f"Error releasing lock: {e}")
            finally:
                self.lock_fd = None

        if self.lock_file and self.lock_file.exists():
            try:
                self.lock_file.unlink()
                self.logger.info(f"Removed lock file: {self.lock_file}")
            except Exception as e:
                self.logger.warning(f"Error removing lock file: {e}")
            finally:
                self.lock_file = None

    def _acquire_migration_lock_with_staleness_check(self) -> None:
        """Acquire migration lock with stale lock detection and cleanup."""
        db_info = self._parse_db_url()
        database_name = db_info["database"]

        temp_dir = Path(tempfile.gettempdir())
        lock_file_path = temp_dir / f"madsci_migration_{database_name}.lock"

        # Check for stale lock
        if lock_file_path.exists():
            try:
                # Try to read lock file
                with lock_file_path.open() as f:
                    lock_content = f.read()

                # Extract timestamp if available
                timestamp = None
                for line in lock_content.split("\n"):
                    if line.startswith("timestamp="):
                        timestamp = float(line.split("=", 1)[1])
                        break

                # Check if lock is stale (older than 1 hour)
                if timestamp and (time.time() - timestamp) > 3600:
                    self.logger.warning(
                        f"Detected stale lock file, removing: {lock_file_path}"
                    )
                    lock_file_path.unlink()

            except (OSError, ValueError) as e:
                self.logger.warning(f"Error checking stale lock: {e}")

        # Now try to acquire lock normally
        self._acquire_migration_lock()

    def _log_alembic_state(self, when: str) -> None:
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            heads = list(script.get_heads())
            self.logger.info(f"[{when}] Alembic script heads: {heads}")

            # DB current revision(s)
            curr = []

            def _capture_current(
                _rev: Any, context: Any
            ) -> None:  # rev is head; context.get_current_revision() returns DB rev
                curr.append(context.get_current_revision())
                return []

            with EnvironmentContext(self.alembic_cfg, script, fn=_capture_current):
                pass
            self.logger.info(
                f"[{when}] Database current revision: {curr[0] if curr else None}"
            )
        except Exception as e:
            self.logger.warning(f"[{when}] Could not log Alembic state: {e}")

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
                # Run Alembic upgrade to head
                try:
                    self.logger.info("=== UPGRADE START ===")  # direct stdout sentinel
                    command.upgrade(self.alembic_cfg, "head")
                    self.logger.info("=== UPGRADE DONE ===")  # direct stdout sentinel
                except Exception:
                    self.logger.error("UPGRADE FAILED", exc_info=True)
                    raise
                self.logger.info("Alembic migrations applied successfully")

                # Ensure our version tracking table exists (separate from Alembic)
                SchemaVersionTable.metadata.create_all(self.engine)

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
        # Acquire migration lock to prevent concurrent migrations
        self._acquire_migration_lock()

        try:
            # Determine target version
            if target_version is None:
                target_version = self.version_checker.get_current_madsci_version()

            current_db_version = self.version_checker.get_database_version()

            self.logger.info(f"Starting migration to version {target_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # Check if this is a fresh database initialization
            if self._is_fresh_database():
                self.logger.info(
                    "Fresh database detected, performing initialization without backup..."
                )
                try:
                    # For fresh databases, just apply schema migrations and set up version tracking
                    self.apply_schema_migrations()

                    # Initialize version tracking for fresh database
                    migration_notes = f"Fresh database initialized with MADSci version {target_version}"
                    self.version_checker.record_version(target_version, migration_notes)

                    self.logger.info(
                        f"Fresh database initialization completed successfully with version {target_version}"
                    )
                    return

                except Exception as init_error:
                    self.logger.error(
                        f"Fresh database initialization failed: {init_error}"
                    )
                    raise init_error

            # EXISTING DATABASE - CREATE BACKUP FIRST using backup tool
            backup_path = self.backup_tool.create_backup("pre_migration")

            # Apply schema migrations for existing database
            try:
                # Apply Alembic migrations (this will detect and apply any schema changes)
                self.apply_schema_migrations()

                # After successful migration, update version tracking
                migration_notes = f"Alembic migration from {current_db_version or 'unversioned'} to {target_version}"
                self.version_checker.record_version(target_version, migration_notes)

                self.logger.info(
                    f"Migration completed successfully to version {target_version}"
                )

            except Exception as migration_error:
                self.logger.error(f"Migration failed: {migration_error}")
                self.logger.info("Attempting to restore from backup...")

                try:
                    self.backup_tool.restore_from_backup(backup_path)
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
        finally:
            # Always release the migration lock
            self._release_migration_lock()

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

    def _is_fresh_database(self) -> bool:
        """Check if this is a fresh database with no existing tables."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            # Consider it fresh if no resource-related tables exist
            resource_tables = ["resource", "resource_history", "madsci_schema_version"]
            has_resource_tables = any(
                table in existing_tables for table in resource_tables
            )

            if not has_resource_tables:
                self.logger.info(
                    "No existing resource tables found, treating as fresh database"
                )
                return True

            self.logger.info(f"Found existing tables: {existing_tables}")
            return False

        except Exception as e:
            self.logger.warning(f"Could not check database tables: {e}")
            return False


def main() -> None:
    """Command line interface for the migration tool."""
    logger = EventClient()

    try:
        settings = DatabaseMigrationSettings()

        migrator = DatabaseMigrator(settings, logger)

        if settings.generate_migration:
            migrator.generate_migration(settings.generate_migration)
        elif settings.restore_from:
            backup_path = Path(settings.restore_from)
            migrator.backup_tool.restore_from_backup(backup_path)
        elif settings.backup_only:
            backup_path = migrator.backup_tool.create_backup()
            logger.info(f"Backup created: {backup_path}")
        else:
            migrator.run_migration(settings.target_version)

    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
