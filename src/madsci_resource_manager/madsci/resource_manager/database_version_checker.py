"""Database version checking and validation for MADSci."""

import importlib.metadata
import os
import traceback
from pathlib import Path
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.resource_manager.resource_tables import SchemaVersionTable
from pydantic_extra_types.semantic_version import SemanticVersion
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select


class DatabaseVersionChecker:
    """Handles database version validation and checking."""

    def __init__(self, db_url: str, logger: Optional[EventClient] = None) -> None:
        """Initialize the DatabaseVersionChecker."""
        self.db_url = db_url
        self.logger = logger or EventClient()
        self.engine = create_engine(db_url)

    def __del__(self) -> None:
        """Cleanup database engine resources."""
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("Database version checker engine disposed")

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

    def is_version_tracked(self) -> bool:
        """
        Check if version tracking exists in the database.

        Returns True if the schema version table exists AND has at least one version record.
        Returns False if the table doesn't exist or is empty.
        """
        try:
            with Session(self.engine) as session:
                inspector = inspect(self.engine)
                if "madsci_schema_version" not in inspector.get_table_names():
                    return False

                # Check if table has any records
                statement = select(SchemaVersionTable)
                result = session.exec(statement).first()
                return result is not None

        except Exception:
            return False

    def versions_match(self, version1: str, version2: str) -> bool:
        """
        Check if two versions match based on major.minor comparison only.

        Ignores patch version and pre-release/build metadata.

        Examples:
            1.0.0 == 1.0.1  -> True (same major.minor)
            1.0.0 == 1.1.0  -> False (different minor)
            1.0.0 == 2.0.0  -> False (different major)
        """
        try:
            # For some reason release candidate versions are extracted as 0.0.0rc1 rather than 0.0.0-rc1
            v1_str = (
                version1.replace("rc", "-rc")
                .replace("alpha", "-alpha")
                .replace("beta", "-beta")
            )
            v2_str = (
                version2.replace("rc", "-rc")
                .replace("alpha", "-alpha")
                .replace("beta", "-beta")
            )

            v1 = SemanticVersion.parse(v1_str)
            v2 = SemanticVersion.parse(v2_str)

            # Compare only major and minor versions
            return v1.major == v2.major and v1.minor == v2.minor
        except Exception as e:
            self.logger.warning(
                f"Could not parse versions for comparison ('{version1}', '{version2}'): {e}"
            )
            # If we can't parse, fall back to exact string comparison
            return version1 == version2

    def is_migration_needed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database migration is needed.

        Migration is only needed if:
        1. Version IS tracked in the database, AND
        2. Major.minor version mismatch between MADSci and database

        If version is NOT tracked, no migration is needed (server will start normally).

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)
        """
        current_version = self.get_current_madsci_version()
        db_version = self.get_database_version()

        # If version tracking doesn't exist, no migration needed
        # User can manually run migration if they want to start tracking
        if not self.is_version_tracked():
            is_docker = self._is_running_in_docker()

            if is_docker:
                container_name = self._get_container_name()
                command = (
                    f"docker-compose run --rm -v $(pwd)/src:/home/madsci/MADSci/src {container_name} "
                    f"python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                )
            else:
                command = f"python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"

            self.logger.info(
                "No version tracking found - database will start without version validation. "
                "To enable version tracking, run the migration tool manually! "
            )

            self.logger.info(f"{command}")
            return False, current_version, None

        # Version IS tracked - check for mismatch using major.minor comparison
        if not self.versions_match(current_version, db_version):
            self.logger.warning(
                f"Version mismatch (major.minor): "
                f"MADSci v{current_version}, Database v{db_version}"
            )
            return True, current_version, db_version

        self.logger.info(
            f"Database version {db_version} is compatible with MADSci version {current_version} "
            "(major.minor versions match)"
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
            # Only raise error if version IS tracked but mismatched
            is_docker = self._is_running_in_docker()

            if is_docker:
                container_name = self._get_container_name()
                message = (
                    f"Database schema version mismatch detected!\n"
                    f"MADSci version: {madsci_version}\n"
                    f"Database version: {db_version}\n"
                    f"Please run the migration tool in the container: \n"
                    f"docker-compose run --rm -v $(pwd)/src:/home/madsci/MADSci/src {container_name} "
                    f"python -m madsci.resource_manager.migration_tool --db-url '{self.db_url}'"
                )
            else:
                message = (
                    f"Database schema version mismatch detected! \n"
                    f"MADSci version: {madsci_version} \n"
                    f"Database version: {db_version} \n"
                    f"Please run the migration tool to update the database schema: \n"
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
