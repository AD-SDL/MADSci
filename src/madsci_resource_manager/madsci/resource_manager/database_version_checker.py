"""Database version checking and validation for MADSci."""

import importlib.metadata
import os
import traceback
from pathlib import Path
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.resource_manager.resource_tables import SchemaVersionTable
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select


class DatabaseVersionChecker:
    """Handles database version validation and checking."""

    def __init__(self, db_url: str, logger: Optional[EventClient] = None) -> None:
        """Initialize the DatabaseVersionChecker."""
        self.db_url = db_url
        self.logger = logger or EventClient()
        self.engine = create_engine(db_url)

    def dispose(self) -> None:
        """Dispose of the engine and cleanup resources."""
        if self.engine:
            self.engine.dispose()
            self.logger.info("Database version checker engine disposed")

    def get_current_madsci_version(self) -> str:
        """Get the current MADSci version from the package."""
        try:
            return importlib.metadata.version("madsci")
        except importlib.metadata.PackageNotFoundError as e:
            self.logger.error("MADSci package not found in the current environment")
            raise RuntimeError(
                "Cannot determine MADSci version: package not found. "
                "Please ensure MADSci is properly installed in the current environment."
            ) from e

    def get_database_version(self) -> Optional[str]:
        """Get the current database schema version."""
        try:
            with Session(self.engine) as session:
                # Check if schema version table exists
                inspector = inspect(self.engine)
                if "madsci_schema_version" not in inspector.get_table_names():
                    return None

                # Get the latest version entry
                statement = select(SchemaVersionTable).order_by(
                    SchemaVersionTable.applied_at.desc()
                )
                result = session.exec(statement).first()
                return result.version if result else None

        except Exception:
            self.logger.error(
                f"Error getting database version: {traceback.format_exc()}"
            )
            return None

    def is_migration_needed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database migration is needed.

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)
        """
        current_version = self.get_current_madsci_version()
        db_version = self.get_database_version()

        if db_version is None:
            # No version table exists, this is either a fresh install or pre-migration
            self.logger.info(
                "No database version found - migration needed for version tracking"
            )
            return True, current_version, None

        if db_version != current_version:
            self.logger.warning(
                f"Version mismatch: MADSci v{current_version}, Database v{db_version}"
            )
            return True, current_version, db_version

        self.logger.info(
            f"Database version {db_version} matches MADSci version {current_version}"
        )
        return False, current_version, db_version

    def _is_running_in_docker(self) -> bool:
        """Detect if the application is running inside a Docker container."""
        try:
            # Check for .dockerenv file
            if Path("/.dockerenv").exists():
                return True

            # Check cgroup for docker
            if Path("/proc/1/cgroup").exists():
                with open("/proc/1/cgroup") as f:  # noqa
                    return "docker" in f.read() or "containerd" in f.read()

            return False
        except Exception:
            return False

    def _get_container_name(self) -> str:
        """Get the container name for resource manager."""
        return os.getenv("container_name", "resource_manager")  # noqa

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.
        """
        needs_migration, madsci_version, db_version = self.is_migration_needed()

        if needs_migration:
            # Detect if running in Docker
            is_docker = self._is_running_in_docker()

            if db_version is None:
                if is_docker:
                    container_name = self._get_container_name()
                    message = (
                        f"Database schema version not found. "
                        f"MADSci version is {madsci_version}. "
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                    )
                else:
                    message = (
                        f"Database schema version not found. "
                        f"MADSci version is {madsci_version}. "
                        f"Please run the migration tool to initialize version tracking:\n"
                        f"python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                    )
                self.logger.warning("Database needs version tracking initialization")
            else:
                if is_docker:
                    container_name = self._get_container_name()
                    message = (
                        f"Database schema version mismatch detected!\n"
                        f"MADSci version: {madsci_version}\n"
                        f"Database version: {db_version}\n"
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                    )
                else:
                    message = (
                        f"Database schema version mismatch detected!\n"
                        f"MADSci version: {madsci_version}\n"
                        f"Database version: {db_version}\n"
                        f"Please run the migration tool to update the database schema:\n"
                        f"python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                    )
                self.logger.error("Database schema version mismatch detected")

            self.logger.error(message)
            raise RuntimeError(message)

        self.logger.info("Database version validation passed")

    def create_version_table_if_not_exists(self) -> None:
        """Create the schema version table if it doesn't exist."""
        try:
            SchemaVersionTable.metadata.create_all(self.engine)
            self.logger.info("Schema version table created")
        except Exception as e:
            self.logger.error(f"Error creating schema version table: {e}")
            raise

    def record_version(
        self, version: str, migration_notes: Optional[str] = None
    ) -> None:
        """Record a new version in the database."""
        try:
            with Session(self.engine) as session:
                # Check if version already exists
                existing_version = session.exec(
                    select(SchemaVersionTable).where(
                        SchemaVersionTable.version == version
                    )
                ).first()

                if existing_version:
                    # Update existing record
                    existing_version.migration_notes = migration_notes
                    session.add(existing_version)
                    self.logger.info(
                        f"Updated existing database version record: {version}"
                    )
                else:
                    # Create new record
                    version_entry = SchemaVersionTable(
                        version=version, migration_notes=migration_notes
                    )
                    session.add(version_entry)
                    self.logger.info(f"Recorded new database version: {version}")

                session.commit()
        except Exception as e:
            self.logger.error(f"Error recording version: {e}")
            raise
