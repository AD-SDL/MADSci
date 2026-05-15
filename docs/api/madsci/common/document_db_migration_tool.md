Module madsci.common.document_db_migration_tool
===============================================
MongoDB-compatible document database migration tool for MADSci databases with backup, schema management, and CLI.

Functions
---------

`handle_migration_commands(settings: madsci.common.types.document_db_migration_types.DocumentDBMigrationSettings, version_checker: madsci.common.document_db_version_checker.DocumentDBVersionChecker, migrator: madsci.common.document_db_migration_tool.DocumentDBMigrator, logger: madsci.client.event_client.EventClient) ‑> None`
:   Handle different migration command options.

`main() ‑> None`
:   Command line interface for the MongoDB-compatible document database migration tool.

Classes
-------

`DocumentDBMigrator(settings: madsci.common.types.document_db_migration_types.DocumentDBMigrationSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Handles MongoDB-compatible document database schema migrations for MADSci with backup and restore capabilities.
    
    Initialize the MongoDB-compatible document database migrator.
    
    Args:
        settings: Migration configuration settings
        logger: Optional logger instance

    ### Instance variables

    `parsed_db_url: pydantic.networks.AnyUrl`
    :   Parse MongoDB-compatible document database connection URL using pydantic AnyUrl.

    ### Methods

    `apply_schema_migrations(self) ‑> None`
    :   Apply schema migrations based on the expected schema.

    `get_current_database_schema(self) ‑> madsci.common.types.document_db_migration_types.MongoDBSchema`
    :   Get the current database schema using Pydantic models.

    `load_expected_schema(self) ‑> madsci.common.types.document_db_migration_types.MongoDBSchema`
    :   Load the expected schema from the schema.json file.

    `run_migration(self, target_version: str | None = None) ‑> None`
    :   Run the complete migration process.

    `validate_schema(self) ‑> Dict[str, Any]`
    :   Validate current database schema against expected schema.
        
        Returns:
            Dictionary with validation results and differences