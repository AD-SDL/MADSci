"""MADSci Event Handling."""

import contextlib
import logging
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import ValidationError
from rich import print

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import PathLike
from madsci.common.types.event_types import Event, EventType


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

    def get_log(self) -> list[Event]:
        """Read the log"""
        events = []
        with self.logfile.open() as log:
            for line in log.readlines():
                try:
                    events.append(Event.model_validate_json(line))
                except ValidationError:
                    events.append(Event(event_type=EventType.UNKNOWN, event_data=line))
        return events

    def log(self, event: Union[Event, Any], level: Optional[int] = None) -> None:
        """Log an event."""

        # * If we've got a string, check if it's a serialized event
        if isinstance(event, str):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate_json(event)
        if isinstance(event, dict):
            with contextlib.suppress(ValidationError):
                event = Event.model_validate(**event)
        if not isinstance(event, Event):
            event = Event(
                event_type=EventType.LOG,
                event_data=event,
            )
        event.log_level = level if level else event.log_level
        event.source = event.source if event.source is not None else self.source
        self.logger.log(event.log_level, event.model_dump_json())
        if self.logger.getEffectiveLevel() <= event.log_level:
            print(
                f"{event.event_timestamp} ({event.log_level}/{event.event_type}): {event.event_data}"
            )
        if self.event_server:
            self.send_event(event)

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

    def send_event(self, event: Event) -> None:
        """Send an event to the event manager."""
        raise NotImplementedError()


default_event_logger = EventClient()
