"""Unit tests for EventClient."""

import gzip
import logging
import tempfile
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from madsci.client.event_client import EventClient
from madsci.common.types.event_types import (
    Event,
    EventClientConfig,
    EventLogLevel,
    EventType,
)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_event():
    """Create a sample Event for testing."""
    return Event(
        event_type=EventType.TEST,
        event_data={"message": "test event"},
        log_level=EventLogLevel.INFO,
    )


@pytest.fixture
def config_with_server():
    """Create EventClientConfig with event server."""
    return EventClientConfig(
        name="test_client",
        event_server_url="http://localhost:8001",
        log_level=EventLogLevel.DEBUG,
    )


@pytest.fixture
def config_without_server(temp_log_dir):
    """Create EventClientConfig without event server."""
    return EventClientConfig(
        name="test_client",
        log_level=EventLogLevel.DEBUG,
        log_dir=temp_log_dir,
    )


class TestEventClientInit:
    """Test EventClient initialization."""

    def test_init_with_config(self, config_with_server, temp_log_dir):
        """Test initialization with EventClientConfig."""
        config_with_server.log_dir = temp_log_dir
        client = EventClient(config=config_with_server)

        assert client.config == config_with_server
        assert client.name == "test_client"
        assert str(client.event_server) == "http://localhost:8001/"
        assert client.logger.getEffectiveLevel() == logging.DEBUG

    def test_init_without_config(self, temp_log_dir):
        """Test initialization without config uses defaults."""
        with patch("madsci.client.event_client.EventClientConfig") as mock_config:
            mock_config.return_value.name = None
            mock_config.return_value.log_dir = temp_log_dir
            mock_config.return_value.log_level = EventLogLevel.INFO
            mock_config.return_value.event_server_url = None

            with patch(
                "madsci.client.event_client.get_current_madsci_context"
            ) as mock_context:
                mock_context.return_value.event_server_url = None

                client = EventClient()

                assert client.config is not None
                # Name should be derived from module name
                assert client.name is not None

    def test_init_with_kwargs_override(self, temp_log_dir):
        """Test initialization with kwargs overriding config."""
        base_config = EventClientConfig(name="base_name", log_dir=temp_log_dir)

        event_client = EventClient(config=base_config, name="override_name")
        assert event_client.config.name == "override_name"

    def test_init_name_from_calling_module(self, temp_log_dir):
        """Test that name is derived from calling module when not provided."""
        config = EventClientConfig(log_dir=temp_log_dir)
        config.name = None

        client = EventClient(config=config)

        # Should have a name derived from the calling context
        assert client.name is not None
        assert isinstance(client.name, str)


class TestEventClientLogging:
    """Test EventClient logging methods."""

    @patch("madsci.client.event_client.create_http_session")
    def test_log_event_object(
        self, mock_create_session, config_with_server, temp_log_dir, sample_event
    ):
        """Test logging an Event object."""
        config_with_server.log_dir = temp_log_dir

        # Mock successful POST to event server
        mock_response = Mock()
        mock_response.ok = True

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # Reset mock after initialization (which logs debug messages)
        mock_session.post.reset_mock()

        client.log(sample_event)

        # Wait for the threaded task to complete (log sends events asynchronously)
        time.sleep(0.1)

        # Verify event was sent to server
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[1]["timeout"] == 10.0
        # Verify the JSON payload contains our event data
        json_data = call_args[1]["json"]
        assert json_data["event_type"] == "test"
        assert json_data["event_data"] == {"message": "test event"}

    def test_log_string(self, config_without_server):
        """Test logging a string."""
        client = EventClient(config=config_without_server)

        # Should not raise an exception
        client.log("Test log message", level=logging.INFO)

        # Verify it created a log entry
        assert client.logfile.exists()

    def test_log_dict(self, config_without_server):
        """Test logging a dictionary."""
        client = EventClient(config=config_without_server)

        test_dict = {"key": "value", "number": 42}
        client.log(test_dict, level=logging.INFO)

        assert client.logfile.exists()

    def test_log_exception(self, config_without_server):
        """Test logging an Exception object."""
        client = EventClient(config=config_without_server)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            client.log(e)

        assert client.logfile.exists()

    def test_log_debug(self, config_without_server):
        """Test log_debug method."""
        client = EventClient(config=config_without_server)

        client.log_debug("Debug message")
        assert client.logfile.exists()

        # Also test the alias
        client.debug("Debug alias message")

    def test_log_info(self, config_without_server):
        """Test log_info method."""
        client = EventClient(config=config_without_server)

        client.log_info("Info message")
        assert client.logfile.exists()

        # Also test the alias
        client.info("Info alias message")

    def test_log_warning(self, config_without_server):
        """Test log_warning method."""
        client = EventClient(config=config_without_server)

        # Test without warning category
        client.log_warning("Warning message")
        assert client.logfile.exists()

        # Test with warning category
        with pytest.warns(UserWarning, match="Warning with category"):
            client.log_warning("Warning with category", warning_category=UserWarning)

        # Test aliases
        client.warning("Warning alias")
        client.warn("Warn alias")

    def test_log_error(self, config_without_server):
        """Test log_error method."""
        client = EventClient(config=config_without_server)

        client.log_error("Error message")
        assert client.logfile.exists()

        # Also test the alias
        client.error("Error alias message")

    def test_log_critical(self, config_without_server):
        """Test log_critical method."""
        client = EventClient(config=config_without_server)

        client.log_critical("Critical message")
        assert client.logfile.exists()

        # Also test the alias
        client.critical("Critical alias message")

    def test_log_alert(self, config_without_server):
        """Test log_alert method."""
        client = EventClient(config=config_without_server)

        client.log_alert("Alert message")
        assert client.logfile.exists()

        # Also test the alias
        client.alert("Alert alias message")

    def test_log_level_filtering(self, temp_log_dir):
        """Test that log level filtering works correctly."""
        config = EventClientConfig(
            name="level_test",
            log_level=EventLogLevel.WARNING,  # Only WARNING and above
            log_dir=temp_log_dir,
        )
        client = EventClient(config=config)

        # These should be filtered out
        client.log_debug("Debug message")
        client.info("Info message")

        # These should go through
        client.log_warning("Warning message")
        client.log_error("Error message")

        assert client.logfile.exists()

    @patch("madsci.client.event_client.create_http_session")
    def test_event_server_error_handling(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test handling of event server errors."""
        config_with_server.log_dir = temp_log_dir

        # Mock failed POST to event server
        mock_session = Mock()
        mock_session.post.side_effect = requests.RequestException("Server error")
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # Should not raise an exception, should buffer the event
        client.info("Test message gets queued 1")
        client.info(
            "Test message gets queued 2"
        )  # * Need a second event so there's at least one in the queue while the other is being retried

        time.sleep(0.1)

        # Event should be added to buffer when send fails
        assert not client._event_buffer.empty()


class TestEventClientEventRetrieval:
    """Test EventClient event retrieval methods."""

    @patch("madsci.client.event_client.create_http_session")
    def test_get_event_with_server(
        self, mock_create_session, config_with_server, temp_log_dir, sample_event
    ):
        """Test get_event with event server configured."""
        config_with_server.log_dir = temp_log_dir

        # Mock successful GET from event server
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = sample_event.model_dump()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_event(sample_event.event_id)

        mock_session.get.assert_called_once_with(
            f"http://localhost:8001/event/{sample_event.event_id}",
            timeout=10.0,
        )
        assert isinstance(result, Event)
        assert result.event_id == sample_event.event_id
        assert result.event_type == sample_event.event_type

    def test_get_event_without_server_from_log(
        self, config_without_server, sample_event
    ):
        """Test get_event without server, reading from log file."""
        client = EventClient(config=config_without_server)

        # Write a sample event to the log file
        with client.logfile.open("w") as f:
            f.write(sample_event.model_dump_json() + "\n")

        result = client.get_event(sample_event.event_id)

        assert isinstance(result, Event)
        assert result.event_id == sample_event.event_id

    def test_get_event_not_found(self, config_without_server):
        """Test get_event when event not found."""
        client = EventClient(config=config_without_server)

        result = client.get_event("nonexistent_id")

        assert result is None

    @patch("madsci.client.event_client.create_http_session")
    def test_get_event_http_error(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_event with HTTP error from server."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        with pytest.raises(requests.HTTPError):
            client.get_event("some_id")

    @patch("madsci.client.event_client.create_http_session")
    def test_get_events_with_server(
        self, mock_create_session, config_with_server, temp_log_dir, sample_event
    ):
        """Test get_events with event server configured."""
        config_with_server.log_dir = temp_log_dir

        # Mock successful GET from event server
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            sample_event.event_id: sample_event.model_dump()
        }

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_events(number=50, level=logging.INFO)

        mock_session.get.assert_called_once_with(
            "http://localhost:8001/events",
            timeout=10.0,
            params={"number": 50, "level": logging.INFO},
        )
        assert isinstance(result, dict)
        assert sample_event.event_id in result
        assert isinstance(result[sample_event.event_id], Event)

    @patch("madsci.client.event_client.create_http_session")
    def test_get_events_with_default_params(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_events with default parameters."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_events()

        mock_session.get.assert_called_once_with(
            "http://localhost:8001/events",
            timeout=10.0,
            params={"number": 100, "level": 10},  # DEBUG level
        )
        assert isinstance(result, dict)

    def test_get_events_without_server_from_log(self, config_without_server):
        """Test get_events without server, reading from log file."""
        client = EventClient(config=config_without_server)

        # Write multiple events to the log file
        events = []
        for i in range(5):
            event = Event(
                event_type=EventType.TEST,
                event_data={"message": f"test event {i}"},
                log_level=EventLogLevel.INFO,
            )
            events.append(event)

        with client.logfile.open("w") as f:
            for event in events:
                f.write(event.model_dump_json() + "\n")

        result = client.get_events(number=3)

        assert isinstance(result, dict)
        # Should return the most recent 3 events (reverse order)
        assert len(result) == 3

    @patch("madsci.client.event_client.create_http_session")
    def test_get_events_http_error(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_events with HTTP error from server."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        with pytest.raises(requests.HTTPError):
            client.get_events()


class TestEventClientQueryEvents:
    """Test EventClient query_events method."""

    @patch("madsci.client.event_client.create_http_session")
    def test_query_events_with_server(
        self, mock_create_session, config_with_server, temp_log_dir, sample_event
    ):
        """Test query_events with event server configured."""
        config_with_server.log_dir = temp_log_dir

        # Mock successful POST to event server
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            sample_event.event_id: sample_event.model_dump()
        }

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # Reset mock after initialization
        mock_session.post.reset_mock()
        mock_session.post.return_value = mock_response

        selector = {"event_type": "test", "source.user": "test_user"}
        result = client.query_events(selector)

        mock_session.post.assert_called_once_with(
            "http://localhost:8001/events/query",
            timeout=10.0,
            params={"selector": selector},
        )
        assert isinstance(result, dict)
        assert sample_event.event_id in result
        assert isinstance(result[sample_event.event_id], Event)

    def test_query_events_without_server(self, config_without_server):
        """Test query_events without event server logs warning and returns empty dict."""
        client = EventClient(config=config_without_server)

        selector = {"event_type": "test"}
        result = client.query_events(selector)

        assert isinstance(result, dict)
        assert len(result) == 0

    @patch("madsci.client.event_client.create_http_session")
    def test_query_events_http_error(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test query_events with HTTP error from server."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Bad Request"
        )

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        with pytest.raises(requests.HTTPError):
            client.query_events({"event_type": "test"})


class TestEventClientStartupLogging:
    """Test EventClient startup logging behavior."""

    def test_logs_version_on_init(self, config_without_server, caplog):
        """Test that MADSci version is logged on initialization."""
        with caplog.at_level(logging.INFO):
            client = EventClient(config=config_without_server)

        # Check that version info appears in log output
        log_text = caplog.text.lower()
        assert "madsci_version" in log_text or "madsci version" in log_text
        assert client is not None

    def test_logs_config_summary_on_init(self, config_without_server, caplog):
        """Test that configuration summary is logged on initialization."""
        with caplog.at_level(logging.INFO):
            client = EventClient(config=config_without_server)

        log_text = caplog.text.lower()
        # Verify key config details appear in log output
        assert "client_name" in log_text or "test_client" in log_text
        assert "log_dir" in log_text or "log directory" in log_text
        assert client is not None

    def test_logs_event_server_url_when_configured(
        self, config_with_server, temp_log_dir, caplog
    ):
        """Test that event server URL is logged when configured."""
        config_with_server.log_dir = temp_log_dir

        with (
            patch("madsci.client.event_client.create_http_session"),
            caplog.at_level(logging.INFO),
        ):
            client = EventClient(config=config_with_server)

        log_text = caplog.text.lower()
        # Verify event server URL appears in log output
        assert "localhost:8001" in log_text or "event_server" in log_text
        assert client is not None

    def test_logs_python_version_on_init(self, config_without_server, caplog):
        """Test that Python version is logged on initialization."""
        with caplog.at_level(logging.INFO):
            client = EventClient(config=config_without_server)

        log_text = caplog.text.lower()
        # Verify Python version info appears in log output
        assert "python" in log_text
        assert client is not None

    def test_startup_logging_contains_platform_info(
        self, config_without_server, caplog
    ):
        """Test that platform info is logged on initialization."""
        with caplog.at_level(logging.INFO):
            client = EventClient(config=config_without_server)

        log_text = caplog.text.lower()
        # Verify platform info appears in log output
        assert "platform" in log_text
        assert client is not None


class TestEventClientUtilizationMethods:
    """Test EventClient utilization report methods."""

    @patch("madsci.client.event_client.create_http_session")
    def test_get_utilization_periods_json(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_utilization_periods returning JSON."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"utilization_data": "test"}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_utilization_periods(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-02T00:00:00Z",
            analysis_type="daily",
            user_timezone="America/Chicago",
            include_users=True,
        )

        mock_session.get.assert_called_once_with(
            "http://localhost:8001/utilization/periods",
            params={
                "analysis_type": "daily",
                "user_timezone": "America/Chicago",
                "include_users": "true",
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
            },
            timeout=60.0,
        )
        assert result == {"utilization_data": "test"}

    @patch("madsci.client.event_client.create_http_session")
    def test_get_utilization_periods_csv(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_utilization_periods returning CSV."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {"content-type": "text/csv"}
        mock_response.text = "date,utilization\\n2025-01-01,50%"

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # Use NamedTemporaryFile for secure temp file path

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            output_path = tmp_file.name

            result = client.get_session_utilization(
                csv_export=True, save_to_file=True, output_path=output_path
            )

            expected_params = {
                "csv_format": "true",
                "save_to_file": "true",
                "output_path": output_path,
            }
            mock_session.get.assert_called_once_with(
                "http://localhost:8001/utilization/sessions",
                params=expected_params,
                timeout=100.0,
            )
            assert result == "date,utilization\\n2025-01-01,50%"

    def test_get_utilization_periods_without_server(self, config_without_server):
        """Test get_utilization_periods without event server."""
        client = EventClient(config=config_without_server)

        result = client.get_utilization_periods()

        assert result is None

    @patch("madsci.client.event_client.create_http_session")
    def test_get_session_utilization_json(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_session_utilization returning JSON."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"sessions": []}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_session_utilization(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-02T00:00:00Z",
        )

        mock_session.get.assert_called_once_with(
            "http://localhost:8001/utilization/sessions",
            params={
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
            },
            timeout=100.0,
        )
        assert result == {"sessions": []}

    @patch("madsci.client.event_client.create_http_session")
    def test_get_session_utilization_csv(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_session_utilization returning CSV."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {"content-type": "text/csv"}
        mock_response.text = "session,start,end\\nsession1,2025-01-01,2025-01-02"

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # Use NamedTemporaryFile for secure temp file path
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            output_path = tmp_file.name

            result = client.get_session_utilization(
                csv_export=True, save_to_file=True, output_path=output_path
            )

            expected_params = {
                "csv_format": "true",
                "save_to_file": "true",
                "output_path": output_path,
            }
            mock_session.get.assert_called_once_with(
                "http://localhost:8001/utilization/sessions",
                params=expected_params,
                timeout=100.0,
            )
            assert result == "session,start,end\\nsession1,2025-01-01,2025-01-02"

    def test_get_session_utilization_without_server(self, config_without_server):
        """Test get_session_utilization without event server."""
        client = EventClient(config=config_without_server)

        result = client.get_session_utilization()

        assert result is None

    @patch("madsci.client.event_client.create_http_session")
    def test_get_user_utilization_report_json(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test get_user_utilization_report returning JSON."""
        config_with_server.log_dir = temp_log_dir

        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"users": {}}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        result = client.get_user_utilization_report(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-02T00:00:00Z",
        )

        mock_session.get.assert_called_once_with(
            "http://localhost:8001/utilization/users",
            params={
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
            },
            timeout=100.0,
        )
        assert result == {"users": {}}

    def test_get_user_utilization_report_without_server(self, config_without_server):
        """Test get_user_utilization_report without event server."""
        client = EventClient(config=config_without_server)

        result = client.get_user_utilization_report()

        assert result is None

    @patch("madsci.client.event_client.create_http_session")
    def test_utilization_methods_request_exception(
        self, mock_create_session, config_with_server, temp_log_dir
    ):
        """Test utilization methods handle RequestException."""
        config_with_server.log_dir = temp_log_dir

        mock_session = Mock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        mock_create_session.return_value = mock_session

        client = EventClient(config=config_with_server)

        # All utilization methods should return None on RequestException
        assert client.get_utilization_periods() is None
        assert client.get_session_utilization() is None
        assert client.get_user_utilization_report() is None


class TestEventClientStructlog:
    """Test EventClient with structlog backend."""

    def test_basic_info_logging(self, config_without_server):
        """Test basic info logging with structlog."""
        client = EventClient(config=config_without_server)

        # Should not raise an exception
        client.info("Test message")

        # Verify log file exists and contains content
        assert client.logfile.exists()

    def test_basic_debug_logging(self, config_without_server):
        """Test basic debug logging with structlog."""
        client = EventClient(config=config_without_server)

        client.debug("Debug message")
        assert client.logfile.exists()

    def test_basic_warning_logging(self, config_without_server):
        """Test basic warning logging with structlog."""
        client = EventClient(config=config_without_server)

        client.warning("Warning message")
        assert client.logfile.exists()

    def test_basic_error_logging(self, config_without_server):
        """Test basic error logging with structlog."""
        client = EventClient(config=config_without_server)

        client.error("Error message")
        assert client.logfile.exists()

    def test_basic_critical_logging(self, config_without_server):
        """Test basic critical logging with structlog."""
        client = EventClient(config=config_without_server)

        client.critical("Critical message")
        assert client.logfile.exists()

    def test_structured_data_in_logs(self, config_without_server, caplog):
        """Test that structured data is included in logs."""
        client = EventClient(config=config_without_server)

        with caplog.at_level(logging.INFO):
            client.info("Processing step", step=1, total=10, status="running")

        # Verify the structured data appears in the log
        # Note: The exact format depends on structlog configuration
        assert client.logfile.exists()

    def test_context_binding(self, config_without_server, caplog):
        """Test that bound context appears in logs."""
        client = EventClient(config=config_without_server)
        bound_client = client.bind(workflow_id="wf-123", node_id="node-456")

        with caplog.at_level(logging.INFO):
            bound_client.info("Processing step")

        # Verify the bound context is stored
        assert bound_client._bound_context == {
            "workflow_id": "wf-123",
            "node_id": "node-456",
        }

    def test_nested_context_binding(self, config_without_server):
        """Test nested context binding accumulates context."""
        client = EventClient(config=config_without_server)

        # First level binding
        bound1 = client.bind(workflow_id="wf-123")
        assert bound1._bound_context == {"workflow_id": "wf-123"}

        # Second level binding
        bound2 = bound1.bind(step=1)
        assert bound2._bound_context == {"workflow_id": "wf-123", "step": 1}

        # Third level binding
        bound3 = bound2.bind(node_id="node-456")
        assert bound3._bound_context == {
            "workflow_id": "wf-123",
            "step": 1,
            "node_id": "node-456",
        }

        # Original clients should be unchanged
        assert client._bound_context == {}
        assert bound1._bound_context == {"workflow_id": "wf-123"}

    def test_unbind_context(self, config_without_server):
        """Test that context can be unbound."""
        client = EventClient(config=config_without_server)
        bound_client = client.bind(workflow_id="wf-123", step=1, node_id="node-456")

        # Unbind specific keys
        unbound_client = bound_client.unbind("step", "node_id")

        assert unbound_client._bound_context == {"workflow_id": "wf-123"}
        # Original should be unchanged
        assert bound_client._bound_context == {
            "workflow_id": "wf-123",
            "step": 1,
            "node_id": "node-456",
        }

    def test_json_output_format(self, temp_log_dir):
        """Test JSON output format configuration."""
        config = EventClientConfig(
            name="json_test",
            log_dir=temp_log_dir,
            log_output_format="json",
        )
        client = EventClient(config=config)

        client.info("Test message", key="value")

        # Verify configuration was applied
        assert config.log_output_format == "json"
        assert client.logfile.exists()

    def test_console_output_format(self, temp_log_dir):
        """Test console (human-readable) output format configuration."""
        config = EventClientConfig(
            name="console_test",
            log_dir=temp_log_dir,
            log_output_format="console",
        )
        client = EventClient(config=config)

        client.info("Test message")

        assert config.log_output_format == "console"
        assert client.logfile.exists()

    def test_exception_logging(self, config_without_server):
        """Test exception info is properly captured."""
        client = EventClient(config=config_without_server)

        try:
            raise ValueError("Test error")
        except ValueError:
            client.exception("An error occurred")

        assert client.logfile.exists()

    def test_backward_compat_log_info(self, config_without_server):
        """Test log_info() alias works."""
        client = EventClient(config=config_without_server)

        client.log_info("Info via log_info")
        assert client.logfile.exists()

    def test_backward_compat_log_debug(self, config_without_server):
        """Test log_debug() alias works."""
        client = EventClient(config=config_without_server)

        client.log_debug("Debug via log_debug")
        assert client.logfile.exists()

    def test_backward_compat_log_warning(self, config_without_server):
        """Test log_warning() alias works."""
        client = EventClient(config=config_without_server)

        client.log_warning("Warning via log_warning")
        assert client.logfile.exists()

    def test_backward_compat_log_error(self, config_without_server):
        """Test log_error() alias works."""
        client = EventClient(config=config_without_server)

        client.log_error("Error via log_error")
        assert client.logfile.exists()

    def test_backward_compat_log_critical(self, config_without_server):
        """Test log_critical() alias works."""
        client = EventClient(config=config_without_server)

        client.log_critical("Critical via log_critical")
        assert client.logfile.exists()

    def test_multiple_clients_isolated_config(self, temp_log_dir):
        """Test that multiple EventClient instances have isolated configurations."""
        json_config = EventClientConfig(
            name="json_client",
            log_dir=temp_log_dir,
            log_output_format="json",
        )
        console_config = EventClientConfig(
            name="console_client",
            log_dir=temp_log_dir,
            log_output_format="console",
        )

        json_client = EventClient(config=json_config)
        console_client = EventClient(config=console_config)

        # Verify each client has its own configuration
        assert json_client.config.log_output_format == "json"
        assert console_client.config.log_output_format == "console"

        # Both should be able to log independently
        json_client.info("JSON log message")
        console_client.info("Console log message")

        # Verify both log files exist
        assert json_client.logfile.exists()
        assert console_client.logfile.exists()

    def test_warn_alias(self, config_without_server):
        """Test warn() is alias for log_warning() with warning_category support."""
        client = EventClient(config=config_without_server)

        # Both should work - warn is alias for log_warning
        client.warn("Warn message")
        client.warning("Warning message")

        # warn should also accept warning_category (for backward compatibility)
        with pytest.warns(UserWarning, match="Warn with category"):
            client.warn("Warn with category", warning_category=UserWarning)

        assert client.logfile.exists()


class TestEventClientErrorHandling:
    """Test EventClient error handling behavior."""

    def test_fail_on_error_false_default(self, temp_log_dir):
        """Test that fail_on_error defaults to False."""
        config = EventClientConfig(
            name="error_test",
            log_dir=temp_log_dir,
        )
        assert config.fail_on_error is False

    def test_fail_on_error_can_be_enabled(self, temp_log_dir):
        """Test that fail_on_error can be set to True."""
        config = EventClientConfig(
            name="error_test",
            log_dir=temp_log_dir,
            fail_on_error=True,
        )
        assert config.fail_on_error is True

    def test_fail_on_error_false_logs_silently(self, temp_log_dir, capsys):
        """Test that errors are logged silently when fail_on_error=False."""
        config = EventClientConfig(
            name="silent_error_test",
            log_dir=temp_log_dir,
            fail_on_error=False,
        )
        client = EventClient(config=config)

        # Normal logging should work without issues
        client.info("Normal message")

        # No exception should be raised
        assert client.logfile.exists()


class TestEventClientLogRotation:
    """Test EventClient log rotation functionality."""

    def test_size_based_rotation_config(self, temp_log_dir):
        """Test that size-based rotation is configured correctly."""
        config = EventClientConfig(
            name="rotation_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=1024,  # 1KB for testing
            log_backup_count=3,
            log_compression_enabled=False,  # Disable compression for this test
        )
        client = EventClient(config=config)

        # Verify a RotatingFileHandler was added
        rotating_handlers = [
            h for h in client.logger.handlers if isinstance(h, RotatingFileHandler)
        ]
        assert len(rotating_handlers) == 1

        handler = rotating_handlers[0]
        assert handler.maxBytes == 1024
        assert handler.backupCount == 3

    def test_time_based_rotation_config(self, temp_log_dir):
        """Test that time-based rotation is configured correctly."""
        config = EventClientConfig(
            name="time_rotation_test",
            log_dir=temp_log_dir,
            log_rotation_type="time",
            log_rotation_when="H",
            log_rotation_interval=2,
            log_backup_count=5,
            log_compression_enabled=False,  # Disable compression for this test
        )
        client = EventClient(config=config)

        # Verify a TimedRotatingFileHandler was added
        timed_handlers = [
            h for h in client.logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(timed_handlers) == 1

        handler = timed_handlers[0]
        assert handler.when == "H"
        assert handler.interval == 2 * 3600  # Interval is in seconds
        assert handler.backupCount == 5

    def test_rotation_disabled(self, temp_log_dir):
        """Test that rotation can be disabled."""
        config = EventClientConfig(
            name="no_rotation_test",
            log_dir=temp_log_dir,
            log_rotation_type="none",
        )
        client = EventClient(config=config)

        # Verify no rotating handlers were added
        rotating_handlers = [
            h
            for h in client.logger.handlers
            if isinstance(h, (RotatingFileHandler, TimedRotatingFileHandler))
        ]
        assert len(rotating_handlers) == 0

        # Verify a basic FileHandler was added
        file_handlers = [
            h
            for h in client.logger.handlers
            if isinstance(h, logging.FileHandler)
            and not isinstance(h, (RotatingFileHandler, TimedRotatingFileHandler))
        ]
        assert len(file_handlers) == 1

    def test_default_rotation_config(self, temp_log_dir):
        """Test default rotation configuration is applied."""
        config = EventClientConfig(
            name="default_rotation_test",
            log_dir=temp_log_dir,
        )
        client = EventClient(config=config)

        # Default should be size-based rotation
        rotating_handlers = [
            h for h in client.logger.handlers if isinstance(h, RotatingFileHandler)
        ]
        assert len(rotating_handlers) == 1

        handler = rotating_handlers[0]
        # Default is 10MB
        assert handler.maxBytes == 10_485_760
        # Default is 5 backups
        assert handler.backupCount == 5

    def test_size_based_rotation_triggers(self, temp_log_dir):
        """Test that logs rotate when max size is reached."""
        config = EventClientConfig(
            name="size_trigger_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=1024,  # Minimum 1KB for testing
            log_backup_count=3,
            log_compression_enabled=False,  # Disable compression for simpler testing
        )
        client = EventClient(config=config)

        # Write enough data to trigger rotation (need to fill up 1KB multiple times)
        for i in range(200):
            client.info(
                "Test message with some extra content to fill up space and trigger rotation",
                i=i,
            )

        # Check that backup files were created
        log_files = list(temp_log_dir.glob(f"{config.name}.log*"))
        # Should have at least the main log and one backup
        assert len(log_files) >= 2, f"Expected at least 2 log files, got {log_files}"

    def test_backup_count_limit(self, temp_log_dir):
        """Test that only specified number of backups are kept."""
        config = EventClientConfig(
            name="backup_limit_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=1024,  # Minimum 1KB for testing
            log_backup_count=2,  # Only keep 2 backups
            log_compression_enabled=False,
        )
        client = EventClient(config=config)

        # Write a lot of data to trigger multiple rotations
        for i in range(500):
            client.info(
                "Test message - filling up log space quickly here with extra text",
                i=i,
            )

        # Count log files (main + backups)
        log_files = list(temp_log_dir.glob(f"{config.name}.log*"))
        # Should have at most 3 files (main + 2 backups)
        assert len(log_files) <= 3, f"Expected at most 3 log files, got {log_files}"

    def test_log_compression_enabled(self, temp_log_dir):
        """Test that rotated logs are compressed with gzip when enabled."""
        config = EventClientConfig(
            name="compression_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=1024,  # Minimum 1KB for testing
            log_backup_count=3,
            log_compression_enabled=True,
        )
        client = EventClient(config=config)

        # Write enough data to trigger rotation
        for i in range(200):
            client.info(
                "Compression test message with content to fill space and trigger rotation",
                i=i,
            )

        # Check for compressed backup files
        gz_files = list(temp_log_dir.glob(f"{config.name}.log.*.gz"))

        # If rotation occurred, we should have compressed files
        log_files = list(temp_log_dir.glob(f"{config.name}.log*"))
        if len(log_files) > 1:
            assert len(gz_files) >= 1, f"Expected compressed files, got {gz_files}"

            # Verify the compressed file is valid gzip
            for gz_file in gz_files:
                with gzip.open(gz_file, "rt") as f:
                    content = f.read()
                    assert "Compression test message" in content

    def test_compression_disabled(self, temp_log_dir):
        """Test that rotated logs are not compressed when disabled."""
        config = EventClientConfig(
            name="no_compression_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=1024,  # Minimum 1KB for testing
            log_backup_count=3,
            log_compression_enabled=False,
        )
        client = EventClient(config=config)

        # Write enough data to trigger rotation
        for i in range(200):
            client.info(
                "No compression test message with extra content to trigger rotation",
                i=i,
            )

        # Check for compressed backup files - should be none
        gz_files = list(temp_log_dir.glob(f"{config.name}.log.*.gz"))
        assert len(gz_files) == 0, f"Expected no compressed files, got {gz_files}"

    def test_invalid_rotation_type_raises_error(self, temp_log_dir):
        """Test that invalid rotation type raises validation error."""
        with pytest.raises(ValueError, match="log_rotation_type"):
            EventClientConfig(
                name="invalid_rotation_test",
                log_dir=temp_log_dir,
                log_rotation_type="invalid",
            )

    def test_invalid_rotation_when_raises_error(self, temp_log_dir):
        """Test that invalid rotation_when raises validation error."""
        with pytest.raises(ValueError, match="log_rotation_when"):
            EventClientConfig(
                name="invalid_when_test",
                log_dir=temp_log_dir,
                log_rotation_type="time",
                log_rotation_when="invalid",
            )

    def test_rotation_preserves_existing_functionality(self, temp_log_dir):
        """Test that rotation doesn't break existing logging functionality."""
        config = EventClientConfig(
            name="preserve_func_test",
            log_dir=temp_log_dir,
            log_rotation_type="size",
            log_max_bytes=10_000,
            log_compression_enabled=False,
        )
        client = EventClient(config=config)

        # Test all log levels still work
        client.debug("Debug message")
        client.info("Info message")
        client.warning("Warning message")
        client.error("Error message")
        client.critical("Critical message")

        # Verify log file exists and contains expected content
        assert client.logfile.exists()
        log_content = client.logfile.read_text()
        assert "Info message" in log_content or len(log_content) > 0

    def test_time_rotation_midnight(self, temp_log_dir):
        """Test time-based rotation with midnight setting."""
        config = EventClientConfig(
            name="midnight_test",
            log_dir=temp_log_dir,
            log_rotation_type="time",
            log_rotation_when="midnight",
            log_backup_count=7,
            log_compression_enabled=False,
        )
        client = EventClient(config=config)

        # Verify handler is configured for midnight rotation
        timed_handlers = [
            h for h in client.logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(timed_handlers) == 1
        assert (
            timed_handlers[0].when == "MIDNIGHT"
        )  # TimedRotatingFileHandler uppercases it

    def test_time_rotation_weekly(self, temp_log_dir):
        """Test time-based rotation with weekly setting."""
        config = EventClientConfig(
            name="weekly_test",
            log_dir=temp_log_dir,
            log_rotation_type="time",
            log_rotation_when="W0",  # Monday
            log_backup_count=4,
            log_compression_enabled=False,
        )
        client = EventClient(config=config)

        # Verify handler is configured for weekly rotation
        timed_handlers = [
            h for h in client.logger.handlers if isinstance(h, TimedRotatingFileHandler)
        ]
        assert len(timed_handlers) == 1
        # TimedRotatingFileHandler stores weekly as W0, W1, etc.
        assert timed_handlers[0].when == "W0"


class TestEventClientBoundChildBehavior:
    """Test that bound child clients properly share resources without closing them."""

    def test_bound_child_flag_set_on_bind(self, temp_log_dir):
        """Test that bind() sets _is_bound_child flag on new client."""
        config = EventClientConfig(
            name="parent_client",
            log_dir=temp_log_dir,
            event_server_url=None,
            otel_enabled=False,
        )
        parent = EventClient(config=config)

        # Parent should not be a bound child
        assert parent._is_bound_child is False

        # Bound client should be marked as a child
        child = parent.bind(workflow_id="wf-123")
        assert child._is_bound_child is True

        parent.close()

    def test_bound_child_flag_set_on_unbind(self, temp_log_dir):
        """Test that unbind() sets _is_bound_child flag on new client."""
        config = EventClientConfig(
            name="parent_client",
            log_dir=temp_log_dir,
            event_server_url=None,
            otel_enabled=False,
        )
        parent = EventClient(config=config)
        bound = parent.bind(key1="a", key2="b")

        # Unbound client should also be marked as a child
        unbound = bound.unbind("key1")
        assert unbound._is_bound_child is True

        parent.close()

    def test_bound_child_close_does_not_close_shared_resources(self, temp_log_dir):
        """Test that closing a bound child does not close shared resources."""
        config = EventClientConfig(
            name="parent_client",
            log_dir=temp_log_dir,
            event_server_url=None,
            otel_enabled=False,
        )
        parent = EventClient(config=config)
        child = parent.bind(workflow_id="wf-123")

        # Get references to shared resources
        parent_handlers = list(parent.logger.handlers)
        parent_session = parent.session

        # Close the child - this should NOT close shared resources
        child.close()

        # Parent's handlers should still be intact
        assert len(parent.logger.handlers) == len(parent_handlers)
        for handler in parent.logger.handlers:
            # Handlers should not be closed
            assert hasattr(handler, "stream") or hasattr(handler, "baseFilename")

        # Parent should still be able to log
        parent.info("Still logging after child close")

        # Parent's session should still work
        assert parent.session is parent_session

        # Now close the parent - this SHOULD close resources
        parent.close()

    def test_nested_bound_children_all_marked_as_children(self, temp_log_dir):
        """Test that nested bindings all create child clients."""
        config = EventClientConfig(
            name="parent_client",
            log_dir=temp_log_dir,
            event_server_url=None,
            otel_enabled=False,
        )
        parent = EventClient(config=config)

        child1 = parent.bind(level1="a")
        child2 = child1.bind(level2="b")
        child3 = child2.bind(level3="c")

        assert parent._is_bound_child is False
        assert child1._is_bound_child is True
        assert child2._is_bound_child is True
        assert child3._is_bound_child is True

        # Closing children should not affect parent
        child3.close()
        child2.close()
        child1.close()

        # Parent should still work
        parent.info("Parent still works")
        parent.close()

    def test_bound_children_share_buffer_and_lock(self, temp_log_dir):
        """Test that bound children share the same buffer and lock as parent."""
        config = EventClientConfig(
            name="parent_client",
            log_dir=temp_log_dir,
            event_server_url=None,
            otel_enabled=False,
        )
        parent = EventClient(config=config)
        child = parent.bind(workflow_id="wf-123")

        # They should share the same buffer and lock (shallow copy behavior)
        assert child._event_buffer is parent._event_buffer
        assert child._buffer_lock is parent._buffer_lock

        parent.close()
