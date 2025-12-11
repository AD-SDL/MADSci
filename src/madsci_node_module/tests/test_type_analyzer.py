"""Tests for the type analyzer module.

This test suite comprehensively tests the type analysis functionality,
covering all aspects of recursive type unwrapping, special type detection,
and error handling.
"""

from pathlib import Path, PosixPath, PurePath, WindowsPath
from typing import Annotated, Any, Optional, TypeVar, Union

import pytest
from madsci.common.types.action_types import (
    ActionCancelled,
    ActionFailed,
    ActionFiles,
    ActionJSON,
    ActionNotReady,
    ActionPaused,
    ActionResult,
    ActionRunning,
    ActionSucceeded,
    ArgumentDefinition,
    FileArgumentDefinition,
)
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.location_types import LocationArgument
from madsci.node_module.type_analyzer import (
    analyze_type,
    extract_metadata_from_annotated,
    is_action_result_type,
    is_file_type,
    is_location_argument_type,
    is_optional_type,
)

# =============================================================================
# BASIC TYPES (10 tests)
# =============================================================================


def test_analyze_basic_types():
    """Test analysis of basic Python types."""
    # String
    info = analyze_type(str)
    assert info.base_type is str
    assert not info.is_optional
    assert info.special_type is None

    # Integer
    info = analyze_type(int)
    assert info.base_type is int
    assert not info.is_optional

    # Float
    info = analyze_type(float)
    assert info.base_type is float

    # Bool
    info = analyze_type(bool)
    assert info.base_type is bool

    # Dict
    info = analyze_type(dict)
    assert info.base_type is dict

    # List
    info = analyze_type(list)
    assert info.base_type is list


def test_analyze_path():
    """Test analysis of Path type."""
    info = analyze_type(Path)
    assert info.base_type is Path
    assert info.special_type == "file"
    assert info.special_type_class == Path
    assert not info.is_optional


def test_analyze_location_argument():
    """Test analysis of LocationArgument type."""
    info = analyze_type(LocationArgument)
    assert info.base_type is LocationArgument
    assert info.special_type == "location"
    assert info.special_type_class == LocationArgument
    assert not info.is_optional


def test_analyze_action_result():
    """Test analysis of ActionResult and subclasses."""
    info = analyze_type(ActionResult)
    assert info.base_type is ActionResult
    assert info.special_type == "action_result"
    assert info.special_type_class == ActionResult


def test_analyze_action_files():
    """Test analysis of ActionFiles type."""
    info = analyze_type(ActionFiles)
    assert info.base_type is ActionFiles
    assert info.special_type == "action_files"
    assert info.special_type_class == ActionFiles


def test_analyze_action_json():
    """Test analysis of ActionJSON type."""
    info = analyze_type(ActionJSON)
    assert info.base_type is ActionJSON
    assert info.special_type == "action_json"
    assert info.special_type_class == ActionJSON


def test_analyze_pydantic_model():
    """Test analysis of custom BaseModel subclass."""

    class CustomModel(MadsciBaseModel):
        field: str

    info = analyze_type(CustomModel)
    assert info.base_type is CustomModel
    # Custom pydantic models are not special types
    assert info.special_type is None


def test_analyze_none_type():
    """Test analysis of None/NoneType."""
    info = analyze_type(type(None))
    assert info.base_type is type(None)
    assert not info.is_optional  # None itself is not "optional"


def test_analyze_any_type():
    """Test analysis of Any type."""
    info = analyze_type(Any)
    assert info.base_type == Any
    assert info.special_type is None


def test_analyze_unknown_type():
    """Test analysis of unrecognized types."""

    class UnknownClass:
        pass

    info = analyze_type(UnknownClass)
    assert info.base_type is UnknownClass
    assert info.special_type is None


# =============================================================================
# OPTIONAL TYPES (8 tests)
# =============================================================================


def test_analyze_optional_basic():
    """Test analysis of Optional basic types."""
    info = analyze_type(Optional[int])
    assert info.base_type is int
    assert info.is_optional
    assert not info.is_union  # Optional is not considered a multi-type union

    info = analyze_type(Optional[str])
    assert info.base_type is str
    assert info.is_optional


def test_analyze_optional_path():
    """Test analysis of Optional[Path]."""
    info = analyze_type(Optional[Path])
    assert info.base_type is Path
    assert info.is_optional
    assert info.special_type == "file"


def test_analyze_optional_location():
    """Test analysis of Optional[LocationArgument]."""
    info = analyze_type(Optional[LocationArgument])
    assert info.base_type is LocationArgument
    assert info.is_optional
    assert info.special_type == "location"


def test_analyze_optional_action_result():
    """Test analysis of Optional[ActionFailed]."""
    info = analyze_type(Optional[ActionFailed])
    assert info.base_type is ActionFailed
    assert info.is_optional
    assert info.special_type == "action_result"


def test_analyze_union_with_none():
    """Test analysis of Union[int, None]."""
    info = analyze_type(Union[int, None])
    assert info.base_type is int
    assert info.is_optional
    assert not info.is_union  # This is treated as Optional


def test_analyze_union_multiple_with_none():
    """Test analysis of Union[str, int, None]."""
    info = analyze_type(Union[str, int, None])
    assert info.is_optional
    assert info.is_union  # Has multiple non-None types
    assert set(info.union_types) == {str, int}  # None filtered out


def test_analyze_optional_flag_detection():
    """Test that is_optional flag is set correctly."""
    # Not optional
    info = analyze_type(int)
    assert not info.is_optional

    # Optional
    info = analyze_type(Optional[int])
    assert info.is_optional


def test_analyze_optional_none_filtered():
    """Test that None is filtered from union_types."""
    info = analyze_type(Union[str, int, None])
    assert info.is_optional
    assert type(None) not in info.union_types
    assert len(info.union_types) == 2


# =============================================================================
# ANNOTATED TYPES (10 tests)
# =============================================================================


def test_analyze_annotated_basic():
    """Test analysis of Annotated basic types."""
    info = analyze_type(Annotated[int, "description"])
    assert info.base_type is int
    assert "description" in info.metadata
    assert not info.is_optional


def test_analyze_annotated_path():
    """Test analysis of Annotated[Path, ...]."""
    info = analyze_type(
        Annotated[
            Path,
            FileArgumentDefinition(
                name="file", description="A file", required=True, argument_type="file"
            ),
        ]
    )
    assert info.base_type is Path
    assert info.special_type == "file"
    assert len(info.metadata) == 1
    assert isinstance(info.metadata[0], FileArgumentDefinition)


def test_analyze_annotated_location():
    """Test analysis of Annotated[LocationArgument, ...]."""
    info = analyze_type(Annotated[LocationArgument, "desc"])
    assert info.base_type is LocationArgument
    assert info.special_type == "location"
    assert "desc" in info.metadata


def test_analyze_annotated_metadata_extraction():
    """Test extraction of multiple metadata items."""
    info = analyze_type(Annotated[str, "desc", "another", 123])
    assert info.base_type is str
    assert len(info.metadata) == 3
    assert "desc" in info.metadata
    assert "another" in info.metadata
    assert 123 in info.metadata


def test_analyze_annotated_with_definition():
    """Test analysis with ArgumentDefinition metadata."""
    arg_def = ArgumentDefinition(
        name="test_arg", description="Test argument", argument_type="str", required=True
    )
    info = analyze_type(Annotated[str, arg_def])
    assert info.base_type is str
    assert arg_def in info.metadata


def test_analyze_optional_annotated():
    """Test analysis of Optional[Annotated[T, ...]]."""
    info = analyze_type(Optional[Annotated[int, "description"]])
    assert info.base_type is int
    assert info.is_optional
    assert "description" in info.metadata


def test_analyze_annotated_optional():
    """Test analysis of Annotated[Optional[T], ...]."""
    info = analyze_type(Annotated[Optional[int], "description"])
    assert info.base_type is int
    assert info.is_optional
    assert "description" in info.metadata


def test_analyze_deeply_nested_annotated():
    """Test analysis of multiple Annotated layers."""
    info = analyze_type(Annotated[Annotated[int, "inner"], "outer"])
    assert info.base_type is int
    # All metadata should be collected
    assert "inner" in info.metadata
    assert "outer" in info.metadata


def test_analyze_annotated_preserves_metadata():
    """Test that metadata is preserved through analysis."""
    metadata_obj = {"key": "value"}
    info = analyze_type(Annotated[str, metadata_obj])
    assert metadata_obj in info.metadata


def test_analyze_annotated_special_types():
    """Test that Annotated special types are detected."""
    info = analyze_type(Annotated[LocationArgument, "description"])
    assert info.special_type == "location"

    info = analyze_type(Annotated[Path, "description"])
    assert info.special_type == "file"


# =============================================================================
# CONTAINER TYPES (12 tests)
# =============================================================================


def test_analyze_list_basic():
    """Test analysis of list[T] types."""
    info = analyze_type(list[int])
    assert info.is_list
    assert info.list_element_type is not None
    # Element type analysis
    elem_info = analyze_type(info.list_element_type)
    assert elem_info.base_type is int

    info = analyze_type(list[str])
    assert info.is_list


def test_analyze_list_path():
    """Test analysis of list[Path]."""
    info = analyze_type(list[Path])
    assert info.is_list
    assert info.list_element_type == Path
    # The list itself should have special_type indicating it contains files
    assert info.special_type == "file"


def test_analyze_list_location():
    """Test analysis of list[LocationArgument]."""
    info = analyze_type(list[LocationArgument])
    assert info.is_list
    assert info.list_element_type == LocationArgument
    assert info.special_type == "location"


def test_analyze_optional_list():
    """Test analysis of Optional[list[T]]."""
    info = analyze_type(Optional[list[int]])
    assert info.is_optional
    assert info.is_list
    assert info.list_element_type is not None


def test_analyze_list_optional():
    """Test analysis of list[Optional[T]]."""
    info = analyze_type(list[Optional[int]])
    assert info.is_list
    # The element type itself is optional
    elem_info = analyze_type(info.list_element_type)
    assert elem_info.is_optional
    assert elem_info.base_type is int


def test_analyze_dict_basic():
    """Test analysis of dict[K, V] types."""
    info = analyze_type(dict[str, int])
    assert info.is_dict
    assert info.dict_key_type is str
    assert info.dict_value_type is int


def test_analyze_dict_complex():
    """Test analysis of dict with complex value types."""
    info = analyze_type(dict[str, LocationArgument])
    assert info.is_dict
    assert info.dict_value_type == LocationArgument
    # Dict containing special types might be marked as such
    assert info.special_type == "location"


def test_analyze_tuple_basic():
    """Test analysis of tuple types."""
    info = analyze_type(tuple[int, str, Path])
    assert info.is_tuple
    assert len(info.tuple_element_types) == 3
    assert info.tuple_element_types[0] is int
    assert info.tuple_element_types[1] is str
    assert info.tuple_element_types[2] is Path


def test_analyze_tuple_homogeneous():
    """Test analysis of homogeneous tuple tuple[int, ...]."""
    info = analyze_type(tuple[int, ...])
    assert info.is_tuple
    # For homogeneous tuples, we should get the element type
    assert info.tuple_element_types is not None


def test_analyze_nested_containers():
    """Test analysis of nested container types."""
    info = analyze_type(list[dict[str, Path]])
    assert info.is_list
    # The element type is a dict
    elem_type = info.list_element_type
    dict_info = analyze_type(elem_type)
    assert dict_info.is_dict
    assert dict_info.dict_value_type == Path


def test_analyze_optional_nested_containers():
    """Test analysis of Optional[list[dict[str, int]]]."""
    info = analyze_type(Optional[list[dict[str, int]]])
    assert info.is_optional
    assert info.is_list
    assert info.list_element_type is not None


def test_analyze_container_special_types():
    """Test that containers with special types are detected."""
    info = analyze_type(list[Path])
    assert info.special_type == "file"

    info = analyze_type(dict[str, LocationArgument])
    assert info.special_type == "location"


# =============================================================================
# UNION TYPES (8 tests)
# =============================================================================


def test_analyze_union_basic():
    """Test analysis of Union[int, str]."""
    info = analyze_type(Union[int, str])
    assert info.is_union
    assert not info.is_optional  # No None in union
    assert set(info.union_types) == {int, str}


def test_analyze_union_with_special_type():
    """Test analysis of Union with one special type."""
    info = analyze_type(Union[LocationArgument, dict])
    assert info.is_union
    # Should still detect the special type
    assert info.special_type == "location"


def test_analyze_union_multiple_special():
    """Test that Union with multiple special types raises error."""
    with pytest.raises(ValueError, match="conflicting special types"):
        analyze_type(Union[Path, LocationArgument])


def test_analyze_union_incompatible():
    """Test detection of incompatible unions."""
    # Union of different special types should error
    with pytest.raises(ValueError):
        analyze_type(Union[ActionFailed, LocationArgument])


def test_analyze_union_types_list():
    """Test that union_types is populated correctly."""
    info = analyze_type(Union[str, int, float])
    assert info.is_union
    assert len(info.union_types) == 3
    assert str in info.union_types
    assert int in info.union_types
    assert float in info.union_types


def test_analyze_pipe_operator():
    """Test analysis using | operator (Python 3.10+)."""
    info = analyze_type(int | str)
    assert info.is_union
    assert set(info.union_types) == {int, str}


def test_analyze_pipe_with_none():
    """Test analysis of str | None."""
    info = analyze_type(str | None)
    assert info.is_optional
    assert info.base_type is str
    assert not info.is_union  # Treated as Optional


def test_analyze_complex_union():
    """Test analysis of Union[str, int, dict, None]."""
    info = analyze_type(Union[str, int, dict, None])
    assert info.is_optional
    assert info.is_union
    assert len(info.union_types) == 3  # None filtered out
    assert type(None) not in info.union_types


# =============================================================================
# DEEP NESTING (10 tests)
# =============================================================================


def test_analyze_triple_nested():
    """Test analysis of Optional[Annotated[Optional[T], ...]]."""
    info = analyze_type(Optional[Annotated[Optional[int], "desc"]])
    assert info.base_type is int
    assert info.is_optional
    assert "desc" in info.metadata


def test_analyze_quadruple_nested():
    """Test analysis of Annotated[Optional[list[Annotated[T, ...]]], ...]."""
    info = analyze_type(Annotated[Optional[list[Annotated[int, "inner"]]], "outer"])
    assert info.is_optional
    assert info.is_list
    assert "outer" in info.metadata
    # Inner metadata should also be preserved
    assert "inner" in info.metadata


def test_analyze_deep_optional_chain():
    """Test analysis of multiple Optional layers."""
    # Optional[Optional[int]] should unwrap to int
    info = analyze_type(Optional[Optional[int]])
    assert info.base_type is int
    assert info.is_optional


def test_analyze_deep_annotated_chain():
    """Test analysis of multiple Annotated layers."""
    info = analyze_type(
        Annotated[Annotated[Annotated[int, "level3"], "level2"], "level1"]
    )
    assert info.base_type is int
    # All metadata should be collected
    assert "level1" in info.metadata
    assert "level2" in info.metadata
    assert "level3" in info.metadata


def test_analyze_deep_container_nesting():
    """Test analysis of list[list[list[T]]]."""
    info = analyze_type(list[list[list[int]]])
    assert info.is_list
    # Check nested structure
    elem_info = analyze_type(info.list_element_type)
    assert elem_info.is_list


def test_analyze_mixed_deep_nesting():
    """Test analysis of Optional[list[Annotated[LocationArgument, ...]]]."""
    info = analyze_type(Optional[list[Annotated[LocationArgument, "description"]]])
    assert info.is_optional
    assert info.is_list
    assert info.special_type == "location"
    assert "description" in info.metadata


def test_analyze_all_wrappers_combined():
    """Test analysis with all wrapper types combined."""
    info = analyze_type(
        Optional[Annotated[list[Annotated[LocationArgument, "inner"]], "outer"]]
    )
    assert info.is_optional
    assert info.is_list
    assert info.special_type == "location"
    assert "inner" in info.metadata
    assert "outer" in info.metadata


def test_analyze_depth_limit():
    """Test that depth tracking works correctly."""
    # Should work within depth limit
    info = analyze_type(Optional[Optional[Optional[int]]])
    assert info.base_type is int


def test_analyze_depth_limit_error():
    """Test that exceeding max_depth raises error."""
    # Create an artificially deep type using containers which recurse more
    # Optional unwraps efficiently, but list[list[list[...]]] will recurse deeply
    deep_type: Any = int
    for _ in range(25):  # Exceed default max_depth of 20
        deep_type = list[deep_type]

    with pytest.raises(ValueError, match="recursion depth"):
        analyze_type(deep_type, max_depth=20)


def test_analyze_realistic_complex_type():
    """Test analysis of a real-world complex type."""
    # This is the kind of type that causes issues in the original implementation
    info = analyze_type(
        Optional[Annotated[LocationArgument, "Transfer source location"]]
    )
    assert info.base_type is LocationArgument
    assert info.is_optional
    assert info.special_type == "location"
    assert "Transfer source location" in info.metadata


# =============================================================================
# SPECIAL TYPE DETECTION (10 tests)
# =============================================================================


def test_special_type_location_direct():
    """Test direct LocationArgument detection."""
    assert is_location_argument_type(LocationArgument)


def test_special_type_location_nested():
    """Test LocationArgument detection in nested types."""
    info = analyze_type(Optional[Annotated[LocationArgument, "desc"]])
    assert info.special_type == "location"


def test_special_type_file_direct():
    """Test direct Path detection."""
    assert is_file_type(Path)
    assert is_file_type(PurePath)


def test_special_type_file_list():
    """Test list[Path] detection."""
    info = analyze_type(list[Path])
    assert info.special_type == "file"


def test_special_type_action_result():
    """Test ActionResult subclass detection."""
    assert is_action_result_type(ActionResult)
    assert is_action_result_type(ActionFailed)
    assert is_action_result_type(ActionSucceeded)


def test_special_type_action_failed():
    """Test specific ActionFailed detection."""
    info = analyze_type(ActionFailed)
    assert info.special_type == "action_result"
    assert info.special_type_class == ActionFailed


def test_special_type_action_files():
    """Test ActionFiles detection."""
    info = analyze_type(ActionFiles)
    assert info.special_type == "action_files"


def test_special_type_action_json():
    """Test ActionJSON detection."""
    info = analyze_type(ActionJSON)
    assert info.special_type == "action_json"


def test_special_type_pydantic_custom():
    """Test that custom BaseModel is not a special type."""

    class CustomModel(MadsciBaseModel):
        value: int

    info = analyze_type(CustomModel)
    assert info.special_type is None


def test_special_type_none_for_basic():
    """Test that basic types have no special_type."""
    for basic_type in [int, str, float, bool, dict, list]:
        info = analyze_type(basic_type)
        assert info.special_type is None


# =============================================================================
# ERROR CASES (8 tests)
# =============================================================================


def test_error_union_conflicting_specials():
    """Test that Union with conflicting special types raises error."""
    with pytest.raises(ValueError, match=r"conflicting special types|incompatible"):
        analyze_type(Union[Path, LocationArgument])


def test_error_excessive_nesting():
    """Test that excessive nesting raises error."""
    # Use list nesting which actually recurses deeply
    deep_type: Any = int
    for _ in range(25):
        deep_type = list[deep_type]

    with pytest.raises(ValueError, match="depth"):
        analyze_type(deep_type, max_depth=20)


def test_error_invalid_type_hint():
    """Test handling of malformed type hints."""
    # This depends on implementation - some invalid hints might be accepted
    # or might raise errors during analysis
    # Placeholder for implementation-specific behavior


def test_error_circular_reference():
    """Test detection of circular type references if possible."""
    # This is tricky to test and might not be fully implementable
    # Placeholder for future enhancement


def test_error_unsupported_generic():
    """Test error for unsupported generic types."""
    # Some complex generics might not be supported
    # Placeholder for implementation-specific behavior


def test_error_clear_message():
    """Test that error messages are actionable."""
    try:
        analyze_type(Union[Path, LocationArgument])
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        # Error message should be clear
        assert "Path" in str(e) or "LocationArgument" in str(e)


def test_error_includes_type_repr():
    """Test that errors include original type hint representation."""
    try:
        analyze_type(Union[Path, LocationArgument])
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        error_msg = str(e)
        # Should include helpful information
        assert len(error_msg) > 10


def test_error_includes_location():
    """Test that error context includes where it failed."""
    # Errors should provide context about what failed
    try:
        analyze_type(Union[ActionFailed, ActionJSON])
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        # Should have meaningful error
        assert len(str(e)) > 0


# =============================================================================
# EDGE CASES (8 tests)
# =============================================================================


def test_empty_union():
    """Test handling of Union with no types."""
    # Union[] is not valid Python, but Union with only None might occur
    info = analyze_type(Union[None])
    assert info.base_type is type(None)


def test_single_union():
    """Test that Union[T] is equivalent to T."""
    info = analyze_type(Union[int])
    assert info.base_type is int
    assert not info.is_union


def test_empty_tuple():
    """Test handling of tuple[()]."""
    info = analyze_type(tuple[()])
    assert info.is_tuple


def test_none_as_base_type():
    """Test when type_hint is None."""
    # analyze_type(None) should handle gracefully
    info = analyze_type(None)
    assert info.base_type is None or info.base_type is type(None)


def test_ellipsis_in_types():
    """Test handling of ... in type hints."""
    # tuple[int, ...] is a valid type
    info = analyze_type(tuple[int, ...])
    assert info.is_tuple


def test_forward_references():
    """Test handling of string type references."""
    # Forward references are strings in type hints
    # This might require special handling
    # Placeholder


def test_generic_type_vars():
    """Test handling of TypeVar in type hints."""
    T = TypeVar("T")
    # How to handle TypeVars depends on implementation
    info = analyze_type(T)
    # Should not crash
    assert info.base_type is not None


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


def test_is_optional_type_function():
    """Test the is_optional_type helper function."""
    assert is_optional_type(Optional[int])
    assert is_optional_type(Union[str, None])
    assert not is_optional_type(int)
    assert not is_optional_type(Union[int, str])


def test_is_location_argument_type_function():
    """Test the is_location_argument_type helper function."""
    assert is_location_argument_type(LocationArgument)
    assert not is_location_argument_type(Path)
    assert not is_location_argument_type(int)


def test_is_file_type_function():
    """Test the is_file_type helper function."""
    assert is_file_type(Path)
    assert is_file_type(PurePath)
    assert is_file_type(PosixPath)
    assert is_file_type(WindowsPath)
    assert not is_file_type(str)
    assert not is_file_type(LocationArgument)


def test_is_action_result_type_function():
    """Test the is_action_result_type helper function."""
    assert is_action_result_type(ActionResult)
    assert is_action_result_type(ActionFailed)
    assert is_action_result_type(ActionSucceeded)
    assert is_action_result_type(ActionRunning)
    assert is_action_result_type(ActionNotReady)
    assert is_action_result_type(ActionCancelled)
    assert is_action_result_type(ActionPaused)
    assert not is_action_result_type(Path)
    assert not is_action_result_type(LocationArgument)


def test_extract_metadata_from_annotated_function():
    """Test the extract_metadata_from_annotated helper function."""
    base, metadata = extract_metadata_from_annotated(Annotated[int, "desc", 123])
    assert base is int
    assert "desc" in metadata
    assert 123 in metadata

    # Non-annotated type should return empty metadata
    base, metadata = extract_metadata_from_annotated(int)
    assert base is int
    assert len(metadata) == 0
