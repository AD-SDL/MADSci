"""Unit tests for the SiLA mode functionality of RestNode."""

import json
import socket
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import MagicMock, patch

import pytest
from madsci.common.types.action_types import ActionFiles
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import (
    RestNode,
    SubServer,
    sila_basic_datatypes,
)
from sila2.client import SilaClient
from sila2.framework import Feature
from sila2.framework.command.unobservable_command import UnobservableCommand


class SilaTestResult(MadsciBaseModel):
    """A pydantic result model for SiLA tests."""

    label: str
    value: float


class SilaTestFiles(ActionFiles):
    """Multiple file results for SiLA tests."""

    first: Path
    second: Path


class SilaTestNode(RestNode):
    """A node whose actions only use SiLA-mappable argument types."""

    __test__ = False

    config: RestNodeConfig
    config_model = RestNodeConfig

    def state_handler(self) -> None:
        """Report a fixed state."""
        self.node_state = {"status_code": 7}

    @action
    def add_numbers(self, a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @action
    def scale(self, value: float, enabled: bool) -> float:
        """Scale a float if enabled."""
        return value * 2 if enabled else value

    @action
    def no_result(self, count: int) -> None:
        """An action with no result."""
        self.last_count = count

    @action
    def read_file(self, input_file: Path) -> dict:
        """Read an uploaded file and report its content."""
        return {"content": input_file.read_text()}

    @action
    def move_to(self, target: LocationArgument) -> dict:
        """Move to a location."""
        return {"representation": target.representation}

    @action
    def make_file(self, count: int) -> Path:
        """Return a single file."""
        out = self.tmp_dir / "single.txt"
        out.write_text(f"count={count}")
        return out

    @action
    def make_files(self, count: int) -> SilaTestFiles:
        """Return multiple files."""
        first = self.tmp_dir / "first.txt"
        second = self.tmp_dir / "second.log"
        first.write_text(f"first={count}")
        second.write_text(f"second={count}")
        return SilaTestFiles(first=first, second=second)

    @action
    def make_model(self, value: float) -> SilaTestResult:
        """Return a pydantic model."""
        return SilaTestResult(label="measurement", value=value)


class SilaStrNode(RestNode):
    """A node with a string action parameter."""

    __test__ = False

    config: RestNodeConfig
    config_model = RestNodeConfig

    @action
    def greet(self, name: str) -> str:
        """Greet someone."""
        return f"hello {name}"


class SilaComplexNode(RestNode):
    """A node with action types that aren't SiLA basic types."""

    __test__ = False

    config: RestNodeConfig
    config_model = RestNodeConfig

    @action
    def sum_values(self, values: list[int]) -> int:
        """Sum a list of integers."""
        return sum(values)

    @action
    def join_words(self, words: list[str]) -> str:
        """Join a list of strings."""
        return " ".join(words)

    @action
    def count_nested(self, groups: list[list[int]]) -> int:
        """Count items in nested lists."""
        return sum(len(group) for group in groups)

    @action
    def describe(self, options: dict[str, int]) -> dict:
        """Echo a dict."""
        return options

    @action
    def pair(self, value: float) -> tuple[SilaTestResult, int]:
        """Return a tuple."""
        return SilaTestResult(label="pair", value=value), 1

    @action
    def untyped_return(self, count: int):
        """An action without a return annotation."""
        self.last_count = count


def _make_config(**overrides: object) -> RestNodeConfig:
    params = {
        "node_name": "sila_test_node",
        "node_type": "device",
        "module_name": "sila_test_module",
        "enable_registry_resolution": False,
    }
    params.update(overrides)
    return RestNodeConfig(**params)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def sila_node(tmp_path: Path) -> SilaTestNode:
    """A SiLA-compatible test node."""
    node = SilaTestNode(node_config=_make_config())
    node.tmp_dir = tmp_path
    return node


@pytest.fixture
def feature(sila_node: SilaTestNode) -> Feature:
    """The test node's feature definition, as parsed by sila2."""
    return Feature(sila_node.generate_feature_xml())


def _command(feature: Feature, action_name: str) -> UnobservableCommand:
    for command in feature._unobservable_commands.values():
        if command._display_name == action_name:
            return command
    raise AssertionError(f"No command for action {action_name}")


def _type_name(data_type: object) -> str:
    return type(data_type).__name__


def _parameter_types(command: UnobservableCommand) -> dict[str, str]:
    return {
        param._display_name: _type_name(param.data_type)
        for param in command.parameters.fields
    }


def _response_types(command: UnobservableCommand) -> list[str]:
    return [_type_name(resp.data_type) for resp in command.responses.fields]


def _handler(node: RestNode, action_name: str) -> Callable:
    """Build the SiLA handler for an action, as construct_sila_class does."""
    return node.generator(node.action_handlers[action_name])


# --- Configuration -----------------------------------------------------------


def test_sila_mode_defaults_to_false() -> None:
    """sila_mode is opt-in."""
    assert _make_config().sila_mode is False


def test_sila_mode_can_be_enabled() -> None:
    """sila_mode can be set on the config."""
    assert _make_config(sila_mode=True).sila_mode is True


# --- Server construction -----------------------------------------------------


def test_node_builds_sila_server(sila_node: SilaTestNode) -> None:
    """Constructing a RestNode creates a SubServer populated with node info."""
    assert isinstance(sila_node.server, SubServer)
    assert sila_node.server.server_name == "sila_test_node"
    assert sila_node.server.server_type == "MADSCIdevice"
    assert sila_node.server.server_description == sila_node.node_info.node_description


def test_default_node_description_is_generated(sila_node: SilaTestNode) -> None:
    """A missing node description is filled in so the SiLA server has one."""
    assert (
        sila_node.node_info.node_description
        == "A node for sila_test_node of type device"
    )


def test_feature_is_registered_on_server(sila_node: SilaTestNode) -> None:
    """The generated MADSci feature is registered on the SiLA server."""
    expected = "MADSCI" + sila_node.node_info.node_id
    identifiers = [f._identifier for f in sila_node.server.features.values()]
    assert expected in identifiers


def test_subserver_metadata() -> None:
    """SubServer passes through name/description/type and sets MADSci metadata."""
    server = SubServer("my_server", "A description", "MADSCIdevice")
    assert server.server_name == "my_server"
    assert server.server_description == "A description"
    assert server.server_type == "MADSCIdevice"
    assert server.server_vendor_url == "https://github.com/AD-SDL/MADSci"


def test_subserver_uuids_are_unique() -> None:
    """Each SubServer gets its own UUID."""
    first = SubServer("a", "A description", "MADSCIdevice")
    second = SubServer("b", "A description", "MADSCIdevice")
    assert first.server_uuid != second.server_uuid


# --- Feature definition ------------------------------------------------------


def test_feature_header(sila_node: SilaTestNode, feature: Feature) -> None:
    """The feature identifier, name and description come from node info."""
    assert feature._identifier == "MADSCI" + sila_node.node_info.node_id
    assert feature._display_name == "sila_test_node"
    assert feature._description == sila_node.node_info.node_description
    assert feature._originator == "org.madsci"
    assert feature._sila2_version == "1.0"


def test_feature_has_state_property(feature: Feature) -> None:
    """The node state is exposed as an unobservable String property."""
    assert list(feature._unobservable_properties) == ["MADSCIGetState"]
    assert not feature._observable_properties
    prop = feature._unobservable_properties["MADSCIGetState"]
    assert _type_name(prop.data_type) == "String"


def test_feature_has_one_unobservable_command_per_action(
    sila_node: SilaTestNode, feature: Feature
) -> None:
    """Every action becomes an unobservable command."""
    assert not feature._observable_commands
    names = {c._display_name for c in feature._unobservable_commands.values()}
    assert names == set(sila_node.action_handlers)


def test_command_identifier_and_description(feature: Feature) -> None:
    """Action names are made into valid SiLA identifiers."""
    command = _command(feature, "add_numbers")
    assert command._identifier == "MADSCIaddnumbers"
    assert command._description == "Add two integers."


@pytest.mark.parametrize(
    ("action_name", "expected"),
    [
        ("add_numbers", {"a": "Integer", "b": "Integer"}),
        ("scale", {"value": "Real", "enabled": "Boolean"}),
        ("read_file", {"input_file": "Binary"}),
        ("move_to", {"target": "String"}),
    ],
)
def test_command_parameter_types(
    feature: Feature, action_name: str, expected: dict[str, str]
) -> None:
    """Arguments, files and locations map to the right SiLA basic types."""
    assert _parameter_types(_command(feature, action_name)) == expected


def test_parameter_identifiers_strip_non_alphanumerics(feature: Feature) -> None:
    """Parameter identifiers are prefixed and sanitized."""
    command = _command(feature, "read_file")
    assert [p._identifier for p in command.parameters.fields] == ["MADSCIinputfile"]


@pytest.mark.parametrize(
    ("action_name", "expected"),
    [
        ("add_numbers", "Integer"),
        ("scale", "Real"),
        ("make_file", "Binary"),
        ("make_files", "Binary"),
        ("make_model", "String"),
        ("read_file", "String"),
    ],
)
def test_command_response_types(
    feature: Feature, action_name: str, expected: str
) -> None:
    """Return types map to the right SiLA basic types."""
    assert _response_types(_command(feature, action_name)) == [expected]


def test_command_without_result_has_no_response(feature: Feature) -> None:
    """Actions returning None have no responses."""
    assert _response_types(_command(feature, "no_result")) == []


def test_str_parameter_maps_to_string() -> None:
    """str arguments map to the SiLA String type."""
    node = SilaStrNode(node_config=_make_config())
    command = _command(Feature(node.generate_feature_xml()), "greet")
    assert _parameter_types(command) == {"name": "String"}
    assert _response_types(command) == ["String"]


def test_list_parameter_maps_to_sila_list() -> None:
    """list[int] arguments map to a SiLA List of Integer."""
    node = SilaComplexNode(node_config=_make_config())
    command = _command(Feature(node.generate_feature_xml()), "sum_values")
    (param,) = command.parameters.fields
    assert _type_name(param.data_type) == "List"
    assert _type_name(param.data_type.element_type) == "Integer"


@pytest.mark.parametrize(
    ("action_name", "expected"),
    [
        ("join_words", ("List", "String")),
        ("count_nested", ("String", None)),
        ("describe", ("String", None)),
    ],
)
def test_complex_parameter_types(
    action_name: str, expected: tuple[str, Optional[str]]
) -> None:
    """Lists of basic types become SiLA Lists; other complex types become String."""
    node = SilaComplexNode(node_config=_make_config())
    command = _command(Feature(node.generate_feature_xml()), action_name)
    (param,) = command.parameters.fields
    element_type = getattr(param.data_type, "element_type", None)
    assert (
        _type_name(param.data_type),
        _type_name(element_type) if element_type else None,
    ) == expected


def test_tuple_return_maps_to_string() -> None:
    """Generic return types such as tuples map to String."""
    node = SilaComplexNode(node_config=_make_config())
    command = _command(Feature(node.generate_feature_xml()), "pair")
    assert _response_types(command) == ["String"]


def test_basic_datatype_map_covers_builtin_names() -> None:
    """The type map is keyed by the type names used in argument definitions."""
    for type_name in ("str", "int", "float", "bool", "Path"):
        assert type_name in sila_basic_datatypes


# --- Argument processing -----------------------------------------------------


def test_process_bytes_argument_writes_temp_file(sila_node: SilaTestNode) -> None:
    """Binary arguments are written to a temp file and passed as a Path."""
    result = sila_node.process_sila_arguments(b"file contents")
    try:
        assert isinstance(result, Path)
        assert result.read_bytes() == b"file contents"
    finally:
        result.unlink(missing_ok=True)


def test_process_location_json_argument(sila_node: SilaTestNode) -> None:
    """JSON strings that validate as a LocationArgument are converted."""
    location = LocationArgument(representation=[1, 2, 3], location_name="deck_1")
    result = sila_node.process_sila_arguments(
        json.dumps(location.model_dump(mode="json"))
    )
    assert isinstance(result, LocationArgument)
    assert result.representation == [1, 2, 3]
    assert result.location_name == "deck_1"


@pytest.mark.parametrize("value", ["plain text", "", "[1, 2"])
def test_process_non_json_string_is_unchanged(
    sila_node: SilaTestNode, value: str
) -> None:
    """Strings that aren't JSON are passed through."""
    assert sila_node.process_sila_arguments(value) == value


def test_process_json_string_that_is_not_a_location(sila_node: SilaTestNode) -> None:
    """JSON that doesn't validate as a LocationArgument stays a string."""
    value = json.dumps({"not_a_location": True})
    assert sila_node.process_sila_arguments(value) == value


@pytest.mark.parametrize("value", [5, 2.5, True, None])
def test_process_other_arguments_are_unchanged(
    sila_node: SilaTestNode, value: object
) -> None:
    """Non-string, non-bytes arguments are passed through."""
    assert sila_node.process_sila_arguments(value) == value


# --- Generated handlers ------------------------------------------------------


def test_handler_returns_basic_types_unchanged(sila_node: SilaTestNode) -> None:
    """Basic return types are returned as-is."""
    assert _handler(sila_node, "add_numbers")(None, 2, 3) == 5
    assert _handler(sila_node, "scale")(None, 1.5, True) == 3.0


def test_handler_drops_sila_metadata_kwarg(sila_node: SilaTestNode) -> None:
    """The metadata kwarg supplied by the SiLA server isn't passed to the action."""
    assert _handler(sila_node, "add_numbers")(None, 2, 3, metadata={}) == 5


def test_handler_none_result(sila_node: SilaTestNode) -> None:
    """Actions returning None still run."""
    _handler(sila_node, "no_result")(None, 4)
    assert sila_node.last_count == 4


def test_handler_passes_bytes_as_file(sila_node: SilaTestNode) -> None:
    """Binary arguments reach the action as a readable Path."""
    result = _handler(sila_node, "read_file")(None, b"uploaded")
    assert json.loads(result) == {"content": "uploaded"}


def test_handler_passes_location_argument(sila_node: SilaTestNode) -> None:
    """Location JSON reaches the action as a LocationArgument."""
    location = json.dumps({"representation": "slot_A"})
    result = _handler(sila_node, "move_to")(None, location)
    assert json.loads(result) == {"representation": "slot_A"}


def test_handler_returns_file_bytes(sila_node: SilaTestNode) -> None:
    """A Path result is returned as the file's bytes."""
    assert _handler(sila_node, "make_file")(None, 3) == b"count=3"


def test_handler_returns_zipped_action_files(sila_node: SilaTestNode) -> None:
    """ActionFiles results are returned as a ZIP named by file label."""
    result = _handler(sila_node, "make_files")(None, 2)
    with zipfile.ZipFile(BytesIO(result)) as archive:
        assert sorted(archive.namelist()) == ["first.txt", "second.log"]
        assert archive.read("first.txt") == b"first=2"
        assert archive.read("second.log") == b"second=2"


def test_handler_serializes_pydantic_result(sila_node: SilaTestNode) -> None:
    """Pydantic results are returned as JSON strings."""
    result = _handler(sila_node, "make_model")(None, 1.25)
    assert json.loads(result) == {"label": "measurement", "value": 1.25}


def test_handler_serializes_dict_result(sila_node: SilaTestNode) -> None:
    """Other results are returned as JSON strings."""
    result = _handler(sila_node, "move_to")(None, json.dumps({"location": [0, 1]}))
    assert json.loads(result) == {"representation": [0, 1]}


def test_handler_returns_str_result_unquoted() -> None:
    """str results are returned as plain strings, not JSON-encoded."""
    node = SilaStrNode(node_config=_make_config())
    assert _handler(node, "greet")(None, "world") == "hello world"


def test_handler_passes_lists_through() -> None:
    """List arguments reach the action as lists."""
    node = SilaComplexNode(node_config=_make_config())
    assert _handler(node, "join_words")(None, ["a", "b"]) == "a b"


def test_handler_serializes_tuple_result() -> None:
    """Tuple results containing models are returned as JSON."""
    node = SilaComplexNode(node_config=_make_config())
    result = _handler(node, "pair")(None, 2.0)
    assert json.loads(result) == [{"label": "pair", "value": 2.0}, 1]


def test_handler_without_return_annotation() -> None:
    """Actions without a return annotation run and return nothing."""
    node = SilaComplexNode(node_config=_make_config())
    assert _handler(node, "untyped_return")(None, 3) is None
    assert node.last_count == 3


# --- Starting in SiLA mode ---------------------------------------------------


def test_start_node_in_sila_mode_runs_grpc_server(sila_node: SilaTestNode) -> None:
    """In SiLA mode, start_node serves gRPC on the node URL instead of REST."""
    sila_node.config.sila_mode = True
    sila_node.config.node_url = "http://127.0.0.1:4321"
    sila_node.server = MagicMock()

    with (
        patch("madsci.node_module.abstract_node_module.AbstractNode.start_node"),
        patch("uvicorn.run") as uvicorn_run,
    ):
        sila_node.start_node()

    sila_node.server.start_insecure.assert_called_once_with("127.0.0.1", 4321)
    sila_node.server.grpc_server.wait_for_termination.assert_called_once()
    sila_node.server.stop.assert_called_once()
    uvicorn_run.assert_not_called()
    assert sila_node.rest_api is None


def test_start_node_without_sila_mode_runs_rest(sila_node: SilaTestNode) -> None:
    """Without SiLA mode, start_node runs the REST API and not the gRPC server."""
    sila_node.server = MagicMock()

    with patch("uvicorn.run") as uvicorn_run:
        sila_node.start_node()

    uvicorn_run.assert_called_once()
    sila_node.server.start_insecure.assert_not_called()


# --- End-to-end over gRPC ----------------------------------------------------


@pytest.fixture
def sila_client(sila_node: SilaTestNode):
    """A SiLA client connected to the test node's running SiLA server."""
    port = _free_port()
    sila_node.server.start_insecure("127.0.0.1", port, enable_discovery=False)
    client = SilaClient("127.0.0.1", port, insecure=True)
    try:
        yield getattr(client, "MADSCI" + sila_node.node_info.node_id)
    finally:
        sila_node.server.stop()


def test_sila_client_reads_state(sila_node: SilaTestNode, sila_client) -> None:
    """The node state is readable over SiLA as JSON."""
    sila_node.node_state = {"status_code": 7}
    assert json.loads(sila_client.MADSCIGetState.get()) == {"status_code": 7}


def test_sila_client_runs_basic_action(sila_client) -> None:
    """Actions can be invoked over SiLA."""
    assert sila_client.MADSCIaddnumbers(4, 5).RESULT == 9


def test_sila_client_sends_file(sila_client) -> None:
    """Binary parameters arrive at the action as files."""
    result = sila_client.MADSCIreadfile(b"over the wire").RESULT
    assert json.loads(result) == {"content": "over the wire"}


def test_sila_client_receives_file(sila_client) -> None:
    """File results are returned as Binary."""
    assert sila_client.MADSCImakefile(8).RESULT == b"count=8"


def test_sila_client_sends_list() -> None:
    """List parameters can be sent over SiLA."""
    node = SilaComplexNode(node_config=_make_config())
    port = _free_port()
    node.server.start_insecure("127.0.0.1", port, enable_discovery=False)
    try:
        client = SilaClient("127.0.0.1", port, insecure=True)
        feature = getattr(client, "MADSCI" + node.node_info.node_id)
        assert feature.MADSCIjoinwords(["x", "y"]).RESULT == "x y"
    finally:
        node.server.stop()


def test_sila_client_runs_action_without_result(
    sila_node: SilaTestNode,
    sila_client,
) -> None:
    """Actions without results can be invoked over SiLA."""
    sila_client.MADSCInoresult(11)
    assert sila_node.last_count == 11
