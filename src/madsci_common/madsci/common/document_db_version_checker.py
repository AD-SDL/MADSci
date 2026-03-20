"""MongoDB-compatible document database version checking and validation for MADSci."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from madsci.client.event_client import EventClient
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,
    PyDocumentStorageHandler,
)
from madsci.common.types.document_db_migration_types import (
    IndexDefinition,
    MongoDBSchema,
)
from pydantic_extra_types.semantic_version import SemanticVersion
from pymongo import MongoClient


def ensure_schema_indexes(
    document_handler: DocumentStorageHandler,
    schema_file_path: Path,
    logger: Optional[EventClient] = None,
) -> None:
    """Create all indexes defined in a schema.json file, idempotently.

    This is a best-effort operation: if the schema file is missing or
    unparseable the function logs a warning and returns without raising.

    Args:
        document_handler: A DocumentStorageHandler (PyDocumentStorageHandler or InMemoryDocumentStorageHandler).
        schema_file_path: Path to the schema.json file.
        logger: Optional logger instance.
    """
    logger = logger or EventClient()

    try:
        if not schema_file_path.exists():
            logger.warning(
                "Schema file not found, skipping index creation",
                schema_file_path=str(schema_file_path),
            )
            return

        schema = MongoDBSchema.from_file(str(schema_file_path))
    except Exception as e:
        logger.warning(
            "Could not load schema file, skipping index creation",
            schema_file_path=str(schema_file_path),
            error=str(e),
        )
        return

    for collection_name, collection_def in schema.collections.items():
        try:
            collection = document_handler.get_collection(collection_name)
            _create_missing_indexes(collection, collection_def.indexes, logger)
        except Exception as e:
            logger.warning(
                "Error ensuring indexes for collection",
                collection_name=collection_name,
                error=str(e),
            )


def _create_missing_indexes(
    collection: Any,
    expected_indexes: list[IndexDefinition],
    logger: EventClient,
) -> None:
    """Create indexes that don't already exist on *collection*."""
    existing_names: set[str] = set()
    try:
        for idx in collection.list_indexes():
            name = (
                idx.get("name") if isinstance(idx, dict) else getattr(idx, "name", None)
            )
            if name:
                existing_names.add(name)
    except Exception:  # noqa: S110
        # list_indexes may fail on empty/new collections; treat as no indexes
        pass

    for index_def in expected_indexes:
        if isinstance(index_def, dict):
            index_def = IndexDefinition(**index_def)  # noqa: PLW2901

        if index_def.name in existing_names:
            continue

        keys = index_def.get_keys_as_tuples()
        index_options = index_def.to_mongo_format()

        try:
            collection.create_index(keys, **index_options)
            logger.info(
                "Created index",
                index_name=index_def.name,
                collection_name=collection.name,
            )
        except Exception as e:
            logger.warning(
                "Failed to create index",
                index_name=index_def.name,
                collection_name=collection.name,
                error=str(e),
            )


class DocumentDBVersionChecker:
    """Handles MongoDB-compatible document database version validation and checking."""

    def __init__(
        self,
        db_url: str,
        database_name: str,
        schema_file_path: str,
        backup_dir: Optional[str] = None,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the DocumentDBVersionChecker.

        Args:
            db_url: MongoDB-compatible document database connection URL
            database_name: Name of the database to check
            schema_file_path: Path to the schema.json file (used for validation only)
            backup_dir: Optional backup directory for document database backups
            logger: Optional logger instance
        """
        self.db_url = db_url
        self.database_name = database_name
        self.schema_file_path = Path(schema_file_path)
        self.backup_dir = str(Path(backup_dir).expanduser()) if backup_dir else None
        self.logger = logger or EventClient()

        # Initialize MongoDB-compatible document database connection
        self.client = MongoClient(db_url)
        self.database = self.client[database_name]

    def __del__(self) -> None:
        """Cleanup MongoDB-compatible document database client resources."""
        if hasattr(self, "client") and self.client:
            self.client.close()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("Document database version checker client disposed")

    def _build_migration_base_args(self) -> list[str]:
        args = [
            "python",
            "-m",
            "madsci.common.document_db_migration_tool",
            "--db_url",
            self.db_url,
            "--database",
            self.database_name,
            "--schema_file",
            str(self.schema_file_path),
        ]
        if self.backup_dir:
            args.extend(["--backup_dir", self.backup_dir])
        return args

    def _build_bare_command(self) -> str:
        """Build bare metal command for migration tool."""
        return " ".join(self._build_migration_base_args())

    def _build_docker_compose_command(self) -> str:
        """Build Docker Compose command for migration tool."""
        service_placeholder = "<your_compose_service_name>"
        return f"docker compose run --rm {service_placeholder} " + " ".join(
            self._build_migration_base_args()
        )

    def get_migration_commands(self) -> dict[str, str]:
        """Get migration commands for bare metal and Docker Compose."""
        return {
            "bare_metal": self._build_bare_command(),
            "docker_compose": self._build_docker_compose_command(),
        }

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
                "Error reading schema version",
                schema_file_path=str(self.schema_file_path),
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Cannot determine expected schema version: {e}") from e

    def get_database_version(self) -> Optional[SemanticVersion]:
        """Get the current database schema version from the schema_versions collection.

        Returns:
            SemanticVersion if a valid semantic version is found
            SemanticVersion(0, 0, 0) if database exists but no version tracking
            None if database doesn't exist or connection errors
        """
        try:
            collection_names = self.database.list_collection_names()
            if not collection_names:
                # Database has no collections (completely fresh)
                return None

            # Check if schema_versions collection exists
            if "schema_versions" not in collection_names:
                # Database exists but no schema_versions collection - return 0.0.0
                return SemanticVersion(0, 0, 0)

            # Check if collection has any records
            version_record = self.database["schema_versions"].find_one(
                {},
                sort=[("applied_at", -1)],  # Most recent first
            )

            if not version_record:
                # Collection exists but is empty - return 0.0.0
                return SemanticVersion(0, 0, 0)

            # Get the latest version entry
            return SemanticVersion.parse(version_record["version"])

        except Exception as e:
            self.logger.error(
                "Error getting database version",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
            return None

    def is_version_tracked(self) -> bool:
        """
        Check if version tracking exists in the database.

        Returns True if the schema_versions collection exists AND has at least one version record.
        Returns False if the collection doesn't exist or is empty.
        """
        try:
            collection_names = self.database.list_collection_names()

            if "schema_versions" not in collection_names:
                return False

            # Check if collection has any records
            version_record = self.database["schema_versions"].find_one({})
            return version_record is not None

        except Exception:
            return False

    def is_migration_needed(
        self,
    ) -> tuple[bool, SemanticVersion, Optional[SemanticVersion]]:
        """
        Check if database migration is needed.

        Migration is needed if:
        1. Database exists but has no version tracking (version 0.0.0), OR
        2. Database has version tracking with version mismatch

        If database doesn't exist at all (None), auto-initialization may be possible.

        Returns:
            tuple: (needs_migration, expected_schema_version, database_version)
        """
        expected_schema_version = self.get_expected_schema_version()
        db_version = self.get_database_version()

        # If database doesn't exist at all (no collections)
        if db_version is None:
            collection_names = self.database.list_collection_names()
            if not collection_names:
                # Completely fresh database - needs migration (may be auto-initialized in validate_or_fail)
                self.logger.info(
                    "Fresh database detected - needs initialization",
                    database_name=self.database_name,
                )
                return True, expected_schema_version, None
            # Some other error occurred
            self.logger.warning(
                "Cannot determine database version",
                database_name=self.database_name,
            )
            return True, expected_schema_version, None

        # Check for version mismatch (including 0.0.0 vs expected version)
        if expected_schema_version != db_version:
            if db_version == SemanticVersion(0, 0, 0):
                cmds = self.get_migration_commands()
                self.logger.warning(
                    "Database exists but has no version tracking; migration required",
                    database_name=self.database_name,
                )
                self.logger.info(
                    "To enable version tracking, run the migration tool using one of the following:"
                )
                self.logger.info(
                    "Migration command (bare metal)", command=cmds["bare_metal"]
                )
                self.logger.info(
                    "Migration command (docker compose)",
                    command=cmds["docker_compose"],
                )
            else:
                self.logger.warning(
                    "Schema version mismatch",
                    database_name=self.database_name,
                    expected_schema_version=str(expected_schema_version),
                    database_version=str(db_version),
                )
            return True, expected_schema_version, db_version

        self.logger.info(
            "Database schema version matches expected version",
            database_name=self.database_name,
            database_version=str(db_version),
            expected_schema_version=str(expected_schema_version),
        )
        return False, expected_schema_version, db_version

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.

        Behavior:
        - If completely fresh database (no collections) -> Auto-initialize
        - If collections exist but no version tracking (0.0.0) -> Auto-initialize
        - If version tracking exists and versions match -> Allow server to start
        - If version tracking exists with version mismatch -> Raise error, require migration
        """
        needs_migration, expected, current = self.is_migration_needed()

        # Handle database auto-initialization for fresh or untracked databases.
        # current is None  => completely empty database (no collections at all)
        # current is 0.0.0 => collections exist but no schema_versions collection
        # Both cases are safe to auto-initialize because no prior version tracking
        # existed, so there is no risk of overwriting an incompatible schema.
        if needs_migration and (current is None or current == SemanticVersion(0, 0, 0)):
            self.logger.info(
                "Auto-initializing database with schema version",
                database_name=self.database_name,
                expected_schema_version=str(expected),
                current_version=str(current),
            )
            try:
                # Create schema_versions collection and record initial version
                self.create_schema_versions_collection()
                self.record_version(
                    expected, f"Auto-initialized schema version {expected}"
                )
                # Create all data-collection indexes from schema.json
                self.ensure_schema_indexes()
                self.logger.info(
                    "Successfully auto-initialized database",
                    database_name=self.database_name,
                    schema_version=str(expected),
                )
                return
            except Exception as e:
                self.logger.error(
                    "Failed to auto-initialize database",
                    database_name=self.database_name,
                    error=str(e),
                    exc_info=True,
                )
                raise RuntimeError(f"Failed to auto-initialize database: {e}") from e

        if needs_migration:
            error_msg = (
                f"Database schema version mismatch detected for {self.database_name}"
            )

            cmds = self.get_migration_commands()
            self.logger.error(error_msg)
            self.logger.error(
                "Expected schema version", expected_schema_version=str(expected)
            )
            self.logger.error("Database version", database_version=str(current))
            self.logger.error(
                "Please run the migration tool with one of the following:"
            )
            self.logger.error(
                "Migration command (bare metal)", command=cmds["bare_metal"]
            )
            self.logger.error(
                "Migration command (docker compose)",
                command=cmds["docker_compose"],
            )
            raise RuntimeError(
                f"{error_msg}!\n"
                f"Expected: {expected}\nCurrent: {current}\n"
                f"Run one of:\n  • {cmds['bare_metal']}\n  • {cmds['docker_compose']}"
            )

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
                "Schema versions collection created",
                database_name=self.database_name,
            )

        except Exception as e:
            self.logger.error(
                "Error creating schema versions collection",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
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
                    "Updated existing database version record",
                    database_name=self.database_name,
                    version=version_str,
                )
            else:
                # Create new record
                schema_versions.insert_one(version_doc)
                self.logger.info(
                    "Recorded new database version",
                    database_name=self.database_name,
                    version=version_str,
                )

        except Exception as e:
            self.logger.error(
                "Error recording database version",
                database_name=self.database_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def database_exists(self) -> bool:
        """Check if the database exists."""
        return self.database_name in self.client.list_database_names()

    def ensure_schema_indexes(self) -> None:
        """Create all indexes from the schema file on this database.

        Wraps ``self.database`` in a ``PyDocumentStorageHandler`` and delegates to the
        module-level :func:`ensure_schema_indexes` function.
        """
        handler = PyDocumentStorageHandler(self.database)
        ensure_schema_indexes(handler, self.schema_file_path, self.logger)

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in the database."""
        if not self.database_exists():
            return False
        return collection_name in self.database.list_collection_names()
