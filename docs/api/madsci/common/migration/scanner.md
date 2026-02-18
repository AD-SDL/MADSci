Module madsci.common.migration.scanner
======================================
Migration scanner for MADSci.

This module scans a project for definition files that need migration.

Classes
-------

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
