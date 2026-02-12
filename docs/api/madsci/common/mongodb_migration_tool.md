Module madsci.common.mongodb_migration_tool
===========================================
MongoDB migration tool for MADSci databases with backup, schema management, and CLI.

Functions
---------

`handle_migration_commands(settings: madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings, version_checker: madsci.common.mongodb_version_checker.MongoDBVersionChecker, migrator: madsci.common.mongodb_migration_tool.MongoDBMigrator, logger: madsci.client.event_client.EventClient) ‑> None`
:   Handle different migration command options.

`main() ‑> None`
:   Command line interface for the MongoDB migration tool.

Classes
-------

`MongoDBMigrator(settings: madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Handles MongoDB schema migrations for MADSci with backup and restore capabilities.

    Initialize the MongoDB migrator.

    Args:
        settings: Migration configuration settings
        logger: Optional logger instance

    ### Instance variables

    `parsed_db_url: pydantic.networks.AnyUrl`
    :   Parse MongoDB connection URL using pydantic AnyUrl.

    ### Methods

    `apply_schema_migrations(self) ‑> None`
    :   Apply schema migrations based on the expected schema.

    `get_current_database_schema(self) ‑> madsci.common.types.mongodb_migration_types.MongoDBSchema`
    :   Get the current database schema using Pydantic models.

    `load_expected_schema(self) ‑> madsci.common.types.mongodb_migration_types.MongoDBSchema`
    :   Load the expected schema from the schema.json file.

    `run_migration(self, target_version: str | None = None) ‑> None`
    :   Run the complete migration process.

    `validate_schema(self) ‑> Dict[str, Any]`
    :   Validate current database schema against expected schema.

        Returns:
            Dictionary with validation results and differences
