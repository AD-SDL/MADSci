Module madsci.common.migration.converter
========================================
Migration converter for MADSci.

This module converts definition files to the new configuration format.

Classes
-------

`MigrationConverter(registry: madsci.common.registry.local_registry.LocalRegistryManager | None = None, output_dir: pathlib.Path | None = None)`
:   Converts definition files to new format.

    The converter performs the actual migration by:
    1. Creating backups of original files
    2. Registering IDs in the registry
    3. Generating environment variable files
    4. Marking original files as deprecated

    Example:
        converter = MigrationConverter()

        # Preview conversion
        result = converter.convert(migration, dry_run=True)

        # Apply conversion
        result = converter.convert(migration, dry_run=False)

    Initialize the converter.

    Args:
        registry: Registry manager for ID registration.
                 Creates one if not provided.
        output_dir: Directory for output files (env files).
                   Defaults to project root.

    ### Methods

    `convert(self, migration: madsci.common.types.migration_types.FileMigration, dry_run: bool = True, create_backup: bool = True) ‑> madsci.common.types.migration_types.FileMigration`
    :   Convert a single file.

        Args:
            migration: The migration plan for this file.
            dry_run: If True, don't make changes.
            create_backup: Create backup before modifying.

        Returns:
            Updated migration with results.

`MigrationRollback(registry: madsci.common.registry.local_registry.LocalRegistryManager | None = None)`
:   Rolls back a migration.

    Use this to undo a migration if something went wrong.

    Example:
        rollback = MigrationRollback()
        rollback.rollback(migration)

    Initialize the rollback handler.

    Args:
        registry: Registry manager for cleanup.

    ### Methods

    `rollback(self, migration: madsci.common.types.migration_types.FileMigration) ‑> madsci.common.types.migration_types.FileMigration`
    :   Roll back a single migration.

        Args:
            migration: The migration to roll back.

        Returns:
            Updated migration with rollback status.
