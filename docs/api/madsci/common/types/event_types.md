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

    `archived: bool`
    :

    `archived_at: datetime.datetime | None`
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

    `span_id: str | None`
    :

    `trace_id: str | None`
    :

    ### Static methods

    `object_id_to_str(v: str | bson.objectid.ObjectId) ‑> str`
    :   Cast ObjectID to string.

`EventClientConfig(**kwargs: Any)`
:   Configuration for an Event Client.

    Inherits all HTTP client configuration from MadsciClientConfig including:
    - Retry configuration (retry_enabled, retry_total, retry_backoff_factor, etc.)
    - Timeout configuration (timeout_default, timeout_data_operations, etc.)
    - Connection pooling (pool_connections, pool_maxsize)
    - Rate limiting (rate_limit_tracking_enabled, rate_limit_warning_threshold, etc.)

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

    * madsci.common.types.client_types.MadsciClientConfig
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `event_server_url: pydantic.networks.AnyUrl | None`
    :

    `fail_on_error: bool`
    :

    `log_backup_count: int`
    :

    `log_compression_enabled: bool`
    :

    `log_dir: str | pathlib.Path`
    :

    `log_level: int | madsci.common.types.event_types.EventLogLevel`
    :

    `log_max_bytes: int`
    :

    `log_output_format: Literal['json', 'console']`
    :

    `log_rotation_interval: int`
    :

    `log_rotation_type: Literal['size', 'time', 'none']`
    :

    `log_rotation_when: str`
    :

    `name: str | None`
    :

    `otel_enabled: bool`
    :

    `otel_endpoint: str | None`
    :

    `otel_exporter: Literal['console', 'otlp', 'none']`
    :

    `otel_metric_export_interval_ms: int`
    :

    `otel_protocol: Literal['grpc', 'http']`
    :

    `otel_service_name: str | None`
    :

    `source: madsci.common.types.auth_types.OwnershipInfo`
    :

    ### Static methods

    `validate_log_rotation_type(v: str) ‑> str`
    :   Validate that log_rotation_type is a valid value.

    `validate_log_rotation_when(v: str) ‑> str`
    :   Validate that log_rotation_when is a valid value for TimedRotatingFileHandler.

    `validate_otel_endpoint(v: str | None) ‑> str | None`
    :   Validate OTLP endpoint format and normalize trailing slash.

`EventClientContext(client: EventClient, hierarchy: list[str] = <factory>, metadata: dict[str, typing.Any] = <factory>)`
:   Holds the current EventClient and its hierarchical context.

    This dataclass is used internally by the context management system
    to track the current EventClient and accumulated context metadata.

    Attributes:
        client: The actual EventClient instance for logging.
        hierarchy: The naming hierarchy, e.g., ["experiment", "workflow", "step"].
        metadata: Accumulated context metadata (experiment_id, workflow_id, etc.).

    Example:
        ctx = EventClientContext(
            client=event_client,
            hierarchy=["experiment", "workflow"],
            metadata={"experiment_id": "exp-123", "workflow_id": "wf-456"},
        )
        print(ctx.name)  # "experiment.workflow"

    ### Instance variables

    `client: EventClient`
    :   The actual EventClient instance.

    `hierarchy: list[str]`
    :   The naming hierarchy, e.g., ["experiment", "workflow", "step"].

    `metadata: dict[str, typing.Any]`
    :   Accumulated context metadata (experiment_id, workflow_id, etc.).

    `name: str`
    :   Get the full hierarchical name.

        Returns:
            Dot-separated hierarchy string, or "madsci" if empty.

    ### Methods

    `child(self, name: str, client: ForwardRef('EventClient') | None = None, **metadata: Any) ‑> EventClientContext`
    :   Create a child context with extended hierarchy.

        Args:
            name: Name for this context level, added to hierarchy.
            client: Optional explicit EventClient. If None, creates a bound
                   child from the parent's client.
            **metadata: Additional context metadata to merge.

        Returns:
            New EventClientContext with extended hierarchy and metadata.

        Example:
            parent_ctx = EventClientContext(client=client, hierarchy=["experiment"])
            child_ctx = parent_ctx.child("workflow", workflow_id="wf-123")
            # child_ctx.hierarchy == ["experiment", "workflow"]
            # child_ctx.metadata == {"workflow_id": "wf-123"}

`EventLogLevel(value, names=None, *, module=None, qualname=None, type=None, start=1)`
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

    `manager_type: madsci.common.types.manager_types.ManagerType`
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

`EventManagerSettings(**kwargs: Any)`
:   Handles settings and configuration for the Event Manager.

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

    `alert_level: madsci.common.types.event_types.EventLogLevel`
    :

    `archive_batch_size: int`
    :

    `backup_dir: str | pathlib.Path`
    :

    `backup_enabled: bool`
    :

    `backup_max_count: int`
    :

    `backup_schedule: str | None`
    :

    `collection_name: str`
    :

    `database_name: str`
    :

    `email_alerts: madsci.common.types.event_types.EmailAlertsConfig | None`
    :

    `fail_on_retention_error: bool`
    :

    `hard_delete_after_days: int`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType | None`
    :

    `max_batches_per_run: int`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

    `retention_check_interval_hours: int`
    :

    `retention_enabled: bool`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

    `soft_delete_after_days: int`
    :

`EventType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   The type of an event.

    Notes:
    - Prefer the most specific type available.
    - The LOG_* types are for general logging; prefer domain-specific types when
      applicable.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `ACTION_COMPLETE`
    :

    `ACTION_FAILED`
    :

    `ACTION_START`
    :

    `ACTION_STATUS_CHANGE`
    :

    `ATTACHMENT_CREATE`
    :

    `ATTACHMENT_DELETE`
    :

    `BACKUP_CREATE`
    :

    `BACKUP_RESTORE`
    :

    `CAMPAIGN_ABORT`
    :

    `CAMPAIGN_COMPLETE`
    :

    `CAMPAIGN_CREATE`
    :

    `CAMPAIGN_START`
    :

    `DATA_EXPORT`
    :

    `DATA_QUERY`
    :

    `DATA_STORE`
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

    `LOCATION_CREATE`
    :

    `LOCATION_DELETE`
    :

    `LOCATION_UPDATE`
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

    `MANAGER_ERROR`
    :

    `MANAGER_HEALTH_CHECK`
    :

    `MANAGER_START`
    :

    `MANAGER_STOP`
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

    `RESOURCE_ALLOCATE`
    :

    `RESOURCE_CREATE`
    :

    `RESOURCE_DELETE`
    :

    `RESOURCE_RELEASE`
    :

    `RESOURCE_UPDATE`
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

    `WORKFLOW_STEP_COMPLETE`
    :

    `WORKFLOW_STEP_FAILED`
    :

    `WORKFLOW_STEP_START`
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
