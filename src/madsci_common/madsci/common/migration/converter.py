"""
Migration converter for MADSci.

This module converts definition files to the new configuration format.
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from madsci.common.registry import LocalRegistryManager
from madsci.common.types.migration_types import (
    FileMigration,
    MigrationStatus,
    OutputFormat,
)

logger = logging.getLogger(__name__)


class MigrationConverter:
    """Converts definition files to new format.

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
    """

    def __init__(
        self,
        registry: Optional[LocalRegistryManager] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the converter.

        Args:
            registry: Registry manager for ID registration.
                     Creates one if not provided.
            output_dir: Directory for output files (env files).
                       Defaults to project root.
        """
        self.registry = registry or LocalRegistryManager()
        self.output_dir = output_dir

    def convert(  # noqa: C901
        self,
        migration: FileMigration,
        dry_run: bool = True,
        create_backup: bool = True,
    ) -> FileMigration:
        """Convert a single file.

        Args:
            migration: The migration plan for this file.
            dry_run: If True, don't make changes.
            create_backup: Create backup before modifying.

        Returns:
            Updated migration with results.
        """
        if dry_run:
            logger.info(
                "Dry run: would migrate file: source_path=%s",
                str(migration.source_path),
            )
            return migration

        try:
            # 1. Create backup
            if create_backup:
                backup_path = migration.source_path.with_suffix(
                    migration.source_path.suffix + ".bak"
                )
                shutil.copy2(migration.source_path, backup_path)
                migration.backup_path = backup_path
                logger.debug("Created backup: backup_path=%s", str(backup_path))

            # 2. Register ID
            for action in migration.actions:
                if action.action_type == "register_id":
                    name = action.details["name"]
                    component_id = action.details["id"]

                    # Import existing ID into registry
                    self.registry.import_entries(
                        {
                            "version": 1,
                            "entries": {
                                name: {
                                    "id": component_id,
                                    "component_type": migration.component_type,
                                    "created_at": datetime.now(
                                        tz=timezone.utc
                                    ).isoformat(),
                                    "last_seen": datetime.now(
                                        tz=timezone.utc
                                    ).isoformat(),
                                    "metadata": {
                                        "migrated_from": str(migration.source_path)
                                    },
                                }
                            },
                        },
                        merge=True,
                    )
                    logger.info(
                        "Registered ID: name=%s component_id=%s", name, component_id
                    )

            # 3. Generate settings file (YAML or env)
            for action in migration.actions:
                if action.action_type in ("generate_settings", "generate_env"):
                    output_format = OutputFormat(
                        action.details.get("output_format", OutputFormat.ENV.value)
                    )

                    # Get settings data (native structure) or fall back to env_vars
                    settings_data = action.details.get(
                        "settings", action.details.get("env_vars", {})
                    )

                    # Determine output path
                    output_file = self._get_output_path(migration, output_format)

                    # Ensure parent directory exists
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    migration_ts = datetime.now(tz=timezone.utc).isoformat()

                    if output_format == OutputFormat.YAML:
                        self._write_yaml_settings(
                            output_file,
                            settings_data,
                            migration.source_path.name,
                            migration_ts,
                        )
                    else:
                        # For env format, convert to env var strings
                        env_vars = self._to_env_vars(settings_data)
                        self._write_env_file(
                            output_file,
                            env_vars,
                            migration.source_path.name,
                            migration_ts,
                        )

                    migration.output_files.append(output_file)
                    logger.info(
                        "Generated settings file: output_file=%s", str(output_file)
                    )

            # 4. Mark original as deprecated
            for action in migration.actions:
                if action.action_type == "mark_deprecated":
                    self._mark_deprecated(migration.source_path)
                    logger.debug(
                        "Marked as deprecated: source_path=%s",
                        str(migration.source_path),
                    )

            migration.status = MigrationStatus.MIGRATED
            migration.migrated_at = datetime.now(tz=timezone.utc)
            logger.info(
                "Successfully migrated: source_path=%s", str(migration.source_path)
            )

        except Exception as e:
            migration.errors.append(str(e))
            migration.status = MigrationStatus.FAILED
            logger.error(
                "Migration failed: source_path=%s error=%s",
                str(migration.source_path),
                str(e),
            )

        return migration

    def _get_output_path(
        self,
        migration: FileMigration,
        output_format: OutputFormat,
    ) -> Path:
        """Get the output path for a migration.

        For managers, outputs go to the base directory with a per-manager name.
        For nodes, outputs go to a per-node subdirectory to avoid conflicts.

        Args:
            migration: The migration being processed.
            output_format: The output format (yaml or env).

        Returns:
            Path to the output file.
        """
        # Determine the project-level base directory.
        # If the source is in a recognized subdirectory (managers/,
        # node_definitions/, nodes/), go up one level. Otherwise, use the
        # source file's own parent to avoid writing outside the project.
        base_dir = self.output_dir
        if base_dir is None:
            parent_name = migration.source_path.parent.name.lower()
            if parent_name in ("managers", "node_definitions", "nodes"):
                base_dir = migration.source_path.parent.parent
            else:
                base_dir = migration.source_path.parent

        if migration.component_type == "manager":
            manager_type = migration.original_data.get("manager_type", "manager")
            prefix = manager_type.replace("_manager", "")
            if output_format == OutputFormat.YAML:
                return base_dir / f"{prefix}.settings.yaml"
            return base_dir / f".env.{prefix}"

        # Nodes: create a per-node directory to avoid conflicting values
        node_name = migration.name or migration.source_path.stem.replace(".node", "")
        node_dir = base_dir / "nodes" / node_name
        if output_format == OutputFormat.YAML:
            return node_dir / "settings.yaml"
        return node_dir / ".env"

    def _write_yaml_settings(
        self,
        output_file: Path,
        settings_data: dict[str, Any],
        source_name: str,
        migration_ts: str,
    ) -> None:
        """Write settings as a YAML file.

        Preserves native data structures (dicts, lists) in YAML format.

        Args:
            output_file: Path to the output file.
            settings_data: Settings key-value pairs with native types.
            source_name: Name of the source file being migrated.
            migration_ts: ISO timestamp of the migration.
        """
        header = f"# Migrated from {source_name}\n# Migration date: {migration_ts}\n"

        with output_file.open("w") as f:
            f.write(header)
            yaml.dump(settings_data, f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _to_env_vars(settings_data: dict[str, Any]) -> dict[str, str]:
        """Convert native settings dict to environment variable format.

        Keys are uppercased. Complex values (dicts, lists) are JSON-serialized.

        Args:
            settings_data: Settings key-value pairs with native types.

        Returns:
            Dictionary of environment variable name to string value.
        """
        env_vars: dict[str, str] = {}
        for key, value in settings_data.items():
            env_key = key.upper()
            if isinstance(value, (dict, list)):
                env_vars[env_key] = json.dumps(value)
            else:
                env_vars[env_key] = str(value)
        return env_vars

    def _write_env_file(
        self,
        output_file: Path,
        env_vars: dict[str, str],
        source_name: str,
        migration_ts: str,
    ) -> None:
        """Write settings as a .env file.

        Args:
            output_file: Path to the output file.
            env_vars: Environment variable name-value pairs.
            source_name: Name of the source file being migrated.
            migration_ts: ISO timestamp of the migration.
        """
        with output_file.open("a") as f:
            f.write(f"\n# Migrated from {source_name}\n")
            f.write(f"# Migration date: {migration_ts}\n")
            for key, value in env_vars.items():
                # Always double-quote values and escape
                # special characters to prevent injection
                escaped = (
                    value.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("$", "\\$")
                    .replace("`", "\\`")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t")
                )
                f.write(f'{key}="{escaped}"\n')

    def _mark_deprecated(self, path: Path) -> None:
        """Add deprecation marker to file.

        Args:
            path: Path to the file to mark.
        """
        with path.open() as f:
            content = f.read()

        now = datetime.now(tz=timezone.utc)
        migration_date = now.strftime("%Y-%m-%d %H:%M:%S")
        deprecation_header = f"""\
# ╔════════════════════════════════════════════════════════════════════════╗
# ║  DEPRECATED - This file format is deprecated                           ║
# ║                                                                         ║
# ║  This file has been migrated to the new configuration system.          ║
# ║  Settings are now in settings.yaml files (or .env overrides).          ║
# ║  Component ID is now in the local .madsci/registry.json.               ║
# ║                                                                         ║
# ║  Migration date: {migration_date:49}║
# ║                                                                         ║
# ║  To complete migration, run:                                            ║
# ║    madsci migrate finalize                                              ║
# ╚════════════════════════════════════════════════════════════════════════╝

_deprecated: true
_migrated_at: "{now.isoformat()}"

"""

        with path.open("w") as f:
            f.write(deprecation_header + content)


class MigrationRollback:
    """Rolls back a migration.

    Use this to undo a migration if something went wrong.

    Example:
        rollback = MigrationRollback()
        rollback.rollback(migration)
    """

    def __init__(self, registry: Optional[LocalRegistryManager] = None) -> None:
        """Initialize the rollback handler.

        Args:
            registry: Registry manager for cleanup.
        """
        self.registry = registry or LocalRegistryManager()

    def rollback(self, migration: FileMigration) -> FileMigration:
        """Roll back a single migration.

        Args:
            migration: The migration to roll back.

        Returns:
            Updated migration with rollback status.
        """
        try:
            # 1. Restore from backup
            if migration.backup_path and migration.backup_path.exists():
                shutil.copy2(migration.backup_path, migration.source_path)
                # Verify the restore succeeded before removing the backup
                if migration.source_path.exists():
                    migration.backup_path.unlink()
                    logger.info(
                        "Restored from backup: source_path=%s",
                        str(migration.source_path),
                    )
                else:
                    logger.error(
                        "Restore verification failed, preserving backup: backup_path=%s",
                        str(migration.backup_path),
                    )

            # 2. Remove generated files
            for output_file in migration.output_files:
                if output_file.exists():
                    try:
                        output_file.unlink()
                        logger.info(
                            "Removed generated file: output_file=%s",
                            str(output_file),
                        )
                    except OSError:
                        logger.warning(
                            "Failed to remove generated file: output_file=%s",
                            str(output_file),
                        )

            # 3. Registry entries are not removed to avoid losing IDs
            # that may be in use

            migration.status = MigrationStatus.PENDING
            migration.migrated_at = None
            migration.output_files = []
            logger.info("Rolled back: source_path=%s", str(migration.source_path))

        except Exception as e:
            migration.errors.append(f"Rollback failed: {e}")
            logger.error(
                "Rollback failed: source_path=%s error=%s",
                str(migration.source_path),
                str(e),
            )

        return migration
