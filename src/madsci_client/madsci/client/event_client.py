"""MADSci Event Handling."""

import contextlib
import copy
import gzip
import inspect
import json
import logging
import platform
import queue
import shutil
import sys
import time
import traceback
import warnings
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError, version
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Optional, Union

import requests
from madsci.client.structlog_config import create_instance_logger, get_log_level_value
from madsci.common.context import get_current_madsci_context
from madsci.common.otel import (
    OtelBootstrapConfig,
    configure_otel,
    current_trace_context,
)
from madsci.common.types.event_types import (
    Event,
    EventClientConfig,
    EventLogLevel,
    EventType,
)
from madsci.common.utils import create_http_session, threaded_task
from pydantic import BaseModel, ValidationError
from rich.logging import RichHandler


def get_madsci_version() -> str:
    """Get the installed MADSci version.

    Returns:
        The installed version string, or "unknown (development mode)" if not installed.
    """
    try:
        return version("madsci_client")
    except PackageNotFoundError:
        return "unknown (development mode)"


class EventClient:
    """A logger and event handler for MADSci system components.

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
    """

    config: EventClientConfig
    _bound_context: dict[str, Any]

    def __init__(
        self,
        config: Optional[EventClientConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the event logger. If no config is provided, use the default config.

        Keyword Arguments are used to override the values of the passed in/default config.
        """
        if kwargs:
            self.config = (
                EventClientConfig(**kwargs)
                if not config
                else config.model_copy(update=kwargs)
            )
        else:
            self.config = config or EventClientConfig()
        if self.config.name:
            self.name = self.config.name
        else:
            # * See if there's a calling module we can name after
            stack = inspect.stack()
            parent = stack[1][0]
            if calling_module := parent.f_globals.get("__name__"):
                self.name = calling_module
            else:
                # * No luck, name after EventClient
                self.name = __name__
        self.name = str(self.name)

        # Initialize bound context
        self._bound_context = {}

        # Initialize thread-safety primitives (per-instance to avoid shared state)
        self._event_buffer: queue.Queue = queue.Queue()
        self._buffer_lock: Lock = Lock()
        self._retry_thread: Optional[Thread] = None
        self._retrying: bool = False
        self._shutdown: bool = False

        # Set up log directory and file
        self.log_dir = Path(self.config.log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logfile = self.log_dir / f"{self.name}.log"

        # Create the stdlib logger for file handling
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(get_log_level_value(self.config.log_level))
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        file_handler = self._create_file_handler()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(RichHandler(rich_tracebacks=True, show_path=False))

        # Create structlog logger for structured logging
        self._structlog_logger = create_instance_logger(
            name=self.name,
            output_format=self.config.log_output_format,
            log_level=get_log_level_value(self.config.log_level),
            include_otel_context=self.config.otel_enabled,
        )

        self.event_server = (
            self.config.event_server_url
            or get_current_madsci_context().event_server_url
        )

        # Create HTTP session for requests to event server
        self.session = create_http_session(config=self.config)

        self._otel_runtime = None
        if self.config.otel_enabled:
            self._setup_otel()

        # Log startup information
        self._log_startup_info()

    def _setup_otel(self) -> None:
        try:
            self._otel_runtime = configure_otel(
                OtelBootstrapConfig(
                    enabled=True,
                    service_name=self.config.otel_service_name or self.name,
                    service_version=get_madsci_version(),
                    exporter=self.config.otel_exporter,
                    otlp_endpoint=self.config.otel_endpoint,
                    otlp_protocol=self.config.otel_protocol,
                    metric_export_interval_ms=self.config.otel_metric_export_interval_ms,
                )
            )
        except Exception as e:
            self._otel_runtime = None
            self.logger.warning(
                "OpenTelemetry setup failed; continuing without OTEL", exc_info=e
            )

    def _log_startup_info(self) -> None:
        """Log startup information on first initialization.

        Logs MADSci version, client configuration, and environment info
        to help with debugging and auditing.
        """
        startup_info = {
            "madsci_version": get_madsci_version(),
            "client_name": self.name,
            "event_server": str(self.event_server)
            if self.event_server
            else "Not configured",
            "log_dir": str(self.log_dir),
            "log_level": self.config.log_level.name
            if hasattr(self.config.log_level, "name")
            else str(self.config.log_level),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }

        self.logger.info(f"EventClient initialized: {startup_info}")

    def _create_file_handler(self) -> logging.Handler:
        """Create the appropriate file handler based on rotation config.

        Returns:
            A logging handler configured for file output with optional rotation.
        """
        handler: logging.Handler

        if self.config.log_rotation_type == "none":
            handler = logging.FileHandler(filename=str(self.logfile), mode="a+")
        elif self.config.log_rotation_type == "size":
            handler = RotatingFileHandler(
                filename=str(self.logfile),
                maxBytes=self.config.log_max_bytes,
                backupCount=self.config.log_backup_count,
            )
            if self.config.log_compression_enabled:
                handler.rotator = self._compress_rotated_log
                handler.namer = self._rotated_log_namer
        elif self.config.log_rotation_type == "time":
            handler = TimedRotatingFileHandler(
                filename=str(self.logfile),
                when=self.config.log_rotation_when,
                interval=self.config.log_rotation_interval,
                backupCount=self.config.log_backup_count,
            )
            if self.config.log_compression_enabled:
                handler.rotator = self._compress_rotated_log
                handler.namer = self._rotated_log_namer
        else:
            # Fallback to basic file handler (should not happen due to validation)
            handler = logging.FileHandler(filename=str(self.logfile), mode="a+")

        return handler

    def _compress_rotated_log(self, source: str, dest: str) -> None:
        """Compress a rotated log file with gzip.

        Args:
            source: Path to the source log file to compress.
            dest: Path to the destination compressed file.
        """
        source_path = Path(source)
        with source_path.open("rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        source_path.unlink()

    def _rotated_log_namer(self, name: str) -> str:
        """Add .gz extension to rotated log file names.

        Args:
            name: The original rotated log file name.

        Returns:
            The file name with .gz extension appended.
        """
        return name + ".gz"

    def __del__(self) -> None:
        """Clean up retry thread on destruction."""
        with self._buffer_lock:
            self._shutdown = True

        # Wait for retry thread to finish if it exists
        if self._retry_thread is not None and self._retry_thread.is_alive():
            # Give the thread a reasonable time to finish (5 seconds)
            self._retry_thread.join(timeout=5.0)
            if self._retry_thread.is_alive():
                # Log warning if thread didn't finish cleanly
                self.logger.warning(
                    "Retry thread did not terminate within timeout during cleanup"
                )

    # ==================== Context Binding ====================

    def bind(self, **context: Any) -> "EventClient":
        """Create a new client with additional bound context.

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
        """
        new_client = copy.copy(self)
        new_client._bound_context = {**self._bound_context, **context}
        new_client._structlog_logger = self._structlog_logger.bind(**context)
        return new_client

    def unbind(self, *keys: str) -> "EventClient":
        """Create a new client with specified context keys removed.

        Args:
            *keys: Keys to remove from the bound context

        Returns:
            New EventClient instance without the specified context keys
        """
        new_client = copy.copy(self)
        new_client._bound_context = {
            k: v for k, v in self._bound_context.items() if k not in keys
        }
        new_client._structlog_logger = self._structlog_logger.unbind(*keys)
        return new_client

    # ==================== Error Handling ====================

    def _handle_error(self, error: Exception, context: str) -> None:
        """Handle errors based on fail_on_error configuration.

        Args:
            error: The exception that occurred
            context: Description of what operation failed

        Raises:
            The original exception if fail_on_error is True
        """
        error_msg = f"{context}: {error}"

        if self.config.fail_on_error:
            # Re-raise with context
            raise type(error)(error_msg) from error
        # Log silently and continue
        # Use stderr to avoid infinite recursion if logging itself fails
        sys.stderr.write(f"[EventClient Warning] {error_msg}\n")

    # ==================== Idiomatic Structlog API ====================

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.debug(message, **combined_context)
            self._maybe_send_to_server(message, EventLogLevel.DEBUG, **kwargs)
        except Exception as e:
            self._handle_error(e, "Failed to log debug message")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.info(message, **combined_context)
            self._maybe_send_to_server(message, EventLogLevel.INFO, **kwargs)
        except Exception as e:
            self._handle_error(e, "Failed to log info message")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.warning(message, **combined_context)
            self._maybe_send_to_server(message, EventLogLevel.WARNING, **kwargs)
        except Exception as e:
            self._handle_error(e, "Failed to log warning message")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.error(message, **combined_context)
            self._maybe_send_to_server(message, EventLogLevel.ERROR, **kwargs)
        except Exception as e:
            self._handle_error(e, "Failed to log error message")

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.critical(message, **combined_context)
            self._maybe_send_to_server(message, EventLogLevel.CRITICAL, **kwargs)
        except Exception as e:
            self._handle_error(e, "Failed to log critical message")

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an exception with traceback.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log entry
        """
        try:
            combined_context = {**self._bound_context, **kwargs}
            self._structlog_logger.exception(message, **combined_context)
            self._maybe_send_to_server(
                message, EventLogLevel.ERROR, exc_info=True, **kwargs
            )
        except Exception as e:
            self._handle_error(e, "Failed to log exception")

    # ==================== Backward Compatible Aliases ====================

    def log_debug(self, event: Union[Event, str], **kwargs: Any) -> None:
        """Log an event at the debug level.

        Alias for debug(). Provided for backward compatibility.
        """
        if isinstance(event, Event):
            self.log(event, logging.DEBUG)
        else:
            self.debug(str(event), **kwargs)

    def log_info(self, event: Union[Event, str], **kwargs: Any) -> None:
        """Log an event at the info level.

        Alias for info(). Provided for backward compatibility.
        """
        if isinstance(event, Event):
            self.log(event, logging.INFO)
        else:
            self.info(str(event), **kwargs)

    def log_warning(
        self,
        event: Union[Event, str],
        warning_category: Optional[type] = UserWarning,
        **kwargs: Any,
    ) -> None:
        """Log an event at the warning level.

        Args:
            event: The event or message to log
            warning_category: Optional warning category for warnings module integration
            **kwargs: Additional structured data
        """
        if isinstance(event, Event):
            self.log(event, logging.WARNING, warning_category=warning_category)
        else:
            if warning_category and self.logger.getEffectiveLevel() <= logging.WARNING:
                # Warn via the warnings module
                warnings.warn(
                    str(event),
                    category=warning_category,
                    stacklevel=3,
                )
            self.warning(str(event), **kwargs)

    # Backward compatible alias - warn points to log_warning for warning_category support
    warn = log_warning

    def log_error(self, event: Union[Event, str], **kwargs: Any) -> None:
        """Log an event at the error level.

        Alias for error(). Provided for backward compatibility.
        """
        if isinstance(event, Event):
            self.log(event, logging.ERROR)
        else:
            self.error(str(event), **kwargs)

    def log_critical(self, event: Union[Event, str], **kwargs: Any) -> None:
        """Log an event at the critical level.

        Alias for critical(). Provided for backward compatibility.
        """
        if isinstance(event, Event):
            self.log(event, logging.CRITICAL)
        else:
            self.critical(str(event), **kwargs)

    def log_alert(self, event: Union[Event, str], **kwargs: Any) -> None:
        """Log an event at the alert level (critical with alert flag).

        Args:
            event: The event or message to log
            **kwargs: Additional structured data
        """
        if isinstance(event, Event):
            self.log(event, alert=True)
        else:
            self.critical(str(event), alert=True, **kwargs)
            self._maybe_send_to_server(
                str(event), EventLogLevel.CRITICAL, alert=True, **kwargs
            )

    alert = log_alert

    # ==================== Event Server Communication ====================

    def _maybe_send_to_server(
        self,
        message: str,
        level: EventLogLevel,
        alert: bool = False,
        **context: Any,
    ) -> None:
        """Optionally send event to event server with error handling.

        Args:
            message: The log message
            level: The log level
            alert: Whether this is an alert
            **context: Additional context to include
        """
        if not self.event_server:
            return

        try:
            log_level_value = get_log_level_value(self.config.log_level)
            if level.value < log_level_value:
                return

            # Determine event type based on level
            event_type = EventType.LOG
            if level == EventLogLevel.DEBUG:
                event_type = EventType.LOG_DEBUG
            elif level == EventLogLevel.INFO:
                event_type = EventType.LOG_INFO
            elif level == EventLogLevel.WARNING:
                event_type = EventType.LOG_WARNING
            elif level == EventLogLevel.ERROR:
                event_type = EventType.LOG_ERROR
            elif level == EventLogLevel.CRITICAL:
                event_type = EventType.LOG_CRITICAL

            # Combine bound context with event context
            event_data = {
                "message": message,
                **self._bound_context,
                **context,
            }

            if self._otel_runtime and self._otel_runtime.enabled:
                trace_ctx = current_trace_context()
            else:
                trace_ctx = {"trace_id": None, "span_id": None}

            event = Event(
                event_type=event_type,
                event_data=event_data,
                log_level=level,
                alert=alert,
                source=self.config.source,
                trace_id=trace_ctx.get("trace_id"),
                span_id=trace_ctx.get("span_id"),
            )

            self._send_event_to_event_server_task(event)
        except Exception as e:
            self._handle_error(e, "Failed to send event to server")

    # ==================== Legacy Log Method ====================

    def get_log(self) -> dict[str, Event]:
        """Read the log"""
        events = {}
        with self.logfile.open() as log:
            for line in log.readlines():
                try:
                    event = Event.model_validate_json(line)
                except ValidationError:
                    event = Event(event_type=EventType.UNKNOWN, event_data=line)
                events[event.event_id] = event
        return events

    def get_event(
        self, event_id: str, timeout: Optional[float] = None
    ) -> Optional[Event]:
        """
        Get a specific event by ID.

        Args:
            event_id: The ID of the event to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        if self.event_server:
            response = self.session.get(
                str(self.event_server) + f"event/{event_id}",
                timeout=timeout or self.config.timeout_default,
            )
            if not response.ok:
                response.raise_for_status()
            return Event.model_validate(response.json())
        events = self.get_log()
        return events.get(event_id, None)

    def get_events(
        self, number: int = 100, level: int = -1, timeout: Optional[float] = None
    ) -> dict[str, Event]:
        """
        Query the event server for a certain number of recent events.

        If no event server is configured, query the log file instead.

        Args:
            number: Number of events to retrieve.
            level: Log level filter. -1 uses effective log level.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        if level == -1:
            level = int(self.logger.getEffectiveLevel())
        events = OrderedDict()
        if self.event_server:
            response = self.session.get(
                str(self.event_server) + "events",
                timeout=timeout or self.config.timeout_default,
                params={"number": number, "level": level},
            )
            if not response.ok:
                response.raise_for_status()
            for key, value in response.json().items():
                events[key] = Event.model_validate(value)
            return dict(events)
        events = self.get_log()
        selected_events = {}
        for event in reversed(list(events.values())):
            selected_events[event.event_id] = event
            if len(selected_events) >= number:
                break
        return selected_events

    def query_events(
        self, selector: dict, timeout: Optional[float] = None
    ) -> dict[str, Event]:
        """
        Query the event server for events based on a selector.

        Requires an event server be configured.

        Args:
            selector: Dictionary selector for filtering events.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        events = OrderedDict()
        if self.event_server:
            response = self.session.post(
                str(self.event_server) + "events/query",
                timeout=timeout or self.config.timeout_default,
                params={"selector": selector},
            )
            if not response.ok:
                response.raise_for_status()
            for key, value in response.json().items():
                events[key] = Event.model_validate(value)
            return dict(events)
        self.logger.warning("No event server configured. Cannot query events.")
        return {}

    def log(
        self,
        event: Union[Event, Any],
        level: Optional[int] = None,
        alert: Optional[bool] = None,
        warning_category: Optional[type] = None,
    ) -> None:
        """Log an event.

        This is the legacy interface. For structured logging, prefer using
        the new methods: debug(), info(), warning(), error(), critical().

        Args:
            event: Event object, string, dict, or other data to log
            level: Log level (defaults to event's level or INFO)
            alert: Whether to force an alert
            warning_category: Optional warning category for warnings module
        """
        # * If we've got a string or dict, check if it's a serialized event
        if isinstance(event, str):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate_json(event)
        if isinstance(event, dict):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate(event)
        if isinstance(event, Exception):
            event = Event(
                event_type=EventType.LOG_ERROR,
                event_data=traceback.format_exc(),
                log_level=logging.ERROR,
            )
        if not isinstance(event, Event):
            event = self._new_event_for_log(event, level or logging.INFO)

        event = Event.model_validate(event)
        event.log_level = level if level is not None else event.log_level
        event.alert = alert if alert is not None else event.alert
        if warning_category and self.logger.getEffectiveLevel() <= logging.WARNING:
            # * Warn via the warnings module
            warnings.warn(
                event.event_data,
                category=warning_category,
                stacklevel=3,
            )
        else:
            self.logger.log(level=event.log_level, msg=event.model_dump_json())
        # * Log the event to the event server if configured
        # * Only log if the event is at the same level or higher than the logger
        if self.logger.getEffectiveLevel() <= event.log_level and self.event_server:
            self._send_event_to_event_server_task(event)

    # ==================== Utilization Methods ====================

    def get_utilization_periods(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago",
        include_users: bool = True,
        csv_export: bool = False,
        save_to_file: bool = False,
        output_path: Optional[str] = None,
    ) -> Optional[Union[dict[str, Any], str]]:
        """
        Get time-series utilization analysis with periodic breakdowns, optionally export to CSV.

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
        """
        if not self.event_server:
            self.logger.warning("No event server configured.")
            return None

        try:
            params = {
                "analysis_type": analysis_type,
                "user_timezone": user_timezone,
                "include_users": str(include_users).lower(),
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            if csv_export:
                params["csv_format"] = "true"
                if save_to_file and output_path:
                    params["save_to_file"] = "true"
                    params["output_path"] = output_path

            response = self.session.get(
                str(self.event_server) + "utilization/periods",
                params=params,
                timeout=self.config.timeout_data_operations,
            )
            if not response.ok:
                self.logger.error(
                    f"Error getting utilization periods: HTTP {response.status_code}"
                )
                response.raise_for_status()

            # Handle CSV response - check if content type contains 'text/csv'
            content_type = response.headers.get("content-type", "").lower()
            if csv_export and "text/csv" in content_type:
                return response.text

            # Handle JSON response (either regular JSON or file save results)
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Error getting utilization periods: {e}")
            return None

    def get_session_utilization(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_export: bool = False,
        save_to_file: bool = False,
        output_path: Optional[str] = None,
    ) -> Optional[Union[dict[str, Any], str]]:
        """
        Get session-based utilization report, optionally export to CSV.

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
        """
        if not self.event_server:
            return None

        try:
            params = {}
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            if csv_export:
                params["csv_format"] = "true"
                if save_to_file and output_path:
                    params["save_to_file"] = "true"
                    params["output_path"] = output_path

            response = self.session.get(
                str(self.event_server) + "utilization/sessions",
                params=params,
                timeout=self.config.timeout_long_operations,
            )

            if not response.ok:
                response.raise_for_status()

            # Handle CSV response - check if content type contains 'text/csv'
            content_type = response.headers.get("content-type", "").lower()
            if csv_export and "text/csv" in content_type:
                return response.text

            # Handle JSON response (either regular JSON or file save results)
            return response.json()

        except requests.RequestException:
            return None

    def get_user_utilization_report(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_export: bool = False,
        save_to_file: bool = False,
        output_path: Optional[str] = None,
    ) -> Optional[Union[dict[str, Any], str]]:
        """
        Get detailed user utilization report from the event server, optionally export to CSV.

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
        """
        if not self.event_server:
            self.logger.warning("No event server configured.")
            return None

        try:
            params = {}
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            if csv_export:
                params["csv_format"] = "true"
                if save_to_file and output_path:
                    params["save_to_file"] = "true"
                    params["output_path"] = output_path

            response = self.session.get(
                str(self.event_server) + "utilization/users",
                params=params,
                timeout=self.config.timeout_long_operations,
            )

            if not response.ok:
                self.logger.error(
                    f"Error getting user utilization report: HTTP {response.status_code}"
                )
                response.raise_for_status()

            # Handle CSV response - check if content type contains 'text/csv'
            content_type = response.headers.get("content-type", "").lower()
            if csv_export and "text/csv" in content_type:
                return response.text

            # Handle JSON response (either regular JSON or file save results)
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Error getting user utilization report: {e}")
            return None

    # ==================== Internal Methods ====================

    def _start_retry_thread(self) -> None:
        with self._buffer_lock:
            if not self._retrying:
                self._retrying = True
                self._retry_thread = Thread(
                    target=self._retry_buffered_events, daemon=True
                )
                self._retry_thread.start()

    def _retry_buffered_events(self) -> None:
        backoff = 2
        max_backoff = 60
        while not self._event_buffer.empty() and not self._shutdown:
            try:
                event = self._event_buffer.get()
                self._send_event_to_event_server(event, retrying=True)
                backoff = 2  # Reset backoff on success
            except Exception:
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                self._event_buffer.put(event)  # Re-add the event to the buffer
        with self._buffer_lock:
            self._retrying = False

    @threaded_task
    def _send_event_to_event_server_task(
        self, event: Event, retrying: bool = False
    ) -> None:
        """Send an event to the event manager. Buffer on failure."""
        try:
            self._send_event_to_event_server(event, retrying=retrying)
        except Exception as e:
            self.logger.error(f"Error in _send_event_to_event_server_task: {e}")

    def _send_event_to_event_server(self, event: Event, retrying: bool = False) -> None:
        """Send an event to the event manager. Buffer on failure."""

        try:
            headers: dict[str, str] = {}
            if self._otel_runtime and self._otel_runtime.enabled:
                with contextlib.suppress(Exception):
                    from opentelemetry.propagate import inject  # noqa: PLC0415

                    inject(headers)
            response = self.session.post(
                url=f"{self.event_server}event",
                json=event.model_dump(mode="json"),
                headers=headers,
                timeout=self.config.timeout_default,
            )

            if not response.ok:
                response.raise_for_status()

        except Exception:
            if not retrying:
                self._event_buffer.put(event)
                self._start_retry_thread()
            else:
                # If already retrying, just re-raise to trigger backoff
                raise

    def _new_event_for_log(self, event_data: Any, level: int) -> Event:
        """Create a new log event from arbitrary data"""
        event_type = EventType.LOG
        if level == logging.DEBUG:
            event_type = EventType.LOG_DEBUG
        elif level == logging.INFO:
            event_type = EventType.LOG_INFO
        elif level == logging.WARNING:
            event_type = EventType.LOG_WARNING
        elif level == logging.ERROR:
            event_type = EventType.LOG_ERROR
        elif level == logging.CRITICAL:
            event_type = EventType.LOG_CRITICAL
        if isinstance(event_data, BaseModel):
            event_data = event_data.model_dump(mode="json")
        elif isinstance(event_data, dict):
            # Keep dict as-is
            pass
        else:
            try:
                event_data = json.dumps(event_data, default=str)
            except Exception:
                try:
                    event_data = str(event_data)
                except Exception:
                    event_data = {
                        "error": "Error during logging. Unable to serialize event data."
                    }
        return Event(
            event_type=event_type,
            event_data=event_data,
        )
