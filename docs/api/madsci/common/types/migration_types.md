Module madsci.common.types.migration_types
==========================================
Migration tool types for MADSci.

This module defines the types used by the migration tool for upgrading
from the old configuration system (Definition files) to the new system
(Settings + ID Registry).

Classes
-------

`FileMigration(**data: Any)`
:   Migration plan for a single file.
    
    Contains all information needed to migrate a definition file to the new
    configuration system.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `actions: list[madsci.common.types.migration_types.MigrationAction]`
    :

    `backup_path: pathlib.Path | None`
    :

    `component_id: str`
    :

    `component_type: str`
    :

    `errors: list[str]`
    :

    `file_type: madsci.common.types.migration_types.FileType`
    :

    `migrated_at: datetime.datetime | None`
    :

    `model_config`
    :

    `name: str`
    :

    `original_data: dict[str, typing.Any]`
    :

    `output_files: list[pathlib.Path]`
    :

    `source_path: pathlib.Path`
    :

    `status: madsci.common.types.migration_types.MigrationStatus`
    :

`FileType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Type of definition file.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `MANAGER_DEFINITION`
    :

    `NODE_DEFINITION`
    :

`MigrationAction(**data: Any)`
:   A single action in a migration.
    
    Represents one step of the migration process, such as registering an ID
    or generating environment variables.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `action_type: str`
    :

    `description: str`
    :

    `details: dict[str, typing.Any]`
    :

    `model_config`
    :

`MigrationPlan(**data: Any)`
:   Complete migration plan for a project.
    
    Contains all files that need to be migrated and their current status.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created_at: datetime.datetime`
    :

    `files: list[madsci.common.types.migration_types.FileMigration]`
    :

    `model_config`
    :

    `project_dir: pathlib.Path`
    :

    ### Instance variables

    `deprecated_count: int`
    :   Count of deprecated files.

    `failed_count: int`
    :   Count of failed migrations.

    `migrated_count: int`
    :   Count of successfully migrated files.

    `pending_count: int`
    :   Count of files still pending migration.

    `progress_percent: int`
    :   Migration progress as a percentage.

    `total_count: int`
    :   Total count of files in the plan.

`MigrationStatus(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Status of a file's migration.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `DEPRECATED`
    :

    `FAILED`
    :

    `MIGRATED`
    :

    `PENDING`
    :

    `REMOVED`
    :

`OutputFormat(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Output format for migrated configuration files.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `ENV`
    :

    `YAML`
    :