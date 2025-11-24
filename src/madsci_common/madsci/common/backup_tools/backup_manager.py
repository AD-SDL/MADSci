"""Backup management operations and utilities."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.client.event_client import EventClient

from .backup_validator import BackupValidator
from .base_backup import BackupInfo


class BackupManager:
    """Manages backup operations like rotation, listing, and cleanup."""

    def __init__(self, logger: Optional[EventClient] = None) -> None:
        """
        Initialize the backup manager.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or EventClient()
        self.validator = BackupValidator(logger)

    def list_backups(self, backup_dir: Path) -> List[BackupInfo]:
        """
        List all available backups in a directory with metadata.

        Args:
            backup_dir: Directory containing backups

        Returns:
            List of BackupInfo objects sorted by creation time (newest first)
        """
        if not backup_dir.exists():
            self.logger.warning(f"Backup directory does not exist: {backup_dir}")
            return []

        backups = []

        # Look for backup files (SQL files and MongoDB backup directories)
        backup_files = []
        backup_files.extend(backup_dir.glob("*.sql"))  # PostgreSQL backups
        backup_files.extend(
            [
                d
                for d in backup_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )  # MongoDB backups

        for backup_path in backup_files:
            try:
                backup_info = self._create_backup_info(backup_path)
                if backup_info:
                    backups.append(backup_info)
            except Exception as e:
                self.logger.warning(f"Error processing backup {backup_path}: {e}")

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.created_at, reverse=True)

        return backups

    def _create_backup_info(self, backup_path: Path) -> Optional[BackupInfo]:
        """
        Create BackupInfo from a backup file/directory.

        Args:
            backup_path: Path to backup file or directory

        Returns:
            BackupInfo object or None if unable to create
        """
        try:
            # Load metadata if available
            metadata = self.validator.load_metadata(backup_path)

            if metadata:
                return BackupInfo(
                    backup_path=backup_path,
                    created_at=datetime.fromisoformat(metadata["timestamp"]),
                    database_version=metadata.get("database_version"),
                    backup_size=metadata.get("backup_size", 0),
                    checksum=metadata.get("checksum", ""),
                    backup_type=metadata.get("backup_type", "unknown"),
                    is_valid=metadata.get("is_valid", False),
                )
            # Fallback to file system metadata
            stat = backup_path.stat()
            return BackupInfo(
                backup_path=backup_path,
                created_at=datetime.fromtimestamp(stat.st_mtime),
                database_version=None,
                backup_size=stat.st_size
                if backup_path.is_file()
                else self._get_directory_size(backup_path),
                checksum="",
                backup_type="unknown",
                is_valid=False,
            )

        except Exception as e:
            self.logger.error(f"Error creating BackupInfo for {backup_path}: {e}")
            return None

    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of all files in a directory."""
        total = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total

    def rotate_backups(self, backup_dir: Path, max_backups: int) -> int:
        """
        Rotate backups according to retention policy.

        Args:
            backup_dir: Directory containing backups
            max_backups: Maximum number of backups to retain

        Returns:
            Number of backups removed
        """
        if max_backups < 0:
            raise ValueError("max_backups must be non-negative")

        backups = self.list_backups(backup_dir)

        if len(backups) <= max_backups:
            return 0

        # Remove oldest backups
        backups_to_remove = backups[max_backups:]
        removed_count = 0

        for backup in backups_to_remove:
            try:
                self._delete_backup_and_metadata(backup.backup_path)
                removed_count += 1
                self.logger.info(f"Removed old backup: {backup.backup_path}")
            except Exception as e:
                self.logger.error(f"Error removing backup {backup.backup_path}: {e}")

        return removed_count

    def _delete_backup_and_metadata(self, backup_path: Path) -> None:
        """Delete backup file/directory and associated metadata files."""
        # Delete the main backup
        if backup_path.is_file():
            backup_path.unlink()
        elif backup_path.is_dir():
            shutil.rmtree(backup_path)

        # Delete associated files
        metadata_file = backup_path.with_suffix(".metadata.json")
        if metadata_file.exists():
            metadata_file.unlink()

        checksum_file = backup_path.with_suffix(".checksum")
        if checksum_file.exists():
            checksum_file.unlink()

    def find_backup_by_version(
        self, backup_dir: Path, version: str
    ) -> Optional[BackupInfo]:
        """
        Find backup by database version.

        Args:
            backup_dir: Directory containing backups
            version: Database version to find

        Returns:
            BackupInfo if found, None otherwise
        """
        backups = self.list_backups(backup_dir)

        for backup in backups:
            if backup.database_version == version:
                return backup

        return None

    def find_backups_in_date_range(
        self, backup_dir: Path, start_date: datetime, end_date: datetime
    ) -> List[BackupInfo]:
        """
        Find backups within a date range.

        Args:
            backup_dir: Directory containing backups
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of BackupInfo objects within the date range
        """
        backups = self.list_backups(backup_dir)

        return [
            backup for backup in backups if start_date <= backup.created_at <= end_date
        ]

    def get_valid_backups(self, backup_dir: Path) -> List[BackupInfo]:
        """Get all valid backups."""
        backups = self.list_backups(backup_dir)
        return [backup for backup in backups if backup.is_valid]

    def get_invalid_backups(self, backup_dir: Path) -> List[BackupInfo]:
        """Get all invalid backups."""
        backups = self.list_backups(backup_dir)
        return [backup for backup in backups if not backup.is_valid]

    def get_total_backup_size(self, backup_dir: Path) -> int:
        """Get total size of all backups in bytes."""
        backups = self.list_backups(backup_dir)
        return sum(backup.backup_size for backup in backups)

    def get_average_backup_size(self, backup_dir: Path) -> float:
        """Get average backup size in bytes."""
        backups = self.list_backups(backup_dir)
        if not backups:
            return 0.0

        total_size = sum(backup.backup_size for backup in backups)
        return total_size / len(backups)

    def cleanup_incomplete_backups(self, backup_dir: Path) -> List[Path]:
        """
        Clean up incomplete backup files (missing metadata or orphaned files).

        Args:
            backup_dir: Directory containing backups

        Returns:
            List of cleaned up file paths
        """
        if not backup_dir.exists():
            return []

        cleaned_files = []

        # Clean up incomplete backups (missing metadata)
        cleaned_files.extend(self._cleanup_incomplete_backup_files(backup_dir))

        # Clean up orphaned metadata files
        cleaned_files.extend(self._cleanup_orphaned_metadata_files(backup_dir))

        # Clean up orphaned checksum files
        cleaned_files.extend(self._cleanup_orphaned_checksum_files(backup_dir))

        return cleaned_files

    def _cleanup_incomplete_backup_files(self, backup_dir: Path) -> List[Path]:
        """Clean up backup files that are missing their metadata files."""
        cleaned_files = []

        # Find backup files without metadata
        backup_files = list(backup_dir.glob("*.sql"))
        backup_files.extend(
            [
                d
                for d in backup_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )

        for backup_path in backup_files:
            metadata_file = backup_path.with_suffix(".metadata.json")
            if not metadata_file.exists():
                # Incomplete backup - remove it
                try:
                    if backup_path.is_file():
                        backup_path.unlink()
                    else:
                        shutil.rmtree(backup_path)
                    cleaned_files.append(backup_path)
                    self.logger.info(f"Cleaned up incomplete backup: {backup_path}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up {backup_path}: {e}")

        return cleaned_files

    def _cleanup_orphaned_metadata_files(self, backup_dir: Path) -> List[Path]:
        """Clean up orphaned metadata files."""
        cleaned_files = []

        metadata_files = list(backup_dir.glob("*.metadata.json"))
        for metadata_file in metadata_files:
            backup_path = metadata_file.with_suffix("")  # Remove .metadata.json
            if not backup_path.exists():
                try:
                    metadata_file.unlink()
                    cleaned_files.append(metadata_file)
                    self.logger.info(f"Cleaned up orphaned metadata: {metadata_file}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up {metadata_file}: {e}")

        return cleaned_files

    def _cleanup_orphaned_checksum_files(self, backup_dir: Path) -> List[Path]:
        """Clean up orphaned checksum files."""
        cleaned_files = []

        checksum_files = list(backup_dir.glob("*.checksum"))
        for checksum_file in checksum_files:
            backup_path = checksum_file.with_suffix("")  # Remove .checksum
            if not backup_path.exists():
                try:
                    checksum_file.unlink()
                    cleaned_files.append(checksum_file)
                    self.logger.info(f"Cleaned up orphaned checksum: {checksum_file}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up {checksum_file}: {e}")

        return cleaned_files

    def check_all_backups_integrity(self, backup_dir: Path) -> Dict[str, Any]:
        """
        Check integrity of all backups in a directory.

        Args:
            backup_dir: Directory containing backups

        Returns:
            Dictionary with integrity check results
        """
        backups = self.list_backups(backup_dir)

        total_backups = len(backups)
        valid_backups = 0
        invalid_backups = 0
        corrupted_backups = []

        for backup in backups:
            try:
                is_valid, _ = self.validator.validate_backup_comprehensive(
                    backup.backup_path
                )
                if is_valid:
                    valid_backups += 1
                else:
                    invalid_backups += 1
                    corrupted_backups.append(str(backup.backup_path))
            except Exception as e:
                invalid_backups += 1
                corrupted_backups.append(str(backup.backup_path))
                self.logger.error(
                    f"Error checking integrity of {backup.backup_path}: {e}"
                )

        return {
            "total_backups": total_backups,
            "valid_backups": valid_backups,
            "invalid_backups": invalid_backups,
            "corrupted_backups": corrupted_backups,
        }

    def export_backup_inventory(self, backup_dir: Path) -> Dict[str, Any]:
        """
        Export backup inventory to a dictionary.

        Args:
            backup_dir: Directory containing backups

        Returns:
            Dictionary with backup inventory information
        """
        backups = self.list_backups(backup_dir)

        inventory = {
            "backup_directory": str(backup_dir),
            "total_backups": len(backups),
            "total_size": self.get_total_backup_size(backup_dir),
            "export_timestamp": datetime.now().isoformat(),
            "backups": [],
        }

        for backup in backups:
            backup_entry = {
                "backup_path": str(backup.backup_path),
                "created_at": backup.created_at.isoformat(),
                "database_version": backup.database_version,
                "backup_size": backup.backup_size,
                "backup_type": backup.backup_type,
                "is_valid": backup.is_valid,
                "checksum": backup.checksum,
            }
            inventory["backups"].append(backup_entry)

        return inventory
