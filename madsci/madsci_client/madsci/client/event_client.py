"""MADSci Event Handling."""

import contextlib
import inspect
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional, Union

import requests
from pydantic import ValidationError
from rich import print

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import PathLike
from madsci.common.types.event_types import Event, EventType
from madsci.common.utils import threaded_task


class EventClient:
    """A logger and event handler for MADSci system components."""

    def __init__(
        self,
        name: Optional[str] = None,
        log_level: int = logging.INFO,
        event_server: Optional[str] = None,
        source: Optional[OwnershipInfo] = None,
        log_dir: Optional[PathLike] = None,
    ) -> None:
        """Initialize the event logger."""
        if name:
            self.name = name
        else:
            # * See if there's a calling class we can name after
            stack = inspect.stack()
            parent = stack[1][0]
            if calling_self := parent.f_locals.get("self"):
                self.name = calling_self.__class__.__name__
            else:
                # * No luck, name after EventClient
                self.name = __name__
        self.name = name if name else __name__
        self.logger = logging.getLogger(self.name)
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".madsci" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logfile = self.log_dir / f"{self.name}.log"
        self.logger.setLevel(log_level)
        if len(self.logger.handlers) == 0:
            file_handler = logging.FileHandler(filename=str(self.logfile), mode="a+")
            self.logger.addHandler(file_handler)
        self.event_server = event_server
        self.source = source

    def get_log(self) -> dict[str, Event]:
        """Read the log"""
        events = {}
        with self.logfile.open() as log:
            for line in log.readlines():
                try:
                    event = Event.model_validate_json(line)
                    events[event.event_id] = event
                except ValidationError:
                    events.append(Event(event_type=EventType.UNKNOWN, event_data=line))
        return events

    def get_events(self, number: int = 100) -> dict[str, Event]:
        """Query the event server for a certain number of recent events. If no event server is configured, query the log file instead."""
        events = OrderedDict()
        if self.event_server:
            response = requests.get(self.event_server + "/events", timeout=10)
            if not response.ok:
                response.raise_for_status()
            print(response.json())
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

    def log(self, event: Union[Event, Any], level: Optional[int] = None) -> None:
        """Log an event."""

        # * If we've got a string or dict, check if it's a serialized event
        if isinstance(event, str):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate_json(event)
        if isinstance(event, dict):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate(**event)
        if not isinstance(event, Event):
            event = self._new_event_for_log(event, level)
        event.log_level = level if level else event.log_level
        event.source = event.source if event.source is not None else self.source
        self.logger.log(event.log_level, event.model_dump_json())
        if self.logger.getEffectiveLevel() <= event.log_level:
            print(f"{event.event_timestamp} ({event.event_type}): {event.event_data}")
        if self.event_server:
            self._send_event(event)

    def log_debug(self, event: Union[Event, str]) -> None:
        """Log an event at the debug level."""
        self.log(event, logging.DEBUG)

    def log_info(self, event: Union[Event, str]) -> None:
        """Log an event at the info level."""
        self.log(event, logging.INFO)

    def log_warning(self, event: Union[Event, str]) -> None:
        """Log an event at the warning level."""
        self.log(event, logging.WARNING)

    def log_error(self, event: Union[Event, str]) -> None:
        """Log an event at the error level."""
        self.log(event, logging.ERROR)

    def log_critical(self, event: Union[Event, str]) -> None:
        """Log an event at the critical level."""
        self.log(event, logging.CRITICAL)

    @threaded_task
    def _send_event_to_event_server(self, event: Event) -> None:
        """Send an event to the event manager."""
        response = requests.post(
            url=self.event_server + "/event",
            json=event.model_dump(mode="json"),
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()

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
        return Event(
            event_type=event_type,
            event_data=event_data,
        )
