"""MongoDB version checking and validation for MADSci."""

import importlib.metadata
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from madsci.client.event_client import EventClient
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
            schema_file_path: Path to the schema.json file
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

    def get_expected_schema_version(self) -> str:
        """Get the expected schema version from the schema.json file."""
        try:
            if not self.schema_file_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {self.schema_file_path}"
                )

            with open(self.schema_file_path) as f:
                schema = json.load(f)

            return schema.get("version", "1.0.0")
        except Exception as e:
            self.logger.error(f"Error reading schema file: {e}")
            raise RuntimeError(f"Cannot read schema file: {e}") from e

    def get_database_version(self) -> Optional[str]:
        """Get the current database schema version from the schema_versions collection."""
        try:
            # Try to access the database directly instead of checking list_database_names()
            # MongoDB only shows databases in list_database_names() if they have collections with data
            collection_names = self.database.list_collection_names()
            # If database has no collections at all, it doesn't really exist
            if not collection_names:
                return None
            
            # Check if schema_versions collection exists
            if "schema_versions" not in collection_names:
                return "NO_VERSION_TRACKING"

            # Get the latest version entry
            schema_versions = self.database["schema_versions"]
            latest_version = schema_versions.find_one(
                {},
                sort=[("applied_at", -1)]  # Most recent first
            )
            
            return latest_version["version"] if latest_version else "NO_VERSION_TRACKING"

        except Exception:
            self.logger.error(f"Error getting database version: {traceback.format_exc()}")
            return None

    def is_migration_needed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database migration is needed.

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)
        """
        current_version = self.get_current_madsci_version()
        db_version = self.get_database_version()
        expected_schema_version = self.get_expected_schema_version()

        if db_version is None:
            # No version tracking exists, this is either a fresh install or pre-migration
            self.logger.info(
                f"No database version found for {self.database_name} - migration needed for version tracking"
            )
            return True, current_version, None

        if db_version != expected_schema_version:
            self.logger.warning(
                f"Version mismatch in {self.database_name}: "
                f"Expected schema v{expected_schema_version}, Database v{db_version}"
            )
            return True, current_version, db_version

        self.logger.info(
            f"Database {self.database_name} version {db_version} matches expected schema version {expected_schema_version}"
        )
        return False, current_version, db_version

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.
        """
        needs_migration, madsci_version, db_version = self.is_migration_needed()
        expected_schema_version = self.get_expected_schema_version()

        if needs_migration:
            if db_version is None:
                # Database exists but no version tracking - this is initialization, not a mismatch
                message = (
                    f"Database {self.database_name} needs version tracking initialization. "
                    f"The database exists but has no schema version tracking set up. "
                    f"MADSci version is {madsci_version}, expected schema version is {expected_schema_version}. "
                    f"Please run the migration tool to initialize version tracking:\n"
                    f"python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                )
                self.logger.warning("Database needs version tracking initialization")
            else:
                # Actual version mismatch between what's expected and what's in database
                message = (
                    f"Database schema version mismatch detected for {self.database_name}!\n"
                    f"MADSci version: {madsci_version}\n"
                    f"Expected schema version: {expected_schema_version}\n"
                    f"Database version: {db_version}\n"
                    f"Please run the migration tool to update the database schema:\n"
                    f"python -m madsci.common.mongodb_migration_tool --db-url '{self.db_url}' --database '{self.database_name}' --schema-file '{self.schema_file_path}'"
                )
                self.logger.error("Database schema version mismatch detected")

            self.logger.error(message)
            raise RuntimeError(message)

        self.logger.info(f"Database version validation passed for {self.database_name}")

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
                "applied_at": datetime.utcnow(),
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
