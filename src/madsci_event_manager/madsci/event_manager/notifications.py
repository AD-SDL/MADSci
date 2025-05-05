"""
Code for sending notifications and alerts based on events
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.common.types.event_types import EmailAlertsConfig


class EmailAlerts:
    """Class for sending email alerts."""

    def __init__(
        self, config: EmailAlertsConfig, logger: Optional[EventClient] = None
    ) -> None:
        """Create an instance of EmailAlerts with the provided configuration."""
        self.config = config
        self.logger = logger if logger else EventClient()

    def send_email(
        self,
        subject: str,
        email_address: str,
        body: str,
        sender: Optional[str] = None,
        headers: Optional[dict] = None,
        importance: Optional[str] = None,
    ) -> bool:
        """Sends an email with the provided subject and body to the specified email address."""
        smtp_server = self.config.smtp_server
        smtp_port = self.config.smtp_port
        smtp_username = self.config.smtp_username
        smtp_password = self.config.smtp_password
        sender = sender or self.config.sender

        try:
            # Create the MIMEText objects for the email content
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = email_address

            # Set email importance
            importance = importance or self.config.default_importance
            msg["Importance"] = importance
            msg["X-Priority"] = (
                "1"
                if importance.lower() == "high"
                else "3"
                if importance.lower() == "low"
                else "5"
            )

            # Add custom headers if provided
            if headers:
                for key, value in headers.items():
                    msg[key] = value

            # Attach both plain text and HTML versions
            import re

            part1 = MIMEText(
                re.sub("<[^<]+?>", "", body), "plain"
            )  # * Strip HTML tags for plaintext
            part2 = MIMEText(body, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send the email via the SMTP server
            server = smtplib.SMTP(smtp_server, smtp_port)
            try:
                if self.config.use_tls:
                    self.logger.log_debug(
                        "Starting TLS for secure connection"
                    )  # Debug log
                    server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.sendmail(sender, email_address, msg.as_string())
            finally:
                server.quit()

            self.logger.log_info(f"Email alert sent to {email_address}")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to send email to {email_address}: {e}")
            return False
