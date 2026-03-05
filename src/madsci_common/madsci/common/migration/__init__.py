"""
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
"""

from madsci.common.migration.converter import MigrationConverter, MigrationRollback
from madsci.common.migration.scanner import MigrationScanner

__all__ = [
    "MigrationConverter",
    "MigrationRollback",
    "MigrationScanner",
]
