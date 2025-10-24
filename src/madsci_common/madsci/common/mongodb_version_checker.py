"""MongoDB version checking and validation for MADSci."""

import importlib.metadata
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from madsci.client.event_client import EventClient
from packaging.version import Version
from pymongo import MongoClient


class MongoDBVersionChecker:
    """Handles MongoDB database version validation and checking."""

    def __init__(
        self,
        db_url: str,
        database_name: str,
        schema_file_path: str,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the MongoDBVersionChecker.

        Args:
            db_url: MongoDB connection URL
            database_name: Name of the database to check
            schema_file_path: Path to the schema.json file (used for validation only)
            logger: Optional logger instance
        """
        self.db_url = db_url
        self.database_name = database_name
        self.schema_file_path = Path(schema_file_path)
        self.logger = logger or EventClient()

        # Initialize MongoDB connection
        self.client = MongoClient(db_url)
        self.database = self.client[database_name]

    def dispose(self) -> None:
        """Dispose of the MongoDB client and cleanup resources."""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB version checker client disposed")

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
        """Get the current database schema version from the schema_versions collection."""
        try:
            # Try to access the database directly instead of checking list_database_names()
            # MongoDB only shows databases in list_database_names() if they have collections with data
            try:
                collection_names = self.database.list_collection_names()
            except Exception:
                # If we can't list collections, database doesn't exist
                return None

            # If database has no collections at all, it doesn't really exist
            if not collection_names:
                return None

            # Check if schema_versions collection exists
            if "schema_versions" not in collection_names:
                # Database exists with collections but no schema_versions collection
                # Return special marker to distinguish from non-existent database
                return "NO_VERSION_TRACKING"

            # Get the latest version entry
            schema_versions = self.database["schema_versions"]
            latest_version = schema_versions.find_one(
                {},
                sort=[("applied_at", -1)],  # Most recent first
            )

            return (
                latest_version["version"] if latest_version else "NO_VERSION_TRACKING"
            )

        except Exception:
            self.logger.error(
                f"Error getting database version: {traceback.format_exc()}"
            )
            return None

    def is_migration_needed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database migration is needed.

        Migration is only needed for major or minor version mismatches,
        not for patch versions or pre-release versions. Uses packaging.version.Version
        for semantic version comparison.

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)
        """
        current_madsci_version = self.get_current_madsci_version()
        db_version = self.get_database_version()

        if db_version is None:
            # Database doesn't exist at all - fresh install
            self.logger.info(
                f"Database {self.database_name} does not exist - migration needed for initial setup"
            )
            return True, current_madsci_version, None

        if db_version == "NO_VERSION_TRACKING":
            # Database exists but no version tracking - needs initialization
            self.logger.info(
                f"Database {self.database_name} exists but has no version tracking - migration needed for version tracking initialization"
            )
            return True, current_madsci_version, db_version

        # Parse semantic versions for comparison
        try:
            current_semver = Version(current_madsci_version)
            db_semver = Version(db_version)

            # Only trigger migration for major or minor version mismatches
            if (
                current_semver.major != db_semver.major
                or current_semver.minor != db_semver.minor
            ):
                self.logger.warning(
                    f"Major/minor version mismatch in {self.database_name}: "
                    f"MADSci v{current_madsci_version} (major.minor: {current_semver.major}.{current_semver.minor}), "
                    f"Database v{db_version} (major.minor: {db_semver.major}.{db_semver.minor})"
                )
                return True, current_madsci_version, db_version
            # Patch or pre-release differences don't require migration
            if current_madsci_version != db_version:
                self.logger.info(
                    f"Database {self.database_name} has compatible version: "
                    f"MADSci v{current_madsci_version}, Database v{db_version} "
                    f"(only patch/pre-release differences, no migration needed)"
                )
            else:
                self.logger.info(
                    f"Database {self.database_name} version {db_version} matches MADSci version {current_madsci_version}"
                )
            return False, current_madsci_version, db_version

        except Exception as e:
            # If version parsing fails, fall back to exact string comparison
            self.logger.warning(
                f"Failed to parse semantic versions (MADSci: {current_madsci_version}, DB: {db_version}): {e}. "
                f"Falling back to exact string comparison."
            )
            if db_version != current_madsci_version:
                self.logger.warning(
                    f"Version mismatch in {self.database_name}: "
                    f"MADSci v{current_madsci_version}, Database v{db_version}"
                )
                return True, current_madsci_version, db_version

        self.logger.info(
            f"Database {self.database_name} version {db_version} matches MADSci version {current_madsci_version}"
        )
        return False, current_madsci_version, db_version

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.
        """
        needs_migration, madsci_version, db_version = self.is_migration_needed()

        if needs_migration:
            # Check if this is a completely fresh database (no collections at all)
            if db_version is None:
                # Auto-initialize fresh databases instead of requiring manual migration
                try:
                    self.auto_initialize_fresh_database()
                    self.logger.info(
                        f"Database version validation passed for {self.database_name}"
                    )
                    return
                except Exception as e:
                    self.logger.error(f"Auto-initialization failed: {e}")
                    # Fall through to manual migration instructions

            # Detect if running in Docker
            is_docker = self._is_running_in_docker()

            if db_version is None or db_version == "NO_VERSION_TRACKING":
                if is_docker:
                    container_name = (
                        os.getenv("container_name") or self._get_container_name()  # noqa
                    )
                    message = (
                        f"Database {self.database_name} needs version tracking initialization. "
                        f"The database exists but has no schema version tracking set up. "
                        f"MADSci version is {madsci_version}. "
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                else:
                    message = (
                        f"Database {self.database_name} needs version tracking initialization. "
                        f"The database exists but has no schema version tracking set up. "
                        f"MADSci version is {madsci_version}. "
                        f"Please run the migration tool to initialize version tracking:\n"
                        f"python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                self.logger.warning("Database needs version tracking initialization")
            else:
                # Similar logic for version mismatches
                if is_docker:
                    container_name = (
                        os.getenv("container_name") or self._get_container_name()  # noqa
                    )
                    message = (
                        f"Database schema version mismatch detected for {self.database_name}!\n"
                        f"MADSci version: {madsci_version}\n"
                        f"Database version: {db_version}\n"
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                else:
                    message = (
                        f"Database schema version mismatch detected for {self.database_name}!\n"
                        f"MADSci version: {madsci_version}\n"
                        f"Database version: {db_version}\n"
                        f"Please run the migration tool to update the database schema:\n"
                        f"python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                self.logger.error("Database schema version mismatch detected")

            self.logger.error(message)
            raise RuntimeError(message)

        self.logger.info(f"Database version validation passed for {self.database_name}")

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
        """Get the container name based on database name."""
        if self.database_name == "madsci_events":
            return "event_manager"
        if self.database_name == "madsci_data":
            return "data_manager"
        if self.database_name == "madsci_experiments":
            return "experiment_manager"
        if self.database_name == "madsci_workcells":
            return "workcell_manager"
        return "container_name"

    def create_schema_versions_collection(self) -> None:
        """Create the schema_versions collection if it doesn't exist."""
        try:
            schema_versions = self.database["schema_versions"]

            # Create unique index on version field
            schema_versions.create_index(
                [("version", 1)], unique=True, background=True, name="version_unique"
            )

            # Create index on applied_at field
            schema_versions.create_index(
                [("applied_at", -1)], background=True, name="applied_at_desc"
            )

            self.logger.info(
                f"Schema versions collection created for {self.database_name}"
            )

        except Exception as e:
            self.logger.error(f"Error creating schema versions collection: {e}")
            raise

    def record_version(
        self, version: str, migration_notes: Optional[str] = None
    ) -> None:
        """Record a new version in the database."""
        try:
            schema_versions = self.database["schema_versions"]

            # Check if version already exists
            existing_version = schema_versions.find_one({"version": version})

            version_doc = {
                "version": version,
                "applied_at": datetime.now(timezone.utc),
                "migration_notes": migration_notes
                or f"Schema version {version} applied",
            }

            if existing_version:
                # Update existing record
                schema_versions.replace_one({"version": version}, version_doc)
                self.logger.info(f"Updated existing database version record: {version}")
            else:
                # Create new record
                schema_versions.insert_one(version_doc)
                self.logger.info(f"Recorded new database version: {version}")

        except Exception as e:
            self.logger.error(f"Error recording version: {e}")
            raise

    def database_exists(self) -> bool:
        """Check if the database exists."""
        return self.database_name in self.client.list_database_names()

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in the database."""
        if not self.database_exists():
            return False
        return collection_name in self.database.list_collection_names()

    def auto_initialize_fresh_database(self) -> None:
        """
        Auto-initialize a completely fresh database with version tracking.

        This method should only be called for databases that have no collections at all.
        It creates the schema_versions collection and records the current MADSci version.
        """
        try:
            current_version = self.get_current_madsci_version()

            self.logger.info(
                f"Auto-initializing fresh database {self.database_name} with MADSci version {current_version}"
            )

            # Create the schema_versions collection and record current version
            self.create_schema_versions_collection()
            self.record_version(
                current_version, f"Auto-initialized fresh database {self.database_name}"
            )

            self.logger.info(
                f"Successfully auto-initialized database {self.database_name} with version {current_version}"
            )

        except Exception as e:
            self.logger.error(f"Failed to auto-initialize fresh database: {e}")
            raise RuntimeError(
                f"Auto-initialization of fresh database failed: {e}"
            ) from e
