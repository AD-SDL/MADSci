Module madsci.common.types.node_types
=====================================
MADSci Node Types.

Classes
-------

`Node(**data: Any)`
:   A runtime representation of a MADSci Node used in a Workcell.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `info: madsci.common.types.node_types.NodeInfo | None`
    :

    `model_config`
    :

    `node_url: pydantic.networks.AnyUrl`
    :

    `reservation: madsci.common.types.node_types.NodeReservation | None`
    :

    `state: dict[str, typing.Any] | None`
    :

    `status: madsci.common.types.node_types.NodeStatus | None`
    :

`NodeCapabilities(**data: Any)`
:   Capabilities of a MADSci Node.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.node_types.NodeClientCapabilities
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `admin_commands: set[madsci.common.types.admin_command_types.AdminCommands]`
    :

    `events: bool | None`
    :

    `model_config`
    :

    `resources: bool | None`
    :

    ### Methods

    `order_admin_commands(self, admin_commands: set[madsci.common.types.admin_command_types.AdminCommands]) ‑> list[madsci.common.types.admin_command_types.AdminCommands]`
    :   Ensure sorted admin commands.

`NodeClientCapabilities(**data: Any)`
:   Capabilities of a MADSci Node Client. Default values are None, meaning the capability is not explicitly set. If a capability is set to False, it is explicitly not supported.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.node_types.NodeCapabilities

    ### Class variables

    `action_files: bool | None`
    :

    `get_action_history: bool | None`
    :

    `get_action_result: bool | None`
    :

    `get_action_status: bool | None`
    :

    `get_info: bool | None`
    :

    `get_log: bool | None`
    :

    `get_resources: bool | None`
    :

    `get_state: bool | None`
    :

    `get_status: bool | None`
    :

    `model_config`
    :

    `send_action: bool | None`
    :

    `send_admin_commands: bool | None`
    :

    `set_config: bool | None`
    :

    ### Methods

    `exclude_unset_by_default(self, nxt: pydantic_core.core_schema.SerializerFunctionWrapHandler, info: pydantic_core.core_schema.SerializationInfo) ‑> dict[str, typing.Any]`
    :   Exclude unset fields by default.

`NodeConfig(**kwargs: Any)`
:   Basic Configuration for a MADSci Node.

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

    * madsci.common.types.node_types.RestNodeConfig

    ### Class variables

    `module_name: str | None`
    :

    `module_version: str | None`
    :

    `node_id: str | None`
    :

    `node_name: str | None`
    :

    `node_type: madsci.common.types.node_types.NodeType | None`
    :

    `state_update_interval: float | None`
    :

    `status_update_interval: float | None`
    :

`NodeDefinition(**data: Any)`
:   Definition of a MADSci Node, a unique instance of a MADSci Node Module.

    .. deprecated:: 0.7.0
        Definition files are removed. Use :class:`NodeConfig` instead.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.node_types.NodeInfo

    ### Class variables

    `capabilities: madsci.common.types.node_types.NodeCapabilities | None`
    :

    `model_config`
    :

    `module_name: str`
    :

    `module_version: pydantic_extra_types.semantic_version.SemanticVersion`
    :

    `node_description: str | None`
    :

    `node_id: str`
    :

    `node_name: str`
    :

    `node_type: madsci.common.types.node_types.NodeType`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

    `model_post_init(self, _NodeDefinition__context: Any) ‑> None`
    :   Emit deprecation warning when NodeDefinition is instantiated directly.

`NodeInfo(**data: Any)`
:   Information about a MADSci Node.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.node_types.NodeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `actions: dict[str, 'ActionDefinition']`
    :

    `config: Any | None`
    :

    `config_schema: dict[str, typing.Any] | None`
    :

    `model_config`
    :

    `node_url: pydantic.networks.AnyUrl | None`
    :

    ### Static methods

    `from_config(config: madsci.common.types.node_types.NodeConfig, *, node_name: str | None = None, module_name: str | None = None, module_version: str | None = None, node_definition: madsci.common.types.node_types.NodeDefinition | None = None) ‑> madsci.common.types.node_types.NodeInfo`
    :   Create a NodeInfo from settings and optional module metadata.

        This factory builds a NodeInfo from ``NodeConfig`` settings fields
        without requiring a separate ``NodeDefinition`` file.  Identity
        fields are resolved with the following priority:

        1. Explicit keyword arguments (``node_name``, ``module_name``, etc.)
        2. Values from ``config`` identity fields (if set)
        3. Values from ``node_definition`` (if provided, for backwards compat)
        4. Sensible defaults

        Args:
            config: The node's configuration settings.
            node_name: Explicit node name override.
            module_name: Explicit module name override.
            module_version: Explicit module version override.
            node_definition: Optional legacy definition for backwards compat.

        Returns:
            NodeInfo: A new NodeInfo instance.

    `from_node_def_and_config(node: madsci.common.types.node_types.NodeDefinition, config: madsci.common.types.node_types.NodeConfig | None = None) ‑> madsci.common.types.node_types.NodeInfo`
    :   Create a NodeInfo from a NodeDefinition and config.

        .. deprecated:: 0.7.0
            Use :meth:`from_config` when possible. This method is maintained
            for backwards compatibility with existing code that passes a
            ``NodeDefinition`` object.

`NodeReservation(**data: Any)`
:   Reservation of a MADSci Node.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created: datetime.datetime`
    :

    `end: datetime.datetime`
    :

    `model_config`
    :

    `owned_by: madsci.common.types.auth_types.OwnershipInfo`
    :

    `start: datetime.datetime`
    :

    ### Methods

    `check(self, ownership: madsci.common.types.auth_types.OwnershipInfo) ‑> bool`
    :   Check if the reservation is 1.) active or not, and 2.) owned by the given ownership.

`NodeSetConfigResponse(**data: Any)`
:   Response from a Node Set Config Request

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

    `success: bool`
    :

`NodeStatus(**data: Any)`
:   Status of a MADSci Node.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `busy: bool`
    :

    `config_values: dict[str, typing.Any]`
    :

    `disconnected: bool`
    :

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

    `running_actions: set[str]`
    :

    `stopped: bool`
    :

    `waiting_for_config: set[str]`
    :

    ### Instance variables

    `description: str`
    :   A description of the node's status.

    `ready: bool`
    :   Whether the node is ready to accept actions.

`NodeType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   The type of a MADSci node.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `COMPUTE`
    :

    `DATA_MANAGER`
    :

    `DEVICE`
    :

    `EVENT_MANAGER`
    :

    `RESOURCE_MANAGER`
    :

    `TRANSFER_MANAGER`
    :

    `WORKCELL_MANAGER`
    :

`RestNodeConfig(**kwargs: Any)`
:   Default Configuration for a MADSci Node that communicates over REST.

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

    * madsci.common.types.node_types.NodeConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.experiment_application.experiment_application.ExperimentApplicationConfig

    ### Class variables

    `enable_rate_limiting: bool`
    :

    `node_url: pydantic.networks.AnyUrl`
    :

    `rate_limit_cleanup_interval: int`
    :

    `rate_limit_requests: int`
    :

    `rate_limit_short_requests: int | None`
    :

    `rate_limit_short_window: int | None`
    :

    `rate_limit_window: int`
    :

    `uvicorn_kwargs: dict[str, typing.Any]`
    :
