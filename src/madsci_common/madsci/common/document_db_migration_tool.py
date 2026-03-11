"""MongoDB-compatible document database migration tool for MADSci databases with backup, schema management, and CLI."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.client.event_client import EventClient
from madsci.common.backup_tools.document_db_backup import (
    DocumentDBBackupSettings,
    DocumentDBBackupTool,
)
from madsci.common.document_db_version_checker import DocumentDBVersionChecker
from madsci.common.types.document_db_migration_types import (
    DocumentDBMigrationSettings,
    IndexDefinition,
    MongoDBSchema,
)
from pydantic import AnyUrl
from pymongo import MongoClient


class DocumentDBMigrator:
    """Handles MongoDB-compatible document database schema migrations for MADSci with backup and restore capabilities."""

    def __init__(
        self,
        settings: DocumentDBMigrationSettings,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the MongoDB-compatible document database migrator.

        Args:
            settings: Migration configuration settings
            logger: Optional logger instance
        """
        self.settings = settings
        self.db_url = str(settings.document_db_url)
        database_name = settings.database
        if not database_name:
            raise ValueError("DocumentDBMigrator requires settings.database to be set")

        database_name_str = str(database_name)
        self.database_name = database_name_str
        self.schema_file_path = settings.get_effective_schema_file_path()
        self.logger = logger or EventClient()

        # Initialize MongoDB-compatible document database connection
        self.client = MongoClient(self.db_url)
        self.database = self.client[self.database_name]

        # Use configured backup directory (with ~ expansion)
        raw_backup = Path(self.settings.backup_dir)
        self.backup_dir = (
            raw_backup if raw_backup.is_absolute() else Path.cwd() / raw_backup
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("Using backup directory", backup_dir=str(self.backup_dir))

        # Create backup tool instance with migration-appropriate settings
        backup_settings = DocumentDBBackupSettings(
            document_db_url=settings.document_db_url,
            database=self.database_name,
            backup_dir=self.backup_dir,
            max_backups=10,  # Migration-specific default
            validate_integrity=True,  # Always validate for migrations
            collections=getattr(
                settings, "collections", None
            ),  # Support collection-specific settings
        )
        self.backup_tool = DocumentDBBackupTool(backup_settings, logger=self.logger)

        # Initialize version checker
        self.version_checker = DocumentDBVersionChecker(
            db_url=self.db_url,
            database_name=self.database_name,
            schema_file_path=str(self.schema_file_path),
            backup_dir=str(self.backup_dir),
            logger=self.logger,
        )

    @property
    def parsed_db_url(self) -> AnyUrl:
        """Parse MongoDB-compatible document database connection URL using pydantic AnyUrl."""
        return self.settings.document_db_url

    def __del__(self) -> None:
        """Cleanup MongoDB-compatible document database client and version checker resources."""
        if hasattr(self, "version_checker") and self.version_checker:
            # Version checker now has its own __del__ method
            pass
        if hasattr(self, "client") and self.client:
            self.client.close()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("Document database migrator client disposed")

    def load_expected_schema(self) -> MongoDBSchema:
        """Load the expected schema from the schema.json file."""
        try:
            if not self.schema_file_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {self.schema_file_path}"
                )

            schema = MongoDBSchema.from_file(str(self.schema_file_path))
            self.logger.info(
                "Loaded schema", schema_file_path=str(self.schema_file_path)
            )
            return schema

        except Exception as e:
            self.logger.error(
                "Error loading schema file",
                schema_file_path=str(self.schema_file_path),
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Cannot load schema file: {e}") from e

    def get_current_database_schema(self) -> MongoDBSchema:
        """Get the current database schema using Pydantic models."""
        try:
            current_version = self.version_checker.get_database_version()
            version_str = str(current_version) if current_version else "0.0.0"

            return MongoDBSchema.from_mongodb_database(
                database_name=self.database_name,
                mongo_client=self.client,
                schema_version=version_str,
            )

        except Exception as e:
            self.logger.error(
                "Error getting current database schema",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def apply_schema_migrations(self) -> None:
        """Apply schema migrations based on the expected schema."""
        try:
            expected_schema = self.load_expected_schema()

            self.logger.info("Applying schema migrations...")

            for collection_name, collection_def in expected_schema.collections.items():
                self._ensure_collection_exists(collection_name)
                self._ensure_indexes_exist(collection_name, collection_def.indexes)

            self.version_checker.create_schema_versions_collection()

            self.logger.info("Schema migrations applied successfully")

        except Exception as e:
            self.logger.error(
                "Schema migration failed",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Schema migration failed: {e}") from e

    def _ensure_collection_exists(self, collection_name: str) -> None:
        """Ensure a collection exists, create it if it doesn't."""
        try:
            if collection_name not in self.database.list_collection_names():
                self.database.create_collection(collection_name)
                self.logger.info("Created collection", collection_name=collection_name)
            else:
                self.logger.info(
                    "Collection already exists",
                    collection_name=collection_name,
                )
        except Exception as e:
            self.logger.error(
                "Error creating collection",
                collection_name=collection_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def _ensure_indexes_exist(
        self, collection_name: str, expected_indexes: List[Any]
    ) -> None:
        """Ensure all expected indexes exist on a collection."""
        try:
            collection = self.database[collection_name]
            existing_indexes = {idx["name"] for idx in collection.list_indexes()}

            for index_def in expected_indexes:
                # Handle both dict and IndexDefinition objects
                if isinstance(index_def, dict):
                    # Convert dict to IndexDefinition for consistent handling
                    index_definition = IndexDefinition(**index_def)
                else:
                    index_definition = index_def

                index_name = index_definition.name

                if index_name not in existing_indexes:
                    keys = index_definition.get_keys_as_tuples()
                    index_options = index_definition.to_mongo_format()

                    collection.create_index(keys, **index_options)
                    self.logger.info(
                        "Created index",
                        index_name=index_name,
                        collection_name=collection_name,
                    )
                else:
                    self.logger.info(
                        "Index already exists",
                        index_name=index_name,
                        collection_name=collection_name,
                    )

        except Exception as e:
            self.logger.error(
                "Error ensuring indexes for collection",
                collection_name=collection_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate current database schema against expected schema.

        Returns:
            Dictionary with validation results and differences
        """
        try:
            expected_schema = self.load_expected_schema()
            current_schema = self.get_current_database_schema()

            differences = expected_schema.compare_with_database_schema(current_schema)

            has_differences = (
                bool(differences["missing_collections"])
                or bool(differences["extra_collections"])
                or bool(differences["collection_differences"])
            )

            return {
                "valid": not has_differences,
                "differences": differences,
                "expected_version": str(expected_schema.schema_version),
                "current_version": str(current_schema.schema_version),
            }

        except Exception as e:
            self.logger.error(
                "Schema validation failed",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
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
                "Starting migration",
                database_name=self.database_name,
                target_version=str(target_version),
            )
            self.logger.info(
                "Expected schema version",
                expected_schema_version=str(expected_schema_version),
            )
            self.logger.info(
                "Current database version",
                database_version=str(current_db_version)
                if current_db_version
                else None,
            )

            # ALWAYS CREATE BACKUP FIRST using backup tool
            backup_path = self.backup_tool.create_backup("pre_migration")

            try:
                # ALWAYS apply schema migrations - this will create collections and indexes as needed
                self.apply_schema_migrations()

                # Record new version in our tracking system
                migration_notes = (
                    "Document database schema migration from "
                    f"{current_db_version or 'unversioned'} to {target_version}"
                )
                self.version_checker.record_version(target_version, migration_notes)

                self.logger.info(
                    "Migration completed successfully",
                    database_name=self.database_name,
                    target_version=str(target_version),
                )

            except Exception as migration_error:
                self.logger.error(
                    "Migration failed",
                    database_name=self.database_name,
                    error=str(migration_error),
                    exc_info=True,
                )
                self.logger.info("Attempting to restore from backup...")

                try:
                    self.backup_tool.restore_from_backup(backup_path)
                    self.logger.info("Database restored from backup successfully")
                except Exception as restore_error:
                    self.logger.error(
                        "Backup restore also failed",
                        database_name=self.database_name,
                        error=str(restore_error),
                        exc_info=True,
                    )
                    self.logger.error("Manual intervention required!")

                raise migration_error

        except Exception as e:
            self.logger.error(
                "Migration process failed",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
            raise


def handle_migration_commands(
    settings: DocumentDBMigrationSettings,
    version_checker: DocumentDBVersionChecker,
    migrator: DocumentDBMigrator,
    logger: EventClient,
) -> None:
    """Handle different migration command options."""
    if settings.check_version:
        # Just check version compatibility
        needs_migration, expected_schema_version, db_version = (
            version_checker.is_migration_needed()
        )

        logger.info(
            "Expected schema version",
            expected_schema_version=str(expected_schema_version),
        )
        logger.info(
            "Database version",
            database_version=str(db_version) if db_version else None,
        )
        logger.info("Migration needed", needs_migration=needs_migration)

        if needs_migration:
            logger.info("Migration is required")
            sys.exit(1)  # Exit with error code if migration needed
        else:
            logger.info("No migration required")

    elif settings.restore_from:
        # Restore from backup using backup tool
        backup_path = Path(settings.restore_from)
        migrator.backup_tool.restore_from_backup(backup_path)
        logger.info("Restore completed successfully")

    elif settings.backup_only:
        # Just create backup using backup tool
        backup_path = migrator.backup_tool.create_backup()
        logger.info("Backup created", backup_path=str(backup_path))

    else:
        # Run full migration
        migrator.run_migration(settings.target_version)
        logger.info("Migration completed successfully")


def main() -> None:  # noqa
    """Command line interface for the MongoDB-compatible document database migration tool."""
    logger = EventClient()

    try:
        settings = DocumentDBMigrationSettings()

        logger.info("Using database", database=settings.database)
        logger.info(
            "Using schema file",
            schema_file_path=str(settings.get_effective_schema_file_path()),
        )

        migrator = DocumentDBMigrator(settings, logger)

        if getattr(settings, "validate_schema", False):
            validation_result = migrator.validate_schema()

            if validation_result["valid"]:
                logger.info(
                    "Schema validation passed - database matches expected schema"
                )
            else:
                logger.log_warning("Schema validation failed - differences detected:")
                diff = validation_result["differences"]

                if diff["missing_collections"]:
                    logger.log_warning(
                        "Missing collections",
                        missing_collections=diff["missing_collections"],
                    )

                if diff["extra_collections"]:
                    logger.log_warning(
                        "Extra collections",
                        extra_collections=diff["extra_collections"],
                    )

                if diff["collection_differences"]:
                    for coll_name, coll_diff in diff["collection_differences"].items():
                        logger.log_warning(
                            "Collection differences",
                            collection_name=coll_name,
                        )
                        if coll_diff["missing_indexes"]:
                            logger.log_warning(
                                "Missing indexes",
                                collection_name=coll_name,
                                missing_indexes=coll_diff["missing_indexes"],
                            )
                        if coll_diff["extra_indexes"]:
                            logger.log_warning(
                                "Extra indexes",
                                collection_name=coll_name,
                                extra_indexes=coll_diff["extra_indexes"],
                            )
                        if coll_diff["different_indexes"]:
                            logger.log_warning(
                                "Different indexes",
                                collection_name=coll_name,
                                different_index_count=len(
                                    coll_diff["different_indexes"]
                                ),
                            )

                sys.exit(1)
        else:
            handle_migration_commands(
                settings, migrator.version_checker, migrator, logger
            )

    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Migration tool failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
