Module madsci.common.backup_tools
=================================
MADSci backup tools package.

Sub-modules
-----------
* madsci.common.backup_tools.backup_manager
* madsci.common.backup_tools.backup_validator
* madsci.common.backup_tools.base_backup
* madsci.common.backup_tools.cli
* madsci.common.backup_tools.mongo_cli
* madsci.common.backup_tools.mongodb_backup
* madsci.common.backup_tools.postgres_backup
* madsci.common.backup_tools.postgres_cli

Functions
---------

`main_mongodb_backup() ‑> None`
:   Entry point for MongoDB backup CLI.

`main_postgres_backup() ‑> None`
:   Entry point for PostgreSQL backup CLI.

Classes
-------

`AbstractBackupTool()`
:   Abstract base class for database backup tools.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.backup_tools.mongodb_backup.MongoDBBackupTool
    * madsci.common.backup_tools.postgres_backup.PostgreSQLBackupTool

    ### Methods

    `create_backup(self, name_suffix: str | None = None) ‑> pathlib.Path`
    :   Create a backup and return the backup path.

        Args:
            name_suffix: Optional suffix to append to backup name

        Returns:
            Path to the created backup

    `delete_backup(self, backup_path: pathlib.Path) ‑> None`
    :   Delete a specific backup.

        Args:
            backup_path: Path to the backup to delete

    `list_available_backups(self) ‑> List[madsci.common.backup_tools.base_backup.BackupInfo]`
    :   List available backups with metadata.

        Returns:
            List of BackupInfo objects for available backups

    `restore_from_backup(self, backup_path: pathlib.Path, target_db: str | None = None) ‑> None`
    :   Restore database from backup.

        Args:
            backup_path: Path to the backup to restore from
            target_db: Optional target database name (uses default if None)

    `validate_backup_integrity(self, backup_path: pathlib.Path) ‑> bool`
    :   Validate backup integrity.

        Args:
            backup_path: Path to the backup to validate

        Returns:
            True if backup is valid and restorable, False otherwise

`BackupInfo(**data: Any)`
:   Metadata about a backup.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `backup_path: pathlib.Path`
    :

    `backup_size: int`
    :

    `backup_type: str`
    :

    `checksum: str`
    :

    `created_at: datetime.datetime`
    :

    `database_version: str | None`
    :

    `is_valid: bool`
    :

    `model_config`
    :

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

`BackupValidator(logger: madsci.client.event_client.EventClient | None = None)`
:   Handles backup validation operations.

    Initialize the backup validator.

    Args:
        logger: Optional logger instance

    ### Methods

    `create_backup_metadata(self, backup_path: pathlib.Path, database_version: str | None, backup_type: str, additional_info: Dict[str, Any] | None = None) ‑> Dict[str, Any]`
    :   Create metadata dictionary for a backup.

        Args:
            backup_path: Path to the backup file
            database_version: Version of the database
            backup_type: Type of backup (postgresql, mongodb, etc.)
            additional_info: Additional metadata to include

        Returns:
            Metadata dictionary

    `generate_checksum(self, backup_path: pathlib.Path) ‑> str`
    :   Generate SHA256 checksum for a backup file.

        Args:
            backup_path: Path to the backup file

        Returns:
            SHA256 checksum as hex string

    `load_checksum(self, backup_path: pathlib.Path) ‑> str | None`
    :   Load checksum from file.

        Args:
            backup_path: Path to the backup file

        Returns:
            Checksum string if file exists, None otherwise

    `load_metadata(self, backup_path: pathlib.Path) ‑> Dict[str, Any] | None`
    :   Load metadata from JSON file.

        Args:
            backup_path: Path to the backup file

        Returns:
            Metadata dictionary if file exists, None otherwise

    `save_checksum(self, backup_path: pathlib.Path, checksum: str) ‑> pathlib.Path`
    :   Save checksum to a file alongside the backup.

        Args:
            backup_path: Path to the backup file
            checksum: Checksum to save

        Returns:
            Path to the checksum file

    `save_metadata(self, backup_path: pathlib.Path, metadata: Dict[str, Any]) ‑> pathlib.Path`
    :   Save metadata to a JSON file alongside the backup.

        Args:
            backup_path: Path to the backup file
            metadata: Metadata dictionary to save

        Returns:
            Path to the metadata file

    `validate_backup_comprehensive(self, backup_path: pathlib.Path, expected_database_version: str | None = None, expected_backup_type: str | None = None) ‑> Tuple[bool, Dict[str, Any]]`
    :   Perform comprehensive backup validation.

        Args:
            backup_path: Path to the backup file
            expected_database_version: Expected database version
            expected_backup_type: Expected backup type

        Returns:
            Tuple of (is_valid, validation_result_dict)

    `validate_backup_size(self, backup_path: pathlib.Path, expected_size: int) ‑> bool`
    :   Validate backup file size matches expected size.

        Args:
            backup_path: Path to the backup file
            expected_size: Expected file size in bytes

        Returns:
            True if size matches, False otherwise

    `validate_checksum(self, backup_path: pathlib.Path) ‑> bool`
    :   Validate backup file against its stored checksum.

        Args:
            backup_path: Path to the backup file

        Returns:
            True if checksum is valid, False otherwise

    `validate_sql_backup_structure(self, backup_path: pathlib.Path) ‑> bool`
    :   Validate SQL backup file structure.

        Args:
            backup_path: Path to the SQL backup file

        Returns:
            True if structure is valid, False otherwise

`MongoDBBackupTool(settings: madsci.common.types.backup_types.MongoDBBackupSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Standalone MongoDB backup and restore tool.

    Initialize MongoDB backup tool.

    Args:
        settings: MongoDB backup configuration settings
        logger: Optional logger instance

    ### Ancestors (in MRO)

    * madsci.common.backup_tools.base_backup.AbstractBackupTool
    * abc.ABC

    ### Methods

    `create_backup(self, name_suffix: str | None = None) ‑> pathlib.Path`
    :   Create a MongoDB backup using mongodump.

        Args:
            name_suffix: Optional suffix to add to backup name

        Returns:
            Path to the created backup directory

        Raises:
            RuntimeError: If backup creation fails

    `delete_backup(self, backup_path: pathlib.Path) ‑> None`
    :   Delete a specific backup directory.

        Args:
            backup_path: Path to backup directory to delete

        Raises:
            RuntimeError: If deletion fails

    `restore_from_backup(self, backup_path: pathlib.Path, target_db: str | None = None) ‑> None`
    :   Restore database from a backup directory using mongorestore.

        Args:
            backup_path: Path to backup directory
            target_db: Optional target database name (defaults to original database)

        Raises:
            FileNotFoundError: If backup directory doesn't exist
            RuntimeError: If restore operation fails

    `validate_backup_integrity(self, backup_path: pathlib.Path) ‑> bool`
    :   Validate backup integrity using checksums and restore testing.

        Args:
            backup_path: Path to backup directory

        Returns:
            True if backup is valid, False otherwise

`PostgreSQLBackupTool(settings: madsci.common.types.backup_types.PostgreSQLBackupSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Standalone PostgreSQL backup and restore tool.

    Initialize PostgreSQL backup tool.

    Args:
        settings: PostgreSQL backup configuration
        logger: Optional event client for logging

    ### Ancestors (in MRO)

    * madsci.common.backup_tools.base_backup.AbstractBackupTool
    * abc.ABC
