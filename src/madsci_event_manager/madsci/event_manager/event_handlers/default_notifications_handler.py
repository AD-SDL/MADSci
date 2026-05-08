"""Default Error Handler for MADSci Event Manager."""

from event_handler import AbstractEventHandler
from madsci.common.types.event_types import Event
from madsci.event_manager.notifications import EmailAlerts


class NotificationHandler(AbstractEventHandler):
    """Default notification handler that sends alerts for events"""

    def handle_event(self, event: Event) -> None:
        """Handle an event by sending notifications for the event."""
        if (
            event.alert or event.log_level >= self.settings.alert_level
        ) and self.settings.email_alerts:
            email_alerter = EmailAlerts(
                config=self.settings.email_alerts, logger=self.logger
            )
            email_alerter.send_email_alerts(event)
