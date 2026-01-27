Module madsci.common.backup_tools.backup_manager
================================================
Backup management operations and utilities.

Classes
-------

`BackupManager(logger: madsci.client.event_client.EventClient | None = None)`
:   Manages backup operations like rotation, listing, and cleanup.

    Initialize the backup manager.

    Args:
        logger: Optional logger instance

    ### Methods

    `check_all_backups_integrity(self, backup_dir: pathlib.Path) ‑> Dict[str, Any]`
    :   Check integrity of all backups in a directory.

        Args:
            backup_dir: Directory containing backups

        Returns:
            Dictionary with integrity check results

    `cleanup_incomplete_backups(self, backup_dir: pathlib.Path) ‑> List[pathlib.Path]`
    :   Clean up incomplete backup files (missing metadata or orphaned files).

        Args:
            backup_dir: Directory containing backups

        Returns:
            List of cleaned up file paths

    `export_backup_inventory(self, backup_dir: pathlib.Path) ‑> Dict[str, Any]`
    :   Export backup inventory to a dictionary.

        Args:
            backup_dir: Directory containing backups

        Returns:
            Dictionary with backup inventory information

    `find_backup_by_version(self, backup_dir: pathlib.Path, version: str) ‑> madsci.common.backup_tools.base_backup.BackupInfo | None`
    :   Find backup by database version.

        Args:
            backup_dir: Directory containing backups
            version: Database version to find

        Returns:
            BackupInfo if found, None otherwise

    `find_backups_in_date_range(self, backup_dir: pathlib.Path, start_date: datetime.datetime, end_date: datetime.datetime) ‑> List[madsci.common.backup_tools.base_backup.BackupInfo]`
    :   Find backups within a date range.

        Args:
            backup_dir: Directory containing backups
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of BackupInfo objects within the date range

    `get_average_backup_size(self, backup_dir: pathlib.Path) ‑> float`
    :   Get average backup size in bytes.

    `get_invalid_backups(self, backup_dir: pathlib.Path) ‑> List[madsci.common.backup_tools.base_backup.BackupInfo]`
    :   Get all invalid backups.

    `get_total_backup_size(self, backup_dir: pathlib.Path) ‑> int`
    :   Get total size of all backups in bytes.

    `get_valid_backups(self, backup_dir: pathlib.Path) ‑> List[madsci.common.backup_tools.base_backup.BackupInfo]`
    :   Get all valid backups.

    `list_backups(self, backup_dir: pathlib.Path) ‑> List[madsci.common.backup_tools.base_backup.BackupInfo]`
    :   List all available backups in a directory with metadata.

        Args:
            backup_dir: Directory containing backups

        Returns:
            List of BackupInfo objects sorted by creation time (newest first)

    `rotate_backups(self, backup_dir: pathlib.Path, max_backups: int) ‑> int`
    :   Rotate backups according to retention policy.

        Args:
            backup_dir: Directory containing backups
            max_backups: Maximum number of backups to retain

        Returns:
            Number of backups removed
