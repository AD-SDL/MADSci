Module madsci.common.types.base_types
=====================================
Base types for MADSci.

Variables
---------

`REDACTED_PLACEHOLDER`
:   Placeholder string used when redacting secret field values.

Functions
---------

`prefixed_alias_generator(prefix: str) ‑> pydantic.aliases.AliasGenerator`
:   Create an AliasGenerator that adds prefixed serialization aliases.
    
    This enables ``model_dump(by_alias=True)`` to produce prefixed keys
    (e.g., ``event_server_url``) while code still uses unprefixed field
    names (e.g., ``server_url``).
    
    Note:
        Only ``serialization_alias`` is set here.  Setting ``validation_alias``
        would override pydantic-settings' ``env_prefix``, causing ``.env`` files
        to lose their per-manager prefixes.  Instead, use
        :func:`prefixed_model_validator` on the settings class to accept
        prefixed keys from YAML or keyword arguments.
    
    Args:
        prefix: The prefix to add (e.g., "event"). Trailing underscores are stripped.
    
    Returns:
        An AliasGenerator that serializes with the prefixed name.

`prefixed_model_validator(prefix: str) ‑> Any`
:   Create a ``model_validator(mode='before')`` that accepts prefixed keys.
    
    When a shared ``settings.yaml`` uses prefixed keys (e.g.,
    ``event_server_url``), this validator strips the prefix so that the
    model can validate them against unprefixed field names (``server_url``).
    
    The validator preserves precedence: if both ``server_url`` and
    ``event_server_url`` are present, the unprefixed value wins (since env
    vars, which have higher priority, are resolved to unprefixed names by
    pydantic-settings' ``env_prefix``).
    
    Usage::
    
        class EventManagerSettings(ManagerSettings, env_prefix="EVENT_", ...):
            model_config = SettingsConfigDict(
                alias_generator=prefixed_alias_generator("event"),
                populate_by_name=True,
            )
            _accept_prefixed_keys = prefixed_model_validator("event")
    
    Args:
        prefix: The prefix to strip (e.g., "event"). Trailing underscores
            are stripped; matching is case-insensitive.
    
    Returns:
        A decorated classmethod suitable for use as a Pydantic model validator.

Classes
-------

`Error(**data: Any)`
:   A MADSci Error
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `error_type: str | None`
    :

    `logged_at: datetime.datetime`
    :

    `message: str | None`
    :

    `model_config`
    :

    ### Static methods

    `from_exception(exception: Exception) ‑> madsci.common.types.base_types.Error`
    :   Create an error from an exception.

`MadsciBaseModel(**data: Any)`
:   Parent class for all MADSci data models.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.backup_tools.base_backup.BackupInfo
    * madsci.common.testing.types.E2ETestCleanup
    * madsci.common.testing.types.E2ETestDefinition
    * madsci.common.testing.types.E2ETestRequirements
    * madsci.common.testing.types.E2ETestResult
    * madsci.common.testing.types.E2ETestStep
    * madsci.common.testing.types.StepResult
    * madsci.common.testing.types.ValidationConfig
    * madsci.common.testing.types.ValidationResult
    * madsci.common.testing.types.WaitConfig
    * madsci.common.types.action_types.ActionDatapoints
    * madsci.common.types.action_types.ActionDefinition
    * madsci.common.types.action_types.ActionFiles
    * madsci.common.types.action_types.ActionJSON
    * madsci.common.types.action_types.ActionRequest
    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.action_types.ActionResultDefinition
    * madsci.common.types.action_types.ArgumentDefinition
    * madsci.common.types.action_types.RestActionRequest
    * madsci.common.types.admin_command_types.AdminCommandResponse
    * madsci.common.types.auth_types.OwnershipInfo
    * madsci.common.types.auth_types.ProjectInfo
    * madsci.common.types.auth_types.UserInfo
    * madsci.common.types.base_types.Error
    * madsci.common.types.condition_types.Condition
    * madsci.common.types.datapoint_types.DataPoint
    * madsci.common.types.event_types.EmailAlertsConfig
    * madsci.common.types.event_types.Event
    * madsci.common.types.event_types.NodeUtilizationData
    * madsci.common.types.event_types.SystemUtilizationData
    * madsci.common.types.experiment_types.Experiment
    * madsci.common.types.experiment_types.ExperimentDesign
    * madsci.common.types.experiment_types.ExperimentRegistration
    * madsci.common.types.experiment_types.ExperimentalCampaign
    * madsci.common.types.location_types.CapacityCostConfig
    * madsci.common.types.location_types.Location
    * madsci.common.types.location_types.LocationArgument
    * madsci.common.types.location_types.LocationDefinition
    * madsci.common.types.location_types.LocationReservation
    * madsci.common.types.location_types.LocationTransferCapabilities
    * madsci.common.types.location_types.TransferGraphEdge
    * madsci.common.types.location_types.TransferStepTemplate
    * madsci.common.types.location_types.TransferTemplateOverrides
    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.migration_types.FileMigration
    * madsci.common.types.migration_types.MigrationAction
    * madsci.common.types.migration_types.MigrationPlan
    * madsci.common.types.node_types.Node
    * madsci.common.types.node_types.NodeClientCapabilities
    * madsci.common.types.node_types.NodeDefinition
    * madsci.common.types.node_types.NodeReservation
    * madsci.common.types.node_types.NodeSetConfigResponse
    * madsci.common.types.node_types.NodeStatus
    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.registry_types.LocalRegistry
    * madsci.common.types.registry_types.RegistryEntry
    * madsci.common.types.registry_types.RegistryLock
    * madsci.common.types.registry_types.RegistryResolveResult
    * madsci.common.types.resource_types.custom_types.CustomResourceAttributeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.resource_types.definitions.TemplateDefinition
    * madsci.common.types.resource_types.server_types.ResourceHierarchy
    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.step_types.StepDefinition
    * madsci.common.types.step_types.StepParameters
    * madsci.common.types.template_types.GeneratedProject
    * madsci.common.types.template_types.ParameterChoice
    * madsci.common.types.template_types.TemplateFile
    * madsci.common.types.template_types.TemplateHook
    * madsci.common.types.template_types.TemplateInfo
    * madsci.common.types.template_types.TemplateManifest
    * madsci.common.types.template_types.TemplateParameter
    * madsci.common.types.workcell_types.WorkcellInfo
    * madsci.common.types.workcell_types.WorkcellManagerDefinition
    * madsci.common.types.workcell_types.WorkcellState
    * madsci.common.types.workcell_types.WorkcellStatus
    * madsci.common.types.workflow_types.SchedulerMetadata
    * madsci.common.types.workflow_types.WorkflowDefinition
    * madsci.common.types.workflow_types.WorkflowMetadata
    * madsci.common.types.workflow_types.WorkflowParameters
    * madsci.common.types.workflow_types.WorkflowStatus

    ### Class variables

    `model_config`
    :

    ### Static methods

    `from_yaml(path: str | pathlib.Path) ‑> ~_T`
    :   Allows all derived data models to be loaded from yaml.

    ### Methods

    `model_dump_safe(self, include_secrets: bool = False, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Dump model data with secret fields redacted by default.
        
        This method provides a safe way to export model data without
        accidentally exposing sensitive values. Secret fields are identified
        by:
        - Fields typed as ``SecretStr`` / ``SecretBytes``
        - Fields with ``json_schema_extra={"secret": True}`` metadata
        
        Args:
            include_secrets: If True, include actual secret values.
                Defaults to False (secrets are replaced with
                ``***REDACTED***``).
            **kwargs: Additional keyword arguments forwarded to
                ``model_dump(mode="json", ...)``.
        
        Returns:
            dict: Model data with secrets redacted unless
                ``include_secrets=True``.

    `model_dump_yaml(self, include_secrets: bool = True) ‑> str`
    :   Convert the model to a YAML string.
        
        Args:
            include_secrets: If False, redact secret field values.
        
        Returns:
            YAML string representation of the model

    `to_mongo(self) ‑> dict[str, typing.Any]`
    :   Convert the model to a MongoDB-compatible dictionary.

    `to_yaml(self, path: str | pathlib.Path, include_secrets: bool = True, **kwargs: Any) ‑> None`
    :   Export the model to a YAML file.
        
        Args:
            path: File path to write to.
            include_secrets: If False, redact secret field values.
                Defaults to True for backwards compatibility with
                internal serialization (e.g., definition file round-trips).
            **kwargs: Additional keyword arguments forwarded to
                ``model_dump``.

`MadsciBaseSettings(**kwargs: Any)`
:   Base class for all MADSci settings.
    
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

    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.context_types.MadsciContext
    * madsci.common.types.datapoint_types.ObjectStorageSettings
    * madsci.common.types.docker_types.DockerComposeSettings
    * madsci.common.types.interface_types.InterfaceSettings
    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.module_types.ModuleSettings
    * madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings
    * madsci.common.types.node_types.NodeConfig
    * madsci.experiment_application.experiment_base.ExperimentBaseConfig
    * madsci.resource_manager.migration_tool.DatabaseMigrationSettings

    ### Class variables

    `model_config: pydantic_settings.main.SettingsConfigDict`
    :   Configuration for the settings model.

    ### Static methods

    `settings_customise_sources(settings_cls: type[pydantic_settings.main.BaseSettings], init_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, env_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, dotenv_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, file_secret_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource) ‑> tuple[pydantic_settings.sources.base.PydanticBaseSettingsSource, ...]`
    :   Sets the order of settings sources for the settings model.
        
        File paths are resolved with walk-up discovery from the settings
        directory (defaulting to CWD). Each filename walks up independently,
        so shared configs in parent directories are found automatically.

    ### Methods

    `model_dump_safe(self, include_secrets: bool = False, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Dump settings data with secret fields redacted by default.
        
        Secret fields are identified by ``json_schema_extra={"secret": True}``
        or ``SecretStr`` / ``SecretBytes`` type annotations. Nested models
        are recursively redacted.
        
        Args:
            include_secrets: If True, include actual secret values.
            **kwargs: Additional keyword arguments forwarded to ``model_dump``.
        
        Returns:
            dict: Settings with secrets redacted unless ``include_secrets=True``.

`MadsciDeveloperSettings(**values: Any)`
:   Developer-focused settings for MADSci behavior.
    
    These settings control development experience features like rich tracebacks.
    All settings use the MADSCI_ prefix for environment variables.
    
    Environment Variables:
        MADSCI_DISABLE_RICH_TRACEBACKS: Set to true to disable rich tracebacks
            (default: false, rich tracebacks are enabled)
        MADSCI_RICH_TRACEBACKS_SHOW_LOCALS: Set to true to show local variables
            in tracebacks (default: false for security - can leak secrets)
    
    Note:
        show_locals is disabled by default to prevent accidental exposure of
        sensitive data (tokens, passwords) that may be present in local variables
        during exceptions.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `disable_rich_tracebacks: bool`
    :

    `model_config: ClassVar[pydantic_settings.main.SettingsConfigDict]`
    :

    `rich_tracebacks_show_locals: bool`
    :

`MadsciSQLModel(**data: Any)`
:   Parent class for all MADSci data models that are SQLModel-based.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.definitions.CustomResourceAttributeDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.resource_manager.resource_tables.SchemaVersionTable

    ### Class variables

    `model_config`
    :   Configuration for the SQLModel model.

    ### Static methods

    `from_yaml(path: str | pathlib.Path) ‑> ~_T`
    :   Allows all derived data models to be loaded from yaml.

    ### Methods

    `to_yaml(self, path: str | pathlib.Path, **kwargs: Any) ‑> None`
    :   Allows all derived data models to be exported into yaml.
        
        kwargs are passed to model_dump