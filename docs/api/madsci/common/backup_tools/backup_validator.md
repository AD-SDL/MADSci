Module madsci.common.backup_tools.backup_validator
==================================================
Backup validation utilities and classes.

Classes
-------

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
