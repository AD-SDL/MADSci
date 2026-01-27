Module madsci.common.types.backup_types
=======================================
Configuration types for MADSci backup operations.

Classes
-------

`BaseBackupSettings(**values: Any)`
:   Common backup configuration settings.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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

`MongoDBBackupSettings(**values: Any)`
:   MongoDB-specific backup settings.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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

`PostgreSQLBackupSettings(**values: Any)`
:   PostgreSQL-specific backup settings.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

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
