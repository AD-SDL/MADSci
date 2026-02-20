Module madsci.common.types.backup_types
=======================================
Configuration types for MADSci backup operations.

Classes
-------

`BaseBackupSettings(**kwargs: Any)`
:   Common backup configuration settings.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.backup_types.MongoDBBackupSettings
    * madsci.common.types.backup_types.PostgreSQLBackupSettings

    ### Class variables

    `backup_dir: pathlib.Path`
    :

    `compression: bool`
    :

    `max_backups: int`
    :

    `validate_integrity: bool`
    :

    ### Static methods

    `convert_backup_dir_to_path(v: str | pathlib.Path) ‑> pathlib.Path`
    :   Convert backup_dir to Path object.

`MongoDBBackupSettings(**kwargs: Any)`
:   MongoDB-specific backup settings.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `collections: List[str] | None`
    :

    `database: str | None`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

`PostgreSQLBackupSettings(**kwargs: Any)`
:   PostgreSQL-specific backup settings.

    Initialize settings, optionally with a settings directory.

    When ``_settings_dir`` is provided (or ``MADSCI_SETTINGS_DIR`` is set),
    configuration file paths are resolved via walk-up discovery from that
    directory instead of the current working directory. Each filename walks
    up independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.

    Without either, existing CWD-relative behavior is preserved exactly.

    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_format: str`
    :

    `db_url: str`
    :
