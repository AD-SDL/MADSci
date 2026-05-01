"""Tests for the SiLA2 node client."""

import base64
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from madsci.client.node.sila_node_client import (
    SILA2_AVAILABLE,
    SilaNodeClient,
    _classify_connection_error,
    _extract_bytes_files,
    _format_connection_error,
    _parse_sila_url,
    _resolve_sila_command,
    _response_to_dict,
    _safe_path_component,
    _serialize_value,
)
from madsci.common.types.action_types import ActionFiles, ActionRequest, ActionStatus
from madsci.common.types.client_types import SilaNodeClientConfig
from pydantic import AnyUrl
from sila2.client.client_observable_command import ClientObservableCommand
from sila2.client.client_observable_property import ClientObservableProperty
from sila2.client.client_unobservable_command import ClientUnobservableCommand
from sila2.client.client_unobservable_property import ClientUnobservableProperty

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_command(observable: bool = False) -> MagicMock:
    """Create a MagicMock that satisfies isinstance against the appropriate SDK base."""
    spec = ClientObservableCommand if observable else ClientUnobservableCommand
    return MagicMock(spec=spec)


def _make_property(observable: bool = False) -> MagicMock:
    """Create a MagicMock that satisfies isinstance against a SiLA property base."""
    spec = ClientObservableProperty if observable else ClientUnobservableProperty
    return MagicMock(spec=spec)


def _make_mock_sila_client():
    """Create a mock SiLA client with standard features and known commands.

    The standard commands are pre-configured as MagicMock(spec=...) so that
    isinstance(attr, _SILA_COMMAND_TYPES) succeeds. Tests that care about
    return values can still set `.return_value` / `.side_effect` on them
    (e.g., mock_client.GreetingProvider.SayHello.return_value = ...).
    """
    mock_client = MagicMock()
    mock_client.SiLAService.ImplementedFeatures.get.return_value = [
        "GreetingProvider",
        "TimerProvider",
    ]
    mock_client.SiLAService.ServerName.get.return_value = "TestServer"
    # Pre-configured commands used across many tests.
    mock_client.GreetingProvider.SayHello = _make_command(observable=False)
    mock_client.GreetingProvider.Reset = _make_command(observable=False)
    mock_client.TimerProvider.Countdown = _make_command(observable=True)
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

    def test_validates_sila_scheme(self):
        """validate_url should accept sila:// URLs."""
        assert SilaNodeClient.validate_url(AnyUrl("sila://localhost:50052")) is True

    def test_rejects_http_scheme(self):
        """validate_url should reject http:// URLs."""
        assert SilaNodeClient.validate_url(AnyUrl("http://localhost:8080")) is False

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
        """'Feature.Command' should resolve directly when attr is a SiLA command."""
        mock_client = MagicMock()
        mock_client.GreetingProvider.SayHello = _make_command(observable=False)
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
        mock_client.GreetingProvider.SayHello = _make_command(observable=False)

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
        mock_client.Feat1.DoStuff = _make_command(observable=False)
        mock_client.Feat2.DoStuff = _make_command(observable=False)

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

    def test_qualified_non_command_raises(self):
        """Qualified name resolving to a SiLA property should raise ValueError."""
        mock_client = MagicMock()
        mock_client.GreetingProvider.ServerName = _make_property(observable=False)

        with pytest.raises(ValueError, match="not a SiLA command"):
            _resolve_sila_command(mock_client, "GreetingProvider.ServerName")

    def test_qualified_callable_non_command_raises(self):
        """Qualified name resolving to a plain callable that is not a SiLA command should raise."""
        mock_client = MagicMock()
        mock_client.GreetingProvider.helper_method = (
            MagicMock()
        )  # callable but not a command

        with pytest.raises(ValueError, match="not a SiLA command"):
            _resolve_sila_command(mock_client, "GreetingProvider.helper_method")

    def test_short_name_ignores_non_command_callables(self):
        """Short-form lookup should resolve unambiguously when only one feature has a real command."""
        mock_client = MagicMock()
        mock_client.SiLAService.ImplementedFeatures.get.return_value = [
            "Feat1",
            "Feat2",
        ]
        mock_client.Feat1.DoStuff = _make_command(observable=False)
        # Feat2.DoStuff is callable but NOT a SiLA command — should be ignored.
        mock_client.Feat2.DoStuff = MagicMock()

        _command, feat, _cmd = _resolve_sila_command(mock_client, "DoStuff")
        assert feat == "Feat1"

    def test_short_name_skips_non_command_callable_only(self):
        """Short-form lookup raises 'not found' if only non-command callables match."""
        mock_client = MagicMock()
        mock_client.SiLAService.ImplementedFeatures.get.return_value = [
            "Feat1",
        ]
        mock_client.Feat1.DoStuff = MagicMock()  # callable, not a command

        with pytest.raises(ValueError, match="not found"):
            _resolve_sila_command(mock_client, "DoStuff")


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
        """Unknown action name should return FAILED with the bare resolution error."""
        mock_client = _make_mock_sila_client()
        # Mark feature as missing BEFORE invoking send_action so resolution fails.
        mock_client.NonExistent = None

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="NonExistent.Command", args={})
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        assert len(result.errors) > 0
        # Bare resolution error message — NOT the connection-error wrapper.
        assert "not found" in result.errors[0].message
        assert "SiLA connection error" not in result.errors[0].message


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

    def test_failed_status_propagated(self):
        """Should return FAILED when get_action_status reports FAILED."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedWithError"
        Resp = namedtuple("Resp", ["PartialData"])
        mock_instance.get_responses.return_value = Resp(PartialData="partial")
        node_client._running_commands["fail-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        result = node_client.get_action_result("fail-id")
        assert result.status == ActionStatus.FAILED
        assert result.json_result == {"PartialData": "partial"}
        assert "fail-id" not in node_client._running_commands

    def test_failed_status_when_get_responses_raises(self):
        """Should return FAILED with errors when FAILED and get_responses() raises."""
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedWithError"
        mock_instance.get_responses.side_effect = RuntimeError("no responses available")
        node_client._running_commands["fail-id-2"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        result = node_client.get_action_result("fail-id-2")
        assert result.status == ActionStatus.FAILED
        assert len(result.errors) > 0
        assert "no responses available" in result.errors[0].message
        assert "fail-id-2" not in node_client._running_commands

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
        """Should create ActionDefinition only for SiLA command instances on each feature."""
        mock_client = _make_mock_sila_client()
        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["SayHello", "_internal"]
        greeting_feature.SayHello = _make_command(observable=False)
        mock_client.GreetingProvider = greeting_feature

        timer_feature = MagicMock()
        timer_feature.__dir__ = lambda _self: ["Countdown", "_private"]
        timer_feature.Countdown = _make_command(observable=True)
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

        greeting_feature = MagicMock()
        greeting_feature.__dir__ = lambda _self: ["SayHello"]

        mock_param = MagicMock()
        mock_param._identifier = "Name"
        mock_param._description = "The name to greet."
        mock_param.data_type = MagicMock()
        type(mock_param.data_type).__name__ = "String"

        mock_wrapped = MagicMock()
        mock_wrapped.parameters.fields = [mock_param]

        say_hello = _make_command(observable=False)
        say_hello._wrapped_command = mock_wrapped  # set first; spec blocks GET, not SET
        greeting_feature.SayHello = say_hello
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
        feature.CountDown = _make_command(observable=True)
        mock_client.GreetingProvider = feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.actions["GreetingProvider.CountDown"].asynchronous is True

    def test_unobservable_flag(self):
        """Should set asynchronous=False for unobservable commands."""
        mock_client = _make_mock_sila_client()

        feature = MagicMock()
        feature.__dir__ = lambda _self: ["Greet"]
        feature.Greet = _make_command(observable=False)
        mock_client.GreetingProvider = feature

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert info.actions["GreetingProvider.Greet"].asynchronous is False

    def test_excludes_properties_from_actions(self):
        """get_info() must not include SiLA properties as ActionDefinitions."""
        mock_client = _make_mock_sila_client()

        feature = MagicMock()
        feature.__dir__ = lambda _self: ["Greet", "ServerUptime"]
        feature.Greet = _make_command(observable=False)
        feature.ServerUptime = _make_property(observable=False)
        mock_client.GreetingProvider = feature
        # Strip the pre-configured TimerProvider from this fixture so only our feature is enumerated.
        timer = MagicMock()
        timer.__dir__ = lambda _self: []
        mock_client.TimerProvider = timer

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert "GreetingProvider.Greet" in info.actions
        assert "GreetingProvider.ServerUptime" not in info.actions

    def test_excludes_non_command_callables_from_actions(self):
        """get_info() must not include arbitrary callables as ActionDefinitions."""
        mock_client = _make_mock_sila_client()

        feature = MagicMock()
        feature.__dir__ = lambda _self: ["Greet", "helper"]
        feature.Greet = _make_command(observable=False)
        feature.helper = MagicMock()  # callable but not a SiLA command
        mock_client.GreetingProvider = feature
        timer = MagicMock()
        timer.__dir__ = lambda _self: []
        mock_client.TimerProvider = timer

        node_client = _make_sila_node_client(mock_client)
        info = node_client.get_info()

        assert "GreetingProvider.Greet" in info.actions
        assert "GreetingProvider.helper" not in info.actions

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
        assert caps.action_files is True
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


# ---------------------------------------------------------------------------
# Bytes handling
# ---------------------------------------------------------------------------


class TestSerializeValueBytes:
    """Test _serialize_value with bytes input."""

    def test_bytes_produces_sentinel_dict(self):
        """Bytes should be converted to a sentinel dict with base64 encoding."""
        data = b"\x89PNG\r\n\x1a\n"
        result = _serialize_value(data)
        assert isinstance(result, dict)
        assert result["__madsci_bytes__"] is True
        assert result["base64"] == base64.b64encode(data).decode("ascii")
        assert result["size"] == len(data)

    def test_empty_bytes(self):
        """Empty bytes should produce a valid sentinel dict."""
        result = _serialize_value(b"")
        assert result["__madsci_bytes__"] is True
        assert result["base64"] == ""
        assert result["size"] == 0

    def test_non_bytes_unchanged(self):
        """Non-bytes primitives should still serialize normally."""
        assert _serialize_value("hello") == "hello"
        assert _serialize_value(42) == 42
        assert _serialize_value(None) is None


class TestExtractBytesFiles:
    """Test _extract_bytes_files post-processing."""

    def test_extracts_single_bytes_field(self, tmp_path, monkeypatch):
        """Should write file and return ActionFiles for a single bytes field."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        raw = b"hello world"
        json_result = {
            "ImageData": {
                "__madsci_bytes__": True,
                "base64": base64.b64encode(raw).decode("ascii"),
                "size": len(raw),
            },
            "Label": "test",
        }

        cleaned, files = _extract_bytes_files(json_result, "action-123")

        assert files is not None
        assert isinstance(files, ActionFiles)
        file_path = files.ImageData
        assert isinstance(file_path, Path)
        assert file_path.read_bytes() == raw
        assert file_path.name == "ImageData.bin"
        assert cleaned["ImageData"] == base64.b64encode(raw).decode("ascii")
        assert cleaned["Label"] == "test"

    def test_extracts_multiple_bytes_fields(self, tmp_path, monkeypatch):
        """Should handle multiple bytes fields."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        json_result = {
            "Data1": {
                "__madsci_bytes__": True,
                "base64": base64.b64encode(b"aaa").decode("ascii"),
                "size": 3,
            },
            "Data2": {
                "__madsci_bytes__": True,
                "base64": base64.b64encode(b"bbb").decode("ascii"),
                "size": 3,
            },
        }

        _cleaned, files = _extract_bytes_files(json_result, "action-456")

        assert files is not None
        assert files.Data1.read_bytes() == b"aaa"
        assert files.Data2.read_bytes() == b"bbb"

    def test_no_bytes_returns_none(self):
        """Should return None for ActionFiles when no bytes fields present."""
        json_result = {"Greeting": "Hello", "Count": 42}
        cleaned, files = _extract_bytes_files(json_result, "action-789")

        assert files is None
        assert cleaned == json_result


class TestBytesEndToEndUnobservable:
    """Test end-to-end bytes handling for unobservable commands."""

    def test_unobservable_command_with_bytes(self, tmp_path, monkeypatch):
        """ActionResult should have files and base64 json_result for bytes responses."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        mock_client = _make_mock_sila_client()

        raw = b"\x00\x01\x02\x03"
        Resp = namedtuple("ReadSensor_Responses", ["Data", "Label"])
        mock_client.SensorFeature.ReadSensor = _make_command(observable=False)
        mock_client.SensorFeature.ReadSensor.return_value = Resp(
            Data=raw, Label="sensor1"
        )

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="SensorFeature.ReadSensor", args={})
        result = node_client.send_action(request)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.files is not None
        assert isinstance(result.files, ActionFiles)
        file_path = result.files.Data
        assert file_path.read_bytes() == raw
        assert result.json_result["Data"] == base64.b64encode(raw).decode("ascii")
        assert result.json_result["Label"] == "sensor1"


class TestBytesEndToEndObservable:
    """Test end-to-end bytes handling for observable commands."""

    def test_observable_command_with_bytes(self, tmp_path, monkeypatch):
        """Observable commands should also produce ActionFiles for bytes responses."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        mock_client = _make_mock_sila_client()

        raw = b"observable-binary-data"
        Resp = namedtuple("Scan_Responses", ["Image"])

        mock_instance = MagicMock()
        mock_instance.status = "running"
        mock_instance.get_responses.return_value = Resp(Image=raw)
        mock_client.Scanner.Scan = _make_command(observable=True)
        mock_client.Scanner.Scan.return_value = mock_instance

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="Scanner.Scan", args={})
        result = node_client.send_action(request, await_result=True)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.files is not None
        file_path = result.files.Image
        assert file_path.read_bytes() == raw
        assert result.json_result["Image"] == base64.b64encode(raw).decode("ascii")

    def test_get_action_result_with_bytes(self, tmp_path, monkeypatch):
        """get_action_result should produce ActionFiles for bytes in observable results."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        mock_client = _make_mock_sila_client()
        node_client = _make_sila_node_client(mock_client)

        raw = b"polled-result-bytes"
        Resp = namedtuple("Resp", ["BinaryOutput"])

        mock_instance = MagicMock()
        mock_instance.done = True
        mock_instance.status = "finishedSuccessfully"
        mock_instance.get_responses.return_value = Resp(BinaryOutput=raw)
        node_client._running_commands["poll-id"] = (
            mock_instance,
            "Feature",
            "Command",
        )

        result = node_client.get_action_result("poll-id")

        assert result.status == ActionStatus.SUCCEEDED
        assert result.files is not None
        file_path = result.files.BinaryOutput
        assert file_path.read_bytes() == raw


class TestMixedBytesAndNonBytes:
    """Test responses with mixed bytes and non-bytes fields."""

    def test_mixed_response(self, tmp_path, monkeypatch):
        """Only bytes fields should be in ActionFiles; non-bytes in json_result."""
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        mock_client = _make_mock_sila_client()

        raw = b"\xff\xfe"
        Resp = namedtuple("Resp", ["BinaryField", "StringField", "IntField"])
        mock_client.Feature.Command = _make_command(observable=False)
        mock_client.Feature.Command.return_value = Resp(
            BinaryField=raw, StringField="text", IntField=99
        )

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="Feature.Command", args={})
        result = node_client.send_action(request)

        assert result.files is not None
        assert hasattr(result.files, "BinaryField")
        assert not hasattr(result.files, "StringField")
        assert result.json_result["StringField"] == "text"
        assert result.json_result["IntField"] == 99


class TestNoBytesFieldsUnchanged:
    """Test that responses without bytes are unaffected."""

    def test_no_bytes_files_none(self):
        """ActionResult.files should remain None when no bytes in response."""
        mock_client = _make_mock_sila_client()

        Resp = namedtuple("Resp", ["Greeting"])
        mock_client.GreetingProvider.SayHello.return_value = Resp(Greeting="Hello")

        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello", args={"Name": "World"}
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.files is None
        assert result.json_result == {"Greeting": "Hello"}


# ---------------------------------------------------------------------------
# Connection error classification
# ---------------------------------------------------------------------------


class TestClassifyConnectionError:
    """Test _classify_connection_error categories."""

    def test_dns_resolution_failed(self):
        assert (
            _classify_connection_error(Exception("DNS resolution failed for host"))
            == "dns_resolution"
        )

    def test_name_resolution_failure(self):
        assert (
            _classify_connection_error(Exception("Name resolution failure"))
            == "dns_resolution"
        )

    def test_connection_refused(self):
        assert (
            _classify_connection_error(ConnectionRefusedError("Connection refused"))
            == "connection_refused"
        )

    def test_connect_failed(self):
        assert (
            _classify_connection_error(Exception("connect failed"))
            == "connection_refused"
        )

    def test_timeout_error_type(self):
        assert (
            _classify_connection_error(TimeoutError("timed out"))
            == "connection_timeout"
        )

    def test_deadline_exceeded(self):
        assert (
            _classify_connection_error(Exception("Deadline exceeded"))
            == "connection_timeout"
        )

    def test_tls_ssl_error(self):
        assert (
            _classify_connection_error(Exception("SSL handshake failed")) == "tls_error"
        )

    def test_tls_certificate_error(self):
        assert (
            _classify_connection_error(Exception("certificate verify failed"))
            == "tls_error"
        )

    def test_grpc_error(self):
        exc = Exception("grpc call failed")
        assert _classify_connection_error(exc) == "grpc_error"

    def test_unknown_fallback(self):
        assert (
            _classify_connection_error(Exception("something unexpected")) == "unknown"
        )


class TestFormatConnectionError:
    """Test _format_connection_error output format."""

    def test_includes_host_and_port(self):
        msg = _format_connection_error(Exception("refused"), "myhost", 50052, True)
        assert "myhost" in msg
        assert "50052" in msg

    def test_includes_tls_disabled(self):
        msg = _format_connection_error(Exception("refused"), "h", 1, insecure=True)
        assert "TLS: disabled" in msg

    def test_includes_tls_enabled(self):
        msg = _format_connection_error(Exception("refused"), "h", 1, insecure=False)
        assert "TLS: enabled" in msg

    def test_includes_category(self):
        msg = _format_connection_error(
            ConnectionRefusedError("Connection refused"), "h", 1, True
        )
        assert "connection_refused" in msg

    def test_includes_hint(self):
        msg = _format_connection_error(
            ConnectionRefusedError("Connection refused"), "h", 1, True
        )
        assert "Hint:" in msg
        assert "SiLA server is running" in msg

    def test_preserves_original_message(self):
        original = "failed to connect to all addresses; last error: UNAVAILABLE"
        msg = _format_connection_error(Exception(original), "h", 1, True)
        assert original in msg

    def test_dns_hint(self):
        msg = _format_connection_error(
            Exception("DNS resolution failed"), "badhost", 50052, True
        )
        assert "hostname" in msg.lower() or "DNS" in msg


# ---------------------------------------------------------------------------
# Enriched errors in client methods
# ---------------------------------------------------------------------------


class TestEnrichedConnectionErrors:
    """Test that client methods produce enriched error messages."""

    def test_get_status_enriched_error(self):
        """get_status() should return enriched error with host/port on connection failure."""
        mock_client = _make_mock_sila_client()
        mock_client.SiLAService.ImplementedFeatures.get.side_effect = ConnectionError(
            "Connection refused"
        )
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_status()
        assert status.errored
        assert status.disconnected
        assert len(status.errors) > 0
        error_msg = status.errors[0].message
        assert "localhost" in error_msg
        assert "50052" in error_msg
        assert "connection_refused" in error_msg
        assert "Hint:" in error_msg

    def test_send_action_enriched_error(self):
        """send_action() should return enriched error on connection failure."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.SayHello.side_effect = ConnectionError(
            "Connection refused"
        )
        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello", args={"Name": "World"}
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        assert len(result.errors) > 0
        error_msg = result.errors[0].message
        assert "localhost" in error_msg
        assert "50052" in error_msg
        assert "Hint:" in error_msg

    def test_get_state_enriched_error_logged(self):
        """get_state() should log enriched error on connection failure."""
        node_client = _make_sila_node_client()
        # Force _get_sila_client to raise by clearing the mock and patching
        node_client._sila_client = None
        with patch(
            "madsci.client.node.sila_node_client.SilaClient",
            side_effect=ConnectionError("Connection refused"),
        ):
            state = node_client.get_state()
        # get_state returns empty dict on failure
        assert state == {}

    def test_get_info_enriched_error_propagates(self):
        """get_info() should propagate enriched error from _get_sila_client."""
        node_client = _make_sila_node_client()
        node_client._sila_client = None
        with (
            patch(
                "madsci.client.node.sila_node_client.SilaClient",
                side_effect=ConnectionError("Connection refused"),
            ),
            pytest.raises(ConnectionError, match="connection_refused"),
        ):
            node_client.get_info()

    def test_get_status_dns_error(self):
        """get_status() should classify DNS errors."""
        mock_client = _make_mock_sila_client()
        mock_client.SiLAService.ImplementedFeatures.get.side_effect = Exception(
            "DNS resolution failed for my-sila-server"
        )
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_status()
        error_msg = status.errors[0].message
        assert "dns_resolution" in error_msg
        assert "hostname" in error_msg.lower() or "DNS" in error_msg

    def test_get_status_tls_error(self):
        """get_status() should classify TLS errors."""
        mock_client = _make_mock_sila_client()
        mock_client.SiLAService.ImplementedFeatures.get.side_effect = Exception(
            "SSL handshake failed: certificate verify failed"
        )
        node_client = _make_sila_node_client(mock_client)

        status = node_client.get_status()
        error_msg = status.errors[0].message
        assert "tls_error" in error_msg
        assert "TLS" in error_msg or "certificate" in error_msg.lower()


# ---------------------------------------------------------------------------
# Path-traversal hardening for _extract_bytes_files
# ---------------------------------------------------------------------------


def _bytes_sentinel(raw: bytes) -> dict:
    """Build a bytes sentinel dict (matches what _serialize_value emits)."""
    return {
        "__madsci_bytes__": True,
        "base64": base64.b64encode(raw).decode("ascii"),
        "size": len(raw),
    }


class TestSafePathComponent:
    """Test the _safe_path_component helper directly."""

    def test_strips_parent_traversal(self):
        assert _safe_path_component("../etc") == "etc"

    def test_strips_absolute_prefix(self):
        assert _safe_path_component("/abs/path") == "path"

    def test_strips_nested_separators(self):
        assert _safe_path_component("a/b/c") == "c"

    def test_passthrough_simple_name(self):
        assert _safe_path_component("safe_name") == "safe_name"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            _safe_path_component("")

    def test_rejects_dot(self):
        with pytest.raises(ValueError, match="Invalid"):
            _safe_path_component(".")

    def test_rejects_double_dot(self):
        with pytest.raises(ValueError, match="Invalid"):
            _safe_path_component("..")


class TestExtractBytesFilesSafety:
    """Path-traversal hardening tests for _extract_bytes_files."""

    def test_action_id_with_parent_traversal_sanitized(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        raw = b"payload"
        json_result = {"k": _bytes_sentinel(raw)}

        _cleaned, files = _extract_bytes_files(json_result, "../etc")

        # File lands inside tmp_path/etc/, not above tmp_path
        expected = tmp_path / "etc" / "k.bin"
        assert expected.exists()
        assert expected.read_bytes() == raw
        assert files.k == expected
        # Path is inside tmp_path (no escape).
        assert tmp_path in expected.parents

    def test_action_id_with_absolute_path_sanitized(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        raw = b"payload"
        json_result = {"k": _bytes_sentinel(raw)}

        _cleaned, files = _extract_bytes_files(json_result, "/abs/path")

        expected = tmp_path / "path" / "k.bin"
        assert expected.exists()
        assert files.k == expected

    def test_response_key_with_parent_traversal_sanitized(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        raw = b"payload"
        json_result = {"../escaped": _bytes_sentinel(raw)}

        _cleaned, _files = _extract_bytes_files(json_result, "ulid-id")

        expected = tmp_path / "ulid-id" / "escaped.bin"
        assert expected.exists()
        # File path is sanitized inside the per-action subdirectory.
        assert tmp_path in expected.parents

    def test_action_id_empty_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        json_result = {"k": _bytes_sentinel(b"x")}
        with pytest.raises(ValueError, match="Empty"):
            _extract_bytes_files(json_result, "")

    def test_action_id_dot_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        json_result = {"k": _bytes_sentinel(b"x")}
        with pytest.raises(ValueError, match="Invalid"):
            _extract_bytes_files(json_result, ".")

    def test_action_id_double_dot_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        json_result = {"k": _bytes_sentinel(b"x")}
        with pytest.raises(ValueError, match="Invalid"):
            _extract_bytes_files(json_result, "..")

    def test_response_key_dot_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "madsci.client.node.sila_node_client.get_madsci_subdir",
            lambda _name: tmp_path,
        )
        json_result = {".": _bytes_sentinel(b"x")}
        with pytest.raises(ValueError, match="Invalid"):
            _extract_bytes_files(json_result, "ulid-id")


# ---------------------------------------------------------------------------
# Layered error classification in send_action
# ---------------------------------------------------------------------------


class TestSendActionErrorLayering:
    """Verify that send_action distinguishes connection / resolution / execution errors."""

    def test_arg_error_not_enriched(self):
        """A TypeError raised inside the SiLA command should not be wrapped as a connection error."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.SayHello.side_effect = TypeError(
            "missing required argument: 'Name'"
        )
        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="GreetingProvider.SayHello", args={})
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        message = result.errors[0].message
        assert "missing required argument" in message
        assert "SiLA connection error" not in message
        assert result.errors[0].error_type == "TypeError"

    def test_unknown_command_not_enriched(self):
        """An unknown action_name should surface the ValueError text from _resolve_sila_command."""
        mock_client = _make_mock_sila_client()
        mock_client.NonExistent = None
        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(action_name="NonExistent.DoStuff", args={})
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        message = result.errors[0].message
        assert "not found" in message
        assert "SiLA connection error" not in message

    def test_connection_failure_not_double_wrapped(self):
        """If _get_sila_client raises an already-enriched message, send_action must not re-wrap."""
        node_client = _make_sila_node_client()
        node_client._sila_client = None
        with patch(
            "madsci.client.node.sila_node_client.SilaClient",
            side_effect=ConnectionError("Connection refused"),
        ):
            request = ActionRequest(
                action_name="GreetingProvider.SayHello", args={"Name": "World"}
            )
            result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        message = result.errors[0].message
        # The enriched prefix appears exactly once — not nested.
        assert message.count("SiLA connection error") == 1
        assert "connection_refused" in message
        assert "Hint:" in message

    def test_recognized_execution_error_is_enriched(self):
        """A recognized connection-category exception during command call MUST be enriched."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.SayHello.side_effect = TimeoutError(
            "deadline exceeded"
        )
        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello", args={"Name": "World"}
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        message = result.errors[0].message
        assert "SiLA connection error" in message
        assert "connection_timeout" in message
        assert "Hint:" in message

    def test_unknown_category_execution_error_not_enriched(self):
        """An execution exception with no recognized category surfaces its plain message."""
        mock_client = _make_mock_sila_client()
        mock_client.GreetingProvider.SayHello.side_effect = RuntimeError(
            "device returned malformed packet"
        )
        node_client = _make_sila_node_client(mock_client)
        request = ActionRequest(
            action_name="GreetingProvider.SayHello", args={"Name": "World"}
        )
        result = node_client.send_action(request)

        assert result.status == ActionStatus.FAILED
        message = result.errors[0].message
        assert "device returned malformed packet" in message
        assert "SiLA connection error" not in message
