Module madsci.common.backup_tools.postgres_backup
=================================================
Standalone PostgreSQL backup and restore tool for MADSci.

Classes
-------

`BackupLockContext(lock_manager: madsci.common.backup_tools.postgres_backup.BackupLockManager, db_url: str)`
:   Context manager for database backup locks.

    Initialize the backup lock context.

`BackupLockManager()`
:   Manages exclusive locks for backup operations.

    Initialize the backup lock manager.

    ### Methods

    `acquire_lock(self, db_url: str) ‑> madsci.common.backup_tools.postgres_backup.BackupLockContext`
    :   Acquire lock for a specific database URL.

`PostgreSQLBackupTool(settings: madsci.common.types.backup_types.PostgreSQLBackupSettings, logger: madsci.client.event_client.EventClient | None = None)`
:   Standalone PostgreSQL backup and restore tool.

    Initialize PostgreSQL backup tool.

    Args:
        settings: PostgreSQL backup configuration
        logger: Optional event client for logging

    ### Ancestors (in MRO)

    * madsci.common.backup_tools.base_backup.AbstractBackupTool
    * abc.ABC
