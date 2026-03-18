Module madsci.common.document_db_version_checker
================================================
MongoDB-compatible document database version checking and validation for MADSci.

Functions
---------

`ensure_schema_indexes(document_handler: madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler, schema_file_path: pathlib.Path, logger: madsci.client.event_client.EventClient | None = None) ‑> None`
:   Create all indexes defined in a schema.json file, idempotently.
    
    This is a best-effort operation: if the schema file is missing or
    unparseable the function logs a warning and returns without raising.
    
    Args:
        document_handler: A DocumentStorageHandler (PyDocumentStorageHandler or InMemoryDocumentStorageHandler).
        schema_file_path: Path to the schema.json file.
        logger: Optional logger instance.

Classes
-------

`DocumentDBVersionChecker(db_url: str, database_name: str, schema_file_path: str, backup_dir: str | None = None, logger: madsci.client.event_client.EventClient | None = None)`
:   Handles MongoDB-compatible document database version validation and checking.
    
    Initialize the DocumentDBVersionChecker.
    
    Args:
        db_url: MongoDB-compatible document database connection URL
        database_name: Name of the database to check
        schema_file_path: Path to the schema.json file (used for validation only)
        backup_dir: Optional backup directory for document database backups
        logger: Optional logger instance

    ### Methods

    `collection_exists(self, collection_name: str) ‑> bool`
    :   Check if a collection exists in the database.

    `create_schema_versions_collection(self) ‑> None`
    :   Create the schema_versions collection if it doesn't exist.

    `database_exists(self) ‑> bool`
    :   Check if the database exists.

    `ensure_schema_indexes(self) ‑> None`
    :   Create all indexes from the schema file on this database.
        
        Wraps ``self.database`` in a ``PyDocumentStorageHandler`` and delegates to the
        module-level :func:`ensure_schema_indexes` function.

    `get_database_version(self) ‑> pydantic_extra_types.semantic_version.SemanticVersion | None`
    :   Get the current database schema version from the schema_versions collection.
        
        Returns:
            SemanticVersion if a valid semantic version is found
            SemanticVersion(0, 0, 0) if database exists but no version tracking
            None if database doesn't exist or connection errors

    `get_expected_schema_version(self) ‑> pydantic_extra_types.semantic_version.SemanticVersion`
    :   Get the expected schema version from the schema.json file.

    `get_migration_commands(self) ‑> dict[str, str]`
    :   Get migration commands for bare metal and Docker Compose.

    `is_migration_needed(self) ‑> tuple[bool, pydantic_extra_types.semantic_version.SemanticVersion, pydantic_extra_types.semantic_version.SemanticVersion | None]`
    :   Check if database migration is needed.
        
        Migration is needed if:
        1. Database exists but has no version tracking (version 0.0.0), OR
        2. Database has version tracking with version mismatch
        
        If database doesn't exist at all (None), auto-initialization may be possible.
        
        Returns:
            tuple: (needs_migration, expected_schema_version, database_version)

    `is_version_tracked(self) ‑> bool`
    :   Check if version tracking exists in the database.
        
        Returns True if the schema_versions collection exists AND has at least one version record.
        Returns False if the collection doesn't exist or is empty.

    `record_version(self, version: pydantic_extra_types.semantic_version.SemanticVersion | str, migration_notes: str | None = None) ‑> None`
    :   Record a new version in the database.

    `validate_or_fail(self) ‑> None`
    :   Validate database version compatibility or raise an exception.
        This should be called during server startup.
        
        Behavior:
        - If completely fresh database (no collections) -> Auto-initialize
        - If version tracking exists and versions match -> Allow server to start
        - If version tracking exists/missing with mismatch -> Raise error, require migration