Module madsci.client.cli.commands.logs
======================================
MADSci CLI logs command.

View and aggregate logs from MADSci services, using the shared utility layer
for timestamp formatting, level colouring, and output rendering.

Functions
---------

`fetch_logs_from_event_manager(base_url: str, limit: int = 100, level: str | None = None, source: str | None = None, since: datetime | None = None, grep: str | None = None, timeout: float = 10.0) ‑> list[dict[str, typing.Any]]`
:   Fetch logs from the Event Manager using EventClient.
    
    Args:
        base_url: Base URL for the Event Manager.
        limit: Maximum number of events to retrieve.
        level: Minimum log level name (e.g. ``"error"``). Passed to
            EventClient and also applied by the caller via ``filter_logs``.
        source: Source service name. Not supported server-side; the caller
            applies this filter after fetching.
        since: Only return events after this datetime. Applied client-side.
        grep: Search pattern. Applied client-side by the caller via
            ``filter_logs``.
        timeout: Request timeout in seconds.
    
    Returns:
        List of log entry dictionaries.

`filter_logs(logs: list[dict[str, Any]], level: str | None = None, grep: str | None = None) ‑> list[dict[str, typing.Any]]`
:   Filter logs locally.

`format_log_entry(entry: dict[str, Any], show_timestamps: bool = True, no_color: bool = False) ‑> Any`
:   Format a log entry for display using shared formatting utilities.

`parse_duration(duration: str) ‑> datetime.timedelta`
:   Parse a duration string into a timedelta.