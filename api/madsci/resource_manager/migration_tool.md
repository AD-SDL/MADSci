Module madsci.resource_manager.migration_tool
=============================================
Database migration tool for MADSci resources using Alembic with automatic type conversion handling.

Functions
---------

`main() ‑> None`
:   Command line interface for the migration tool.

Classes
-------

`DatabaseMigrationSettings(**values: Any)`
:   Configuration settings for PostgreSQL database migration operations.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_dir: str | pathlib.Path`
    :

    `backup_only: bool`
    :

    `db_url: str | None`
    :

    `generate_migration: str | None`
    :

    `restore_from: str | pathlib.Path | None`
    :

    `target_version: str | None`
    :

    ### Methods

    `get_effective_db_url(self) ‑> str`
    :   Get the effective database URL, trying fallback environment variables if needed.

`DatabaseMigrator(settings: madsci.resource_manager.migration_tool.DatabaseMigrationSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Handles database schema migrations for MADSci using Alembic with automatic type conversion handling.

    Initialize the migrator with settings and logger.

    ### Methods

    `apply_schema_migrations(self) ‑> None`
    :   Apply schema migrations using Alembic with automatic migration generation.

    `generate_migration(self, message: str) ‑> None`
    :   Generate a new Alembic migration based on model changes.

    `run_migration(self, target_version: str | None = None) ‑> None`
    :   Run the complete migration process using Alembic.
