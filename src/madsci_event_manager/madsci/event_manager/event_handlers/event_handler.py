"""Abstract Error Handler for MADSci Event Manager."""

from madsci.common.types.base_types import MadsciBaseSettings
from madsci.common.types.event_types import Event, EventManagerSettings


class EventHandlerSettings(MadsciBaseSettings):
    """Settings for the Event Handler."""


class AbstractEventHandler:
    """Abstract base class for event handlers in the MADSci Event Manager."""

    def __init__(
        self,
        custom_settings: EventHandlerSettings,
        event_manager_settings: EventManagerSettings,
    ) -> None:
        """Initialize the event handler with the given settings."""
        self.custom_settings = custom_settings
        self.event_manager_settings = event_manager_settings

    def handle_event(self, event: Event) -> None:
        """
        Handle an event that occurs during processing.

        Args:
            event (Event): The event to handle.
        """
        raise NotImplementedError("Subclasses must implement this method.")
