"""Unit tests for EventClient."""

import logging
import tempfile
import time
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
    def test_get_event_http_error(self, mock_create_session, config_with_server, temp_log_dir):
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
    def test_get_events_http_error(self, mock_create_session, config_with_server, temp_log_dir):
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
    def test_query_events_http_error(self, mock_create_session, config_with_server, temp_log_dir):
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
            timeout=30.0,
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
                timeout=60.0,
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
            timeout=60.0,
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
                timeout=60.0,
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
            timeout=60.0,
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
