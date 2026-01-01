Module madsci.common.backup_tools.mongodb_backup
================================================
Standalone MongoDB backup and restore tool.

Classes
-------

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
