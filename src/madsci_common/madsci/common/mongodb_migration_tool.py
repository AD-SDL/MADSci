"""MongoDB migration tool for MADSci databases with backup, schema management, and CLI."""

import argparse
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.client.event_client import EventClient
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from madsci.common.types.mongodb_migration_types import MongoDBMigrationSettings
from pydantic import AnyUrl
from pymongo import MongoClient


class MongoDBMigrator:
    """Handles MongoDB schema migrations for MADSci with backup and restore capabilities."""

    def __init__(
        self,
        settings: MongoDBMigrationSettings,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the MongoDB migrator.

        Args:
            settings: Migration configuration settings
            logger: Optional logger instance
        """
        self.settings = settings
        self.db_url = str(settings.mongo_db_url)
        self.database_name = settings.database
        self.schema_file_path = settings.get_effective_schema_file_path()
        self.logger = logger or EventClient()

        # Initialize MongoDB connection
        self.client = MongoClient(self.db_url)
        self.database = self.client[self.database_name]

        # Use configured backup directory (with ~ expansion)
        raw_backup = Path(self.settings.backup_dir)
        self.backup_dir = (
            raw_backup if raw_backup.is_absolute() else Path.cwd() / raw_backup
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using backup directory: {self.backup_dir}")
        # Initialize version checker
        self.version_checker = MongoDBVersionChecker(
            db_url=self.db_url,
            database_name=self.database_name,
            schema_file_path=str(self.schema_file_path),
            backup_dir=str(self.backup_dir),
            logger=self.logger,
        )

    @property
    def parsed_db_url(self) -> AnyUrl:
        """Parse MongoDB connection URL using pydantic AnyUrl."""
        return self.settings.mongo_db_url

    def __del__(self) -> None:
        """Cleanup MongoDB client and version checker resources."""
        if hasattr(self, "version_checker") and self.version_checker:
            # Version checker now has its own __del__ method
            pass
        if hasattr(self, "client") and self.client:
            self.client.close()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("MongoDB migrator client disposed")

    def load_expected_schema(self) -> Dict[str, Any]:
        """Load the expected schema from the schema.json file."""
        try:
            if not self.schema_file_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {self.schema_file_path}"
                )

            with open(self.schema_file_path) as f:  # noqa
                schema = json.load(f)

            self.logger.info(f"Loaded schema from {self.schema_file_path}")
            return schema

        except Exception as e:
            self.logger.error(f"Error loading schema file: {e}")
            raise RuntimeError(f"Cannot load schema file: {e}") from e

    def create_backup(self) -> Path:
        """Create a backup of the current database using mongodump."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.database_name}_backup_{timestamp}"
        backup_path = self.backup_dir / backup_filename

        # Build mongodump command
        mongodump_cmd = ["mongodump"]

        # Add connection parameters
        if self.parsed_db_url.host:
            port = self.parsed_db_url.port or 27017
            mongodump_cmd.extend(["--host", f"{self.parsed_db_url.host}:{port}"])

        if self.parsed_db_url.username:
            mongodump_cmd.extend(["--username", self.parsed_db_url.username])

        if self.parsed_db_url.password:
            mongodump_cmd.extend(["--password", self.parsed_db_url.password])

        # Specify database and output directory
        mongodump_cmd.extend(["--db", self.database_name, "--out", str(backup_path)])

        try:
            self.logger.info(f"Creating database backup: {backup_path}")
            result = subprocess.run(  # noqa
                mongodump_cmd, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database backup completed successfully: {backup_path}"
                )
                return backup_path
            raise RuntimeError(f"mongodump failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e.stderr}")
            raise RuntimeError(f"Database backup failed: {e}") from e
        except FileNotFoundError as fe:
            raise RuntimeError(
                f"mongodump command not found. Please ensure MongoDB tools are installed. {fe}"
            ) from fe

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore database from a backup directory using mongorestore."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")

        # The backup path should contain a subdirectory with the database name
        db_backup_path = backup_path / self.database_name
        if not db_backup_path.exists():
            raise FileNotFoundError(f"Database backup not found in: {db_backup_path}")

        # Build mongorestore command
        mongorestore_cmd = ["mongorestore"]

        # Add connection parameters
        if self.parsed_db_url.host:
            port = self.parsed_db_url.port or 27017
            mongorestore_cmd.extend(["--host", f"{self.parsed_db_url.host}:{port}"])

        if self.parsed_db_url.username:
            mongorestore_cmd.extend(["--username", self.parsed_db_url.username])

        if self.parsed_db_url.password:
            mongorestore_cmd.extend(["--password", self.parsed_db_url.password])

        # Drop existing database and restore
        mongorestore_cmd.extend(
            [
                "--drop",  # Drop existing collections before restoring
                "--db",
                self.database_name,
                str(db_backup_path),
            ]
        )

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")
            result = subprocess.run(  # noqa
                mongorestore_cmd, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
            else:
                raise RuntimeError(f"mongorestore failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            raise RuntimeError(f"Database restore failed: {e}") from e

    def get_current_database_schema(self) -> Dict[str, Any]:
        """Get the current database schema (collections and indexes)."""
        current_schema = {"database": self.database_name, "collections": {}}

        try:
            # Get all collections except system collections
            collection_names = [
                name
                for name in self.database.list_collection_names()
                if not name.startswith("system.")
            ]

            for collection_name in collection_names:
                collection = self.database[collection_name]
                indexes = list(collection.list_indexes())

                # Filter out the default _id index for comparison
                filtered_indexes = []
                for index in indexes:
                    if index["name"] != "_id_":
                        filtered_indexes.append(
                            {
                                "keys": list(index["key"].items()),
                                "name": index["name"],
                                "unique": index.get("unique", False),
                                "background": index.get("background", False),
                            }
                        )

                current_schema["collections"][collection_name] = {
                    "indexes": filtered_indexes
                }

            return current_schema

        except Exception as e:
            self.logger.error(f"Error getting current database schema: {e}")
            raise

    def apply_schema_migrations(self) -> None:
        """Apply schema migrations based on the expected schema."""
        try:
            expected_schema = self.load_expected_schema()

            self.logger.info("Applying schema migrations...")

            # Create collections and indexes
            for collection_name, collection_config in expected_schema[
                "collections"
            ].items():
                self._ensure_collection_exists(collection_name)
                self._ensure_indexes_exist(
                    collection_name, collection_config.get("indexes", [])
                )

            # Create/update schema versions collection
            self.version_checker.create_schema_versions_collection()

            self.logger.info("Schema migrations applied successfully")

        except Exception as e:
            self.logger.error(f"Schema migration failed: {traceback.format_exc()}")
            raise RuntimeError(f"Schema migration failed: {e}") from e

    def _ensure_collection_exists(self, collection_name: str) -> None:
        """Ensure a collection exists, create it if it doesn't."""
        try:
            if collection_name not in self.database.list_collection_names():
                self.database.create_collection(collection_name)
                self.logger.info(f"Created collection: {collection_name}")
            else:
                self.logger.info(f"Collection already exists: {collection_name}")
        except Exception as e:
            self.logger.error(f"Error creating collection {collection_name}: {e}")
            raise

    def _ensure_indexes_exist(
        self, collection_name: str, expected_indexes: List[Dict[str, Any]]
    ) -> None:
        """Ensure all expected indexes exist on a collection."""
        try:
            collection = self.database[collection_name]
            existing_indexes = {idx["name"] for idx in collection.list_indexes()}

            for index_config in expected_indexes:
                index_name = index_config["name"]

                if index_name not in existing_indexes:
                    # Convert keys format from [["field", direction]] to [("field", direction)]
                    keys = [
                        (field, direction) for field, direction in index_config["keys"]
                    ]

                    index_options = {
                        "name": index_name,
                        "background": index_config.get("background", True),
                    }

                    if index_config.get("unique", False):
                        index_options["unique"] = True

                    collection.create_index(keys, **index_options)
                    self.logger.info(
                        f"Created index: {index_name} on collection {collection_name}"
                    )
                else:
                    self.logger.info(
                        f"Index already exists: {index_name} on collection {collection_name}"
                    )

        except Exception as e:
            self.logger.error(
                f"Error ensuring indexes for collection {collection_name}: {e}"
            )
            raise

    def run_migration(self, target_version: Optional[str] = None) -> None:
        """Run the complete migration process."""
        try:
            # Use expected schema version as target if not specified
            if target_version is None:
                target_version = str(self.version_checker.get_expected_schema_version())

            expected_schema_version = self.version_checker.get_expected_schema_version()
            current_db_version = self.version_checker.get_database_version()

            self.logger.info(
                f"Starting migration of {self.database_name} to version {target_version}"
            )
            self.logger.info(f"Expected schema version: {expected_schema_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # ALWAYS CREATE BACKUP FIRST
            backup_path = self.create_backup()

            try:
                # ALWAYS apply schema migrations - this will create collections and indexes as needed
                self.apply_schema_migrations()

                # Record new version in our tracking system
                migration_notes = f"MongoDB schema migration from {current_db_version or 'unversioned'} to {target_version}"
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


def handle_migration_commands(
    settings: MongoDBMigrationSettings,
    version_checker: MongoDBVersionChecker,
    migrator: MongoDBMigrator,
    logger: EventClient,
) -> None:
    """Handle different migration command options."""
    if settings.check_version:
        # Just check version compatibility
        needs_migration, expected_schema_version, db_version = (
            version_checker.is_migration_needed()
        )

        logger.log_warning(f"Expected schema version: {expected_schema_version}")
        logger.log_warning(f"Database version: {db_version or 'None'}")
        logger.log_warning(f"Migration needed: {needs_migration}")

        if needs_migration:
            sys.exit(1)  # Exit with error code if migration needed

    elif settings.restore_from:
        # Restore from backup
        backup_path = Path(settings.restore_from)
        migrator.restore_from_backup(backup_path)
        logger.info("Restore completed successfully")

    elif settings.backup_only:
        # Just create backup
        backup_path = migrator.create_backup()
        logger.info(f"Backup created: {backup_path}")

    else:
        # Run full migration
        migrator.run_migration(settings.target_version)
        logger.info("Migration completed successfully")


def main() -> None:
    """Command line interface for the MongoDB migration tool."""
    logger = EventClient()

    try:
        # Parse command-line arguments
        parser = argparse.ArgumentParser(
            description="MADSci MongoDB migration tool for Event and Data Managers"
        )
        parser.add_argument(
            "--db-url",
            type=str,
            help="MongoDB connection URL (e.g., mongodb://localhost:27017)",
        )
        parser.add_argument(
            "--database",
            type=str,
            required=True,
            help="Database name to migrate (e.g., madsci_events, madsci_data)",
        )
        parser.add_argument(
            "--schema-file",
            type=str,
            required=True,
            help="Path to schema.json file (auto-detects if not provided)",
        )
        parser.add_argument(
            "--backup-dir",
            type=str,
            help="Directory for database backups (default: ~/.madsci/mongodb/backups)",
        )
        parser.add_argument(
            "--target-version",
            type=str,
            help="Target version to migrate to (defaults to version in schema.json)",
        )
        parser.add_argument(
            "--backup-only",
            action="store_true",
            help="Only create a backup, do not run migration",
        )
        parser.add_argument(
            "--restore-from",
            type=str,
            help="Restore from specified backup directory instead of migrating",
        )
        parser.add_argument(
            "--check-version",
            action="store_true",
            help="Only check version compatibility, do not migrate",
        )

        args = parser.parse_args()

        # Create settings with CLI arguments (override only when provided)
        kwargs = dict(  # noqa
            mongo_db_url=args.db_url,
            database=args.database,
            schema_file=args.schema_file,
            target_version=args.target_version,
            backup_only=args.backup_only,
            restore_from=args.restore_from,
            check_version=args.check_version,
        )
        if args.backup_dir is not None and str(args.backup_dir).strip():
            kwargs["backup_dir"] = (
                args.backup_dir
            )  # only override default if user passed it

        settings = MongoDBMigrationSettings(**kwargs)

        logger.info(f"Using database: {settings.database}")
        logger.info(f"Using schema file: {settings.get_effective_schema_file_path()}")

        # Create migrator with settings
        migrator = MongoDBMigrator(settings, logger)

        # Handle migration commands
        handle_migration_commands(settings, migrator.version_checker, migrator, logger)

    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
