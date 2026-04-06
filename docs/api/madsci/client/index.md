Module madsci.client
====================
The Modular Autonomous Discovery for Science (MADSci) Python Client and CLI.

Sub-modules
-----------
* madsci.client.cli
* madsci.client.client_mixin
* madsci.client.data_client
* madsci.client.event_client
* madsci.client.experiment_client
* madsci.client.http
* madsci.client.lab_client
* madsci.client.location_client
* madsci.client.node
* madsci.client.otel_processors
* madsci.client.resource_client
* madsci.client.structlog_config
* madsci.client.workcell_client
* madsci.client.workflow_display

Classes
-------

`AbstractNodeClient(url: pydantic.networks.AnyUrl)`
:   Base Node Client, protocol agnostic, all node clients should inherit from or be based on this.
    
    Initialize the client.

    ### Descendants

    * madsci.client.node.rest_node_client.RestNodeClient

    ### Class variables

    `supported_capabilities: ClassVar[madsci.common.types.node_types.NodeClientCapabilities]`
    :   The capabilities supported by this node client.

    `url_protocols: ClassVar[list[str]]`
    :   The protocol(s) to use for node URL's using this client.

    ### Static methods

    `validate_url(url: pydantic.networks.AnyUrl) ‑> bool`
    :   check if a url matches this node type

    ### Methods

    `await_action_result(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds.

    `get_action_history(self) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the history of a specific action, or all actions run by the node.

    `get_action_result(self, action_id: str) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action on the node.

    `get_action_status(self, action_id: str) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action on the node.

    `get_info(self) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node.

    `get_log(self) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log of the node.

    `get_resources(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Get the resources of the node.

    `get_state(self) ‑> dict[str, typing.Any]`
    :   Get the state of the node.

    `get_status(self) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node.

    `send_action(self, action_request: madsci.common.types.action_types.ActionRequest, await_result: bool = True, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Perform an action on the node.

    `send_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node.

    `set_config(self, config_dict: dict[str, typing.Any]) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Set configuration values of the node.

`DataClient(data_server_url: Optional[Union[str, AnyUrl]] = None, object_storage_settings: Optional[ObjectStorageSettings] = None, config: Optional[DataClientConfig] = None)`
:   Client for the MADSci Experiment Manager.
    
    Create a new Datapoint Client.
    
    Args:
        data_server_url: The base URL of the Data Manager. If not provided, it will be taken from the current MadsciContext.
        object_storage_settings: Configuration for S3-compatible object storage. If not provided, defaults will be used.
        config: Client configuration for retry and timeout settings. If not provided, uses default DataClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `data_server_url: Optional[AnyUrl]`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `async_get_datapoint(self, datapoint_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Get a datapoint's metadata by ID asynchronously.
        
        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_datapoints(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.datapoint_types.DataPoint]`
    :   Get a list of the latest datapoints asynchronously.
        
        Args:
            number: Number of datapoints to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_query_datapoints(self, selector: Any, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.datapoint_types.DataPoint]`
    :   Query datapoints based on a selector asynchronously.
        
        Args:
            selector: Query selector for filtering datapoints.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_submit_datapoint(self, datapoint: DataPoint, timeout: Optional[float] = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Submit a Datapoint object asynchronously.
        
        Args:
            datapoint: The datapoint to submit.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        
        Returns:
            The submitted datapoint with server-assigned IDs if applicable

    `extract_datapoint_ids_from_action_result(self, action_result: Any) ‑> list[str]`
    :   Extract all datapoint IDs from an ActionResult.
        
        Args:
            action_result: ActionResult object to extract IDs from
        
        Returns:
            List of unique datapoint ULID strings

    `get_datapoint(self, datapoint_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Get a datapoint's metadata by ID, either from local storage or server.
        
        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_datapoint_metadata(self, datapoint_id: str) ‑> dict[str, typing.Any]`
    :   Get basic metadata for a datapoint without fetching the full data.
        
        Useful for UI display where you need labels, types, timestamps, etc.
        without loading large file contents or values.
        
        Args:
            datapoint_id: ULID string of the datapoint
        
        Returns:
            Dictionary with metadata fields like label, data_type, data_timestamp

    `get_datapoint_value(self, datapoint_id: Union[str, ULID], timeout: Optional[float] = None) ‑> Any`
    :   Get a datapoint value by ID. If the datapoint is JSON, returns the JSON data.
        Otherwise, returns the raw data as bytes.
        
        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

    `get_datapoints(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.datapoint_types.DataPoint]`
    :   Get a list of the latest datapoints.
        
        Args:
            number: Number of datapoints to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_datapoints_by_ids(self, datapoint_ids: list[str]) ‑> dict[str, madsci.common.types.datapoint_types.DataPoint]`
    :   Fetch multiple datapoints by their IDs in a batch operation.
        
        This method enables just-in-time fetching of datapoints when only IDs are stored
        in workflows, following the principle of efficient datapoint management.
        
        Args:
            datapoint_ids: List of datapoint ULID strings to fetch
        
        Returns:
            Dictionary mapping datapoint IDs to DataPoint objects
        
        Raises:
            Exception: If any datapoint cannot be fetched

    `get_datapoints_metadata(self, datapoint_ids: list[str]) ‑> dict[str, dict[str, typing.Any]]`
    :   Get metadata for multiple datapoints efficiently.
        
        Args:
            datapoint_ids: List of datapoint ULID strings
        
        Returns:
            Dictionary mapping datapoint IDs to metadata dictionaries

    `query_datapoints(self, selector: Any, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.datapoint_types.DataPoint]`
    :   Query datapoints based on a selector.
        
        Args:
            selector: Query selector for filtering datapoints.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `save_datapoint_value(self, datapoint_id: Union[str, ULID], output_filepath: str, timeout: Optional[float] = None) ‑> None`
    :   Get an datapoint value by ID.
        
        Args:
            datapoint_id: The ID of the datapoint to save.
            output_filepath: Path where the datapoint value should be saved.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

    `submit_datapoint(self, datapoint: DataPoint, timeout: Optional[float] = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Submit a Datapoint object.
        
        If object storage is configured and the datapoint is a file type,
        the file will be automatically uploaded to object storage instead
        of being sent to the Data Manager server.
        
        Args:
            datapoint: The datapoint to submit.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        
        Returns:
            The submitted datapoint with server-assigned IDs if applicable

`EventClient(config: madsci.common.types.event_types.EventClientConfig | None = None, **kwargs: Any)`
:   A logger and event handler for MADSci system components.
    
    Uses structlog for structured logging with context binding support.
    Each EventClient instance has its own isolated logger configuration.
    
    Example:
        # Basic usage
        client = EventClient(name="my_module")
        client.info("Starting process", step=1, total=10)
    
        # Context binding
        client = client.bind(workflow_id="wf-123")
        client.info("Processing")  # Automatically includes workflow_id
    
        # Nested binding
        client = client.bind(node_id="node-456")
        client.info("Action complete")  # Includes both workflow_id and node_id
    
        # Multiple clients with different configs (fully isolated)
        json_client = EventClient(name="json_logger", config=EventClientConfig(log_output_format="json"))
        console_client = EventClient(name="console_logger", config=EventClientConfig(log_output_format="console"))
    
    Initialize the event logger. If no config is provided, use the default config.
    
    Keyword Arguments are used to override the values of the passed in/default config.

    ### Class variables

    `config: madsci.common.types.event_types.EventClientConfig`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `alert(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the alert level (critical with alert flag).
        
        Args:
            event: The event or message to log
            **kwargs: Additional structured data

    `async_get_event(self, event_id: str, timeout: float | None = None) ‑> madsci.common.types.event_types.Event | None`
    :   Get a specific event by ID asynchronously.
        
        Args:
            event_id: The ID of the event to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_events(self, number: int = 100, level: int = -1, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Query the event server for a certain number of recent events asynchronously.
        
        Args:
            number: Number of events to retrieve.
            level: Log level filter. -1 uses effective log level.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_query_events(self, selector: dict, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Query the event server for events based on a selector asynchronously.
        
        Args:
            selector: Dictionary selector for filtering events.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `bind(self, **context: Any) ‑> madsci.client.event_client.EventClient`
    :   Create a new client with additional bound context.
        
        Bound context is automatically included in all subsequent log messages
        from the returned client.
        
        Args:
            **context: Key-value pairs to bind to all future log messages
        
        Returns:
            New EventClient instance with bound context
        
        Example:
            client = EventClient(name="workflow")
            client = client.bind(workflow_id="wf-123")
            client.info("Starting workflow")  # Includes workflow_id
        
            client = client.bind(step=1)
            client.info("Executing step")  # Includes workflow_id and step

    `close(self) ‑> None`
    :   Clean up resources including file handlers.
        
        This method should be called when the EventClient is no longer needed,
        especially in test scenarios where many clients may be created.
        
        Note: Bound child clients (created via bind()/unbind()) share resources
        with their parent and will skip cleanup to avoid closing shared resources.

    `critical(self, message: str, **kwargs: Any) ‑> None`
    :   Log a critical message.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

    `debug(self, message: str, **kwargs: Any) ‑> None`
    :   Log a debug message.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

    `error(self, message: str, **kwargs: Any) ‑> None`
    :   Log an error message.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

    `exception(self, message: str, **kwargs: Any) ‑> None`
    :   Log an exception with traceback.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

    `get_event(self, event_id: str, timeout: float | None = None) ‑> madsci.common.types.event_types.Event | None`
    :   Get a specific event by ID.
        
        Args:
            event_id: The ID of the event to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_events(self, number: int = 100, level: int = -1, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Query the event server for a certain number of recent events.
        
        If no event server is configured, query the log file instead.
        
        Args:
            number: Number of events to retrieve.
            level: Log level filter. -1 uses effective log level.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_log(self) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Read the log

    `get_session_utilization(self, start_time: str | None = None, end_time: str | None = None, csv_export: bool = False, save_to_file: bool = False, output_path: str | None = None) ‑> dict[str, typing.Any] | str | None`
    :   Get session-based utilization report, optionally export to CSV.
        
        Sessions represent workcell/lab start and stop periods. Each session
        indicates when laboratory equipment was actively configured and available.
        
        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            csv_export: If True, convert report to CSV format
            save_to_file: If True, save to file (requires output_path)
            output_path: Path to save files (used when save_to_file=True)
        
        Returns:
            - If csv_export=False: JSON dict
            - If csv_export=True and save_to_file=False: CSV string
            - If csv_export=True and save_to_file=True: dict with file save results

    `get_user_utilization_report(self, start_time: str | None = None, end_time: str | None = None, csv_export: bool = False, save_to_file: bool = False, output_path: str | None = None) ‑> dict[str, typing.Any] | str | None`
    :   Get detailed user utilization report from the event server, optionally export to CSV.
        
        Args:
            start_time: ISO format start time (e.g., "2025-07-20T00:00:00Z")
            end_time: ISO format end time (e.g., "2025-07-23T00:00:00Z")
            csv_export: If True, convert report to CSV format
            save_to_file: If True, save to file (requires output_path)
            output_path: Path to save files (used when save_to_file=True)
        
        Returns:
            - If csv_export=False: JSON dict with detailed user utilization data
            - If csv_export=True and save_to_file=False: CSV string
            - If csv_export=True and save_to_file=True: dict with file save results

    `get_utilization_periods(self, start_time: str | None = None, end_time: str | None = None, analysis_type: str = 'daily', user_timezone: str = 'America/Chicago', include_users: bool = True, csv_export: bool = False, save_to_file: bool = False, output_path: str | None = None) ‑> dict[str, typing.Any] | str | None`
    :   Get time-series utilization analysis with periodic breakdowns, optionally export to CSV.
        
        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            analysis_type: "hourly", "daily", "weekly", "monthly"
            user_timezone: Timezone for day boundaries (e.g., "America/Chicago")
            include_users: Whether to include user utilization data
            csv_export: If True, convert report to CSV format
            save_to_file: If True, save to file (requires output_path)
            output_path: Path to save files (used when save_to_file=True)
        
        Returns:
            - If csv_export=False: JSON dict with utilization data
            - If csv_export=True and save_to_file=False: CSV string
            - If csv_export=True and save_to_file=True: dict with file save results

    `info(self, message: str, **kwargs: Any) ‑> None`
    :   Log an info message.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

    `log(self, event: madsci.common.types.event_types.Event | Any, level: int | madsci.common.types.event_types.EventLogLevel | None = None, alert: bool | None = None, warning_category: type | None = None) ‑> None`
    :   Log an event.
        
        This is the legacy interface. For structured logging, prefer using
        the new methods: debug(), info(), warning(), error(), critical().
        
        Args:
            event: Event object, string, dict, or other data to log
            level: Log level (defaults to event's level or INFO)
            alert: Whether to force an alert
            warning_category: Optional warning category for warnings module

    `log_alert(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the alert level (critical with alert flag).
        
        Args:
            event: The event or message to log
            **kwargs: Additional structured data

    `log_critical(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the critical level.
        
        Alias for critical(). Provided for backward compatibility.

    `log_debug(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the debug level.
        
        Alias for debug(). Provided for backward compatibility.

    `log_error(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the error level.
        
        Alias for error(). Provided for backward compatibility.

    `log_info(self, event: madsci.common.types.event_types.Event | str, **kwargs: Any) ‑> None`
    :   Log an event at the info level.
        
        Alias for info(). Provided for backward compatibility.

    `log_warning(self, event: madsci.common.types.event_types.Event | str, warning_category: type | None = builtins.UserWarning, **kwargs: Any) ‑> None`
    :   Log an event at the warning level.
        
        Args:
            event: The event or message to log
            warning_category: Optional warning category for warnings module integration
            **kwargs: Additional structured data

    `query_events(self, selector: dict, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Query the event server for events based on a selector.
        
        Requires an event server be configured.
        
        Args:
            selector: Dictionary selector for filtering events.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `unbind(self, *keys: str) ‑> madsci.client.event_client.EventClient`
    :   Create a new client with specified context keys removed.
        
        Args:
            *keys: Keys to remove from the bound context
        
        Returns:
            New EventClient instance without the specified context keys

    `warn(self, event: madsci.common.types.event_types.Event | str, warning_category: type | None = builtins.UserWarning, **kwargs: Any) ‑> None`
    :   Log an event at the warning level.
        
        Args:
            event: The event or message to log
            warning_category: Optional warning category for warnings module integration
            **kwargs: Additional structured data

    `warning(self, message: str, **kwargs: Any) ‑> None`
    :   Log a warning message.
        
        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry

`ExperimentClient(experiment_server_url: Optional[Union[str, AnyUrl]] = None, config: Optional[ExperimentClientConfig] = None)`
:   Client for the MADSci Experiment Manager.
    
    Create a new Experiment Client.
    
    Args:
        experiment_server_url: The URL of the experiment server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default ExperimentClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `experiment_server_url: AnyUrl`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `async_cancel_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_continue_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_end_experiment(self, experiment_id: Union[str, ULID], status: Optional[ExperimentStatus] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_campaign(self, campaign_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Get an experimental campaign by ID asynchronously.
        
        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> dict`
    :   Get an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_experiments(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get a list of the latest experiments asynchronously.
        
        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_pause_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID asynchronously.
        
        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_register_campaign(self, campaign: ExperimentalCampaign, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Register a new experimental campaign asynchronously.
        
        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_start_experiment(self, experiment_design: ExperimentDesign, run_name: Optional[str] = None, run_description: Optional[str] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start an experiment based on an ExperimentDesign asynchronously.
        
        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `cancel_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Cancel an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `continue_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Continue an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `end_experiment(self, experiment_id: Union[str, ULID], status: Optional[ExperimentStatus] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   End an experiment by ID. Optionally, set the status.
        
        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_campaign(self, campaign_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Get an experimental campaign by ID.
        
        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> dict`
    :   Get an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_experiments(self, number: int = 10, timeout: Optional[float] = None) ‑> list[madsci.common.types.experiment_types.Experiment]`
    :   Get a list of the latest experiments.
        
        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `pause_experiment(self, experiment_id: Union[str, ULID], timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Pause an experiment by ID.
        
        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `register_campaign(self, campaign: ExperimentalCampaign, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.ExperimentalCampaign`
    :   Register a new experimental campaign.
        
        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `start_experiment(self, experiment_design: ExperimentDesign, run_name: Optional[str] = None, run_description: Optional[str] = None, timeout: Optional[float] = None) ‑> madsci.common.types.experiment_types.Experiment`
    :   Start an experiment based on an ExperimentDesign.
        
        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

`LabClient(lab_server_url: Optional[Union[str, AnyUrl]] = None, config: Optional[LabClientConfig] = None)`
:   Client for the MADSci Lab Manager.
    
    Create a new Lab Client.
    
    Args:
        lab_server_url: The URL of the lab server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default LabClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `lab_server_url: AnyUrl`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.
        
        Returns the httpx.Client so that existing code accessing
        ``client.session`` continues to work.

    ### Methods

    `async_get_lab_context(self, timeout: Optional[float] = None) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the lab context asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_lab_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health of the lab asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_manager_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health of the lab manager asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_context(self, timeout: Optional[float] = None) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the lab context.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health of the lab.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_manager_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health of the lab manager.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

`LocationClient(location_server_url: str | pydantic.networks.AnyUrl | None = None, event_client: madsci.client.event_client.EventClient | None = None, config: madsci.common.types.client_types.LocationClientConfig | None = None)`
:   A client for interacting with the Location Manager to perform location operations.
    
    Initialize the LocationClient.
    
    Parameters
    ----------
    location_server_url : Optional[Union[str, AnyUrl]]
        The URL of the location server. If None, will try to get from context.
    event_client : Optional[EventClient]
        Event client for logging. If not provided, a new one will be created.
    config : Optional[LocationClientConfig]
        Client configuration for retry and timeout settings. If not provided, uses default LocationClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `location_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `add_location(self, location: madsci.common.types.location_types.Location, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Add a location.
        
        Parameters
        ----------
        location : Location
            The location object to add.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The created location.

    `async_add_location(self, location: madsci.common.types.location_types.Location, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Add a location asynchronously.

    `async_attach_resource(self, location_name: str, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location asynchronously.

    `async_create_location_from_template(self, location_name: str, template_name: str, node_bindings: dict[str, str] | None = None, representation_overrides: dict[str, dict[str, typing.Any]] | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, description: str | None = None, allow_transfers: bool | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Create a location from a LocationTemplate asynchronously.

    `async_create_location_template(self, template: madsci.common.types.location_types.LocationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Create a new location template asynchronously.

    `async_create_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Create a new representation template asynchronously.

    `async_delete_location(self, location_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a specific location by name asynchronously.

    `async_delete_location_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a location template by name asynchronously.

    `async_delete_representation_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a representation template by name asynchronously.

    `async_detach_resource(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location asynchronously.

    `async_export_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Export all locations from the server asynchronously.

    `async_get_location(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get details of a specific location by ID asynchronously.

    `async_get_location_by_name(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by name asynchronously.

    `async_get_location_resources(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources at a specific location asynchronously.

    `async_get_location_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Get a location template by name asynchronously.

    `async_get_location_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Get all location templates asynchronously.

    `async_get_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations asynchronously.

    `async_get_representation_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Get a representation template by name asynchronously.

    `async_get_representation_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Get all representation templates asynchronously.

    `async_get_transfer_graph(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list asynchronously.

    `async_import_locations(self, location_file_path: pathlib.Path | None = None, locations: list[madsci.common.types.location_types.Location] | None = None, overwrite: bool = False, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationImportResult`
    :   Import multiple locations from a file or a list asynchronously.
        
        Parameters
        ----------
        location_file_path : Optional[Path]
            Path to a YAML file containing location definitions.
        locations : Optional[list[Location]]
            A list of Location objects to import directly.
        overwrite : bool
            If True, overwrite existing locations with the same name.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        LocationImportResult
            Result with imported/skipped/error counts and imported locations.

    `async_plan_transfer(self, source_location_id: str, target_location_id: str, resource_id: str | None = None, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Plan a transfer from source to target location asynchronously.

    `async_remove_representation(self, location_name: str, node_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node asynchronously.

    `async_set_representation(self, location_name: str, node_name: str, representation: Any, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Set a representation for a location for a specific node asynchronously.

    `attach_resource(self, location_name: str, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location.
        
        Parameters
        ----------
        location_name : str
            The name of the location.
        resource_id : str
            The ID of the resource to attach.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The updated location.

    `create_location_from_template(self, location_name: str, template_name: str, node_bindings: dict[str, str] | None = None, representation_overrides: dict[str, dict[str, typing.Any]] | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, description: str | None = None, allow_transfers: bool | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Create a location from a LocationTemplate.

    `create_location_template(self, template: madsci.common.types.location_types.LocationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Create a new location template.

    `create_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Create a new representation template.

    `delete_location(self, location_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a specific location by name.
        
        Parameters
        ----------
        location_name : str
            The name of the location to delete.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        dict[str, str]
            A message confirming deletion.

    `delete_location_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a location template by name.

    `delete_representation_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a representation template by name.

    `detach_resource(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location.
        
        Parameters
        ----------
        location_name : str
            The name of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The updated location.

    `export_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Export all locations from the server.
        
        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        list[Location]
            All locations managed by the location server.

    `get_location(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get details of a specific location by ID.
        
        Parameters
        ----------
        location_id : str
            The ID of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The location details.

    `get_location_by_name(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by name.
        
        Parameters
        ----------
        location_name : str
            The name of the location to retrieve.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The requested location.

    `get_location_resources(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources currently at a specific location.
        
        Parameters
        ----------
        location_name : str
            The name of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        ResourceHierarchy
            Hierarchy of resources at the location, or empty hierarchy if no attached resource.

    `get_location_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Get a location template by name.

    `get_location_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Get all location templates.

    `get_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations.
        
        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        list[Location]
            A list of all locations.

    `get_representation_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Get a representation template by name.

    `get_representation_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Get all representation templates.

    `get_transfer_graph(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list.
        
        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        dict[str, list[str]]
            Transfer graph as adjacency list mapping source location IDs to
            lists of reachable destination location IDs.

    `import_locations(self, location_file_path: pathlib.Path | None = None, locations: list[madsci.common.types.location_types.Location] | None = None, overwrite: bool = False, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationImportResult`
    :   Import multiple locations from a file or a list.
        
        Posts the full list to the server's /locations/import endpoint.
        
        Parameters
        ----------
        location_file_path : Optional[Path]
            Path to a YAML file containing location definitions.
        locations : Optional[list[Location]]
            A list of Location objects to import directly.
        overwrite : bool
            If True, overwrite existing locations with the same name.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        LocationImportResult
            Result with imported/skipped/error counts and imported locations.

    `init_location_template(self, template_name: str, representation_templates: dict[str, str] | None = None, resource_template_name: str | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, default_allow_transfers: bool = True, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', description: str | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Idempotent init: get-or-create, version-update for a location template.
        
        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.

    `init_representation_template(self, template_name: str, default_values: dict[str, typing.Any] | None = None, schema: dict[str, typing.Any] | None = None, required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', description: str | None = None, timeout: float | None = None, schema_def: dict[str, typing.Any] | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Idempotent init: get-or-create, version-update for a representation template.
        
        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.
        
        The ``schema`` parameter is deprecated; use ``schema_def`` instead.
        If both are provided, ``schema_def`` takes precedence.

    `plan_transfer(self, source_location_id: str, target_location_id: str, resource_id: str | None = None, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Plan a transfer from source to target location.
        
        Parameters
        ----------
        source_location_id : str
            ID of the source location.
        target_location_id : str
            ID of the target location.
        resource_id : Optional[str]
            ID of the resource to transfer (for transfer_resource actions).
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        WorkflowDefinition
            A WorkflowDefinition including the necessary steps to transfer a resource between locations.

    `remove_representation(self, location_name: str, node_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node.
        
        Parameters
        ----------
        location_name : str
            The name of the location.
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The updated location.

    `set_representation(self, location_name: str, node_name: str, representation: Any, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Set a representation for a location for a specific node.
        
        Parameters
        ----------
        location_name : str
            The name of the location.
        node_name : str
            The name of the node.
        representation : Any
            The representation to set for the specified node.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        Location
            The updated location.

`MadsciClientMixin()`
:   Mixin for managing MADSci client lifecycle.
    
    Provides automatic initialization and management of MADSci service clients
    with support for:
    - Context-based auto-configuration
    - Explicit URL overrides
    - Selective client initialization
    - EventClient sharing across clients
    - Lazy initialization
    
    Usage:
        class MyComponent(MadsciClientMixin):
            # Optional: Declare which clients to initialize eagerly
            REQUIRED_CLIENTS = ["event", "resource", "data"]
    
            def __init__(self):
                super().__init__()
                self.setup_clients()  # Initialize required clients
    
            def my_method(self):
                # Access clients via properties
                self.event_client.info("Hello")
                self.resource_client.get_resource("xyz")
    
    Class Attributes:
        REQUIRED_CLIENTS: List of client names to initialize in setup_clients().
                         Available: "event", "resource", "data", "experiment",
                                   "workcell", "location", "lab"
        OPTIONAL_CLIENTS: List of client names that may be used but aren't required.
    
    Client Properties:
        event_client: EventClient for logging and event management
        resource_client: ResourceClient for resource and inventory tracking
        data_client: DataClient for data storage and retrieval
        experiment_client: ExperimentClient for experiment management
        workcell_client: WorkcellClient for workflow coordination
        location_client: LocationClient for location management
        lab_client: LabClient for lab configuration and context
    
    Configuration:
        The mixin supports several ways to configure clients:
        1. Context-based (default): URLs from get_current_madsci_context()
        2. Explicit URLs: Pass *_server_url as instance attributes
        3. Client configs: Pass *_client_config as instance attributes
        4. Direct injection: Pass pre-initialized clients to setup_clients()

    ### Descendants

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.experiment_application.experiment_base.ExperimentBase
    * madsci.node_module.abstract_node_module.AbstractNode

    ### Class variables

    `OPTIONAL_CLIENTS: ClassVar[list[str]]`
    :

    `REQUIRED_CLIENTS: ClassVar[list[str]]`
    :

    `client_retry_backoff_factor: float`
    :

    `client_retry_enabled: bool`
    :

    `client_retry_status_forcelist: list[int] | None`
    :

    `client_retry_total: int`
    :

    `data_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `event_client_config: madsci.common.types.event_types.EventClientConfig | None`
    :

    `event_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `experiment_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `lab_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `location_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `name: str | None`
    :

    `object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None`
    :

    `resource_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `workcell_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `workcell_working_directory: str`
    :

    ### Instance variables

    `data_client: madsci.client.data_client.DataClient`
    :   Get or create the DataClient instance.
        
        Returns:
            DataClient: The data client for data storage and retrieval

    `event_client: madsci.client.event_client.EventClient`
    :   Get or create the EventClient instance.
        
        Resolution order:
        1. Explicitly set client (_event_client)
        2. Context client with component binding (if context exists)
        3. New client from config (legacy fallback)
        
        Returns:
            EventClient: The event client for logging and event management

    `experiment_client: madsci.client.experiment_client.ExperimentClient`
    :   Get or create the ExperimentClient instance.
        
        Returns:
            ExperimentClient: The experiment client for experiment management

    `lab_client: madsci.client.lab_client.LabClient`
    :   Get or create the LabClient instance.
        
        Returns:
            LabClient: The lab client for lab configuration

    `location_client: madsci.client.location_client.LocationClient`
    :   Get or create the LocationClient instance.
        
        Returns:
            LocationClient: The location client for location management

    `resource_client: madsci.client.resource_client.ResourceClient`
    :   Get or create the ResourceClient instance.
        
        Returns:
            ResourceClient: The resource client for inventory tracking

    `workcell_client: madsci.client.workcell_client.WorkcellClient`
    :   Get or create the WorkcellClient instance.
        
        Returns:
            WorkcellClient: The workcell client for workflow coordination

    ### Methods

    `setup_clients(self, clients: list[str] | None = None, event_client: madsci.client.event_client.EventClient | None = None, resource_client: madsci.client.resource_client.ResourceClient | None = None, data_client: madsci.client.data_client.DataClient | None = None, experiment_client: madsci.client.experiment_client.ExperimentClient | None = None, workcell_client: madsci.client.workcell_client.WorkcellClient | None = None, location_client: madsci.client.location_client.LocationClient | None = None, lab_client: madsci.client.lab_client.LabClient | None = None) ‑> None`
    :   Initialize specified clients.
        
        This method initializes the clients specified in the 'clients' parameter,
        or all REQUIRED_CLIENTS if not specified. Clients can also be directly
        injected as parameters (useful for testing).
        
        Args:
            clients: List of client names to initialize. If None, initializes
                    all clients in REQUIRED_CLIENTS. Available: "event",
                    "resource", "data", "experiment", "workcell", "location", "lab"
            event_client: Pre-initialized EventClient to use
            resource_client: Pre-initialized ResourceClient to use
            data_client: Pre-initialized DataClient to use
            experiment_client: Pre-initialized ExperimentClient to use
            workcell_client: Pre-initialized WorkcellClient to use
            location_client: Pre-initialized LocationClient to use
            lab_client: Pre-initialized LabClient to use
        
        Example:
            # Initialize required clients
            self.setup_clients()
        
            # Initialize specific clients
            self.setup_clients(clients=["event", "resource"])
        
            # Inject a mock client for testing
            mock_event = Mock(spec=EventClient)
            self.setup_clients(event_client=mock_event)

    `teardown_clients(self) ‑> None`
    :   Clean up client resources.
        
        This method closes the EventClient and any other clients that
        have resources that need explicit cleanup (file handlers,
        connection pools, background threads).
        
        This method should be called in shutdown handlers or when
        the component is no longer needed to prevent resource leaks.

`ResourceClient(resource_server_url: str | pydantic.networks.AnyUrl | None = None, event_client: madsci.client.event_client.EventClient | None = None, config: madsci.common.types.client_types.ResourceClientConfig | None = None)`
:   REST client for interacting with a MADSci Resource Manager.
    
    Initialize the resource client.
    
    Args:
        resource_server_url: The URL of the resource server. If not provided, will use the URL from the current MADSci context.
        event_client: Optional EventClient for logging. If not provided, creates a new one.
        config: Client configuration for retry and timeout settings. If not provided, uses default ResourceClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `local_resources: dict[str, typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]]`
    :

    `local_templates: ClassVar[dict[str, dict]]`
    :

    `resource_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `acquire_lock(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, client_id: str | None = None, timeout: float | None = None) ‑> bool`
    :   Acquire a lock on a resource.
        
        Args:
            resource: Resource object or resource ID
            lock_duration: Lock duration in seconds (default 5 minutes)
            client_id: Client identifier (auto-generated if not provided)
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            bool: True if lock was acquired, False otherwise

    `add_or_update_resource(self, resource: madsci.common.types.resource_types.Resource, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource`
    :   Add a resource to the server.
        
        Args:
            resource (Resource): The resource to add.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            Resource: The added resource as returned by the server.

    `add_resource(self, resource: madsci.common.types.resource_types.Resource, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource`
    :   Add a resource to the server.
        
        Args:
            resource (Resource): The resource to add.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            Resource: The added resource as returned by the server.

    `async_acquire_lock(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, client_id: str | None = None, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Acquire a lock on a resource asynchronously.
        
        Args:
            resource: Resource object or resource ID.
            lock_duration: Lock duration in seconds (default 5 minutes).
            client_id: Client identifier (auto-generated if not provided).
            timeout: Optional timeout override in seconds.
        
        Returns:
            Optional[ResourceDataModels]: The locked resource, or None if lock acquisition failed.

    `async_add_resource(self, resource: madsci.common.types.resource_types.Resource, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource`
    :   Add a resource to the server asynchronously.
        
        Args:
            resource: The resource to add.
            timeout: Optional timeout override in seconds.
        
        Returns:
            Resource: The added resource as returned by the server.

    `async_change_quantity_by(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the quantity of a resource by a given amount asynchronously.
        
        Args:
            resource: The resource or its ID.
            amount: The quantity to change by.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The updated resource.

    `async_create_resource_from_template(self, template_name: str, resource_name: str, overrides: dict[str, typing.Any] | None = None, add_to_database: bool = True, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a resource from a template asynchronously.
        
        Args:
            template_name: Name of the template to use.
            resource_name: Name for the new resource.
            overrides: Values to override template defaults.
            add_to_database: Whether to add the resource to the database.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The created resource.

    `async_get_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Retrieve a resource from the server asynchronously.
        
        Args:
            resource: The resource object or ID to retrieve.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The retrieved resource.

    `async_get_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a template by name asynchronously.
        
        Args:
            template_name: Name of the template to retrieve.
            timeout: Optional timeout override in seconds.
        
        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.

    `async_is_locked(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> tuple[bool, str | None]`
    :   Check if a resource is currently locked asynchronously.
        
        Args:
            resource: Resource object or resource ID.
            timeout: Optional timeout override in seconds.
        
        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)

    `async_query_all_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query all resource templates asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds.
        
        Returns:
            list[ResourceDataModels]: List of template resources.

    `async_query_history(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, version: int | None = None, change_type: str | None = None, removed: bool | None = None, start_date: datetime.datetime | None = None, end_date: datetime.datetime | None = None, limit: int | None = 100, timeout: float | None = None) ‑> list[dict[str, typing.Any]]`
    :   Retrieve the history of a resource with flexible filters asynchronously.
        
        Args:
            resource: The resource or resource ID to query history for.
            version: Filter by specific version number.
            change_type: Filter by change type.
            removed: Filter by removed status.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of history entries to return.
            timeout: Optional timeout override in seconds.
        
        Returns:
            list[dict[str, Any]]: History entries matching the query.

    `async_query_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, resource_name: str | None = None, parent_id: str | None = None, resource_class: str | None = None, base_type: str | None = None, unique: bool | None = False, multiple: bool | None = False, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query for one or more resources matching specific properties asynchronously.
        
        Args:
            resource: The (ID of) the resource to retrieve.
            resource_name: The name of the resource to retrieve.
            parent_id: The ID of the parent resource.
            resource_class: The class of the resource.
            base_type: The base type of the resource.
            unique: Whether to require a unique resource or not.
            multiple: Whether to return multiple resources or just the first.
            timeout: Optional timeout override in seconds.
        
        Returns:
            Resource or list of Resources matching the query.

    `async_query_resource_hierarchy(self, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Query the hierarchical relationships of a resource asynchronously.
        
        Args:
            resource_id: The ID of the resource to query hierarchy for.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceHierarchy: Hierarchy information with ancestor_ids, resource_id, and descendant_ids.

    `async_release_lock(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], client_id: str | None = None, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Release a lock on a resource asynchronously.
        
        Args:
            resource: Resource object or resource ID.
            client_id: Client identifier.
            timeout: Optional timeout override in seconds.
        
        Returns:
            Optional[ResourceDataModels]: The unlocked resource, or None if release failed.

    `async_remove_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource asynchronously by moving it to the history table.
        
        Args:
            resource: The resource or resource ID to remove.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The removed resource.

    `async_restore_deleted_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Restore a deleted resource from the history table asynchronously.
        
        Args:
            resource: The resource or resource ID to restore.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The restored resource.

    `async_set_quantity(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], quantity: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the quantity of a resource asynchronously.
        
        Args:
            resource: The resource or its ID.
            quantity: The quantity to set.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The updated resource.

    `async_update_resource(self, resource: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update a resource on the server asynchronously.
        
        Args:
            resource: The resource to update.
            timeout: Optional timeout override in seconds.
        
        Returns:
            ResourceDataModels: The updated resource as returned by the server.

    `change_quantity_by(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the quantity of a resource by a given amount.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to change by.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `create_resource_from_template(self, template_name: str, resource_name: str, overrides: dict[str, typing.Any] | None = None, add_to_database: bool = True, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a resource from a template.
        
        Args:
            template_name (str): Name of the template to use.
            resource_name (str): Name for the new resource.
            overrides (Optional[dict[str, Any]]): Values to override template defaults.
            add_to_database (bool): Whether to add the resource to the database.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The created resource.

    `create_template(self, resource: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], template_name: str, description: str = '', required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a new resource template from a resource.
        
        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The created template resource.

    `decrease_quantity(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Decrease the quantity of a resource by a given amount.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to decrease by. Note that this is a magnitude, so negative and positive values will have the same effect.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `delete_template(self, template_name: str, timeout: float | None = None) ‑> bool`
    :   Delete a template from the database.
        
        Args:
            template_name (str): Name of the template to delete.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            bool: True if template was deleted, False if not found.

    `empty(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Empty the contents of a container or consumable resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `fill(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Fill a consumable resource to capacity.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `get_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Retrieve a resource from the server.
        
        Args:
            resource (Optional[Union[str, ResourceDataModels]]): The resource object or ID to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The retrieved resource.

    `get_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a template by name.
        
        Args:
            template_name (str): Name of the template to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.

    `get_template_info(self, template_name: str, timeout: float | None = None) ‑> dict[str, typing.Any] | None`
    :   Get detailed template metadata.
        
        Args:
            template_name (str): Name of the template.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            Optional[dict[str, Any]]: Template metadata if found, None otherwise.

    `get_templates_by_category(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get templates organized by base_type category.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            dict[str, list[str]]: Dictionary mapping base_type to template names.

    `increase_quantity(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Increase the quantity of a resource by a given amount.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to increase by. Note that this is a magnitude, so negative and positive values will have the same effect.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `init_resource(self, resource_definition: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.definitions.ResourceDefinition, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.definitions.AssetResourceDefinition, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.definitions.ContainerResourceDefinition, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.definitions.CollectionResourceDefinition, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.definitions.RowResourceDefinition, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.definitions.GridResourceDefinition, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.definitions.StackResourceDefinition, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.definitions.QueueResourceDefinition, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.definitions.PoolResourceDefinition, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.definitions.SlotResourceDefinition, Tag(tag='slot')] | typing.Annotated[madsci.common.types.resource_types.definitions.ConsumableResourceDefinition, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition, Tag(tag='continuous_consumable')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Initializes a resource with the resource manager based on a definition, either creating a new resource if no matching one exists, or returning an existing match.
        
        Args:
            resource (Resource): The resource to initialize.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The initialized resource as returned by the server.

    `init_template(self, resource: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], template_name: str, description: str = '', required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0') ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Initialize a template with the resource manager.
        
        If a template with the given name already exists, returns the existing template.
        If no matching template exists, creates a new one.
        
        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.
        
        Returns:
            ResourceDataModels: The existing or newly created template resource.

    `is_locked(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> tuple[bool, str | None]`
    :   Check if a resource is currently locked.
        
        Args:
            resource: Resource object or resource ID
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)

    `lock(self, *resources: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, auto_refresh: bool = True, client_id: str | None = None) ‑> Generator[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, ...], None, None]`
    :   Create a context manager for locking multiple resources.
        
        Args:
            *resources: Resources to lock (can be Resource objects or IDs)
            lock_duration: Lock duration in seconds
            auto_refresh: Whether to refresh resources on entry/exit
            client_id: Client identifier (auto-generated if not provided)
        
        Returns:
            Context manager that yields locked resources
        
        Usage:
            with client.lock(stack1, child1) as (stack, child):
                stack.push(child)

    `pop(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Pop an asset from a stack or queue resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The parent resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            tuple[ResourceDataModels, ResourceDataModels]: The popped asset and updated parent.

    `push(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], child: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Push a child resource onto a parent stack or queue.
        
        Args:
            resource (Union[ResourceDataModels, str]): The parent resource or its ID.
            child (Union[ResourceDataModels, str]): The child resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated parent resource.

    `query_history(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, version: int | None = None, change_type: str | None = None, removed: bool | None = None, start_date: datetime.datetime | None = None, end_date: datetime.datetime | None = None, limit: int | None = 100, timeout: float | None = None) ‑> list[dict[str, typing.Any]]`
    :   Retrieve the history of a resource with flexible filters.
        
        Args:
            resource: The resource or resource ID to query history for.
            version: Filter by specific version number.
            change_type: Filter by change type.
            removed: Filter by removed status.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of history entries to return.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `query_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, resource_name: str | None = None, parent_id: str | None = None, resource_class: str | None = None, base_type: str | None = None, unique: bool | None = False, multiple: bool | None = False, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query for one or more resources matching specific properties.
        
        Args:
            resource (str, Resource): The (ID of) the resource to retrieve.
            resource_name (str): The name of the resource to retrieve.
            parent_id (str): The ID of the parent resource.
            resource_class (str): The class of the resource.
            base_type (str): The base type of the resource.
            unique (bool): Whether to require a unique resource or not.
            multiple (bool): Whether to return multiple resources or just the first.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            Resource: The retrieved resource.

    `query_resource_hierarchy(self, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Query the hierarchical relationships of a resource.
        
        Returns the ancestors (successive parent IDs from closest to furthest)
        and descendants (direct children organized by parent) of the specified resource.
        
        Args:
            resource_id (str): The ID of the resource to query hierarchy for.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceHierarchy: Hierarchy information with ancestor_ids, resource_id, and descendant_ids.
        
        Raises:
            ValueError: If resource not found.
            httpx.HTTPStatusError: If server request fails.

    `query_templates(self, base_type: str | None = None, tags: list[str] | None = None, created_by: str | None = None, timeout: float | None = None) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   List templates with optional filtering.
        
        Args:
            base_type (Optional[str]): Filter by base resource type.
            tags (Optional[list[str]]): Filter by templates that have any of these tags.
            created_by (Optional[str]): Filter by creator.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            list[ResourceDataModels]: List of template resources.

    `release_lock(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], client_id: str | None = None, timeout: float | None = None) ‑> bool`
    :   Release a lock on a resource.
        
        Args:
            resource: Resource object or resource ID
            client_id: Client identifier
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            bool: True if lock was released, False otherwise

    `remove(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource by moving it to the history table with `removed=True`.
        
        Args:
            resource: The resource or resource ID to remove.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `remove_capacity_limit(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove the capacity limit of a resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `remove_child(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], key: str | tuple[int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)]] | tuple[int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)]], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a child resource from a parent container resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated parent container resource.

    `remove_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource by moving it to the history table with `removed=True`.
        
        Args:
            resource: The resource or resource ID to remove.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `restore_deleted_resource(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Restore a deleted resource from the history table.
        
        Args:
            resource: The resource or resource ID to restore.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `set_capacity(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], capacity: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the capacity of a resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            capacity (Union[float, int]): The capacity to set.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `set_child(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], key: str | tuple[int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)]] | tuple[int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)], int | typing.Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator>)]], child: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set a child resource in a parent container resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.
            child (Union[str, ResourceDataModels]): The child resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated parent container resource.

    `set_quantity(self, resource: str | typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], quantity: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the quantity of a resource.
        
        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            quantity (Union[float, int]): The quantity to set.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource.

    `update(self, resource: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update or refresh a resource, including its children, on the server.
        
        Args:
            resource (ResourceDataModels): The resource to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource as returned by the server.

    `update_resource(self, resource: typing.Annotated[typing.Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | typing.Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | typing.Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | typing.Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | typing.Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | typing.Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | typing.Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | typing.Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | typing.Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | typing.Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | typing.Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | typing.Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | typing.Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | typing.Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update or refresh a resource, including its children, on the server.
        
        Args:
            resource (ResourceDataModels): The resource to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated resource as returned by the server.

    `update_template(self, template_name: str, updates: dict[str, typing.Any], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update an existing template.
        
        Args:
            template_name (str): Name of the template to update.
            updates (dict[str, Any]): Fields to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns:
            ResourceDataModels: The updated template resource.

`RestNodeClient(url: pydantic.networks.AnyUrl, config: madsci.common.types.client_types.RestNodeClientConfig | None = None, event_client: madsci.client.event_client.EventClient | None = None)`
:   REST-based node client.
    
    Initialize the client.
    
    Args:
        url: The URL of the node to connect to.
        config: Client configuration for retry and timeout settings.
               If not provided, uses default RestNodeClientConfig.
        event_client: Optional EventClient to use for logging.
                     If not provided, uses context client or creates new.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin
    * madsci.client.node.abstract_node_client.AbstractNodeClient

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `async_get_action_history(self, action_id: str | None = None, timeout: float | None = None) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get action history asynchronously.

    `async_get_info(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node asynchronously.

    `async_get_log(self, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log from the node asynchronously.

    `async_get_state(self, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Get the state of the node asynchronously.

    `async_get_status(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node asynchronously.

    `async_send_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands, timeout: float | None = None) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node asynchronously.

    `async_set_config(self, new_config: dict[str, typing.Any], timeout: float | None = None) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Update configuration values of the node asynchronously.

    `await_action_result(self, action_id: str, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds.
        
        Args:
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `await_action_result_by_name(self, action_name: str, action_id: str, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds. REST-implementation specific.
        
        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `get_action_history(self, action_id: str | None = None, timeout: float | None = None) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the history of a single action performed on the node, or every action, if no action_id is specified.
        
        Args:
            action_id: Optional action ID to filter by.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_result(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action on the node.
        
        Note: This method uses the legacy API endpoint and cannot fetch files
        since it lacks the action_name needed for file download URLs.
        
        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_result_by_name(self, action_name: str, action_id: str, include_files: bool = True, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action by name. REST-implementation specific.
        
        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            include_files: Whether to include files in the result.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_status(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action on the node.
        
        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_status_by_name(self, action_name: str, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action by action name.
        
        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_info(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_log(self, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log from the node.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_state(self, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Get the state of the node.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_status(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `send_action(self, action_request: madsci.common.types.action_types.ActionRequest, await_result: bool = True, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Perform the action defined by action_request on the specified node.
        
        Args:
            action_request: The action request to send.
            await_result: Whether to wait for the action to complete.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `send_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands, timeout: float | None = None) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node.
        
        Args:
            admin_command: The administrative command to send.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `set_config(self, new_config: dict[str, typing.Any], timeout: float | None = None) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Update configuration values of the node.
        
        Args:
            new_config: Dictionary of configuration values to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

`WorkcellClient(workcell_server_url: Optional[Union[str, AnyUrl]] = None, working_directory: str = './', event_client: Optional[EventClient] = None, config: Optional[WorkcellClientConfig] = None)`
:   A client for interacting with the Workcell Manager to perform various actions.
    
    Initialize the WorkcellClient.
    
    Parameters
    ----------
    workcell_server_url : Optional[Union[str, AnyUrl]]
        The base URL of the Workcell Manager. If not provided, it will be taken from the current MadsciContext.
    working_directory : str, optional
        The directory to look for relative paths. Defaults to "./".
    event_client : Optional[EventClient], optional
        Event client for logging. If not provided, a new one will be created.
    config : Optional[WorkcellClientConfig], optional
        Client configuration for retry strategies, timeouts, and connection pooling.
        If not provided, uses default WorkcellClientConfig settings.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `workcell_server_url: Optional[AnyUrl]`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `add_node(self, node_name: str, node_url: str, node_description: str = 'A Node', permanent: bool = False, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Add a node to the workcell.
        
        Parameters
        ----------
        node_name : str
            The name of the node.
        node_url : str
            The URL of the node.
        node_description : str, optional
            A description of the node, by default "A Node".
        permanent : bool, optional
            If True, add the node permanently, by default False.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Node
            The added node details.

    `async_cancel_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a workflow asynchronously.

    `async_get_active_workflows(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all active workflows asynchronously.

    `async_get_archived_workflows(self, number: int = 20, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get archived workflows asynchronously.

    `async_get_node(self, node_name: str, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Get details of a specific node asynchronously.

    `async_get_nodes(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get all nodes in the workcell asynchronously.

    `async_get_workcell_state(self, timeout: Optional[float] = None) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the full state of the workcell asynchronously.

    `async_get_workflow_definition(self, workflow_definition_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Get the definition of a workflow asynchronously.

    `async_get_workflow_queue(self, timeout: Optional[float] = None) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get the workflow queue asynchronously.

    `async_pause_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a workflow asynchronously.

    `async_query_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Check the status of a workflow using its ID asynchronously.

    `async_resume_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow asynchronously.

    `await_workflow(self, workflow_id: str, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, query_frequency: float = 2.0, display_mode: DisplayMode = 'auto') ‑> madsci.common.types.workflow_types.Workflow`
    :   Wait for a workflow to complete.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to wait for.
        prompt_on_error : bool, optional
            If True, prompt the user for action on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        query_frequency : float, optional
            How often to query the workflow status in seconds, by default 2.0.
        display_mode : DisplayMode, optional
            Display backend: "auto" (detect), "rich", "jupyter", or "plain".
        
        Returns
        -------
        Workflow
            The completed workflow object.

    `cancel_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to cancel.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The cancelled workflow object.

    `get_active_workflows(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.
        
        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_archived_workflows(self, number: int = 20, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.
        
        Parameters
        ----------
        number : int
            Number of archived workflows to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.
        
        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_node(self, node_name: str, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Get details of a specific node.
        
        Parameters
        ----------
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Node
            The node details.

    `get_nodes(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get all nodes in the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.

    `get_workcell_state(self, timeout: Optional[float] = None) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the full state of the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        WorkcellState
            The current state of the workcell.

    `get_workflow_definition(self, workflow_definition_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Get the definition of a workflow.
        
        Parameters
        ----------
        workflow_definition_id : str
            The ID of the workflow definition to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        WorkflowDefinition
            The workflow definition object.

    `get_workflow_queue(self, timeout: Optional[float] = None) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get the workflow queue from the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        list[Workflow]
            A list of queued workflows.

    `make_paths_absolute(self, files: dict[str, PathLike]) ‑> dict[str, pathlib.Path]`
    :   Extract file paths from a workflow definition.
        
        Parameters
        ----------
        files : dict[str, PathLike]
            A dictionary mapping unique file keys to their paths.
        
        Returns
        -------
        dict[str, Path]
            A dictionary mapping unique file keys to their paths.

    `pause_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to pause.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The paused workflow object.

    `query_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Check the status of a workflow using its ID.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to query.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Optional[Workflow]
            The workflow object if found, otherwise None.

    `resubmit_workflow(self, workflow_id: str, await_completion: bool = True, raise_on_cancelled: bool = True, raise_on_failed: bool = True, prompt_on_error: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resubmit a workflow as a brand new workflow run with the same parameters.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resubmit.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The new workflow object.

    `resume_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resume.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The resumed workflow object.

    `retry_workflow(self, workflow_id: str, index: int = 0, await_completion: bool = True, raise_on_cancelled: bool = True, raise_on_failed: bool = True, prompt_on_error: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Retry a workflow from a specific step.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to retry.
        index : int, optional
            The step index to retry from, by default -1 (retry the entire workflow).
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        dict
            The response from the Workcell Manager.

    `start_workflow(self, workflow_definition: Union[str, PathLike, WorkflowDefinition], json_inputs: Optional[dict[str, Any]] = None, file_inputs: Optional[dict[str, PathLike]] = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow(self, workflow_definition: Union[str, PathLike, WorkflowDefinition], json_inputs: Optional[dict[str, Any]] = None, file_inputs: Optional[dict[str, PathLike]] = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow_batch(self, workflows: list[str], json_inputs: list[dict[str, Any]] = [], file_inputs: list[dict[str, PathLike]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a batch of workflows to run concurrently.
        
        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.
        
        Returns
        -------
        list[Workflow]
            A list of completed workflow objects.

    `submit_workflow_definition(self, workflow_definition: Union[PathLike, WorkflowDefinition], timeout: Optional[float] = None) ‑> str`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition : Union[PathLike, WorkflowDefinition]
            The workflow definition to submit.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        str
            The ID of the submitted workflow.

    `submit_workflow_sequence(self, workflows: list[str], json_inputs: list[dict[str, Any]] = [], file_inputs: list[dict[str, PathLike]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a sequence of workflows to run in order.
        
        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.
        
        Returns
        -------
        list[Workflow]
            A list of submitted workflow objects.

`WorkflowClient(workcell_server_url: Optional[Union[str, AnyUrl]] = None, working_directory: str = './', event_client: Optional[EventClient] = None, config: Optional[WorkcellClientConfig] = None)`
:   A client for interacting with the Workcell Manager to perform various actions.
    
    Initialize the WorkcellClient.
    
    Parameters
    ----------
    workcell_server_url : Optional[Union[str, AnyUrl]]
        The base URL of the Workcell Manager. If not provided, it will be taken from the current MadsciContext.
    working_directory : str, optional
        The directory to look for relative paths. Defaults to "./".
    event_client : Optional[EventClient], optional
        Event client for logging. If not provided, a new one will be created.
    config : Optional[WorkcellClientConfig], optional
        Client configuration for retry strategies, timeouts, and connection pooling.
        If not provided, uses default WorkcellClientConfig settings.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `workcell_server_url: Optional[AnyUrl]`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

    ### Methods

    `add_node(self, node_name: str, node_url: str, node_description: str = 'A Node', permanent: bool = False, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Add a node to the workcell.
        
        Parameters
        ----------
        node_name : str
            The name of the node.
        node_url : str
            The URL of the node.
        node_description : str, optional
            A description of the node, by default "A Node".
        permanent : bool, optional
            If True, add the node permanently, by default False.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Node
            The added node details.

    `async_cancel_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a workflow asynchronously.

    `async_get_active_workflows(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all active workflows asynchronously.

    `async_get_archived_workflows(self, number: int = 20, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get archived workflows asynchronously.

    `async_get_node(self, node_name: str, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Get details of a specific node asynchronously.

    `async_get_nodes(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get all nodes in the workcell asynchronously.

    `async_get_workcell_state(self, timeout: Optional[float] = None) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the full state of the workcell asynchronously.

    `async_get_workflow_definition(self, workflow_definition_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Get the definition of a workflow asynchronously.

    `async_get_workflow_queue(self, timeout: Optional[float] = None) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get the workflow queue asynchronously.

    `async_pause_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a workflow asynchronously.

    `async_query_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Check the status of a workflow using its ID asynchronously.

    `async_resume_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow asynchronously.

    `await_workflow(self, workflow_id: str, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, query_frequency: float = 2.0, display_mode: DisplayMode = 'auto') ‑> madsci.common.types.workflow_types.Workflow`
    :   Wait for a workflow to complete.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to wait for.
        prompt_on_error : bool, optional
            If True, prompt the user for action on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        query_frequency : float, optional
            How often to query the workflow status in seconds, by default 2.0.
        display_mode : DisplayMode, optional
            Display backend: "auto" (detect), "rich", "jupyter", or "plain".
        
        Returns
        -------
        Workflow
            The completed workflow object.

    `cancel_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Cancel a workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to cancel.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The cancelled workflow object.

    `get_active_workflows(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.
        
        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_archived_workflows(self, number: int = 20, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.workflow_types.Workflow]`
    :   Get all workflows from the Workcell Manager.
        
        Parameters
        ----------
        number : int
            Number of archived workflows to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the long operations timeout from config.
        
        Returns
        -------
        dict[str, Workflow]
            A dictionary of workflow IDs and their details.

    `get_node(self, node_name: str, timeout: Optional[float] = None) ‑> madsci.common.types.node_types.Node`
    :   Get details of a specific node.
        
        Parameters
        ----------
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Node
            The node details.

    `get_nodes(self, timeout: Optional[float] = None) ‑> dict[str, madsci.common.types.node_types.Node]`
    :   Get all nodes in the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        dict[str, Node]
            A dictionary of node names and their details.

    `get_workcell_state(self, timeout: Optional[float] = None) ‑> madsci.common.types.workcell_types.WorkcellState`
    :   Get the full state of the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        WorkcellState
            The current state of the workcell.

    `get_workflow_definition(self, workflow_definition_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Get the definition of a workflow.
        
        Parameters
        ----------
        workflow_definition_id : str
            The ID of the workflow definition to retrieve.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        WorkflowDefinition
            The workflow definition object.

    `get_workflow_queue(self, timeout: Optional[float] = None) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Get the workflow queue from the workcell.
        
        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        list[Workflow]
            A list of queued workflows.

    `make_paths_absolute(self, files: dict[str, PathLike]) ‑> dict[str, pathlib.Path]`
    :   Extract file paths from a workflow definition.
        
        Parameters
        ----------
        files : dict[str, PathLike]
            A dictionary mapping unique file keys to their paths.
        
        Returns
        -------
        dict[str, Path]
            A dictionary mapping unique file keys to their paths.

    `pause_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Pause a workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to pause.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The paused workflow object.

    `query_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow | None`
    :   Check the status of a workflow using its ID.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to query.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Optional[Workflow]
            The workflow object if found, otherwise None.

    `resubmit_workflow(self, workflow_id: str, await_completion: bool = True, raise_on_cancelled: bool = True, raise_on_failed: bool = True, prompt_on_error: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resubmit a workflow as a brand new workflow run with the same parameters.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resubmit.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The new workflow object.

    `resume_workflow(self, workflow_id: str, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Resume a paused workflow.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to resume.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The resumed workflow object.

    `retry_workflow(self, workflow_id: str, index: int = 0, await_completion: bool = True, raise_on_cancelled: bool = True, raise_on_failed: bool = True, prompt_on_error: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Retry a workflow from a specific step.
        
        Parameters
        ----------
        workflow_id : str
            The ID of the workflow to retry.
        index : int, optional
            The step index to retry from, by default -1 (retry the entire workflow).
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        dict
            The response from the Workcell Manager.

    `start_workflow(self, workflow_definition: Union[str, PathLike, WorkflowDefinition], json_inputs: Optional[dict[str, Any]] = None, file_inputs: Optional[dict[str, PathLike]] = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow(self, workflow_definition: Union[str, PathLike, WorkflowDefinition], json_inputs: Optional[dict[str, Any]] = None, file_inputs: Optional[dict[str, PathLike]] = None, await_completion: bool = True, prompt_on_error: bool = True, raise_on_failed: bool = True, raise_on_cancelled: bool = True, timeout: Optional[float] = None) ‑> madsci.common.types.workflow_types.Workflow`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition: Optional[Union[PathLike, WorkflowDefinition]],
            Either a workflow definition ID, WorkflowDefinition or a path to a YAML file of one.
        parameters: Optional[dict[str, Any]] = None,
            Parameters to be inserted into the workflow.
        validate_only : bool, optional
            If True, only validate the workflow without submitting, by default False.
        await_completion : bool, optional
            If True, wait for the workflow to complete, by default True.
        prompt_on_error : bool, optional
            If True, prompt the user for what action to take on workflow errors, by default True.
        raise_on_failed : bool, optional
            If True, raise an exception if the workflow fails, by default True.
        raise_on_cancelled : bool, optional
            If True, raise an exception if the workflow is cancelled, by default True.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        Workflow
            The submitted workflow object.

    `submit_workflow_batch(self, workflows: list[str], json_inputs: list[dict[str, Any]] = [], file_inputs: list[dict[str, PathLike]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a batch of workflows to run concurrently.
        
        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.
        
        Returns
        -------
        list[Workflow]
            A list of completed workflow objects.

    `submit_workflow_definition(self, workflow_definition: Union[PathLike, WorkflowDefinition], timeout: Optional[float] = None) ‑> str`
    :   Submit a workflow to the Workcell Manager.
        
        Parameters
        ----------
        workflow_definition : Union[PathLike, WorkflowDefinition]
            The workflow definition to submit.
        timeout : Optional[float]
            Timeout in seconds for this request. If not provided, uses the default timeout from config.
        
        Returns
        -------
        str
            The ID of the submitted workflow.

    `submit_workflow_sequence(self, workflows: list[str], json_inputs: list[dict[str, Any]] = [], file_inputs: list[dict[str, PathLike]] = []) ‑> list[madsci.common.types.workflow_types.Workflow]`
    :   Submit a sequence of workflows to run in order.
        
        Parameters
        ----------
        workflows : list[str]
            A list of workflow definitions in YAML format.
        parameters : list[dict[str, Any]]
            A list of parameter dictionaries for each workflow.
        
        Returns
        -------
        list[Workflow]
            A list of submitted workflow objects.