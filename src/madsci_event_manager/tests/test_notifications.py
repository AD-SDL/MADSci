"""Unit tests for the EmailAlerts class in the madsci.event_manager.notifications module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.event_types import EmailAlertsConfig
from madsci.event_manager.notifications import EmailAlerts


@pytest.fixture
def email_alerts_config() -> EmailAlertsConfig:
    """
    Fixture to provide a sample EmailAlertsConfig object for testing.

    Returns:
        EmailAlertsConfig: A configuration object with test SMTP settings.
    """
    return EmailAlertsConfig(
        smtp_server="smtp.test.com",
        smtp_port=587,
        smtp_username="test_user",
        smtp_password="test_password",  # noqa: S106
        use_tls=True,
        sender="test_sender@test.com",
    )


@pytest.fixture
def email_alerts(
    email_alerts_config: EmailAlertsConfig,
) -> Generator[EmailAlerts, None, None]:
    """
    Fixture to provide an EmailAlerts instance with a mocked logger.

    Args:
        email_alerts_config (EmailAlertsConfig): The configuration object for EmailAlerts.

    Yields:
        EmailAlerts: An instance of EmailAlerts with a mocked logger.
    """
    yield EmailAlerts(config=email_alerts_config)


@patch("madsci.event_manager.notifications.smtplib.SMTP")
def test_send_email_success(mock_smtp: MagicMock, email_alerts: EmailAlerts) -> None:
    """
    Test that send_email successfully sends an email when no errors occur.

    Args:
        mock_smtp (MagicMock): Mocked SMTP class.
        email_alerts (EmailAlerts): The EmailAlerts instance to test.
    """
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    result: bool = email_alerts.send_email(
        subject="Test Subject",
        email_address="recipient@test.com",
        body="<p>This is a test email</p>",
    )

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("test_user", "test_password")
    mock_server.sendmail.assert_called_once()


@patch("madsci.event_manager.notifications.smtplib.SMTP")
def test_send_email_failure(mock_smtp: MagicMock, email_alerts: EmailAlerts) -> None:
    """
    Test that send_email returns False and logs an error when an exception occurs.

    Args:
        mock_smtp (MagicMock): Mocked SMTP class.
        email_alerts (EmailAlerts): The EmailAlerts instance to test.
    """
    mock_server = MagicMock()
    mock_server.sendmail.side_effect = Exception("SMTP error")
    mock_smtp.return_value = mock_server

    with patch.object(email_alerts.logger, "log_error") as mock_log_error:
        result: bool = email_alerts.send_email(
            subject="Test Subject",
            email_address="recipient@test.com",
            body="This is a test email",
        )

        assert result is False
        mock_log_error.assert_called_once()


@patch("madsci.event_manager.notifications.smtplib.SMTP")
def test_send_email_no_auth(
    mock_smtp: MagicMock, email_alerts_config: EmailAlertsConfig
) -> None:
    """
    Test that send_email works without authentication when username and password are not provided.

    Args:
        mock_smtp (MagicMock): Mocked SMTP class.
        email_alerts_config (EmailAlertsConfig): The configuration object for EmailAlerts.
    """
    email_alerts_config.smtp_username = None
    email_alerts_config.smtp_password = None
    email_alerts = EmailAlerts(config=email_alerts_config, logger=MagicMock())

    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    result: bool = email_alerts.send_email(
        subject="Test Subject",
        email_address="recipient@test.com",
        body="This is a test email",
    )

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_not_called()
    mock_server.sendmail.assert_called_once()


@patch("madsci.event_manager.notifications.ThreadPoolExecutor")
def test_send_email_alerts(mock_executor: MagicMock, email_alerts: EmailAlerts) -> None:
    """
    Test that send_email_alerts sends emails to all configured addresses in parallel.

    Args:
        mock_executor (MagicMock): Mocked ThreadPoolExecutor class.
        email_alerts (EmailAlerts): The EmailAlerts instance to test.
    """
    mock_executor_instance = MagicMock()
    mock_executor.return_value.__enter__.return_value = mock_executor_instance

    email_alerts.config.email_addresses = [
        "recipient1@test.com",
        "recipient2@test.com",
        "recipient3@test.com",
    ]

    event = MagicMock()
    event.log_level = "INFO"
    event.event_type = "Test Event"
    event.model_dump_json.return_value = '{"key": "value"}'
    event.event_id = "12345"

    email_alerts.send_email_alerts(event)

    mock_executor_instance.map.assert_called_once()
    args, _ = mock_executor_instance.map.call_args
    assert len(args[1]) == 3  # Ensure all email addresses are passed
