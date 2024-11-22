"""MADSci Event Handling."""

import logging

from madsci.common.types.event_types import Event


class MADSciEventLogger:
    """A logger for MADSci events."""

    def __init__(self, name: str = __name__, log_level: int = logging.NOTSET) -> None:
        """Initialize the event logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

    def log_event(self, event: Event) -> None:
        """Log an event."""
        logging.log(event.log_level, event.event_data)
