"""Abstract Error Handler for MADSci Event Manager."""

from madsci.common.types.event_types import Event
from madsci.common.types.event_types import EventManagerSettings


class AbstractEventHandler:
    """Abstract base class for event handlers in the MADSci Event Manager."""
    def __init__(self, settings: EventManagerSettings) -> None:
        self.settings = settings
    def handle_event(self, event: Event) -> None:
        """
        Handle an event that occurs during processing.

        Args:
            event (Event): The event to handle.
        """
        raise NotImplementedError("Subclasses must implement this method.")
