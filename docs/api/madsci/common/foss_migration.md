Module madsci.common.foss_migration
===================================
FOSS stack migration tool for MADSci.

Migrates data from the old proprietary infrastructure (MongoDB, Redis, MinIO)
to the new FOSS alternatives (FerretDB, Valkey, SeaweedFS).

Classes
-------

`FossMigrationReport(**data: Any)`
:   Aggregate report for a full FOSS migration run.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `finished_at: datetime.datetime | None`
    :

    `model_config`
    :

    `started_at: datetime.datetime`
    :

    `steps: List[madsci.common.foss_migration.FossMigrationStepResult]`
    :

    ### Instance variables

    `all_succeeded: bool`
    :   Return True if every step succeeded.

    `total_duration_seconds: float`
    :   Total wall-clock duration of all steps.

`FossMigrationSettings(**kwargs: Any)`
:   Settings for the FOSS stack migration tool.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_dir: pathlib.Path`
    :

    `compose_dir: pathlib.Path`
    :

    `compose_files: List[str]`
    :

    `document_db_databases: List[str]`
    :

    `migration_compose_files: List[str]`
    :

    `minio_access_key: str`
    :

    `minio_secret_key: str`
    :

    `new_document_db_url: pydantic.networks.AnyUrl`
    :

    `new_postgres_url: str`
    :

    `new_seaweedfs_url: pydantic.networks.AnyUrl`
    :

    `old_container_services: List[str]`
    :

    `old_document_db_url: pydantic.networks.AnyUrl`
    :

    `old_minio_url: pydantic.networks.AnyUrl`
    :

    `old_postgres_url: str`
    :

    `seaweedfs_access_key: str`
    :

    `seaweedfs_secret_key: str`
    :

`FossMigrationStepResult(**data: Any)`
:   Result of a single migration step.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `details: dict | None`
    :

    `duration_seconds: float`
    :

    `error: str | None`
    :

    `message: str`
    :

    `model_config`
    :

    `step: str`
    :

    `success: bool`
    :

`FossMigrationTool(settings: madsci.common.foss_migration.FossMigrationSettings | None = None, logger: madsci.client.event_client.EventClient | None = None)`
:   Orchestrates migration from proprietary to FOSS infrastructure.
    
    Initialize the FOSS migration tool.

    ### Class variables

    `STEP_METHODS: ClassVar[Dict[str, str]]`
    :

    ### Methods

    `build_mongodump_command(self, database: str) ‑> list[str]`
    :   Build a mongodump command for the given database on the *old* server.

    `build_mongorestore_command(self, database: str, dump_path: str) ‑> list[str]`
    :   Build a mongorestore command targeting the *new* FerretDB instance.

    `build_pg_dump_command(self) ‑> list[str]`
    :   Build a pg_dump command for the old PostgreSQL database.

    `build_pg_restore_command(self, dump_file: str) ‑> list[str]`
    :   Build a pg_restore command for the new PostgreSQL database.

    `check_prerequisites(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Validate that required CLI tools are available.

    `create_pre_migration_backup(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Create filesystem-level copies of old data directories.

    `detect_old_data(self) ‑> dict[str, bool]`
    :   Check which old data directories exist.
        
        Returns a dict mapping component name to whether data was found.

    `migrate_document_databases(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Migrate all configured document databases from MongoDB to FerretDB.

    `migrate_minio_to_seaweedfs(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Copy objects from MinIO to SeaweedFS via the S3-compatible SDK.

    `migrate_postgresql(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Migrate PostgreSQL data from old instance to new instance.

    `migrate_redis_to_valkey(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Report that Redis data migration is not needed.
        
        Redis/Valkey data in MADSci is ephemeral (workcell state, location
        caches) and is repopulated automatically by the managers on startup.
        Additionally, Redis 7.4 uses RDB format v12 which is incompatible
        with Valkey 8 (forked from Redis 7.2, RDB v11), so file-level or
        DUMP/RESTORE migration is not possible.

    `run_full_migration(self, *, skip_backup: bool = False, skip_docker: bool = False, steps: List[str] | None = None) ‑> madsci.common.foss_migration.FossMigrationReport`
    :   Run the full migration pipeline.
        
        Args:
            skip_backup: Skip creating a pre-migration backup.
            skip_docker: Skip starting/stopping old containers.
            steps: If provided, only run these steps (choices from STEP_METHODS).
                   Defaults to all steps.

    `start_foss_stack(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Start the new FOSS infrastructure stack (FerretDB, Valkey, etc.).

    `start_old_containers(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Start old MongoDB and PostgreSQL containers via Docker Compose.

    `stop_old_containers(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Stop and remove old migration containers.

    `verify_migration(self) ‑> madsci.common.foss_migration.FossMigrationStepResult`
    :   Connect to each new service and verify data presence.