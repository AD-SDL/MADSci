Module madsci.common.types.base_types
=====================================
Base types for MADSci.

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
    * madsci.common.types.node_types.Node
    * madsci.common.types.node_types.NodeClientCapabilities
    * madsci.common.types.node_types.NodeDefinition
    * madsci.common.types.node_types.NodeReservation
    * madsci.common.types.node_types.NodeSetConfigResponse
    * madsci.common.types.node_types.NodeStatus
    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.resource_types.custom_types.CustomResourceAttributeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.resource_types.definitions.TemplateDefinition
    * madsci.common.types.resource_types.server_types.ResourceHierarchy
    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.step_types.StepDefinition
    * madsci.common.types.step_types.StepParameters
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

    `model_dump_yaml(self) ‑> str`
    :   Convert the model to a YAML string.

        Returns:
            YAML string representation of the model

    `to_mongo(self) ‑> dict[str, typing.Any]`
    :   Convert the model to a MongoDB-compatible dictionary.

    `to_yaml(self, path: str | pathlib.Path, **kwargs: Any) ‑> None`
    :   Allows all derived data models to be exported into yaml.

        kwargs are passed to model_dump

`MadsciBaseSettings(**values: Any)`
:   Base class for all MADSci settings.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.backup_types.BaseBackupSettings
    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.context_types.MadsciContext
    * madsci.common.types.datapoint_types.ObjectStorageSettings
    * madsci.common.types.docker_types.DockerComposeSettings
    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.mongodb_migration_types.MongoDBMigrationSettings
    * madsci.common.types.node_types.NodeConfig
    * madsci.resource_manager.migration_tool.DatabaseMigrationSettings

    ### Class variables

    `model_config: pydantic_settings.main.SettingsConfigDict`
    :   Configuration for the settings model.

    ### Static methods

    `settings_customise_sources(settings_cls: type[pydantic_settings.main.BaseSettings], init_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, env_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, dotenv_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource, file_secret_settings: pydantic_settings.sources.base.PydanticBaseSettingsSource) ‑> tuple[pydantic_settings.sources.base.PydanticBaseSettingsSource, ...]`
    :   Sets the order of settings sources for the settings model.

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
