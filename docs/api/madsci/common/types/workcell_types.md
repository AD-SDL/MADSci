Module madsci.common.types.workcell_types
=========================================
Types for MADSci Workcell configuration.

Classes
-------

`WorkcellInfo(**data: Any)`
:   Runtime info for a MADSci Workcell, stored in Redis for state sharing.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `manager_id: str`
    :

    `model_config`
    :

    `name: str`
    :

    `nodes: dict[str, pydantic.networks.AnyUrl]`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`WorkcellManagerDefinition(**data: Any)`
:   Definition of a MADSci Workcell.
    
    .. deprecated:: 0.7.0
        ``WorkcellManagerDefinition`` is removed in v0.7.0.
        Use ``WorkcellInfo`` for runtime state or ``WorkcellManagerSettings``
        for configuration.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `manager_id: str`
    :

    `manager_type: Literal[<ManagerType.WORKCELL_MANAGER: 'workcell_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

    `nodes: dict[str, pydantic.networks.AnyUrl]`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

    `model_post_init(self, _WorkcellManagerDefinition__context: Any) ‑> None`
    :   Emit deprecation warning on instantiation.

`WorkcellManagerHealth(**data: Any)`
:   Health status for Workcell Manager including Redis connectivity.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `nodes_reachable: int | None`
    :

    `redis_connected: bool | None`
    :

    `total_nodes: int | None`
    :

`WorkcellManagerSettings(**kwargs: Any)`
:   Settings for the MADSci Workcell Manager.
    
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

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `cold_start_delay: int`
    :

    `collection_name: str`
    :

    `database_name: str`
    :

    `document_db_url: pydantic.networks.AnyUrl | None`
    :

    `get_action_result_retries: int`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType | None`
    :

    `node_info_update_interval: float`
    :

    `node_update_interval: float`
    :

    `nodes: dict[str, pydantic.networks.AnyUrl] | None`
    :

    `reconnect_attempt_interval: float`
    :

    `redis_host: str`
    :

    `redis_password: str | None`
    :

    `redis_port: int`
    :

    `scheduler: str`
    :

    `scheduler_update_interval: float`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

    `workcells_directory: str | pathlib.Path | None`
    :

`WorkcellState(**data: Any)`
:   Represents the live state of a MADSci workcell.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `nodes: dict[str, madsci.common.types.node_types.Node]`
    :

    `status: madsci.common.types.workcell_types.WorkcellStatus`
    :

    `workcell_info: madsci.common.types.workcell_types.WorkcellInfo`
    :

    `workflow_queue: list[madsci.common.types.workflow_types.Workflow]`
    :

`WorkcellStatus(**data: Any)`
:   Represents the status of a MADSci workcell.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `errored: bool`
    :

    `errors: list[madsci.common.types.base_types.Error]`
    :

    `initializing: bool`
    :

    `locked: bool`
    :

    `model_config`
    :

    `paused: bool`
    :

    `shutdown: bool`
    :

    ### Static methods

    `ensure_list_of_errors(v: Any) ‑> Any`
    :   Ensure that errors is a list of MADSci Errors

    ### Instance variables

    `ok: bool`
    :   Whether the workcell is in a good state.