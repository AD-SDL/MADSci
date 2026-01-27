Module madsci.resource_manager.database_version_checker
=======================================================
Database version checking and validation for MADSci.

Classes
-------

`DatabaseVersionChecker(db_url: str, logger: madsci.client.event_client.EventClient | None = None)`
:   Handles database version validation and checking.

    Initialize the DatabaseVersionChecker.

    ### Methods

    `create_version_table_if_not_exists(self) ‑> None`
    :   Create the schema version table if it doesn't exist.

    `get_current_madsci_version(self) ‑> str`
    :   Get the current MADSci version from the package.

    `get_database_version(self) ‑> str | None`
    :   Get the current database schema version.

    `is_fresh_database(self) ‑> bool`
    :   Check if this is a fresh database with no existing tables.

        Returns True if the database has no tables or only system tables.

    `is_migration_needed(self) ‑> tuple[bool, str | None, str | None]`
    :   Check if database migration is needed.

        Migration is needed if:
        1. Database exists but has no version tracking, OR
        2. Database has version tracking with major.minor version mismatch

        For fresh databases (no version tracking), migration is required to establish proper schema.

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)

    `is_version_tracked(self) ‑> bool`
    :   Check if version tracking exists in the database.

        Returns True if the schema version table exists AND has at least one version record.
        Returns False if the table doesn't exist or is empty.

    `record_version(self, version: str, migration_notes: str | None = None) ‑> None`
    :   Record a new version in the database.

    `validate_or_fail(self) ‑> None`
    :   Validate database version compatibility or raise an exception.
        This should be called during server startup.

        Behavior:
        - If completely fresh database (no tables) -> Auto-initialize
        - If version tracking exists and versions match -> Allow server to start
        - If version tracking exists/missing with mismatch -> Raise error, require migration

    `versions_match(self, version1: str, version2: str) ‑> bool`
    :   Check if two versions match based on major.minor comparison only.

        Ignores patch version and pre-release/build metadata.

        Examples:
            1.0.0 == 1.0.1  -> True (same major.minor)
            1.0.0 == 1.1.0  -> False (different minor)
            1.0.0 == 2.0.0  -> False (different major)
