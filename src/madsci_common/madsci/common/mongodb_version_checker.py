"""MongoDB version checking and validation for MADSci."""

import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from madsci.client.event_client import EventClient
from pydantic_extra_types.semantic_version import SemanticVersion
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

    def __del__(self) -> None:
        """Cleanup MongoDB client resources."""
        if hasattr(self, "client") and self.client:
            self.client.close()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("MongoDB version checker client disposed")

    def get_expected_schema_version(self) -> SemanticVersion:
        """Get the expected schema version from the schema.json file."""
        try:
            if not self.schema_file_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {self.schema_file_path}"
                )

            with self.schema_file_path.open() as f:
                schema = json.load(f)

            schema_version = schema.get("schema_version")
            if not schema_version:
                raise ValueError(
                    f"Schema file {self.schema_file_path} does not contain a 'schema_version' field"
                )

            return SemanticVersion.parse(schema_version)
        except Exception as e:
            self.logger.error(
                f"Error reading schema version from {self.schema_file_path}: {e}"
            )
            raise RuntimeError(f"Cannot determine expected schema version: {e}") from e

    def get_database_version(self) -> Optional[SemanticVersion]:
        """Get the current database schema version from the schema_versions collection.

        Returns:
            SemanticVersion if a valid semantic version is found
            0.0.0 if no version tracking exists
            None if database/collection doesn't exist or an error occurs
        """
        try:
            # Try to access the database directly instead of checking list_database_names()
            # MongoDB only shows databases in list_database_names() if they have collections with data
            collection_names = self.database.list_collection_names()
            if not collection_names:
                # If database has no collections at all, it doesn't really exist
                raise Exception("No collections found")

            # Check if schema_versions collection exists
            if "schema_versions" not in collection_names:
                # Database exists with collections but no schema_versions collection
                return SemanticVersion(0, 0, 0)

            # Get the latest version entry
            return SemanticVersion.parse(
                self.database["schema_versions"].find_one(
                    {},
                    sort=[("applied_at", -1)],  # Most recent first
                )["version"]
            ) or SemanticVersion(0, 0, 0)

        except Exception:
            self.logger.error(
                f"Error getting database version: {traceback.format_exc()}"
            )
            return None

    def is_migration_needed(
        self,
    ) -> tuple[bool, SemanticVersion, Optional[Union[SemanticVersion, str]]]:
        """
        Check if database migration is needed.

        Migration is only needed for major or minor schema version mismatches,
        not for patch versions or pre-release versions. Uses SemanticVersion
        for semantic version comparison.

        Returns:
            tuple: (needs_migration, expected_schema_version, database_version)
        """
        expected_schema_version = self.get_expected_schema_version()
        db_version = self.get_database_version()

        if db_version is None:
            # Database doesn't exist at all - fresh install
            self.logger.info(
                f"Database {self.database_name} does not exist - migration needed for initial setup"
            )
            return True, expected_schema_version, None

        if db_version == SemanticVersion(0, 0, 0):
            # Database exists but no version tracking - needs initialization
            self.logger.info(
                f"Database {self.database_name} exists but has no version tracking - migration needed for version tracking initialization"
            )
            return True, expected_schema_version, db_version

        # Both versions are SemanticVersion objects - compare them
        try:
            # Schema versions must match exactly - any difference requires migration
            if expected_schema_version != db_version:
                self.logger.warning(
                    f"Schema version mismatch in {self.database_name}: "
                    f"Expected schema v{expected_schema_version}, "
                    f"Database v{db_version}"
                )
                return True, expected_schema_version, db_version

            self.logger.info(
                f"Database {self.database_name} schema version {db_version} matches expected version {expected_schema_version}"
            )
            return False, expected_schema_version, db_version

        except Exception as e:
            # If version comparison fails, require migration to be safe
            self.logger.warning(
                f"Failed to compare semantic versions (Expected: {expected_schema_version}, DB: {db_version}): {e}. "
                f"Migration will be required for safety."
            )
            return True, expected_schema_version, db_version

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.
        """
        needs_migration, expected_schema_version, db_version = (
            self.is_migration_needed()
        )

        if needs_migration:
            # Check if this is a completely fresh database (no collections at all)
            if db_version is None:
                # Auto-initialize fresh databases instead of requiring manual migration
                try:
                    self.auto_initialize_fresh_database(expected_schema_version)
                    self.logger.info(
                        f"Database version validation passed for {self.database_name}"
                    )
                    return
                except Exception as e:
                    self.logger.error(f"Auto-initialization failed: {e}")
                    # Fall through to manual migration instructions

            # Detect if running in Docker
            is_docker = self._is_running_in_docker()

            if db_version is None or db_version == SemanticVersion(0, 0, 0):
                if is_docker:
                    container_name = (
                        os.getenv("container_name") or self._get_container_name()  # noqa
                    )
                    message = (
                        f"Database {self.database_name} needs version tracking initialization. "
                        f"The database exists but has no schema version tracking set up. "
                        f"Expected schema version is {expected_schema_version}. "
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                else:
                    message = (
                        f"Database {self.database_name} needs version tracking initialization. "
                        f"The database exists but has no schema version tracking set up. "
                        f"Expected schema version is {expected_schema_version}. "
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
                        f"Expected schema version: {expected_schema_version}\n"
                        f"Database version: {db_version}\n"
                        f"Please run the migration tool in the container:\n"
                        f"docker-compose run --rm {container_name} python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                    )
                else:
                    message = (
                        f"Database schema version mismatch detected for {self.database_name}!\n"
                        f"Expected schema version: {expected_schema_version}\n"
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
        self,
        version: Union[SemanticVersion, str],
        migration_notes: Optional[str] = None,
    ) -> None:
        """Record a new version in the database."""
        try:
            schema_versions = self.database["schema_versions"]

            # Convert SemanticVersion to string for storage
            version_str = str(version)

            # Check if version already exists
            existing_version = schema_versions.find_one({"version": version_str})

            version_doc = {
                "version": version_str,
                "applied_at": datetime.now(timezone.utc),
                "migration_notes": migration_notes
                or f"Schema version {version_str} applied",
            }

            if existing_version:
                # Update existing record
                schema_versions.replace_one({"version": version_str}, version_doc)
                self.logger.info(
                    f"Updated existing database version record: {version_str}"
                )
            else:
                # Create new record
                schema_versions.insert_one(version_doc)
                self.logger.info(f"Recorded new database version: {version_str}")

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

    def auto_initialize_fresh_database(
        self, schema_version: Optional[SemanticVersion] = None
    ) -> None:
        """
        Auto-initialize a completely fresh database with version tracking.

        This method should only be called for databases that have no collections at all.
        It creates the schema_versions collection and records the expected schema version.
        """
        try:
            if schema_version is None:
                schema_version = self.get_expected_schema_version()

            self.logger.info(
                f"Auto-initializing fresh database {self.database_name} with schema version {schema_version}"
            )

            # Create the schema_versions collection and record current version
            self.create_schema_versions_collection()
            self.record_version(
                schema_version, f"Auto-initialized fresh database {self.database_name}"
            )

            self.logger.info(
                f"Successfully auto-initialized database {self.database_name} with version {schema_version}"
            )

        except Exception as e:
            self.logger.error(f"Failed to auto-initialize fresh database: {e}")
            raise RuntimeError(
                f"Auto-initialization of fresh database failed: {e}"
            ) from e
