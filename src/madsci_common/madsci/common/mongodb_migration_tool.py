"""MongoDB migration tool for MADSci databases with backup, schema management, and CLI."""

import argparse
import json
import os
import subprocess
import sys
import traceback
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.client.event_client import EventClient
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from pymongo import MongoClient


class MongoDBMigrator:
    """Handles MongoDB schema migrations for MADSci with backup and restore capabilities."""

    def __init__(
        self,
        db_url: str,
        database_name: str,
        schema_file_path: str,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the MongoDB migrator.

        Args:
            db_url: MongoDB connection URL
            database_name: Name of the database to migrate
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

        # Initialize version checker
        self.version_checker = MongoDBVersionChecker(
            db_url, database_name, schema_file_path, logger
        )

        # Parse database connection details for backup
        self.backup_dir = self._get_backup_directory()

    def dispose(self) -> None:
        """Dispose of MongoDB client and cleanup resources."""
        if self.version_checker:
            self.version_checker.dispose()
        if self.client:
            self.client.close()
            self.logger.info("MongoDB migrator client disposed")

    def _get_backup_directory(self) -> Path:
        """Get the backup directory path that works consistently in both local and Docker environments."""
        # Check if we're running in a Docker container
        if Path("/.dockerenv").exists() or self._is_running_in_docker():
            # In Docker, use the mounted .madsci directory
            backup_dir = Path("/home/madsci/.madsci/mongodb/backups")
        else:
            # Local development - use current directory structure
            current_dir = Path.cwd()
            backup_dir = current_dir / ".madsci" / "mongodb" / "backups"

        backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using backup directory: {backup_dir}")
        return backup_dir

    def _is_running_in_docker(self) -> bool:
        """Detect if running inside a Docker container."""
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

    def _parse_db_url(self) -> Dict[str, Any]:
        """Parse MongoDB connection details from database URL."""
        parsed = urlparse.urlparse(self.db_url)

        # Handle both mongodb:// and mongodb+srv:// schemes
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 27017,
            "username": parsed.username,
            "password": parsed.password,
            "scheme": parsed.scheme,
            "options": parsed.query,
        }

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

        db_info = self._parse_db_url()

        # Build mongodump command
        mongodump_cmd = ["mongodump"]

        # Add connection parameters
        if db_info["host"]:
            mongodump_cmd.extend(["--host", f"{db_info['host']}:{db_info['port']}"])

        if db_info["username"]:
            mongodump_cmd.extend(["--username", db_info["username"]])

        if db_info["password"]:
            mongodump_cmd.extend(["--password", db_info["password"]])

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

        db_info = self._parse_db_url()

        # Build mongorestore command
        mongorestore_cmd = ["mongorestore"]

        # Add connection parameters
        if db_info["host"]:
            mongorestore_cmd.extend(["--host", f"{db_info['host']}:{db_info['port']}"])

        if db_info["username"]:
            mongorestore_cmd.extend(["--username", db_info["username"]])

        if db_info["password"]:
            mongorestore_cmd.extend(["--password", db_info["password"]])

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
            # Use MADSci version as target if not specified
            if target_version is None:
                target_version = self.version_checker.get_current_madsci_version()

            current_madsci_version = self.version_checker.get_current_madsci_version()
            current_db_version = self.version_checker.get_database_version()

            self.logger.info(
                f"Starting migration of {self.database_name} to version {target_version}"
            )
            self.logger.info(f"Current MADSci version: {current_madsci_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # ALWAYS CREATE BACKUP FIRST
            backup_path = self.create_backup()

            try:
                # ALWAYS apply schema migrations - this will create collections and indexes as needed
                self.apply_schema_migrations()

                # Record new version in our tracking system
                migration_notes = f"MongoDB migration from {current_db_version or 'unversioned'} to {target_version}"
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


# CLI Functions
def get_database_url_from_env() -> str:
    """Get database URL from environment variables as fallback."""
    # Try common environment variable names
    for env_var in ["MONGODB_URL", "MONGO_URL", "DATABASE_URL"]:
        db_url = os.getenv(env_var)
        if db_url:
            return db_url

    # If no URL found, raise an error with helpful message
    raise RuntimeError(
        "No database URL provided and none found in environment variables. "
        "Please either:\n"
        "1. Provide --db-url argument, or\n"
        "2. Set MONGODB_URL, MONGO_URL, or DATABASE_URL in your environment/.env file\n"
        "Example: MONGODB_URL=mongodb://localhost:27017"
    )


def resolve_schema_file_path(
    database_name: str, schema_file: Optional[str] = None
) -> Path:
    """Resolve the schema file path based on database name or explicit path."""
    if schema_file:
        schema_path = Path(schema_file)
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        return schema_path

    # Auto-detect schema file based on database name
    current_dir = Path.cwd()

    # Common schema file locations based on database name
    possible_paths = []

    if database_name == "madsci_events":
        possible_paths = [
            current_dir / "madsci" / "event_manager" / "schema.json",
            current_dir / "event_manager" / "schema.json",
            current_dir / "schema" / "event_manager.json",
        ]
    elif database_name == "madsci_data":
        possible_paths = [
            current_dir / "madsci" / "data_manager" / "schema.json",
            current_dir / "data_manager" / "schema.json",
            current_dir / "schema" / "data_manager.json",
        ]
    else:
        # Generic paths for custom database names
        possible_paths = [
            current_dir / "madsci" / database_name / "schema.json",
            current_dir / database_name / "schema.json",
            current_dir / "schema" / f"{database_name}.json",
        ]

    # Find the first existing schema file
    for path in possible_paths:
        if path.exists():
            return path

    # If no schema file found, provide helpful error
    paths_str = "\n".join(f"  - {path}" for path in possible_paths)
    raise FileNotFoundError(
        f"No schema file found for database '{database_name}'. "
        f"Searched in:\n{paths_str}\n\n"
        f"Please either:\n"
        f"1. Create a schema.json file in one of the above locations, or\n"
        f"2. Specify the path explicitly with --schema-file"
    )


def setup_migration_components(
    db_url: str, database: str, schema_file_path: Path, logger: EventClient
) -> tuple[MongoDBVersionChecker, MongoDBMigrator]:
    """Setup version checker and migrator components."""
    version_checker = MongoDBVersionChecker(
        db_url=db_url,
        database_name=database,
        schema_file_path=str(schema_file_path),
        logger=logger,
    )

    migrator = MongoDBMigrator(
        db_url=db_url,
        database_name=database,
        schema_file_path=str(schema_file_path),
        logger=logger,
    )

    return version_checker, migrator


def handle_migration_commands(
    args: Any,
    version_checker: MongoDBVersionChecker,
    migrator: MongoDBMigrator,
    logger: EventClient,
) -> None:
    """Handle different migration command options."""
    if args.check_version:
        # Just check version compatibility
        needs_migration, madsci_version, db_version = (
            version_checker.is_migration_needed()
        )

        logger.log_warning(f"MADSci version: {madsci_version}")
        logger.log_warning(f"Database version: {db_version or 'None'}")
        logger.log_warning(f"Migration needed: {needs_migration}")

        if needs_migration:
            sys.exit(1)  # Exit with error code if migration needed

    elif args.restore_from:
        # Restore from backup
        backup_path = Path(args.restore_from)
        migrator.restore_from_backup(backup_path)
        logger.info("Restore completed successfully")

    elif args.backup_only:
        # Just create backup
        backup_path = migrator.create_backup()
        logger.info(f"Backup created: {backup_path}")

    else:
        # Run full migration
        migrator.run_migration(args.target_version)
        logger.info("Migration completed successfully")


def main() -> None:
    """Command line interface for the MongoDB migration tool."""
    parser = argparse.ArgumentParser(
        description="MADSci MongoDB Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate event manager database (auto-detects schema file)
  python -m madsci.common.mongodb_migration_tool --database madsci_events

  # Migrate data manager database with explicit DB URL
  python -m madsci.common.mongodb_migration_tool --db-url mongodb://localhost:27017 --database madsci_data

  # Use custom schema file
  python -m madsci.common.mongodb_migration_tool --database madsci_events --schema-file /path/to/schema.json

  # Just create backup without migrating
  python -m madsci.common.mongodb_migration_tool --database madsci_events --backup-only

  # Restore from backup
  python -m madsci.common.mongodb_migration_tool --database madsci_events --restore-from /path/to/backup
        """,
    )

    parser.add_argument(
        "--db-url",
        help="MongoDB connection URL (e.g., mongodb://localhost:27017). If not provided, will try to read from MONGODB_URL, MONGO_URL, or DATABASE_URL environment variables.",
    )
    parser.add_argument(
        "--database",
        required=True,
        help="Database name to migrate (e.g., madsci_events, madsci_data)",
    )
    parser.add_argument(
        "--schema-file",
        help="Path to schema.json file. If not provided, will auto-detect based on database name.",
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
        "--restore-from",
        help="Restore from specified backup directory instead of migrating",
    )
    parser.add_argument(
        "--check-version",
        action="store_true",
        help="Only check version compatibility, do not migrate",
    )

    args = parser.parse_args()
    logger = EventClient()

    try:
        # Get database URL
        db_url = args.db_url or get_database_url_from_env()

        # Resolve schema file path
        schema_file_path = resolve_schema_file_path(args.database, args.schema_file)

        logger.info(f"Using database: {args.database}")
        logger.info(f"Using schema file: {schema_file_path}")

        # Setup components
        version_checker, migrator = setup_migration_components(
            db_url, args.database, schema_file_path, logger
        )

        try:
            handle_migration_commands(args, version_checker, migrator, logger)
        finally:
            # Always cleanup resources
            version_checker.dispose()
            migrator.dispose()

    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
