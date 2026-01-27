Module madsci.client.event_client
=================================
MADSci Event Handling.

Classes
-------

`EventClient(config: madsci.common.types.event_types.EventClientConfig | None = None, **kwargs: Any)`
:   A logger and event handler for MADSci system components.

    Initialize the event logger. If no config is provided, use the default config.

    Keyword Arguments are used to override the values of the passed in/default config.

    ### Class variables

    `config: madsci.common.types.event_types.EventClientConfig | None`
    :

    ### Methods

    `alert(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the alert level.

    `critical(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the critical level.

    `debug(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the debug level.

    `error(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the error level.

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

    `info(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the info level.

    `log(self, event: madsci.common.types.event_types.Event | Any, level: int | None = None, alert: bool | None = None, warning_category: Warning | None = None) ‑> None`
    :   Log an event.

    `log_alert(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the alert level.

    `log_critical(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the critical level.

    `log_debug(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the debug level.

    `log_error(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the error level.

    `log_info(self, event: madsci.common.types.event_types.Event | str) ‑> None`
    :   Log an event at the info level.

    `log_warning(self, event: madsci.common.types.event_types.Event | str, warning_category: Warning = builtins.UserWarning) ‑> None`
    :   Log an event at the warning level.

    `query_events(self, selector: dict, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Query the event server for events based on a selector.

        Requires an event server be configured.

        Args:
            selector: Dictionary selector for filtering events.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `warn(self, event: madsci.common.types.event_types.Event | str, warning_category: Warning = builtins.UserWarning) ‑> None`
    :   Log an event at the warning level.

    `warning(self, event: madsci.common.types.event_types.Event | str, warning_category: Warning = builtins.UserWarning) ‑> None`
    :   Log an event at the warning level.
