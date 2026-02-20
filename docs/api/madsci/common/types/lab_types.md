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

`LabManagerSettings(**kwargs: Any)`
:   Settings for the MADSci Lab.

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

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `dashboard_files_path: str | pathlib.Path | None`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType | None`
    :

    `server_url: pydantic.networks.AnyUrl`
    :
