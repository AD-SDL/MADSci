"""Abstract base classes and shared utilities for backup operations."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field


class BackupInfo(MadsciBaseModel):
    """Metadata about a backup."""

    backup_path: Path = Field(
        title="Backup Path", description="Path to the backup file or directory"
    )
    created_at: datetime = Field(
        title="Created At", description="Timestamp when the backup was created"
    )
    database_version: Optional[str] = Field(
        default=None,
        title="Database Version",
        description="Version of the database at backup time",
    )
    backup_size: int = Field(
        title="Backup Size", description="Size of the backup in bytes"
    )
    checksum: str = Field(
        title="Checksum",
        description="Checksum of the backup for integrity verification",
    )
    backup_type: str = Field(
        title="Backup Type", description="Type of backup (postgresql, mongodb, etc.)"
    )
    is_valid: bool = Field(
        title="Is Valid",
        description="Whether the backup has been validated as restorable",
    )


class AbstractBackupTool(ABC):
    """Abstract base class for database backup tools."""

    @abstractmethod
    def create_backup(self, name_suffix: Optional[str] = None) -> Path:
        """
        Create a backup and return the backup path.

        Args:
            name_suffix: Optional suffix to append to backup name

        Returns:
            Path to the created backup
        """

    @abstractmethod
    def restore_from_backup(
        self, backup_path: Path, target_db: Optional[str] = None
    ) -> None:
        """
        Restore database from backup.

        Args:
            backup_path: Path to the backup to restore from
            target_db: Optional target database name (uses default if None)
        """

    @abstractmethod
    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Validate backup integrity.

        Args:
            backup_path: Path to the backup to validate

        Returns:
            True if backup is valid and restorable, False otherwise
        """

    @abstractmethod
    def list_available_backups(self) -> List[BackupInfo]:
        """
        List available backups with metadata.

        Returns:
            List of BackupInfo objects for available backups
        """

    @abstractmethod
    def delete_backup(self, backup_path: Path) -> None:
        """
        Delete a specific backup.

        Args:
            backup_path: Path to the backup to delete
        """
