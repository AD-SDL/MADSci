"""MADSci Event Handling."""

import contextlib
import inspect
import json
import logging
import queue
import time
import warnings
from collections import OrderedDict
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Optional, Union

import requests
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import (
    Event,
    EventClientConfig,
    EventType,
    UtilizationSummary,
)
from madsci.common.utils import threaded_task
from pydantic import BaseModel, ValidationError
from rich import print


class EventClient:
    """A logger and event handler for MADSci system components."""

    config: Optional[EventClientConfig] = None
    _event_buffer = queue.Queue()
    _buffer_lock = Lock()
    _retry_thread = None
    _retrying = False

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
                EventClientConfig(**kwargs) if not config else config.__init__(**kwargs)
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
        self.logger = logging.getLogger(self.name)
        self.log_dir = Path(self.config.log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logfile = self.log_dir / f"{self.name}.log"
        self.logger.setLevel(self.config.log_level)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(
                self.logfile
            ):
                self.logger.removeHandler(handler)
        file_handler = logging.FileHandler(filename=str(self.logfile), mode="a+")
        self.logger.addHandler(file_handler)
        self.event_server = (
            self.config.event_server_url or MadsciContext().event_server_url
        )
        self.log_debug(
            "Event logger {self.name} initialized.",
        )
        self.log_debug(self.config)

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

    def get_events(self, number: int = 100, level: int = -1) -> dict[str, Event]:
        """Query the event server for a certain number of recent events. If no event server is configured, query the log file instead."""
        if level == -1:
            level = int(self.logger.getEffectiveLevel())
        events = OrderedDict()
        if self.event_server:
            response = requests.get(
                str(self.event_server) + "/events",
                timeout=10,
                params={"number": number, "level": level},
            )
            if not response.ok:
                response.raise_for_status()
            # print(response.json())
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

    def query_events(self, selector: dict) -> dict[str, Event]:
        """Query the event server for events based on a selector. Requires an event server be configured."""
        events = OrderedDict()
        if self.event_server:
            response = requests.post(
                str(self.event_server) + "/events/query",
                timeout=10,
                params={"selector": selector},
            )
            if not response.ok:
                response.raise_for_status()
            for key, value in response.json().items():
                events[key] = Event.model_validate(value)
            return dict(events)
        raise ValueError("No event server configured, cannot query events.")
    
    def get_utilization_summary(self) -> Optional[UtilizationSummary]:
        """Get current utilization summary from the event server."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization summary.")
        
        try:
            response = requests.get(
                str(self.event_server) + "/utilization/summary",
                timeout=10,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Utilization tracking error: {data['error']}")
                return None
            
            return UtilizationSummary.model_validate(data)
        except requests.RequestException as e:
            print(f"Error getting utilization summary: {e}")
            return None

    def query_utilization_events(self, hours_back: int = 24, utilization_type: Optional[str] = None) -> dict[str, Event]:
        """Query utilization events from the past N hours."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot query utilization events.")
        
        try:
            response = requests.post(
                str(self.event_server) + "/events/query/utilization",
                json={"hours_back": hours_back, "utilization_type": utilization_type},
                timeout=10,
            )
            if not response.ok:
                response.raise_for_status()
            
            events = {}
            for key, value in response.json().items():
                events[key] = Event.model_validate(value)
            return events
        except requests.RequestException as e:
            print(f"Error querying utilization events: {e}")
            return {}

    def get_system_utilization_graph(self, hours_back: int = 24) -> Optional[str]:
        """Get system utilization graph as base64 encoded PNG."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization graph.")
        
        try:
            response = requests.get(
                str(self.event_server) + "/utilization/graphs/system",
                params={"hours_back": hours_back},
                timeout=30,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Graph generation error: {data['error']}")
                return None
            
            return data.get("graph")
        except requests.RequestException as e:
            print(f"Error getting system utilization graph: {e}")
            return None

    def get_node_utilization_graph(self, node_id: str, hours_back: int = 24) -> Optional[str]:
        """Get node utilization graph as base64 encoded PNG."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization graph.")
        
        try:
            response = requests.get(
                str(self.event_server) + f"/utilization/graphs/node/{node_id}",
                params={"hours_back": hours_back},
                timeout=30,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Graph generation error: {data['error']}")
                return None
            
            return data.get("graph")
        except requests.RequestException as e:
            print(f"Error getting node utilization graph: {e}")
            return None

    def get_node_comparison_graph(self, hours_back: int = 24, max_nodes: int = 6) -> Optional[str]:
        """Get multi-node comparison graph as base64 encoded PNG."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization graph.")
        
        try:
            response = requests.get(
                str(self.event_server) + "/utilization/graphs/comparison",
                params={"hours_back": hours_back, "max_nodes": max_nodes},
                timeout=30,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Graph generation error: {data['error']}")
                return None
            
            return data.get("graph")
        except requests.RequestException as e:
            print(f"Error getting node comparison graph: {e}")
            return None

    def get_utilization_heatmap(self, hours_back: int = 24) -> Optional[str]:
        """Get utilization heatmap as base64 encoded PNG."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization graph.")
        
        try:
            response = requests.get(
                str(self.event_server) + "/utilization/graphs/heatmap",
                params={"hours_back": hours_back},
                timeout=30,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Graph generation error: {data['error']}")
                return None
            
            return data.get("graph")
        except requests.RequestException as e:
            print(f"Error getting utilization heatmap: {e}")
            return None

    def get_utilization_report(self, hours_back: int = 24) -> Optional[dict[str, Any]]:
        """Get comprehensive utilization report with statistics and graphs."""
        if not self.event_server:
            raise ValueError("No event server configured, cannot get utilization report.")
        
        try:
            response = requests.get(
                str(self.event_server) + "/utilization/report",
                params={"hours_back": hours_back},
                timeout=60,
            )
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                print(f"Report generation error: {data['error']}")
                return None
            
            return data
        except requests.RequestException as e:
            print(f"Error getting utilization report: {e}")
            return None

    def save_graph_to_file(self, graph_base64: str, filename: str) -> bool:
        """Save a base64 encoded graph to a PNG file."""
        try:
            import base64
            
            # Decode base64 and save to file
            graph_data = base64.b64decode(graph_base64)
            
            with open(filename, 'wb') as f:
                f.write(graph_data)
            
            print(f"Graph saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving graph to file: {e}")
            return False

    def log(
        self,
        event: Union[Event, Any],
        level: Optional[int] = None,
        alert: Optional[bool] = None,
        warning_category: Optional[Warning] = None,
    ) -> None:
        """Log an event."""

        # * If we've got a string or dict, check if it's a serialized event
        if isinstance(event, str):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate_json(event)
        if isinstance(event, dict):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate(event)
        if isinstance(event, Exception):
            import traceback

            event = Event(
                event_type=EventType.LOG_ERROR,
                event_data=traceback.format_exc(),
            )
        if not isinstance(event, Event):
            event = self._new_event_for_log(event, level)
        event.log_level = level if level else event.log_level
        event.alert = alert if alert is not None else event.alert
        if warning_category:
            warnings.warn(
                event.model_dump_json(),
                category=warning_category,
                stacklevel=3,
            )
        self.logger.log(event.log_level, event.model_dump_json())
        # * Log the event to the event server if configured
        # * Only log if the event is at the same level or higher than the logger
        if self.logger.getEffectiveLevel() <= event.log_level:
            print(f"{event.event_timestamp} ({event.event_type}): {event.event_data}")
            if self.event_server:
                print("Sending event to event server...")
                self._send_event_to_event_server_task(event)
            else:
                print("DEBUG CLIENT: No event_server configured")  # ADD THIS LINE

    def log_debug(self, event: Union[Event, str]) -> None:
        """Log an event at the debug level."""
        self.log(event, logging.DEBUG)

    debug = log_debug

    def log_info(self, event: Union[Event, str]) -> None:
        """Log an event at the info level."""
        self.log(event, logging.INFO)

    info = log_info

    def log_warning(
        self, event: Union[Event, str], warning_category: Warning = UserWarning
    ) -> None:
        """Log an event at the warning level."""
        self.log(event, logging.WARNING, warning_category=warning_category)

    warning = log_warning
    warn = log_warning

    def log_error(self, event: Union[Event, str]) -> None:
        """Log an event at the error level."""
        self.log(event, logging.ERROR)

    error = log_error

    def log_critical(self, event: Union[Event, str]) -> None:
        """Log an event at the critical level."""
        self.log(event, logging.CRITICAL)

    critical = log_critical

    def log_alert(self, event: Union[Event, str]) -> None:
        """Log an event at the alert level."""
        self.log(event, alert=True)

    alert = log_alert

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
        while not self._event_buffer.empty():
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
        print(f"DEBUG CLIENT: _send_event_to_event_server_task called for {event.event_type}")
        try:
            self._send_event_to_event_server(event, retrying=retrying)
            print(f"DEBUG CLIENT: Successfully sent {event.event_type}")
        except Exception as e:
            print(f"DEBUG CLIENT: Error in _send_event_to_event_server_task: {e}")

    def _send_event_to_event_server(self, event: Event, retrying: bool = False) -> None:
        """Send an event to the event manager. Buffer on failure."""
        print(f"DEBUG CLIENT: _send_event_to_event_server called for {event.event_type}")
  
        try:
            response = requests.post(
                url=f"{str(self.event_server).rstrip('/')}/event",
                json=event.model_dump(mode="json"),
                timeout=10,
            )
            print(f"DEBUG CLIENT: Response status: {response.status_code}")

            if not response.ok:
                print(f"DEBUG CLIENT: Response error: {response.text}")
                response.raise_for_status()
            else:
                print(f"DEBUG CLIENT: Event sent successfully!")
    
        except Exception as e:
            print(f"DEBUG CLIENT: Exception occurred: {e}")
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
    