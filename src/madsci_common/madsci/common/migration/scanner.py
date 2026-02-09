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
        FileType.WORKFLOW_DEFINITION: ["**/*.workflow.yaml", "**/*.workflow.yml"],
    }

    def __init__(self, project_dir: Path) -> None:
        """Initialize the scanner.

        Args:
            project_dir: Root directory of the project to scan.
        """
        self.project_dir = Path(project_dir)

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
            "Scanned project directory",
            project_dir=str(self.project_dir),
            files_found=len(plan.files),
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
            elif file_type == FileType.NODE_DEFINITION:
                name = data.get("node_name", path.stem.replace(".node", ""))
                component_id = data.get("node_id", "")
                component_type = "node"
            else:
                name = data.get("name", path.stem.replace(".workflow", ""))
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
            logger.warning("Error analyzing file", path=str(path), error=str(e))
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
        elif file_type == FileType.NODE_DEFINITION:
            id_field = "node_id"
            name_field = "node_name"
        else:
            id_field = "workflow_definition_id"
            name_field = "name"

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

        # 2. Generate environment variables
        env_vars = self._data_to_env_vars(data, file_type)
        if env_vars:
            actions.append(
                MigrationAction(
                    action_type="generate_env",
                    description=f"Generate {len(env_vars)} environment variables",
                    details={"env_vars": env_vars},
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

    def _data_to_env_vars(
        self, data: dict[str, Any], file_type: FileType
    ) -> dict[str, str]:
        """Convert definition data to environment variables.

        Args:
            data: Parsed YAML data.
            file_type: Type of definition file.

        Returns:
            Dictionary of environment variable name to value.
        """
        env_vars: dict[str, str] = {}

        if file_type == FileType.MANAGER_DEFINITION:
            manager_type = data.get("manager_type", "").upper()
            # Remove _MANAGER suffix for prefix
            prefix = manager_type.replace("_MANAGER", "") if manager_type else "MANAGER"

            # Map fields to env vars
            field_mapping = {
                "name": f"{prefix}_NAME",
                "description": f"{prefix}_DESCRIPTION",
                "nodes": f"{prefix}_NODES",
                "locations": f"{prefix}_LOCATIONS",
            }

            for field, env_name in field_mapping.items():
                if data.get(field):
                    value = data[field]
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    env_vars[env_name] = str(value)

        elif file_type == FileType.NODE_DEFINITION:
            if data.get("node_name"):
                env_vars["NODE_NAME"] = data["node_name"]
            if data.get("node_description"):
                env_vars["NODE_DESCRIPTION"] = data["node_description"]
            if data.get("module_name"):
                env_vars["NODE_MODULE_NAME"] = data["module_name"]

        # Workflow definitions are kept as YAML, not migrated to env vars

        return env_vars
