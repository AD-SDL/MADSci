"""Tests for the SiLA2 node client."""

from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest
from madsci.client.node.sila_node_client import (
    SILA2_AVAILABLE,
    SilaNodeClient,
    _parse_sila_url,
    _resolve_sila_command,
    _response_to_dict,
)
from madsci.common.types.action_types import ActionRequest, ActionStatus
from madsci.common.types.client_types import SilaNodeClientConfig
from pydantic import AnyUrl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_sila_client():
    """Create a mock SiLA client with standard features."""
    mock_client = MagicMock()
    mock_client.SiLAService.ImplementedFeatures.get.return_value = [
        "GreetingProvider",
        "TimerProvider",
    ]
    mock_client.SiLAService.ServerName.get.return_value = "TestServer"
    return mock_client


def _make_sila_node_client(mock_sila_client=None):
    """Create a SilaNodeClient with a mocked SiLA client."""
    with (
        patch("madsci.client.node.sila_node_client.SILA2_AVAILABLE", True),
        patch("madsci.client.node.sila_node_client.SilaClient"),
    ):
        client = SilaNodeClient(url="sila://localhost:50052")
        if mock_sila_client is not None:
            client._sila_client = mock_sila_client
        return client


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------


class TestSilaImportGuard:
    """Test behavior when sila2 is not installed."""

    def test_sila2_not_available_raises_import_error(self):
        """SilaNodeClient() should raise ImportError when sila2 is not installed."""
        with (
            patch("madsci.client.node.sila_node_client.SILA2_AVAILABLE", False),
            pytest.raises(ImportError, match="sila2"),
        ):
            SilaNodeClient(url="sila://localhost:50052")

    def test_sila2_available_flag(self):
        """SILA2_AVAILABLE should be importable and reflect actual package state."""
        assert isinstance(SILA2_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


class TestSilaUrlValidation:
    """Test URL scheme detection."""

    def test_validates_sila_scheme_string(self):
        """validate_url should accept sila:// URLs as strings."""
        assert SilaNodeClient.validate_url("sila://localhost:50052") is True

    def test_rejects_http_scheme_string(self):
        """validate_url should reject http:// URLs."""
        assert SilaNodeClient.validate_url("http://localhost:8080") is False

    def test_validates_anyurl_object(self):
        """validate_url should work with AnyUrl objects."""
        url = AnyUrl("sila://192.168.1.100:50052")
        assert SilaNodeClient.validate_url(url) is True

    def test_rejects_anyurl_http(self):
        """validate_url should reject AnyUrl with http scheme."""
        url = AnyUrl("http://localhost:8080")
        assert SilaNodeClient.validate_url(url) is False


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


class TestSilaUrlParsing:
    """Test _parse_sila_url helper."""

    def test_parses_host_and_port(self):
        host, port = _parse_sila_url("sila://192.168.1.100:50052")
        assert host == "192.168.1.100"
        assert port == 50052

    def test_custom_port(self):
        host, port = _parse_sila_url("sila://myhost:12345")
        assert host == "myhost"
        assert port == 12345

    def test_default_port(self):
        host, port = _parse_sila_url("sila://myhost")
        assert host == "myhost"
        assert port == 50052


# ---------------------------------------------------------------------------
# Action name resolution
# ---------------------------------------------------------------------------


class TestActionNameResolution:
    """Test qualified vs short-form action name resolution."""

    def test_qualified_name(self):
        """'Feature.Command' should resolve directly."""
        mock_client = MagicMock()
        _command, feat, cmd = _resolve_sila_command(
            mock_client, "GreetingProvider.SayHello"
        )
        assert feat == "GreetingProvider"
        assert cmd == "SayHello"

    def test_short_name_unambiguous(self):
        """Short command name should resolve when only one feature has it."""
        mock_client = MagicMock()
        mock_client.SiLAService.ImplementedFeatures.get.return_value = [
            "GreetingProvider"
        ]
        # Only GreetingProvider has SayHello
        mock_client.GreetingProvider.SayHello = MagicMock()

        _command, feat, cmd = _resolve_sila_command(mock_client, "SayHello")
        assert feat == "GreetingProvider"
        assert cmd == "SayHello"

    def test_short_name_ambiguous_raises(self):
        """Short command name on multiple features should raise ValueError."""
        mock_client = MagicMock()
        mock_client.SiLAService.ImplementedFeatures.get.return_value = [
            "Feat1",
            "Feat2",
        ]
        mock_client.Feat1.DoStuff = MagicMock()
        mock_client.Feat2.DoStuff = MagicMock()

        with pytest.raises(ValueError, match="Ambiguous"):
            _resolve_sila_command(mock_client, "DoStuff")

    def test_unknown_command_raises(self):
        """Non-existent command should raise ValueError."""
        mock_client = MagicMock()
        mock_client.SiLAService.ImplementedFeatures.get.return_value = []

        with pytest.raises(ValueError, match="not found"):
            _resolve_sila_command(mock_client, "NonExistent")

    def test_qualified_unknown_feature_raises(self):
        """Qualified name with unknown feature should raise ValueError."""
        mock_client = MagicMock()
        mock_client.UnknownFeature = None  # getattr returns None

        with pytest.raises(ValueError, match="not found"):
            _resolve_sila_command(mock_client, "UnknownFeature.DoStuff")

    def test_qualified_unknown_command_raises(self):
        """Qualified name with unknown command should raise ValueError."""
        mock_client = MagicMock()
        mock_client.GreetingProvider = MagicMock(spec=[])  # no attributes

        with pytest.raises(ValueError, match="not found"):
            _resolve_sila_command(mock_client, "GreetingProvider.NoSuchCommand")


# ---------------------------------------------------------------------------
# Response conversion
# ---------------------------------------------------------------------------


class TestResponseToDict:
    """Test SiLA response conversion."""

    def test_namedtuple_response(self):
        Resp = namedtuple("Resp", ["Greeting", "Count"])
        resp = Resp(Greeting="Hello", Count=42)
        result = _response_to_dict(resp)
        assert result == {"Greeting": "Hello", "Count": 42}

    def test_none_response(self):
        assert _response_to_dict(None) == {}

    def test_dict_passthrough(self):
        d = {"key": "value"}
        assert _response_to_dict(d) == d

    def test_object_with_dict(self):
        class Resp:
            def __init__(self):
                self.Greeting = "Hello"
                self.Count = 42

        result = _response_to_dict(Resp())
        assert result == {"Greeting": "Hello", "Count": 42}

    def test_fallback_to_str(self):
        result = _response_to_dict(12345)
        assert result == {"result": "12345"}


# ---------------------------------------------------------------------------
# send_action
# ---------------------------------------------------------------------------


class TestSendAction:
    """Test SiLA command execution."""

    def test_unobservable_command_succeeds(self):
        """Unobservable SiLA commands should return SUCCEEDED immediately."""
        mock_client = _make_mock_sila_client()

        Resp = namedtuple("SayHello_Responses", ["Greeting"])
        mock_client.GreetingProvider.SayHello.return_value = Resp(
            Greeting="Hello World"
        )

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello",
            args={"Name": "World"},
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result == {"Greeting": "Hello World"}

    def test_unobservable_void_command(self):
        """Void commands (returning None) should succeed with empty json_result."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.Reset.return_value = None

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="GreetingProvider.Reset", args={})
        result = node_client.send_action(request)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result == {}

    def test_observable_command_with_await(self):
        """Observable SiLA commands with await_result=True should block and return result."""
        mock_client = _make_mock_sila_client()

        mock_instance = MagicMock()
        mock_instance.status = "running"
        Resp = namedtuple("Countdown_Responses", ["Result"])
        mock_instance.get_responses.return_value = Resp(Result="Done")
        mock_client.TimerProvider.Countdown.return_value = mock_instance

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="TimerProvider.Countdown",
            args={"Duration": 1},
        )
        result = node_client.send_action(request, await_result=True)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result == {"Result": "Done"}

    def test_observable_command_without_await(self):
        """Observable SiLA commands with await_result=False should return RUNNING."""
        mock_client = _make_mock_sila_client()

        mock_instance = MagicMock()
        mock_instance.status = "running"
        mock_client.TimerProvider.Countdown.return_value = mock_instance

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="TimerProvider.Countdown",
            args={"Duration": 10},
        )
        result = node_client.send_action(request, await_result=False)

        assert result.status == ActionStatus.RUNNING
        assert result.action_id in node_client._running_commands

    def test_command_failure_returns_failed(self):
        """Command exceptions should produce FAILED ActionResult."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.SayHello.side_effect = RuntimeError(
            "gRPC unavailable"
        )

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello",
            args={"Name": "World"},
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        assert len(result.errors) > 0
        assert "gRPC unavailable" in result.errors[0].message

    def test_unknown_action_returns_failed(self):
        """Unknown action name should return FAILED."""
        mock_client = _make_mock_sila_client()

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="NonExistent.Command", args={})
        # NonExistent feature is not None on MagicMock, but the command
        # resolution will fail since getattr returns a new MagicMock
        # Let's explicitly set it to None
        mock_client.NonExistent = None

        result = node_client.send_action(request)
        assert result.status == ActionStatus.FAILED


# ---------------------------------------------------------------------------
# get_action_status / get_action_result
# ---------------------------------------------------------------------------


class TestGetActionStatus:
    """Test observable command status queries."""

    def test_running_status(self):
        """Should return RUNNING for active commands."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = False
        mock_instance.status = "running"
        node_client._running_commands["test-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        status = node_client.get_action_status("test-id")
        assert status == ActionStatus.RUNNING

    def test_finished_status(self):
        """Should return SUCCEEDED for finished commands."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedSuccessfully"
        node_client._running_commands["test-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        status = node_client.get_action_status("test-id")
        assert status == ActionStatus.SUCCEEDED

    def test_error_status(self):
        """Should return FAILED for errored commands."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedWithError"
        node_client._running_commands["test-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        status = node_client.get_action_status("test-id")
        assert status == ActionStatus.FAILED

    def test_unknown_action_id(self):
        """Should return UNKNOWN for untracked action IDs."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_action_status("nonexistent-id")
        assert status == ActionStatus.UNKNOWN


class TestGetActionResult:
    """Test observable command result retrieval."""

    def test_completed_result(self):
        """Should return ActionResult with json_result for completed commands."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedSuccessfully"
        Resp = namedtuple("Resp", ["Value"])
        mock_instance.get_responses.return_value = Resp(Value=42)
        node_client._running_commands["test-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        result = node_client.get_action_result("test-id")
        assert result.status == ActionStatus.SUCCEEDED
        assert result.json_result == {"Value": 42}
        # Should be cleaned up from tracking
        assert "test-id" not in node_client._running_commands

    def test_still_running(self):
        """Should return RUNNING status with no json_result."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = False
        mock_instance.status = "running"
        node_client._running_commands["test-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        result = node_client.get_action_result("test-id")
        assert result.status == ActionStatus.RUNNING

    def test_unknown_action_id(self):
        """Should return UNKNOWN with error for untracked action IDs."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        result = node_client.get_action_result("nonexistent-id")
        assert result.status == ActionStatus.UNKNOWN
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# get_status / get_info / get_state
# ---------------------------------------------------------------------------


class TestGetStatus:
    """Test SiLA node status reporting."""

    def test_connected_idle(self):
        """Should return non-errored status when connected and idle."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_status()
        assert not status.errored
        assert not status.disconnected
        assert not status.busy

    def test_connected_busy(self):
        """Should report busy when observable commands are tracked."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)
        node_client._running_commands["action-1"] = (MagicMock(), "F", "C")

        status = node_client.get_status()
        assert status.busy
        assert "action-1" in status.running_actions

    def test_disconnected(self):
        """Should report disconnected when server is unreachable."""
        mock_client = _make_mock_sila_client()
        mock_client.SiLAService.ImplementedFeatures.get.side_effect = ConnectionError(
            "unreachable"
        )
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_status()
        assert status.errored
        assert status.disconnected
        assert len(status.errors) > 0


class TestGetInfo:
    """Test SiLA node introspection."""

    def test_builds_action_definitions(self):
        """Should create ActionDefinition for each callable on each feature."""
        mock_client = _make_mock_sila_client()
        # Configure GreetingProvider to have SayHello as callable
        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["SayHello", "_internal"]
        mock_client.GreetingProvider = greeting_feature

        timer_feature = MagicMock()
        timer_feature.__dir__ = lambda _self: ["Countdown", "_private"]
        mock_client.TimerProvider = timer_feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.node_name == "TestServer"
        assert info.module_name == "sila2"
        assert "GreetingProvider.SayHello" in info.actions
        assert "TimerProvider.Countdown" in info.actions

    def test_action_args_populated(self):
        """Should populate ArgumentDefinition from SiLA command parameters."""
        mock_client = _make_mock_sila_client()

        # Mock a feature with a command that has parameters
        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["SayHello"]

        # Build mock wrapped command with parameters
        mock_param = MagicMock()
        mock_param._identifier = "Name"
        mock_param._description = "The name to greet."
        mock_param.data_type = MagicMock()
        type(mock_param.data_type).__name__ = "String"

        mock_wrapped = MagicMock()
        mock_wrapped.parameters.fields = [mock_param]

        greeting_feature.SayHello._wrapped_command = mock_wrapped
        mock_client.GreetingProvider = greeting_feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        action_def = info.actions["GreetingProvider.SayHello"]
        assert "Name" in action_def.args
        arg = action_def.args["Name"]
        assert arg.name == "Name"
        assert arg.description == "The name to greet."
        assert arg.argument_type == "String"
        assert arg.required is True

    def test_observable_flag(self):
        """Should set asynchronous=True for observable commands."""
        mock_client = _make_mock_sila_client()

        feature = MagicMock()
        feature.__dir__ = lambda _self: ["CountDown"]

        # ClientObservableCommand class name
        mock_cmd = MagicMock()
        mock_cmd.__class__.__name__ = "ClientObservableCommand"
        mock_cmd._wrapped_command.parameters.fields = []
        feature.CountDown = mock_cmd
        mock_client.GreetingProvider = feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.actions["GreetingProvider.CountDown"].asynchronous is True

    def test_unobservable_flag(self):
        """Should set asynchronous=False for unobservable commands."""
        mock_client = _make_mock_sila_client()

        feature = MagicMock()
        feature.__dir__ = lambda _self: ["Greet"]

        mock_cmd = MagicMock()
        mock_cmd.__class__.__name__ = "ClientUnobservableCommand"
        mock_cmd._wrapped_command.parameters.fields = []
        feature.Greet = mock_cmd
        mock_client.GreetingProvider = feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.actions["GreetingProvider.Greet"].asynchronous is False

    def test_server_name_fallback(self):
        """Should use fallback name when SiLAService.ServerName fails."""
        mock_client = _make_mock_sila_client()
        mock_client.SiLAService.ServerName.get.side_effect = Exception("no name")
        mock_client.SiLAService.ImplementedFeatures.get.return_value = []

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.node_name == "SiLA Server"


class TestGetState:
    """Test SiLA property reading."""

    def test_reads_properties(self):
        """Should read property values from all features."""
        mock_client = _make_mock_sila_client()

        # Create a mock feature with a property-like attribute
        # SiLA properties have .get() but are not callable
        class MockProperty:
            def get(self):
                return 2022

        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["StartYear"]
        greeting_feature.StartYear = MockProperty()

        mock_client.GreetingProvider = greeting_feature
        mock_client.TimerProvider = MagicMock()
        mock_client.TimerProvider.__dir__ = lambda _self: []

        node_client = _make_sila_node_client(mock_client)
        state = node_client.get_state()

        assert "GreetingProvider.StartYear" in state
        assert state["GreetingProvider.StartYear"] == 2022

    def test_property_error_returns_none(self):
        """Should return None for properties that fail to read."""
        mock_client = _make_mock_sila_client()

        class BrokenProperty:
            def get(self):
                raise RuntimeError("read failed")

        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["BrokenProp"]
        greeting_feature.BrokenProp = BrokenProperty()

        mock_client.GreetingProvider = greeting_feature
        mock_client.TimerProvider = MagicMock()
        mock_client.TimerProvider.__dir__ = lambda _self: []

        node_client = _make_sila_node_client(mock_client)
        state = node_client.get_state()

        assert state.get("GreetingProvider.BrokenProp") is None


# ---------------------------------------------------------------------------
# Capabilities declaration
# ---------------------------------------------------------------------------


class TestCapabilities:
    """Test capability declaration."""

    def test_supported_capabilities(self):
        """Should declare the correct capability set."""
        caps = SilaNodeClient.supported_capabilities
        assert caps.send_action is True
        assert caps.get_info is True
        assert caps.get_status is True
        assert caps.get_state is True
        assert caps.get_action_status is True
        assert caps.get_action_result is True
        assert caps.action_files is False
        assert caps.get_action_history is False
        assert caps.send_admin_commands is False
        assert caps.set_config is False
        assert caps.get_resources is False
        assert caps.get_log is False


# ---------------------------------------------------------------------------
# Registration / dispatch
# ---------------------------------------------------------------------------


class TestRegistration:
    """Test conditional NODE_CLIENT_MAP registration."""

    def test_url_protocols(self):
        """SilaNodeClient should declare sila as its protocol."""
        assert "sila" in SilaNodeClient.url_protocols

    def test_find_node_client_dispatches_sila(self):
        """find_node_client should return SilaNodeClient for sila:// URLs."""
        from madsci.client.node import NODE_CLIENT_MAP  # noqa: PLC0415

        if not SILA2_AVAILABLE:
            pytest.skip("sila2 not installed")

        assert "sila_node_client" in NODE_CLIENT_MAP

        from madsci.workcell_manager.workcell_utils import (  # noqa: PLC0415
            find_node_client,
        )

        with patch("madsci.client.node.sila_node_client.SilaClient"):
            client = find_node_client(AnyUrl("sila://localhost:50052"))

        assert client is not None
        assert type(client).__name__ == "SilaNodeClient"


# ---------------------------------------------------------------------------
# Close / cleanup
# ---------------------------------------------------------------------------


class TestClose:
    """Test cleanup."""

    def test_close_clears_state(self):
        """close() should clear the SiLA client and tracked commands."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)
        node_client._running_commands["test"] = (MagicMock(), "F", "C")

        node_client.close()

        assert node_client._sila_client is None
        assert len(node_client._running_commands) == 0


# ---------------------------------------------------------------------------
# SilaNodeClientConfig
# ---------------------------------------------------------------------------


class TestSilaNodeClientConfig:
    """Test SiLA client configuration."""

    def test_defaults(self):
        """Should have sensible defaults."""
        config = SilaNodeClientConfig()
        assert config.insecure is True
        assert config.root_certs_path is None
        assert config.command_timeout == 300.0
        assert config.poll_interval == 0.5

    def test_env_override(self, monkeypatch):
        """Should respect environment variable overrides."""
        monkeypatch.setenv("SILA_NODE_CLIENT_INSECURE", "false")
        monkeypatch.setenv("SILA_NODE_CLIENT_COMMAND_TIMEOUT", "60.0")

        config = SilaNodeClientConfig()
        assert config.insecure is False
        assert config.command_timeout == 60.0
