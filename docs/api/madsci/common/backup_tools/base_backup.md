Module madsci.common.backup_tools.base_backup
=============================================
Abstract base classes and shared utilities for backup operations.

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
