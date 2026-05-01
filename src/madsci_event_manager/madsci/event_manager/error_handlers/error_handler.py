

from madsci.common.types.event_types import Event


class AbstractErrorHandler:
    """Abstract base class for error handlers in the MADSci Event Manager."""

    def handle_error(self, error_event: Event):
        """
        Handle an error that occurs during event processing.

        Args:
            error_event (Event): The event that caused the error.
        """
        raise NotImplementedError("Subclasses must implement this method.")