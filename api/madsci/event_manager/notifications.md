Module madsci.event_manager.notifications
=========================================
Code for sending notifications and alerts based on events

Classes
-------

`EmailAlerts(config: madsci.common.types.event_types.EmailAlertsConfig, logger: madsci.client.event_client.EventClient | None = None)`
:   Class for sending email alerts.

    Create an instance of EmailAlerts with the provided configuration.

    ### Methods

    `send_email(self, subject: str, email_address: str, body: str, sender: str | None = None, headers: dict | None = None, importance: str | None = None) ‑> bool`
    :   Sends an email with the provided subject and body to the specified email address.

    `send_email_alerts(self, event: madsci.common.types.event_types.Event) ‑> None`
    :   Send email alerts to the configured email addresses.
