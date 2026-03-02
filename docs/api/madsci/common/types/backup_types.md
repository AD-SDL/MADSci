Module madsci.common.types.backup_types
=======================================
Configuration types for MADSci backup operations.

Classes
-------

`BaseBackupSettings(**kwargs: Any)`
:   Common backup configuration settings.
    
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

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_format: str`
    :

    `db_url: str`
    :