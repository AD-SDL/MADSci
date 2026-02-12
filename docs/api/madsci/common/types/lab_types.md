Module madsci.common.types.lab_types
====================================
Types for MADSci Squid Lab configuration.

Classes
-------

`LabHealth(**data: Any)`
:   Health status for Lab Manager including status of other managers in the lab.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `healthy_managers: int | None`
    :

    `managers: dict[str, madsci.common.types.manager_types.ManagerHealth] | None`
    :

    `model_config`
    :

    `total_managers: int | None`
    :

`LabManagerDefinition(**data: Any)`
:   Definition for a MADSci Lab Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `manager_id: str`
    :

    `manager_type: Literal[<ManagerType.LAB_MANAGER: 'lab_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

`LabManagerSettings(**values: Any)`
:   Settings for the MADSci Lab.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `dashboard_files_path: str | pathlib.Path | None`
    :

    `manager_definition: str | pathlib.Path`
    :

    `server_url: pydantic.networks.AnyUrl`
    :
