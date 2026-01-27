Module madsci.common.types.manager_types
========================================
Types used primarily by MADSci Managers.

Classes
-------

`ManagerDefinition(**data: Any)`
:   Definition for a MADSci Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.datapoint_types.DataManagerDefinition
    * madsci.common.types.event_types.EventManagerDefinition
    * madsci.common.types.experiment_types.ExperimentManagerDefinition
    * madsci.common.types.lab_types.LabManagerDefinition
    * madsci.common.types.location_types.LocationManagerDefinition
    * madsci.common.types.resource_types.definitions.ResourceManagerDefinition

    ### Class variables

    `description: str | None`
    :

    `manager_id: str`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType`
    :

    `model_config`
    :

    `name: str`
    :

`ManagerHealth(**data: Any)`
:   Base health status for MADSci Manager services.

    This class provides common health check fields that all managers need.
    Manager-specific health classes should inherit from this class and add
    additional fields for database connections, external dependencies, etc.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.datapoint_types.DataManagerHealth
    * madsci.common.types.event_types.EventManagerHealth
    * madsci.common.types.experiment_types.ExperimentManagerHealth
    * madsci.common.types.lab_types.LabHealth
    * madsci.common.types.location_types.LocationManagerHealth
    * madsci.common.types.resource_types.definitions.ResourceManagerHealth
    * madsci.common.types.workcell_types.WorkcellManagerHealth

    ### Class variables

    `description: str | None`
    :

    `healthy: bool`
    :

    `model_config`
    :

`ManagerSettings(**values: Any)`
:   Base settings class for MADSci Manager services.

    This class provides common configuration fields that all managers need,
    such as server URL and manager definition file path.

    Manager-specific settings classes should inherit from this class and:
    1. Add their specific configuration parameters
    2. Set appropriate env_prefix, env_file, toml_file, etc. parameters
    3. Override default values as needed (especially server_url default port)

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.datapoint_types.DataManagerSettings
    * madsci.common.types.event_types.EventManagerSettings
    * madsci.common.types.experiment_types.ExperimentManagerSettings
    * madsci.common.types.lab_types.LabManagerSettings
    * madsci.common.types.location_types.LocationManagerSettings
    * madsci.common.types.resource_types.definitions.ResourceManagerSettings
    * madsci.common.types.workcell_types.WorkcellManagerSettings

    ### Class variables

    `manager_definition: str | pathlib.Path`
    :

    `rate_limit_cleanup_interval: int`
    :

    `rate_limit_enabled: bool`
    :

    `rate_limit_exempt_ips: list[str] | None`
    :

    `rate_limit_requests: int`
    :

    `rate_limit_short_requests: int | None`
    :

    `rate_limit_short_window: int | None`
    :

    `rate_limit_window: int`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

    `uvicorn_limit_concurrency: int | None`
    :

    `uvicorn_limit_max_requests: int | None`
    :

    `uvicorn_workers: int | None`
    :

`ManagerType(*args, **kwds)`
:   Types of Squid Managers.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `AUTH_MANAGER`
    :

    `DATA_MANAGER`
    :

    `EVENT_MANAGER`
    :

    `EXPERIMENT_MANAGER`
    :

    `LAB_MANAGER`
    :

    `LOCATION_MANAGER`
    :

    `RESOURCE_MANAGER`
    :

    `TRANSFER_MANAGER`
    :

    `WORKCELL_MANAGER`
    :
