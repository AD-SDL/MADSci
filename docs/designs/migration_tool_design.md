# MADSci Migration Tool Design Document

**Status**: Draft
**Date**: 2026-02-07
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for the MADSci Migration Tool. The tool provides an incremental, safe migration path from the old configuration system (Definition files) to the new configuration system (Settings + ID Registry).

## Problem Statement

### Current State

Production MADSci deployments use definition files:
- `*.manager.yaml` files for managers
- `*.node.yaml` files for nodes
- `*.workflow.yaml` files for workflows

These files contain:
- Component IDs (should be in registry)
- Configuration (should be in Settings)
- Structural information (should be in Settings)

### Goals

1. **Safe migration**: No data loss, easy rollback
2. **Incremental**: Convert one file at a time
3. **Automated**: Minimal manual intervention
4. **Validated**: Verify conversion is correct
5. **Clear upgrade path**: For production deployments

---

## Migration Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Migration Workflow                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: SCAN                                                                │
│  ─────────────────────────────────────────────────────────────              │
│  Discover all definition files that need migration                          │
│                                                                              │
│      madsci migrate scan                                                     │
│                                                                              │
│          │                                                                   │
│          ▼                                                                   │
│                                                                              │
│  Step 2: CONVERT (per file)                                                  │
│  ─────────────────────────────────────────────────────────────              │
│  Convert definition file to Settings + Registry entry                       │
│                                                                              │
│      madsci migrate convert <file> --dry-run    (preview)                   │
│      madsci migrate convert <file> --apply      (execute)                   │
│                                                                              │
│          │                                                                   │
│          ▼                                                                   │
│                                                                              │
│  Step 3: VALIDATE                                                            │
│  ─────────────────────────────────────────────────────────────              │
│  Verify the migration worked correctly                                      │
│                                                                              │
│      madsci validate                                                         │
│      madsci start lab   (test it works)                                     │
│                                                                              │
│          │                                                                   │
│          ▼                                                                   │
│                                                                              │
│  Step 4: FINALIZE                                                            │
│  ─────────────────────────────────────────────────────────────              │
│  Remove deprecated files, clean up                                          │
│                                                                              │
│      madsci migrate finalize --dry-run          (preview)                   │
│      madsci migrate finalize --apply            (execute)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CLI Commands

### `madsci migrate scan`

Scan for files that need migration.

```bash
madsci migrate scan [OPTIONS] [DIRECTORY]
```

**Options:**
- `--json` - Output as JSON
- `--verbose` - Show detailed information about each file

**Output:**
```
Scanning for deprecated configuration files...

Found 12 files requiring migration:

Manager Definitions:
  ✗ managers/example_lab.manager.yaml
      → Convert to: LAB_* environment variables
      → Register ID: example_lab → 01JK7069E1EVFT4SA5M0VQT35G
  ✗ managers/example_workcell.manager.yaml
      → Convert to: WORKCELL_* environment variables
      → Register ID: example_workcell → 01JK706A23XYZFT4SA5M0VQT35H
  ...

Node Definitions:
  ✗ node_definitions/liquidhandler_1.node.yaml
      → Convert to: NODE_* environment variables
      → Register ID: liquidhandler_1 → 01JYFEHVSV20D60Z88RVERJ75N
  ...

Summary:
  Manager definitions: 7 files
  Node definitions: 5 files
  Total: 12 files

Next step:
  madsci migrate convert --all --dry-run    Preview all conversions
  madsci migrate convert <file>             Convert single file
```

---

### `madsci migrate convert`

Convert definition files to new format.

```bash
madsci migrate convert [OPTIONS] [FILES...]
```

**Arguments:**
- `FILES` - Specific files to convert (or use `--all`)

**Options:**
- `--all` - Convert all detected files
- `--dry-run` - Preview changes without applying
- `--apply` - Apply the conversion
- `--backup/--no-backup` - Create backup before converting (default: backup)
- `--output-format FORMAT` - Output format for env vars (env, yaml, toml)
- `--force` - Overwrite existing converted files

**Example (single file, dry-run):**
```bash
$ madsci migrate convert managers/example_workcell.manager.yaml --dry-run

Migrating: managers/example_workcell.manager.yaml
─────────────────────────────────────────────────

Original file:
  name: Example Workcell
  manager_type: workcell_manager
  manager_id: 01JK706A23XYZFT4SA5M0VQT35H
  nodes:
    liquidhandler_1: http://localhost:2000/
    robotarm_1: http://localhost:2002/

Actions:
  1. Register ID in registry:
     └─ example_workcell → 01JK706A23XYZFT4SA5M0VQT35H (manager)

  2. Generate environment variables:
     ┌─────────────────────────────────────────────────────────────┐
     │ WORKCELL_NAME=example_workcell                              │
     │ WORKCELL_DESCRIPTION="Example Workcell"                     │
     │ WORKCELL_NODES='{"liquidhandler_1": "http://localhost:2000/",│
     │   "robotarm_1": "http://localhost:2002/"}'                  │
     └─────────────────────────────────────────────────────────────┘

  3. Create backup:
     └─ managers/example_workcell.manager.yaml.bak

  4. Mark file as deprecated:
     └─ Add deprecation header to original file

Dry run - no changes made.
Run with --apply to execute.
```

**Example (apply):**
```bash
$ madsci migrate convert managers/example_workcell.manager.yaml --apply

Migrating: managers/example_workcell.manager.yaml
─────────────────────────────────────────────────

✓ Created backup: managers/example_workcell.manager.yaml.bak
✓ Registered ID: example_workcell → 01JK706A23XYZFT4SA5M0VQT35H
✓ Generated: .env.workcell (environment variables)
✓ Marked original as deprecated

Next steps:
  1. Add the following to your .env file or Docker Compose:

     WORKCELL_NAME=example_workcell
     WORKCELL_NODES='{"liquidhandler_1": "http://localhost:2000/"}'

  2. Test the configuration:
     madsci start manager workcell

  3. Once verified, finalize:
     madsci migrate finalize
```

---

### `madsci migrate finalize`

Finalize migration by removing deprecated files.

```bash
madsci migrate finalize [OPTIONS]
```

**Options:**
- `--dry-run` - Preview what would be removed
- `--apply` - Actually remove files
- `--keep-backups` - Keep .bak files
- `--force` - Skip confirmation prompt

**Output:**
```bash
$ madsci migrate finalize --dry-run

Finalizing migration...

Files to remove:
  ✗ managers/example_lab.manager.yaml (deprecated)
  ✗ managers/example_workcell.manager.yaml (deprecated)
  ✗ node_definitions/liquidhandler_1.node.yaml (deprecated)
  ...

Backup files to keep:
  ✓ managers/example_lab.manager.yaml.bak
  ✓ managers/example_workcell.manager.yaml.bak
  ...

Registry entries verified: 12/12

Dry run - no changes made.
Run with --apply to remove deprecated files.
```

---

### `madsci migrate status`

Show migration status.

```bash
madsci migrate status
```

**Output:**
```
MADSci Migration Status
=======================

Overall: 8/12 files migrated (67%)

Manager Definitions:
  ✓ example_lab.manager.yaml         migrated
  ✓ example_workcell.manager.yaml    migrated
  ✓ example_event.manager.yaml       migrated
  ✗ example_resource.manager.yaml    pending
  ...

Node Definitions:
  ✓ liquidhandler_1.node.yaml        migrated
  ✓ robotarm_1.node.yaml             migrated
  ✗ platereader_1.node.yaml          pending
  ...

Registry Status:
  Entries: 8
  Active: 8
  Stale: 0

Next steps:
  madsci migrate convert --all    Complete remaining migrations
```

---

### `madsci migrate rollback`

Roll back a migration.

```bash
madsci migrate rollback [OPTIONS] [FILES...]
```

**Options:**
- `--all` - Rollback all migrated files
- `--dry-run` - Preview rollback

**Output:**
```bash
$ madsci migrate rollback managers/example_workcell.manager.yaml

Rolling back: managers/example_workcell.manager.yaml
───────────────────────────────────────────────────

✓ Restored from backup: managers/example_workcell.manager.yaml.bak
✓ Removed generated .env.workcell
✓ Removed registry entry: example_workcell

Rollback complete.
```

---

## Implementation

### Data Types

```python
# src/madsci_common/madsci/common/migration/types.py
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from pydantic import Field
from madsci.common.types.base_types import MadsciBaseModel


class MigrationStatus(str, Enum):
    """Status of a file's migration."""
    PENDING = "pending"
    MIGRATED = "migrated"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class FileType(str, Enum):
    """Type of definition file."""
    MANAGER_DEFINITION = "manager_definition"
    NODE_DEFINITION = "node_definition"
    WORKFLOW_DEFINITION = "workflow_definition"


class MigrationAction(MadsciBaseModel):
    """A single action in a migration."""
    action_type: str  # "register_id", "generate_env", "create_backup", etc.
    description: str
    details: dict = Field(default_factory=dict)


class FileMigration(MadsciBaseModel):
    """Migration plan for a single file."""
    source_path: Path
    file_type: FileType
    status: MigrationStatus = MigrationStatus.PENDING

    # Extracted data
    name: str
    component_id: str
    component_type: str
    original_data: dict

    # Planned actions
    actions: list[MigrationAction] = Field(default_factory=list)

    # Results
    backup_path: Optional[Path] = None
    output_files: list[Path] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class MigrationPlan(MadsciBaseModel):
    """Complete migration plan for a project."""
    project_dir: Path
    files: list[FileMigration] = Field(default_factory=list)

    @property
    def pending_count(self) -> int:
        return sum(1 for f in self.files if f.status == MigrationStatus.PENDING)

    @property
    def migrated_count(self) -> int:
        return sum(1 for f in self.files if f.status == MigrationStatus.MIGRATED)
```

### Scanner

```python
# src/madsci_common/madsci/common/migration/scanner.py
import yaml
from pathlib import Path
from typing import Iterator

from madsci.common.migration.types import (
    FileMigration, FileType, MigrationPlan, MigrationAction
)


class MigrationScanner:
    """Scans for files that need migration."""

    # Patterns for finding definition files
    PATTERNS = {
        FileType.MANAGER_DEFINITION: ["**/*.manager.yaml", "**/*.manager.yml"],
        FileType.NODE_DEFINITION: ["**/*.node.yaml", "**/*.node.yml"],
        FileType.WORKFLOW_DEFINITION: ["**/*.workflow.yaml", "**/*.workflow.yml"],
    }

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def scan(self) -> MigrationPlan:
        """Scan for all files needing migration."""
        plan = MigrationPlan(project_dir=self.project_dir)

        for file_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for path in self.project_dir.glob(pattern):
                    # Skip backups
                    if path.suffix == ".bak":
                        continue

                    migration = self._analyze_file(path, file_type)
                    if migration:
                        plan.files.append(migration)

        return plan

    def _analyze_file(self, path: Path, file_type: FileType) -> FileMigration | None:
        """Analyze a single file for migration."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            if data is None:
                return None

            # Check if already migrated (has deprecation marker)
            if data.get("_deprecated"):
                status = MigrationStatus.DEPRECATED
            else:
                status = MigrationStatus.PENDING

            # Extract identity info based on file type
            if file_type == FileType.MANAGER_DEFINITION:
                name = data.get("name", path.stem)
                component_id = data.get("manager_id", "")
                component_type = "manager"
            elif file_type == FileType.NODE_DEFINITION:
                name = data.get("node_name", path.stem)
                component_id = data.get("node_id", "")
                component_type = "node"
            else:
                name = data.get("name", path.stem)
                component_id = data.get("workflow_definition_id", "")
                component_type = "workflow"

            # Build migration actions
            actions = self._plan_actions(data, file_type)

            return FileMigration(
                source_path=path,
                file_type=file_type,
                status=status,
                name=name,
                component_id=component_id,
                component_type=component_type,
                original_data=data,
                actions=actions,
            )

        except Exception as e:
            # Return migration with error
            return FileMigration(
                source_path=path,
                file_type=file_type,
                name=path.stem,
                component_id="",
                component_type="unknown",
                original_data={},
                errors=[str(e)],
            )

    def _plan_actions(self, data: dict, file_type: FileType) -> list[MigrationAction]:
        """Plan migration actions for a file."""
        actions = []

        # 1. Register ID
        if file_type == FileType.MANAGER_DEFINITION:
            id_field = "manager_id"
            name_field = "name"
        elif file_type == FileType.NODE_DEFINITION:
            id_field = "node_id"
            name_field = "node_name"
        else:
            id_field = "workflow_definition_id"
            name_field = "name"

        if data.get(id_field):
            actions.append(MigrationAction(
                action_type="register_id",
                description=f"Register {data.get(name_field)} → {data.get(id_field)}",
                details={
                    "name": data.get(name_field),
                    "id": data.get(id_field),
                },
            ))

        # 2. Generate environment variables
        env_vars = self._data_to_env_vars(data, file_type)
        if env_vars:
            actions.append(MigrationAction(
                action_type="generate_env",
                description=f"Generate {len(env_vars)} environment variables",
                details={"env_vars": env_vars},
            ))

        # 3. Create backup
        actions.append(MigrationAction(
            action_type="create_backup",
            description="Create backup of original file",
        ))

        # 4. Mark as deprecated
        actions.append(MigrationAction(
            action_type="mark_deprecated",
            description="Add deprecation marker to original file",
        ))

        return actions

    def _data_to_env_vars(self, data: dict, file_type: FileType) -> dict[str, str]:
        """Convert definition data to environment variables."""
        env_vars = {}

        if file_type == FileType.MANAGER_DEFINITION:
            manager_type = data.get("manager_type", "").upper()
            if manager_type:
                # Remove _MANAGER suffix for prefix
                prefix = manager_type.replace("_MANAGER", "")
            else:
                prefix = "MANAGER"

            # Map fields to env vars
            field_mapping = {
                "name": f"{prefix}_NAME",
                "description": f"{prefix}_DESCRIPTION",
                "nodes": f"{prefix}_NODES",
                "locations": f"{prefix}_LOCATIONS",
            }

            for field, env_name in field_mapping.items():
                if field in data and data[field]:
                    value = data[field]
                    if isinstance(value, (dict, list)):
                        import json
                        value = json.dumps(value)
                    env_vars[env_name] = str(value)

        elif file_type == FileType.NODE_DEFINITION:
            env_vars["NODE_NAME"] = data.get("node_name", "")
            if data.get("node_description"):
                env_vars["NODE_DESCRIPTION"] = data["node_description"]
            if data.get("module_name"):
                env_vars["NODE_MODULE_NAME"] = data["module_name"]

        return env_vars
```

### Converter

```python
# src/madsci_common/madsci/common/migration/converter.py
import shutil
import yaml
from pathlib import Path
from datetime import datetime

from madsci.common.migration.types import FileMigration, MigrationStatus
from madsci.common.registry import LocalRegistryManager


class MigrationConverter:
    """Converts definition files to new format."""

    def __init__(
        self,
        registry: LocalRegistryManager = None,
        output_dir: Path = None,
    ):
        self.registry = registry or LocalRegistryManager()
        self.output_dir = output_dir

    def convert(
        self,
        migration: FileMigration,
        dry_run: bool = True,
        create_backup: bool = True,
    ) -> FileMigration:
        """Convert a single file.

        Args:
            migration: The migration plan for this file
            dry_run: If True, don't make changes
            create_backup: Create backup before modifying

        Returns:
            Updated migration with results
        """
        if dry_run:
            return migration

        try:
            # 1. Create backup
            if create_backup:
                backup_path = migration.source_path.with_suffix(
                    migration.source_path.suffix + ".bak"
                )
                shutil.copy2(migration.source_path, backup_path)
                migration.backup_path = backup_path

            # 2. Register ID
            for action in migration.actions:
                if action.action_type == "register_id":
                    name = action.details["name"]
                    component_id = action.details["id"]

                    # Import existing ID into registry
                    self.registry.import_entries(
                        {
                            "entries": {
                                name: {
                                    "id": component_id,
                                    "component_type": migration.component_type,
                                    "created_at": datetime.utcnow().isoformat(),
                                    "last_seen": datetime.utcnow().isoformat(),
                                    "metadata": {},
                                }
                            }
                        },
                        merge=True,
                    )

            # 3. Generate env file
            for action in migration.actions:
                if action.action_type == "generate_env":
                    env_vars = action.details["env_vars"]

                    # Determine output file name
                    env_file = self._get_env_output_path(migration)

                    # Append to existing or create new
                    with open(env_file, "a") as f:
                        f.write(f"\n# Migrated from {migration.source_path.name}\n")
                        f.write(f"# Migration date: {datetime.utcnow().isoformat()}\n")
                        for key, value in env_vars.items():
                            # Quote values with special characters
                            if any(c in value for c in " \n\t{}[]"):
                                value = f"'{value}'"
                            f.write(f"{key}={value}\n")

                    migration.output_files.append(env_file)

            # 4. Mark original as deprecated
            for action in migration.actions:
                if action.action_type == "mark_deprecated":
                    self._mark_deprecated(migration.source_path)

            migration.status = MigrationStatus.MIGRATED

        except Exception as e:
            migration.errors.append(str(e))

        return migration

    def _get_env_output_path(self, migration: FileMigration) -> Path:
        """Get the output path for environment variables."""
        if self.output_dir:
            base_dir = self.output_dir
        else:
            base_dir = migration.source_path.parent.parent  # Go up from managers/

        # Use component-specific env file
        if migration.component_type == "manager":
            manager_type = migration.original_data.get("manager_type", "manager")
            prefix = manager_type.replace("_manager", "")
            return base_dir / f".env.{prefix}"
        else:
            return base_dir / f".env.{migration.component_type}s"

    def _mark_deprecated(self, path: Path):
        """Add deprecation marker to file."""
        with open(path) as f:
            content = f.read()

        deprecation_header = f"""\
# ╔════════════════════════════════════════════════════════════════════════╗
# ║  DEPRECATED - This file format is deprecated                          ║
# ║                                                                        ║
# ║  This file has been migrated to the new configuration system.         ║
# ║  Settings are now in environment variables or .env files.             ║
# ║  Component ID is now in the registry (~/.madsci/registry.json).       ║
# ║                                                                        ║
# ║  Migration date: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}                                  ║
# ║                                                                        ║
# ║  To complete migration, run:                                           ║
# ║    madsci migrate finalize                                             ║
# ╚════════════════════════════════════════════════════════════════════════╝

_deprecated: true
_migrated_at: "{datetime.utcnow().isoformat()}"

"""

        with open(path, "w") as f:
            f.write(deprecation_header + content)


class MigrationRollback:
    """Rolls back a migration."""

    def __init__(self, registry: LocalRegistryManager = None):
        self.registry = registry or LocalRegistryManager()

    def rollback(self, migration: FileMigration) -> FileMigration:
        """Roll back a single migration."""
        try:
            # 1. Restore from backup
            if migration.backup_path and migration.backup_path.exists():
                shutil.copy2(migration.backup_path, migration.source_path)
                migration.backup_path.unlink()

            # 2. Remove generated files
            for output_file in migration.output_files:
                if output_file.exists():
                    # TODO: Only remove lines added by this migration
                    pass

            # 3. Remove registry entry
            # Note: Be careful not to remove if still in use

            migration.status = MigrationStatus.PENDING

        except Exception as e:
            migration.errors.append(f"Rollback failed: {e}")

        return migration
```

### CLI Commands

```python
# src/madsci_client/madsci/client/cli/commands/migrate.py
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from madsci.common.migration import MigrationScanner, MigrationConverter
from madsci.common.migration.types import MigrationStatus

console = Console()


@click.group()
def migrate():
    """Migration tools for upgrading configuration."""
    pass


@migrate.command()
@click.argument("directory", default=".", type=click.Path(exists=True))
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def scan(directory, json_output, verbose):
    """Scan for files that need migration."""
    scanner = MigrationScanner(Path(directory))
    plan = scanner.scan()

    if json_output:
        import json
        console.print_json(json.dumps(plan.model_dump(mode="json"), default=str))
        return

    if not plan.files:
        console.print("[green]No files need migration.[/green]")
        return

    console.print(f"\nFound {len(plan.files)} files requiring migration:\n")

    # Group by type
    by_type = {}
    for migration in plan.files:
        by_type.setdefault(migration.file_type, []).append(migration)

    for file_type, migrations in by_type.items():
        console.print(f"[bold]{file_type.value.replace('_', ' ').title()}:[/bold]")

        for m in migrations:
            status_icon = {
                MigrationStatus.PENDING: "✗",
                MigrationStatus.MIGRATED: "✓",
                MigrationStatus.DEPRECATED: "○",
            }.get(m.status, "?")

            status_color = {
                MigrationStatus.PENDING: "red",
                MigrationStatus.MIGRATED: "green",
                MigrationStatus.DEPRECATED: "yellow",
            }.get(m.status, "white")

            console.print(f"  [{status_color}]{status_icon}[/] {m.source_path}")

            if verbose:
                console.print(f"      Name: {m.name}")
                console.print(f"      ID: {m.component_id}")
                for action in m.actions:
                    console.print(f"      → {action.description}")

        console.print()

    # Summary
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Pending: {plan.pending_count}")
    console.print(f"  Migrated: {plan.migrated_count}")
    console.print()
    console.print("[bold]Next step:[/bold]")
    console.print("  madsci migrate convert --all --dry-run")


@migrate.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--all", "convert_all", is_flag=True, help="Convert all detected files")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--apply", is_flag=True, help="Apply the conversion")
@click.option("--backup/--no-backup", default=True, help="Create backup")
@click.option("--output", "-o", type=click.Path(), help="Output directory")
def convert(files, convert_all, dry_run, apply, backup, output):
    """Convert definition files to new format."""
    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        return

    # Get files to convert
    if convert_all:
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [m for m in plan.files if m.status == MigrationStatus.PENDING]
    else:
        if not files:
            console.print("[red]Error: Specify files to convert or use --all[/red]")
            return
        scanner = MigrationScanner(Path.cwd())
        plan = scanner.scan()
        migrations = [m for m in plan.files if str(m.source_path) in files]

    if not migrations:
        console.print("[yellow]No files to convert.[/yellow]")
        return

    converter = MigrationConverter(
        output_dir=Path(output) if output else None,
    )

    for migration in migrations:
        console.print(f"\n[bold]Migrating: {migration.source_path}[/bold]")
        console.print("─" * 50)

        # Show actions
        for action in migration.actions:
            console.print(f"  → {action.description}")

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        else:
            result = converter.convert(migration, dry_run=False, create_backup=backup)

            if result.errors:
                for error in result.errors:
                    console.print(f"[red]Error: {error}[/red]")
            else:
                console.print(f"[green]✓ Migrated successfully[/green]")
                if result.backup_path:
                    console.print(f"  Backup: {result.backup_path}")
                for output_file in result.output_files:
                    console.print(f"  Output: {output_file}")


@migrate.command()
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--apply", is_flag=True, help="Apply the finalization")
@click.option("--keep-backups", is_flag=True, help="Keep backup files")
@click.option("--force", is_flag=True, help="Skip confirmation")
def finalize(dry_run, apply, keep_backups, force):
    """Finalize migration by removing deprecated files."""
    if not dry_run and not apply:
        console.print("[red]Error: Specify --dry-run or --apply[/red]")
        return

    scanner = MigrationScanner(Path.cwd())
    plan = scanner.scan()

    deprecated = [
        m for m in plan.files
        if m.status in (MigrationStatus.MIGRATED, MigrationStatus.DEPRECATED)
    ]

    if not deprecated:
        console.print("[yellow]No deprecated files to remove.[/yellow]")
        return

    console.print("\n[bold]Files to remove:[/bold]")
    for m in deprecated:
        console.print(f"  ✗ {m.source_path}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made.[/yellow]")
        return

    if not force:
        if not click.confirm("\nRemove these files?"):
            console.print("Cancelled.")
            return

    for m in deprecated:
        m.source_path.unlink()
        console.print(f"[green]✓[/green] Removed {m.source_path}")

        if not keep_backups and m.backup_path and m.backup_path.exists():
            m.backup_path.unlink()

    console.print("\n[green]Migration finalized.[/green]")


@migrate.command()
def status():
    """Show migration status."""
    scanner = MigrationScanner(Path.cwd())
    plan = scanner.scan()

    total = len(plan.files)
    if total == 0:
        console.print("[green]No definition files found. Migration complete![/green]")
        return

    migrated = plan.migrated_count
    pending = plan.pending_count

    console.print("\n[bold]MADSci Migration Status[/bold]")
    console.print("=" * 40)
    console.print(f"\nOverall: {migrated}/{total} files migrated ({100*migrated//total}%)\n")

    # Progress bar
    bar_width = 30
    filled = int(bar_width * migrated / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    console.print(f"[{bar}]\n")

    if pending > 0:
        console.print(f"[bold]Next steps:[/bold]")
        console.print("  madsci migrate convert --all --apply")
```

---

## Migration Guide for Users

### Quick Start

```bash
# 1. Check what needs to be migrated
madsci migrate scan

# 2. Preview the migration
madsci migrate convert --all --dry-run

# 3. Run the migration
madsci migrate convert --all --apply

# 4. Test your lab still works
madsci start lab
madsci status

# 5. Clean up deprecated files
madsci migrate finalize --apply
```

### What Changes

| Before | After |
|--------|-------|
| `managers/workcell.manager.yaml` | Environment variables + Registry |
| `node_definitions/node.node.yaml` | Environment variables + Registry |
| IDs in YAML files | IDs in `~/.madsci/registry.json` |
| `nodes:` section in definition | `WORKCELL_NODES` env var |

### Rollback

If something goes wrong:

```bash
# Rollback a specific file
madsci migrate rollback managers/workcell.manager.yaml

# Rollback all
madsci migrate rollback --all
```

---

## Testing

```python
# tests/migration/test_scanner.py
import tempfile
from pathlib import Path
import pytest

from madsci.common.migration import MigrationScanner
from madsci.common.migration.types import MigrationStatus, FileType


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project with definition files."""
    # Create manager definition
    managers_dir = tmp_path / "managers"
    managers_dir.mkdir()

    (managers_dir / "test.manager.yaml").write_text("""
name: Test Manager
manager_type: workcell_manager
manager_id: 01ABC123
nodes:
  node1: http://localhost:2000/
""")

    # Create node definition
    nodes_dir = tmp_path / "node_definitions"
    nodes_dir.mkdir()

    (nodes_dir / "test.node.yaml").write_text("""
node_name: test_node
node_id: 01XYZ789
module_name: test_module
""")

    return tmp_path


def test_scan_finds_definitions(sample_project):
    scanner = MigrationScanner(sample_project)
    plan = scanner.scan()

    assert len(plan.files) == 2

    types = {m.file_type for m in plan.files}
    assert FileType.MANAGER_DEFINITION in types
    assert FileType.NODE_DEFINITION in types


def test_scan_extracts_ids(sample_project):
    scanner = MigrationScanner(sample_project)
    plan = scanner.scan()

    manager = next(m for m in plan.files if m.file_type == FileType.MANAGER_DEFINITION)
    assert manager.component_id == "01ABC123"
    assert manager.name == "Test Manager"

    node = next(m for m in plan.files if m.file_type == FileType.NODE_DEFINITION)
    assert node.component_id == "01XYZ789"
    assert node.name == "test_node"
```

---

## Design Decisions

The following decisions have been made based on review:

1. **Workflow definitions**: **Keep as YAML.** Workflow definitions are structurally different from manager/node definitions - they describe step sequences and parameters, not runtime configuration. The migration tool will NOT attempt to migrate workflow files. They remain as `*.workflow.yaml` files.

2. **Docker Compose**: **Yes, auto-update docker-compose.yaml files.** The migration tool will:
   - Detect docker-compose.yaml files in the project
   - Remove volume mounts for definition files that are no longer needed
   - Add environment variable configurations for migrated settings
   - Create a backup before modifying

3. **Secrets**: Sensitive data should go into **non-version-controlled `.env` files**. The migration tool will:
   - Detect fields that look like secrets (passwords, tokens, keys)
   - Emit a warning if they're in the definition file
   - Generate the secret into a `.env` file instead of docker-compose.yaml
   - Add `.env` to `.gitignore` if not already present

4. **Multi-lab**: **Not a concern at this time.** The migration tool assumes it is being run in a directory containing exactly one lab. Users with multiple labs on one machine should run migration separately in each lab directory.

5. **CI/CD**: **Not providing GitHub Actions templates.** The migration is expected to be a one-time operation for each lab. We aim to migrate all existing labs within 1-2 months, after which the migration tool becomes legacy code. Maintaining CI/CD templates isn't worth the effort.

---

## Docker Compose Migration

Since docker-compose.yaml auto-update was approved, here's the detailed approach:

### Detection

The migration tool will look for:
- `docker-compose.yaml`
- `docker-compose.yml`
- `compose.yaml`
- `compose.yml`

### Transformations

**Before:**
```yaml
services:
  workcell_manager:
    image: madsci:latest
    command: python -m madsci.workcell_manager
    volumes:
      - ./managers/example_workcell.manager.yaml:/app/workcell.manager.yaml
    environment:
      - WORKCELL_MANAGER_DEFINITION=/app/workcell.manager.yaml
```

**After:**
```yaml
services:
  workcell_manager:
    image: madsci:latest
    command: python -m madsci.workcell_manager
    # Volume mount for definition file removed
    volumes:
      - ~/.madsci:/app/.madsci  # Share registry
    environment:
      - WORKCELL_NAME=example_workcell
      - WORKCELL_NODES={"liquidhandler_1": "http://liquidhandler_1:2000/"}
    env_file:
      - .env.workcell  # Secrets go here
```

### CLI Command

```bash
# Preview docker-compose changes
madsci migrate docker-compose --dry-run

# Apply docker-compose changes
madsci migrate docker-compose --apply
```

### Implementation

```python
# In migration/docker_compose.py
def migrate_compose_file(path: Path, migrations: list[FileMigration], dry_run: bool = True):
    """Update docker-compose.yaml based on completed migrations."""
    import yaml

    with open(path) as f:
        compose = yaml.safe_load(f)

    if not compose or 'services' not in compose:
        return

    changes = []

    for service_name, service_config in compose['services'].items():
        volumes = service_config.get('volumes', [])
        environment = service_config.get('environment', [])

        # Find and remove definition file mounts
        for migration in migrations:
            if migration.status != MigrationStatus.MIGRATED:
                continue

            # Check if this service mounts the migrated file
            for i, volume in enumerate(volumes):
                if migration.source_path.name in str(volume):
                    changes.append(f"Remove volume mount: {volume}")
                    if not dry_run:
                        volumes.pop(i)

        # Add environment variables from migration
        # ... (implementation details)

    if not dry_run and changes:
        backup_path = path.with_suffix(path.suffix + '.bak')
        shutil.copy2(path, backup_path)

        with open(path, 'w') as f:
            yaml.dump(compose, f, default_flow_style=False)

    return changes
```

---

## Module Migration

### Migrating External Module Repositories

For external module repositories (e.g., `pf400_module`, `ot2_module`), the migration tool can help standardize the structure and add missing components.

### `madsci migrate module`

Analyze and update an existing module repository to follow MADSci conventions.

```bash
madsci migrate module [OPTIONS] [MODULE_DIR]
```

**Options:**
- `--dry-run` - Preview changes without applying
- `--apply` - Apply the changes
- `--add-types` - Generate a `foo_types.py` file from existing code
- `--add-fake` - Generate a fake interface from the real interface
- `--update-structure` - Reorganize files to match recommended structure

**Example:**
```bash
$ madsci migrate module ./pf400_module --dry-run

Analyzing module: pf400_module
──────────────────────────────

Current structure:
  src/
  ├── pf400_rest_node.py        ✓ Node found
  ├── pf400_interface/          ✓ Interface package found
  │   ├── pf400.py
  │   ├── pf400_constants.py
  │   └── pf400_errors.py
  └── keyboard_control.py
Recommended additions:
  ⚠ Missing: src/pf400_types.py
      → Will extract settings and models from existing code
  ⚠ Missing: src/pf400_fake_interface.py
      → Will generate from pf400_interface with stubbed methods
  ⚠ Missing: tests/test_pf400_fake.py
      → Will generate basic fake interface tests
Actions:
  1. Generate pf400_types.py with:
     - PF400NodeSettings (extracted from node)
     - PF400InterfaceSettings (extracted from interface)
     - Existing Pydantic models
  2. Generate pf400_fake_interface.py with:
     - Same method signatures as real interface
     - Configurable delays and responses
     - State tracking for testing
  3. Update pf400_rest_node.py to:
     - Import from pf400_types
      - Support interface_variant selection

Dry run - no changes made.
Run with --apply to execute.
```

### Interface Standardization

For modules that have interfaces but don't follow the recommended pattern, the migration tool can help:

```bash
# Generate a fake interface from an existing real interface
madsci migrate module ./my_module --add-fake

# Extract types into a foo_types.py file
madsci migrate module ./my_module --add-types
```

### What Gets Generated

**`foo_types.py`** (from `--add-types`):
- Extracts settings classes from node and interface
- Consolidates Pydantic models
- Adds proper imports and documentation

**`foo_fake_interface.py`** (from `--add-fake`):
- Copies method signatures from real interface
- Replaces hardware calls with configurable stubs
- Adds state tracking for verification in tests
- Includes delay simulation for realistic timing

---
