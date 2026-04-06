Module madsci.client.event_client
=================================
MADSci Event Handling.

Functions
---------

`get_madsci_version() ‑> str`
:   Get the installed MADSci version.
    
    Returns:
        The installed version string, or "unknown (development mode)" if not installed.

Classes
-------

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