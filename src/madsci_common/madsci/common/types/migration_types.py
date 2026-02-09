"""
Migration tool types for MADSci.

This module defines the types used by the migration tool for upgrading
from the old configuration system (Definition files) to the new system
(Settings + ID Registry).
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field


class MigrationStatus(str, Enum):
    """Status of a file's migration."""

    PENDING = "pending"
    MIGRATED = "migrated"
    DEPRECATED = "deprecated"
    REMOVED = "removed"
    FAILED = "failed"


class FileType(str, Enum):
    """Type of definition file."""

    MANAGER_DEFINITION = "manager_definition"
    NODE_DEFINITION = "node_definition"
    WORKFLOW_DEFINITION = "workflow_definition"


class MigrationAction(MadsciBaseModel):
    """A single action in a migration.

    Represents one step of the migration process, such as registering an ID
    or generating environment variables.
    """

    action_type: str = Field(
        description="Type of action (register_id, generate_env, create_backup, etc.)"
    )
    description: str = Field(description="Human-readable description of the action")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Action-specific details"
    )


class FileMigration(MadsciBaseModel):
    """Migration plan for a single file.

    Contains all information needed to migrate a definition file to the new
    configuration system.
    """

    source_path: Path = Field(description="Path to the definition file")
    file_type: FileType = Field(description="Type of definition file")
    status: MigrationStatus = Field(
        default=MigrationStatus.PENDING, description="Current migration status"
    )

    # Extracted data
    name: str = Field(description="Component name from the definition")
    component_id: str = Field(description="Component ID from the definition")
    component_type: str = Field(description="Type of component (node, manager, etc.)")
    original_data: dict[str, Any] = Field(
        default_factory=dict, description="Original content of the definition file"
    )

    # Planned actions
    actions: list[MigrationAction] = Field(
        default_factory=list, description="Actions to perform during migration"
    )

    # Results
    backup_path: Optional[Path] = Field(
        default=None, description="Path to backup file if created"
    )
    output_files: list[Path] = Field(
        default_factory=list, description="Files generated during migration"
    )
    errors: list[str] = Field(
        default_factory=list, description="Errors encountered during migration"
    )
    migrated_at: Optional[datetime] = Field(
        default=None, description="When migration was completed"
    )


class MigrationPlan(MadsciBaseModel):
    """Complete migration plan for a project.

    Contains all files that need to be migrated and their current status.
    """

    project_dir: Path = Field(description="Root directory of the project")
    files: list[FileMigration] = Field(
        default_factory=list, description="All files in the migration plan"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the plan was created"
    )

    @property
    def pending_count(self) -> int:
        """Count of files still pending migration."""
        return sum(1 for f in self.files if f.status == MigrationStatus.PENDING)

    @property
    def migrated_count(self) -> int:
        """Count of successfully migrated files."""
        return sum(1 for f in self.files if f.status == MigrationStatus.MIGRATED)

    @property
    def deprecated_count(self) -> int:
        """Count of deprecated files."""
        return sum(1 for f in self.files if f.status == MigrationStatus.DEPRECATED)

    @property
    def failed_count(self) -> int:
        """Count of failed migrations."""
        return sum(1 for f in self.files if f.status == MigrationStatus.FAILED)

    @property
    def total_count(self) -> int:
        """Total count of files in the plan."""
        return len(self.files)

    @property
    def progress_percent(self) -> int:
        """Migration progress as a percentage."""
        if self.total_count == 0:
            return 100
        return int(100 * self.migrated_count / self.total_count)
