Module madsci.common.migration
==============================
Migration tools for MADSci.

This module provides tools for migrating from the old configuration system
(Definition files) to the new configuration system (Settings + ID Registry).

Example:
    from madsci.common.migration import MigrationScanner, MigrationConverter

    # Scan for files needing migration
    scanner = MigrationScanner(Path("./my_project"))
    plan = scanner.scan()

    # Preview migrations
    for migration in plan.files:
        print(f"{migration.source_path}: {migration.status}")

    # Convert a file
    converter = MigrationConverter()
    result = converter.convert(migration, dry_run=False)

Sub-modules
-----------
* madsci.common.migration.converter
* madsci.common.migration.scanner

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

`MigrationScanner(project_dir: pathlib.Path, output_format: madsci.common.types.migration_types.OutputFormat = OutputFormat.YAML)`
:   Scans for files that need migration.
    
    The scanner finds all definition files in a project directory and
    creates a migration plan with actions for each file.
    
    Example:
        scanner = MigrationScanner(Path("./my_project"))
        plan = scanner.scan()
    
        for migration in plan.files:
            print(f"{migration.source_path}: {migration.status}")
            for action in migration.actions:
                print(f"  - {action.description}")
    
    Initialize the scanner.
    
    Args:
        project_dir: Root directory of the project to scan.
        output_format: Output format for generated config files.

    ### Class variables

    `PATTERNS: ClassVar[dict[madsci.common.types.migration_types.FileType, list[str]]]`
    :

    ### Methods

    `scan(self) ‑> madsci.common.types.migration_types.MigrationPlan`
    :   Scan for all files needing migration.
        
        Returns:
            MigrationPlan containing all discovered files and their status.