"""
Migration converter for MADSci.

This module converts definition files to the new configuration format.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from madsci.common.registry import LocalRegistryManager
from madsci.common.types.migration_types import FileMigration, MigrationStatus

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

            # 3. Generate env file
            for action in migration.actions:
                if action.action_type == "generate_env":
                    env_vars = action.details["env_vars"]

                    # Determine output file name
                    env_file = self._get_env_output_path(migration)

                    # Append to existing or create new
                    migration_ts = datetime.now(tz=timezone.utc).isoformat()
                    with env_file.open("a") as f:
                        f.write(f"\n# Migrated from {migration.source_path.name}\n")
                        f.write(f"# Migration date: {migration_ts}\n")
                        for key, value in env_vars.items():
                            # Always double-quote values and escape
                            # special characters to prevent injection
                            escaped = (
                                value.replace("\\", "\\\\")
                                .replace('"', '\\"')
                                .replace("$", "\\$")
                                .replace("`", "\\`")
                            )
                            f.write(f'{key}="{escaped}"\n')

                    migration.output_files.append(env_file)
                    logger.info("Generated env file: env_file=%s", str(env_file))

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

    def _get_env_output_path(self, migration: FileMigration) -> Path:
        """Get the output path for environment variables.

        Args:
            migration: The migration being processed.

        Returns:
            Path to the env file.
        """
        # Go up from managers/ or node_definitions/
        base_dir = self.output_dir or migration.source_path.parent.parent

        # Use component-specific env file
        if migration.component_type == "manager":
            manager_type = migration.original_data.get("manager_type", "manager")
            prefix = manager_type.replace("_manager", "")
            return base_dir / f".env.{prefix}"
        return base_dir / f".env.{migration.component_type}s"

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
# ║  Settings are now in environment variables or .env files.              ║
# ║  Component ID is now in the registry (~/.madsci/registry.json).        ║
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
                migration.backup_path.unlink()
                logger.info(
                    "Restored from backup: source_path=%s", str(migration.source_path)
                )

            # 2. Remove generated files
            for output_file in migration.output_files:
                if output_file.exists():
                    # For env files, we should be more careful
                    # For now, just log a warning
                    logger.warning(
                        "Generated file exists - manual cleanup may be needed: output_file=%s",
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
