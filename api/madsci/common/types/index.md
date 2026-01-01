Module madsci.common.types
==========================
Common Types for the MADSci Framework.

Sub-modules
-----------
* madsci.common.types.action_types
* madsci.common.types.admin_command_types
* madsci.common.types.auth_types
* madsci.common.types.backup_types
* madsci.common.types.base_types
* madsci.common.types.client_types
* madsci.common.types.condition_types
* madsci.common.types.context_types
* madsci.common.types.datapoint_types
* madsci.common.types.docker_types
* madsci.common.types.event_types
* madsci.common.types.experiment_types
* madsci.common.types.lab_types
* madsci.common.types.location_types
* madsci.common.types.manager_types
* madsci.common.types.mongodb_migration_types
* madsci.common.types.node_types
* madsci.common.types.parameter_types
* madsci.common.types.resource_types
* madsci.common.types.step_types
* madsci.common.types.workcell_types
* madsci.common.types.workflow_types

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
