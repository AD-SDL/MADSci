"""MADSci Event Handling."""

import logging
from typing import Optional

from madsci.common.types.event_types import Event


class MADSciEventLogger:
    """A logger for MADSci events."""

    def __init__(
        self,
        name: Optional[str] = None,
        log_level: int = logging.INFO,
        event_server: Optional[str] = None,
    ) -> None:
        """Initialize the event logger."""
        if name:
            self.logger = logging.getLogger(__name__ + "." + name)
        else:
            self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.event_server = event_server

    def get_log(self) -> list[Event]:
        """Read the log"""
        # TODO: Read logs

    def log(self, event: Event, level: Optional[int] = None) -> None:
        """Log an event."""
        event.log_level = level if level else event.log_level
        logging.log(event.log_level, event.event_data)
        if self.event_server:
            self.send_event(event)

    def log_debug(self, event: Event) -> None:
        """Log an event at the debug level."""
        self.log(event, logging.DEBUG)

    def log_info(self, event: Event) -> None:
        """Log an event at the info level."""
        self.log(event, logging.INFO)

    def log_warning(self, event: Event) -> None:
        """Log an event at the warning level."""
        self.log(event, logging.WARNING)

    def log_error(self, event: Event) -> None:
        """Log an event at the error level."""
        self.log(event, logging.ERROR)

    def log_critical(self, event: Event) -> None:
        """Log an event at the critical level."""
        self.log(event, logging.CRITICAL)

    def send_event(self, event: Event) -> None:
        """Send an event to the event manager."""


default_event_logger = MADSciEventLogger()
