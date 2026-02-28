Module madsci.resource_manager.migration_tool
=============================================
Database migration tool for MADSci resources using Alembic with automatic type conversion handling.

Functions
---------

`main() ‑> None`
:   Command line interface for the migration tool.

Classes
-------

`DatabaseMigrationSettings(**kwargs: Any)`
:   Configuration settings for PostgreSQL database migration operations.

    Initialize settings with walk-up file discovery.

    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

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
