"""
Migration scanner for MADSci.

This module scans a project for definition files that need migration.
"""

import json
import logging
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml
from madsci.common.types.migration_types import (
    FileMigration,
    FileType,
    MigrationAction,
    MigrationPlan,
    MigrationStatus,
    OutputFormat,
)

logger = logging.getLogger(__name__)


class MigrationScanner:
    """Scans for files that need migration.

    The scanner finds all definition files in a project directory and
    creates a migration plan with actions for each file.

    Example:
        scanner = MigrationScanner(Path("./my_project"))
        plan = scanner.scan()

        for migration in plan.files:
            print(f"{migration.source_path}: {migration.status}")
            for action in migration.actions:
                print(f"  - {action.description}")
    """

    # Patterns for finding definition files
    PATTERNS: ClassVar[dict[FileType, list[str]]] = {
        FileType.MANAGER_DEFINITION: ["**/*.manager.yaml", "**/*.manager.yml"],
        FileType.NODE_DEFINITION: ["**/*.node.yaml", "**/*.node.yml"],
    }

    def __init__(
        self,
        project_dir: Path,
        output_format: OutputFormat = OutputFormat.YAML,
    ) -> None:
        """Initialize the scanner.

        Args:
            project_dir: Root directory of the project to scan.
            output_format: Output format for generated config files.
        """
        self.project_dir = Path(project_dir)
        self.output_format = output_format

    def scan(self) -> MigrationPlan:
        """Scan for all files needing migration.

        Returns:
            MigrationPlan containing all discovered files and their status.
        """
        plan = MigrationPlan(project_dir=self.project_dir)

        for file_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for path in self.project_dir.glob(pattern):
                    # Skip backups
                    if path.suffix == ".bak":
                        continue
                    if ".bak." in path.name:
                        continue

                    migration = self._analyze_file(path, file_type)
                    if migration:
                        plan.files.append(migration)

        logger.info(
            "Scanned project directory: project_dir=%s files_found=%d",
            str(self.project_dir),
            len(plan.files),
        )
        return plan

    def _analyze_file(self, path: Path, file_type: FileType) -> Optional[FileMigration]:
        """Analyze a single file for migration.

        Args:
            path: Path to the file.
            file_type: Type of definition file.

        Returns:
            FileMigration object, or None if file is invalid.
        """
        try:
            with path.open() as f:
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
                name = data.get("name", path.stem.replace(".manager", ""))
                component_id = data.get("manager_id", "")
                component_type = "manager"
            else:
                name = data.get("node_name", path.stem.replace(".node", ""))
                component_id = data.get("node_id", "")
                component_type = "node"

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
            logger.warning("Error analyzing file: path=%s error=%s", str(path), str(e))
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

    def _plan_actions(
        self, data: dict[str, Any], file_type: FileType
    ) -> list[MigrationAction]:
        """Plan migration actions for a file.

        Args:
            data: Parsed YAML data.
            file_type: Type of definition file.

        Returns:
            List of actions to perform during migration.
        """
        actions = []

        # Determine field names based on file type
        if file_type == FileType.MANAGER_DEFINITION:
            id_field = "manager_id"
            name_field = "name"
        else:
            id_field = "node_id"
            name_field = "node_name"

        # 1. Register ID
        if data.get(id_field):
            actions.append(
                MigrationAction(
                    action_type="register_id",
                    description=f"Register {data.get(name_field)} → {data.get(id_field)}",
                    details={
                        "name": data.get(name_field),
                        "id": data.get(id_field),
                    },
                )
            )

        # 2. Generate settings file
        settings_data = self._extract_settings(data, file_type)
        if settings_data:
            if self.output_format == OutputFormat.YAML:
                description = (
                    f"Generate settings.yaml with {len(settings_data)} settings"
                )
            else:
                env_vars = self._settings_to_env_vars(settings_data)
                description = f"Generate {len(env_vars)} environment variables"
            actions.append(
                MigrationAction(
                    action_type="generate_settings",
                    description=description,
                    details={
                        "settings": settings_data,
                        "output_format": self.output_format.value,
                    },
                )
            )

        # 3. Create backup
        actions.append(
            MigrationAction(
                action_type="create_backup",
                description="Create backup of original file",
            )
        )

        # 4. Mark as deprecated
        actions.append(
            MigrationAction(
                action_type="mark_deprecated",
                description="Add deprecation marker to original file",
            )
        )

        return actions

    def _extract_settings(
        self, data: dict[str, Any], file_type: FileType
    ) -> dict[str, Any]:
        """Extract settings from definition data.

        Returns a dict of prefixed setting keys to their native values
        (preserving dicts, lists, etc.).

        Args:
            data: Parsed YAML data.
            file_type: Type of definition file.

        Returns:
            Dictionary of prefixed setting key to native value.
        """
        settings: dict[str, Any] = {}

        if file_type == FileType.MANAGER_DEFINITION:
            manager_type = data.get("manager_type", "")
            # Remove _manager suffix for prefix
            prefix = manager_type.replace("_manager", "") if manager_type else "manager"

            # Map definition fields to prefixed settings keys.
            # Note: the old definition 'name' and 'description' fields
            # correspond to 'manager_name' and 'manager_description' in
            # ManagerSettings, so the prefixed keys must include 'manager_'.
            field_mapping = {
                "name": f"{prefix}_manager_name",
                "description": f"{prefix}_manager_description",
                "nodes": f"{prefix}_nodes",
                "locations": f"{prefix}_locations",
                "transfer_capabilities": f"{prefix}_transfer_capabilities",
                "default_templates": f"{prefix}_default_templates",
            }

            for field, settings_key in field_mapping.items():
                if data.get(field) is not None:
                    settings[settings_key] = data[field]

        elif file_type == FileType.NODE_DEFINITION:
            if data.get("node_name"):
                settings["node_name"] = data["node_name"]
            if data.get("node_description"):
                settings["node_description"] = data["node_description"]
            if data.get("module_name"):
                settings["node_module_name"] = data["module_name"]

        return settings

    @staticmethod
    def _settings_to_env_vars(settings: dict[str, Any]) -> dict[str, str]:
        """Convert settings dict to environment variable format.

        Converts keys to uppercase and serializes complex values as JSON.

        Args:
            settings: Dictionary of setting key to native value.

        Returns:
            Dictionary of environment variable name to string value.
        """
        env_vars: dict[str, str] = {}
        for key, value in settings.items():
            env_key = key.upper()
            if isinstance(value, (dict, list)):
                env_vars[env_key] = json.dumps(value)
            else:
                env_vars[env_key] = str(value)
        return env_vars
