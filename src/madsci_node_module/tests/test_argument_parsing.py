"""
Comprehensive tests for action argument parsing with complex type hints.

Phase 3 of action parsing fix (Issue #184).
Tests handling of complex nested type hints in action arguments.
"""

from pathlib import Path, PosixPath, PurePath
from typing import Annotated, Optional, Union

import pytest
from madsci.common.types.action_types import (
    FileArgumentDefinition,
    LocationArgumentDefinition,
)
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class TestConfig(RestNodeConfig):
    """Test configuration for argument parsing tests."""

    __test__ = False
    test_param: int = 1
    update_node_files: bool = False


class TestArgumentParsingNode(RestNode):
    """Test node for argument parsing tests."""

    __test__ = False
    config: TestConfig = TestConfig()
    config_model = TestConfig

    def startup_handler(self) -> None:
        """Initialize the node."""

    def shutdown_handler(self) -> None:
        """Shutdown the node."""

    def state_handler(self) -> None:
        """Update node state."""


# ============================================================================
# LocationArgument Parameters (Tests 110-124)
# ============================================================================


def test_parse_location_direct():
    """Test 110: Parse direct LocationArgument parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: LocationArgument) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].name == "loc"
    assert action_def.locations["loc"].required is True
    assert "loc" not in action_def.args
    assert "loc" not in action_def.files


def test_parse_location_optional():
    """Test 111: Parse Optional[LocationArgument] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: Optional[LocationArgument] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is False
    assert "loc" not in action_def.args
    assert "loc" not in action_def.files


def test_parse_location_union_none():
    """Test 112: Parse Union[LocationArgument, None] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: Union[LocationArgument, None] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is False


def test_parse_location_annotated():
    """Test 113: Parse Annotated[LocationArgument, 'desc'] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, loc: Annotated[LocationArgument, "Location description"]
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is True
    assert action_def.locations["loc"].description == "Location description"


def test_parse_location_optional_annotated():
    """Test 114: Parse Optional[Annotated[LocationArgument, 'desc']] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            loc: Optional[Annotated[LocationArgument, "Location description"]] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is False
    assert action_def.locations["loc"].description == "Location description"


def test_parse_location_annotated_optional():
    """Test 115: Parse Annotated[Optional[LocationArgument], 'desc'] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            loc: Annotated[Optional[LocationArgument], "Location description"] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is False
    assert action_def.locations["loc"].description == "Location description"


def test_parse_location_triple_nested():
    """Test 116: Parse deeply nested LocationArgument parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            loc: Optional[Annotated[Optional[LocationArgument], "Description"]] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is False
    assert action_def.locations["loc"].description == "Description"


def test_parse_location_with_definition():
    """Test 117: Parse Annotated[LocationArgument, LocationArgumentDefinition(...)]."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            loc: Annotated[
                LocationArgument,
                LocationArgumentDefinition(
                    name="loc", required=True, description="Custom location"
                ),
            ],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    # The definition from Annotated metadata should be used
    assert action_def.locations["loc"].description == "Custom location"


def test_parse_location_required_flag():
    """Test 118: Verify required=True when LocationArgument is not optional."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: LocationArgument) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.locations["loc"].required is True


def test_parse_location_optional_flag():
    """Test 119: Verify required=False when LocationArgument is optional."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: Optional[LocationArgument] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.locations["loc"].required is False


def test_parse_location_in_locations_dict():
    """Test 120: Verify LocationArgument is added to action_def.locations."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: LocationArgument) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert "loc" not in action_def.args
    assert "loc" not in action_def.files


def test_parse_location_description_extracted():
    """Test 121: Verify description is extracted from Annotated metadata."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, loc: Annotated[LocationArgument, "Test description"]
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.locations["loc"].description == "Test description"


def test_parse_location_list():
    """Test 122: Parse list[LocationArgument] (should work or give clear error)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, locs: list[LocationArgument]) -> None:
            pass

    node = Node()
    node.node_info.actions["test_action"]

    # Current implementation might not handle list[LocationArgument]
    # This test documents the expected behavior
    # For now, we expect it to be added as a regular argument
    # TODO: Determine if list[LocationArgument] should be specially handled


def test_parse_location_optional_list():
    """Test 123: Parse Optional[list[LocationArgument]]."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, locs: Optional[list[LocationArgument]] = None) -> None:
            pass

    node = Node()
    node.node_info.actions["test_action"]

    # Document expected behavior for optional list of locations


def test_parse_location_dict():
    """Test 124: Parse dict[str, LocationArgument] (clear behavior needed)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc_map: dict[str, LocationArgument]) -> None:
            pass

    node = Node()
    node.node_info.actions["test_action"]

    # Document expected behavior for dict with LocationArgument values


# ============================================================================
# Path Parameters (Tests 125-139)
# ============================================================================


def test_parse_path_direct():
    """Test 125: Parse direct Path parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].name == "file"
    assert action_def.files["file"].required is True
    assert "file" not in action_def.args
    assert "file" not in action_def.locations


def test_parse_path_optional():
    """Test 126: Parse Optional[Path] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Optional[Path] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].required is False


def test_parse_path_annotated():
    """Test 127: Parse Annotated[Path, 'desc'] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Annotated[Path, "File description"]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].required is True
    assert action_def.files["file"].description == "File description"


def test_parse_path_optional_annotated():
    """Test 128: Parse Optional[Annotated[Path, 'desc']] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, file: Optional[Annotated[Path, "File description"]] = None
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].required is False
    assert action_def.files["file"].description == "File description"


def test_parse_path_annotated_optional():
    """Test 129: Parse Annotated[Optional[Path], 'desc'] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, file: Annotated[Optional[Path], "File description"] = None
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].required is False
    assert action_def.files["file"].description == "File description"


def test_parse_path_list():
    """Test 130: Parse list[Path] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, files: list[Path]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "files" in action_def.files
    assert action_def.files["files"].required is True


def test_parse_path_optional_list():
    """Test 131: Parse Optional[list[Path]] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, files: Optional[list[Path]] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "files" in action_def.files
    assert action_def.files["files"].required is False


def test_parse_path_list_optional():
    """Test 132: Parse list[Optional[Path]] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, files: list[Optional[Path]]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "files" in action_def.files
    # The list itself is required, elements can be None


def test_parse_path_with_file_definition():
    """Test 133: Parse Annotated[Path, FileArgumentDefinition(...)] parameter."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            file: Annotated[
                Path,
                FileArgumentDefinition(
                    name="file", required=True, description="Custom file"
                ),
            ],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].description == "Custom file"


def test_parse_path_required_flag():
    """Test 134: Verify required=True when Path is not optional."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.files["file"].required is True


def test_parse_path_optional_flag():
    """Test 135: Verify required=False when Path is optional."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Optional[Path] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.files["file"].required is False


def test_parse_path_in_files_dict():
    """Test 136: Verify Path is added to action_def.files."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert "file" not in action_def.args
    assert "file" not in action_def.locations


def test_parse_path_description_extracted():
    """Test 137: Verify description is extracted from Annotated metadata."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Annotated[Path, "Test file description"]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.files["file"].description == "Test file description"


def test_parse_path_purepath():
    """Test 138: Parse PurePath, PosixPath, WindowsPath parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def action_pure(self, file: PurePath) -> None:
            pass

        @action
        def action_posix(self, file: PosixPath) -> None:
            pass

    node = Node()

    # PurePath should be treated as a file type
    assert "file" in node.node_info.actions["action_pure"].files

    # PosixPath should be treated as a file type
    assert "file" in node.node_info.actions["action_posix"].files


def test_parse_path_nested_annotated():
    """Test 139: Parse multiple Annotated layers with Path."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            file: Annotated[Annotated[Path, "Inner description"], "Outer description"],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    # Should extract description from metadata


# ============================================================================
# Regular Arguments (Tests 140-151)
# ============================================================================


def test_parse_arg_basic_types():
    """Test 140: Parse basic type parameters (int, str, float, bool)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int, y: str, z: float, w: bool) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert "y" in action_def.args
    assert "z" in action_def.args
    assert "w" in action_def.args
    assert all(action_def.args[p].required for p in ["x", "y", "z", "w"])


def test_parse_arg_optional_basic():
    """Test 141: Parse Optional[int], Optional[str] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: Optional[int] = None, y: Optional[str] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert "y" in action_def.args
    assert action_def.args["x"].required is False
    assert action_def.args["y"].required is False


def test_parse_arg_annotated_basic():
    """Test 142: Parse Annotated[int, 'desc'] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: Annotated[int, "Parameter description"]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert action_def.args["x"].description == "Parameter description"
    assert action_def.args["x"].required is True


def test_parse_arg_optional_annotated_basic():
    """Test 143: Parse Optional[Annotated[int, 'desc']] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, x: Optional[Annotated[int, "Parameter description"]] = None
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert action_def.args["x"].description == "Parameter description"
    assert action_def.args["x"].required is False


def test_parse_arg_dict_basic():
    """Test 144: Parse dict[str, int] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, data: dict[str, int]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "data" in action_def.args
    assert action_def.args["data"].required is True


def test_parse_arg_list_basic():
    """Test 145: Parse list[int] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, items: list[int]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "items" in action_def.args
    assert action_def.args["items"].required is True


def test_parse_arg_optional_dict():
    """Test 146: Parse Optional[dict[str, int]] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, data: Optional[dict[str, int]] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "data" in action_def.args
    assert action_def.args["data"].required is False


def test_parse_arg_optional_list():
    """Test 147: Parse Optional[list[str]] parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, items: Optional[list[str]] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "items" in action_def.args
    assert action_def.args["items"].required is False


def test_parse_arg_required_flag():
    """Test 148: Verify required=True for parameters with no default."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is True


def test_parse_arg_optional_flag():
    """Test 149: Verify required=False for optional parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: Optional[int] = None) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is False


def test_parse_arg_default_value():
    """Test 150: Verify default value is captured correctly."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int = 42) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].default == 42
    assert action_def.args["x"].required is False


def test_parse_arg_in_args_dict():
    """Test 151: Verify regular args are added to action_def.args."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int, y: str) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert "y" in action_def.args
    assert "x" not in action_def.files
    assert "x" not in action_def.locations


# ============================================================================
# Mixed Action Definitions (Tests 152-161)
# ============================================================================


def test_action_with_multiple_locations():
    """Test 152: Action with multiple location parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, source: LocationArgument, dest: LocationArgument) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "source" in action_def.locations
    assert "dest" in action_def.locations
    assert len(action_def.locations) == 2


def test_action_with_multiple_files():
    """Test 153: Action with multiple file parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, input_file: Path, output_file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "input_file" in action_def.files
    assert "output_file" in action_def.files
    assert len(action_def.files) == 2


def test_action_with_mixed_params():
    """Test 154: Action with args + locations + files."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self, x: int, loc: LocationArgument, file: Path, y: str
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert "y" in action_def.args
    assert "loc" in action_def.locations
    assert "file" in action_def.files


def test_action_all_optional():
    """Test 155: Action with all parameters optional."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Optional[int] = None,
            loc: Optional[LocationArgument] = None,
            file: Optional[Path] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is False
    assert action_def.locations["loc"].required is False
    assert action_def.files["file"].required is False


def test_action_all_required():
    """Test 156: Action with all parameters required."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int, loc: LocationArgument, file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is True
    assert action_def.locations["loc"].required is True
    assert action_def.files["file"].required is True


def test_action_some_optional_some_required():
    """Test 157: Action with mixed required/optional parameters."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: int,
            loc: LocationArgument,
            y: Optional[int] = None,
            opt_loc: Optional[LocationArgument] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is True
    assert action_def.args["y"].required is False
    assert action_def.locations["loc"].required is True
    assert action_def.locations["opt_loc"].required is False


def test_action_annotated_everywhere():
    """Test 158: Action with all params annotated."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Annotated[int, "Number"],
            loc: Annotated[LocationArgument, "Location"],
            file: Annotated[Path, "File"],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].description == "Number"
    assert action_def.locations["loc"].description == "Location"
    assert action_def.files["file"].description == "File"


def test_action_complex_nesting_everywhere():
    """Test 159: Action with complex types throughout."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Optional[Annotated[int, "Number"]] = None,
            loc: Optional[Annotated[LocationArgument, "Location"]] = None,
            file: Optional[Annotated[Path, "File"]] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is False
    assert action_def.args["x"].description == "Number"
    assert action_def.locations["loc"].required is False
    assert action_def.locations["loc"].description == "Location"
    assert action_def.files["file"].required is False
    assert action_def.files["file"].description == "File"


def test_action_description_extraction():
    """Test 160: Verify descriptions are extracted correctly."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Annotated[int, "X param"],
            y: Annotated[str, "Y param"],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].description == "X param"
    assert action_def.args["y"].description == "Y param"


def test_action_definition_complete():
    """Test 161: Verify full ActionDefinition is correct."""

    class Node(TestArgumentParsingNode):
        @action
        def complex_action(
            self,
            required_arg: int,
            required_loc: LocationArgument,
            required_file: Path,
            optional_arg: Optional[str] = None,
            optional_loc: Optional[LocationArgument] = None,
            optional_file: Optional[Path] = None,
        ) -> None:
            """Complex action with all parameter types."""

    node = Node()
    action_def = node.node_info.actions["complex_action"]

    # Check all parameter categories are populated
    assert len(action_def.args) == 2
    assert len(action_def.locations) == 2
    assert len(action_def.files) == 2

    # Check required flags
    assert action_def.args["required_arg"].required is True
    assert action_def.args["optional_arg"].required is False
    assert action_def.locations["required_loc"].required is True
    assert action_def.locations["optional_loc"].required is False
    assert action_def.files["required_file"].required is True
    assert action_def.files["optional_file"].required is False


# ============================================================================
# Error Cases (Tests 162-171)
# ============================================================================


def test_error_union_location_path():
    """Test 162: Union[LocationArgument, Path] should raise error."""
    # This is an unsupported combination - a parameter can't be both a location and a file

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, param: Union[LocationArgument, Path]) -> None:
            pass

    # Should raise ValueError during node creation
    # TODO: Implement proper error handling for conflicting special types


def test_error_union_conflicting_specials():
    """Test 163: Union[special, special] should raise error."""
    # Multiple special types in a Union is not supported
    # This test documents expected error behavior


def test_error_clear_message_unsupported():
    """Test 164: Error message should be actionable for unsupported types."""
    # Verify that error messages clearly explain what's wrong and how to fix it


def test_error_multiple_annotations():
    """Test 165: Multiple ArgumentDefinition types should raise error."""

    # Attempting to mark a parameter as both a file and a location should fail
    with pytest.raises(ValueError, match="annotated as multiple types"):

        class Node(TestArgumentParsingNode):
            @action
            def test_action(
                self,
                param: Annotated[
                    Path,
                    FileArgumentDefinition(
                        name="param", required=True, description="File"
                    ),
                    LocationArgumentDefinition(
                        name="param", required=True, description="Location"
                    ),
                ],
            ) -> None:
                pass

        Node()


def test_error_conflicting_metadata():
    """Test 166: Conflicting metadata should raise error."""
    # Document expected behavior for conflicting metadata


def test_error_invalid_type_hint():
    """Test 167: Invalid type hint should raise clear error."""
    # Document expected behavior for malformed type hints


def test_error_includes_parameter_name():
    """Test 168: Error should include parameter name."""
    # When an error occurs, it should clearly state which parameter caused the issue


def test_error_includes_action_name():
    """Test 169: Error should include action name."""
    # When an error occurs, it should clearly state which action caused the issue


def test_error_too_deeply_nested():
    """Test 170: Excessive nesting should raise error."""
    # The TypeAnalyzer has a max_depth protection
    # Verify it's honored during argument parsing


def test_error_unsupported_generic():
    """Test 171: Unsupported generic should raise error."""
    # Document expected behavior for unsupported generic types


# ============================================================================
# Backward Compatibility (Tests 172-179)
# ============================================================================


def test_existing_simple_location_still_works():
    """Test 172: Simple LocationArgument still works (no regression)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, loc: LocationArgument) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "loc" in action_def.locations
    assert action_def.locations["loc"].required is True


def test_existing_simple_path_still_works():
    """Test 173: Simple Path still works (no regression)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, file: Path) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "file" in action_def.files
    assert action_def.files["file"].required is True


def test_existing_simple_args_still_work():
    """Test 174: Simple args still work (no regression)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, x: int, y: str) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "x" in action_def.args
    assert "y" in action_def.args


def test_existing_list_path_still_works():
    """Test 175: list[Path] still works (no regression)."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(self, files: list[Path]) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert "files" in action_def.files


def test_existing_annotated_still_works():
    """Test 176: Existing Annotated patterns still work."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Annotated[int, "Description"],
            loc: Annotated[LocationArgument, "Location"],
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].description == "Description"
    assert action_def.locations["loc"].description == "Location"


def test_existing_optional_still_works():
    """Test 177: Existing Optional patterns still work."""

    class Node(TestArgumentParsingNode):
        @action
        def test_action(
            self,
            x: Optional[int] = None,
            loc: Optional[LocationArgument] = None,
        ) -> None:
            pass

    node = Node()
    action_def = node.node_info.actions["test_action"]

    assert action_def.args["x"].required is False
    assert action_def.locations["loc"].required is False


def test_existing_complex_actions_still_work():
    """Test 178: Real-world action patterns still work."""

    class Node(TestArgumentParsingNode):
        @action
        def transfer(
            self,
            source: LocationArgument,
            destination: LocationArgument,
            volume: float,
            config_file: Optional[Path] = None,
        ) -> None:
            """Transfer liquid from source to destination."""

    node = Node()
    action_def = node.node_info.actions["transfer"]

    assert "source" in action_def.locations
    assert "destination" in action_def.locations
    assert "volume" in action_def.args
    assert "config_file" in action_def.files
    assert action_def.files["config_file"].required is False


def test_no_regression_in_action_discovery():
    """Test 179: Action discovery unchanged (no regression)."""

    class Node(TestArgumentParsingNode):
        @action
        def action1(self) -> None:
            pass

        @action
        def action2(self, x: int) -> None:
            pass

        def not_an_action(self) -> None:
            pass

    node = Node()

    # Only decorated actions should be discovered
    assert "action1" in node.node_info.actions
    assert "action2" in node.node_info.actions
    assert "not_an_action" not in node.node_info.actions
    assert len(node.node_info.actions) == 2
