"""Default Notificiation Handler for MADSci Event Manager."""

from typing import Optional

from event_handler import AbstractEventHandler, EventHandlerSettings
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.event_types import Event, EventManagerSettings
from madsci.event_manager.notifications import EmailAlerts
from pydantic import Field


class EmailAlertsConfig(MadsciBaseModel):
    """Configuration for sending emails."""

    smtp_server: str = Field(
        default="smtp.example.com",
        title="SMTP Server",
        description="The SMTP server address used for sending emails.",
    )
    smtp_port: int = Field(
        default=587,
        title="SMTP Port",
        description="The port number used by the SMTP server.",
    )
    smtp_username: Optional[str] = Field(
        default=None,
        title="SMTP Username",
        description="The username for authenticating with the SMTP server.",
        json_schema_extra={"secret": True},
    )
    smtp_password: Optional[str] = Field(
        default=None,
        title="SMTP Password",
        description="The password for authenticating with the SMTP server.",
        json_schema_extra={"secret": True},
    )
    use_tls: bool = Field(
        default=True,
        title="Use TLS",
        description="Whether to use TLS for the SMTP connection.",
    )
    sender: str = Field(
        default="no-reply@example.com",
        title="Sender Email",
        description="The default sender email address.",
    )
    default_importance: str = Field(
        default="Normal",
        title="Default Importance",
        description="The default importance level of the email. Options are: High, Normal, Low.",
    )
    email_addresses: list[str] = Field(
        default_factory=list,
        title="Default Email Addresses",
        description="The default email addresses to send alerts to.",
    )


class NotificationHandlerSettings(EventHandlerSettings):
    """Settings for the default notification handler."""

    email_alerts: Optional["EmailAlertsConfig"] = Field(
        default=None,
        title="Email Alerts Configuration",
        description="The configuration for sending email alerts.",
    )


class NotificationHandler(AbstractEventHandler):
    """Default notification handler that sends alerts for events"""

    def __init__(
        self,
        custom_settings: NotificationHandlerSettings,
        event_manager_settings: EventManagerSettings,
    ) -> None:
        """Initialize the event handler with the given settings."""
        self.custom_settings = custom_settings
        self.event_manager_settings = event_manager_settings

    def handle_event(self, event: Event) -> None:
        """Handle an event by sending notifications for the event."""
        if (
            event.alert or event.log_level >= self.custom_settings.alert_level
        ) and self.custom_settings.email_alerts:
            email_alerter = EmailAlerts(
                config=self.custom_settings.email_alerts, logger=self.logger
            )
            email_alerter.send_email_alerts(event)
