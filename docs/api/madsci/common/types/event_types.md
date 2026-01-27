Module madsci.common.types.event_types
======================================
Event types for the MADSci system.

Classes
-------

`EmailAlertsConfig(**data: Any)`
:   Configuration for sending emails.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `default_importance: str`
    :

    `email_addresses: list[str]`
    :

    `model_config`
    :

    `sender: str`
    :

    `smtp_password: str | None`
    :

    `smtp_port: int`
    :

    `smtp_server: str`
    :

    `smtp_username: str | None`
    :

    `use_tls: bool`
    :

`Event(**data: Any)`
:   An event in the MADSci system.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `alert: bool`
    :

    `event_data: Any`
    :

    `event_id: str`
    :

    `event_timestamp: datetime.datetime`
    :

    `event_type: madsci.common.types.event_types.EventType`
    :

    `log_level: madsci.common.types.event_types.EventLogLevel`
    :

    `model_config`
    :

    `source: madsci.common.types.auth_types.OwnershipInfo`
    :

    ### Static methods

    `object_id_to_str(v: str | bson.objectid.ObjectId) ‑> str`
    :   Cast ObjectID to string.

`EventClientConfig(**values: Any)`
:   Configuration for an Event Client.

    Inherits all HTTP client configuration from MadsciClientConfig including:
    - Retry configuration (retry_enabled, retry_total, retry_backoff_factor, etc.)
    - Timeout configuration (timeout_default, timeout_data_operations, etc.)
    - Connection pooling (pool_connections, pool_maxsize)
    - Rate limiting (rate_limit_tracking_enabled, rate_limit_warning_threshold, etc.)

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `event_server_url: pydantic.networks.AnyUrl | None`
    :

    `log_dir: str | pathlib.Path`
    :

    `log_level: int | madsci.common.types.event_types.EventLogLevel`
    :

    `name: str | None`
    :

    `source: madsci.common.types.auth_types.OwnershipInfo`
    :

`EventLogLevel(*args, **kwds)`
:   The log level of an event.

    ### Ancestors (in MRO)

    * builtins.int
    * enum.Enum

    ### Class variables

    `CRITICAL`
    :

    `DEBUG`
    :

    `ERROR`
    :

    `INFO`
    :

    `NOTSET`
    :

    `WARNING`
    :

`EventManagerDefinition(**data: Any)`
:   Definition for a Squid Event Manager

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `manager_id: str`
    :

    `manager_type: Literal[<ManagerType.EVENT_MANAGER: 'event_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

`EventManagerHealth(**data: Any)`
:   Health status for Event Manager including database connectivity.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `db_connected: bool | None`
    :

    `model_config`
    :

    `total_events: int | None`
    :

`EventManagerSettings(**values: Any)`
:   Handles settings and configuration for the Event Manager.

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

    `alert_level: madsci.common.types.event_types.EventLogLevel`
    :

    `collection_name: str`
    :

    `database_name: str`
    :

    `email_alerts: madsci.common.types.event_types.EmailAlertsConfig | None`
    :

    `manager_definition: str | pathlib.Path`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

    `server_url: pydantic.networks.AnyUrl | None`
    :

`EventType(*args, **kwds)`
:   The type of an event.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `ACTION_STATUS_CHANGE`
    :

    `CAMPAIGN_ABORT`
    :

    `CAMPAIGN_COMPLETE`
    :

    `CAMPAIGN_CREATE`
    :

    `CAMPAIGN_START`
    :

    `EXPERIMENT_CANCELLED`
    :

    `EXPERIMENT_COMPLETE`
    :

    `EXPERIMENT_CONTINUED`
    :

    `EXPERIMENT_CREATE`
    :

    `EXPERIMENT_FAILED`
    :

    `EXPERIMENT_PAUSE`
    :

    `EXPERIMENT_START`
    :

    `LAB_CREATE`
    :

    `LAB_START`
    :

    `LAB_STOP`
    :

    `LOG`
    :

    `LOG_CRITICAL`
    :

    `LOG_DEBUG`
    :

    `LOG_ERROR`
    :

    `LOG_INFO`
    :

    `LOG_WARNING`
    :

    `NODE_CONFIG_UPDATE`
    :

    `NODE_CREATE`
    :

    `NODE_ERROR`
    :

    `NODE_START`
    :

    `NODE_STATUS_UPDATE`
    :

    `NODE_STOP`
    :

    `TEST`
    :

    `UNKNOWN`
    :

    `WORKCELL_CONFIG_UPDATE`
    :

    `WORKCELL_CREATE`
    :

    `WORKCELL_START`
    :

    `WORKCELL_STATUS_UPDATE`
    :

    `WORKCELL_STOP`
    :

    `WORKFLOW_ABORT`
    :

    `WORKFLOW_COMPLETE`
    :

    `WORKFLOW_CREATE`
    :

    `WORKFLOW_START`
    :

`NodeUtilizationData(**data: Any)`
:   Utilization data for a single node.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `active_actions: set[str]`
    :

    `active_state: str`
    :

    `active_time: float`
    :

    `busy_time: float`
    :

    `current_state: str`
    :

    `error_time: float`
    :

    `idle_time: float`
    :

    `inactive_time: float`
    :

    `last_active_change: datetime.datetime | None`
    :

    `last_state_change: datetime.datetime | None`
    :

    `model_config`
    :

    `node_id: str`
    :

    `total_time: float`
    :

    `utilization_percentage: float`
    :

`SystemUtilizationData(**data: Any)`
:   System-wide utilization data.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `active_experiments: set[str]`
    :

    `active_time: float`
    :

    `active_workflows: set[str]`
    :

    `current_state: str`
    :

    `idle_time: float`
    :

    `last_state_change: datetime.datetime | None`
    :

    `model_config`
    :

    `total_time: float`
    :

    `utilization_percentage: float`
    :
