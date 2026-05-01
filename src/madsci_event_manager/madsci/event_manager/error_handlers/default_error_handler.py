from event_handler import AbstractErrorHandler
from madsci.common.types.event_types import Event

class ErrorHandler(AbstractErrorHandler):
    """Default error handler that simply logs the error event."""

    def parse_error_message(self, error_message: dict) -> dict:
        if 
    def handle_error(self, event_data: Event):
        # For this default implementation, we'll just print the error event.
        # In a real implementation, you might want to log this to a file or external logging service.
        parsed_message = self.parse_error_message(error_event.data)