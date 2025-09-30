"""Tests for the helpers module."""

from pathlib import Path

import pytest
from madsci.common.types.action_types import (
    ActionFiles,
    ActionJSON,
    FileActionResultDefinition,
    JSONActionResultDefinition,
)
from madsci.node_module.helpers import parse_result, parse_results


class ExampleJSONData(ActionJSON):
    """Example JSON data for testing."""

    value1: str
    value2: int


class ExampleFileData(ActionFiles):
    """Example file data for testing."""

    file1: Path
    file2: Path


def test_parse_result_basic_types():
    """Test parse_result with basic types."""
    # Test int
    result = parse_result(int)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "data"
    assert result[0].data_type == "int"

    # Test str
    result = parse_result(str)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "data"
    assert result[0].data_type == "str"

    # Test dict
    result = parse_result(dict)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "data"
    assert result[0].data_type == "dict"


def test_parse_result_path():
    """Test parse_result with Path type."""
    result = parse_result(Path)
    assert len(result) == 1
    assert isinstance(result[0], FileActionResultDefinition)
    assert result[0].result_label == "file"


def test_parse_result_action_json():
    """Test parse_result with ActionJSON subclass."""
    result = parse_result(ExampleJSONData)
    assert len(result) == 2

    # Check that both fields are present
    labels = [r.result_label for r in result]
    assert "value1" in labels
    assert "value2" in labels

    # Check that they're all JSON result definitions
    for r in result:
        assert isinstance(r, JSONActionResultDefinition)


def test_parse_result_action_files():
    """Test parse_result with ActionFiles subclass."""
    result = parse_result(ExampleFileData)
    assert len(result) == 2

    # Check that both fields are present
    labels = [r.result_label for r in result]
    assert "file1" in labels
    assert "file2" in labels

    # Check that they're all file result definitions
    for r in result:
        assert isinstance(r, FileActionResultDefinition)


def test_parse_result_tuple_basic_types():
    """Test parse_result with tuple of basic types."""
    result = parse_result(tuple[int, str])
    assert len(result) == 2

    # Should get two JSON result definitions
    assert all(isinstance(r, JSONActionResultDefinition) for r in result)

    # Check data types
    data_types = [r.data_type for r in result]
    assert "int" in data_types
    assert "str" in data_types


def test_parse_result_tuple_mixed_types():
    """Test parse_result with tuple of mixed types including Path."""
    result = parse_result(tuple[int, Path])
    assert len(result) == 2

    # Should get one JSON and one file result definition
    result_types = [type(r) for r in result]
    assert JSONActionResultDefinition in result_types
    assert FileActionResultDefinition in result_types


def test_parse_result_tuple_action_types():
    """Test parse_result with tuple of ActionJSON and ActionFiles."""
    result = parse_result(tuple[ExampleJSONData, ExampleFileData])
    assert len(result) == 4  # 2 JSON fields + 2 file fields

    # Check that we get the right mix of result types
    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 2
    assert len(file_results) == 2


def test_parse_result_nested_tuple():
    """Test parse_result with nested tuple types."""
    # This should work since we recursively handle tuples
    result = parse_result(tuple[tuple[int, str], Path])
    assert len(result) == 3  # int + str + Path

    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 2  # int and str
    assert len(file_results) == 1  # Path


def test_parse_result_invalid_type():
    """Test parse_result with invalid type."""
    with pytest.raises(ValueError, match="Action return type must be"):
        parse_result(object)


def dummy_function_with_tuple() -> tuple[int, Path]:
    """Dummy function for testing parse_results with tuple."""
    return 42, Path("/test")


def dummy_function_with_action_tuple() -> tuple[ExampleJSONData, ExampleFileData]:
    """Dummy function for testing parse_results with action types in tuple."""
    return (
        ExampleJSONData(value1="test", value2=42),
        ExampleFileData(file1=Path("/test1"), file2=Path("/test2")),
    )


def test_parse_results_with_tuple():
    """Test parse_results function with tuple return annotation."""
    result = parse_results(dummy_function_with_tuple)
    assert len(result) == 2

    # Should get one JSON and one file result definition
    result_types = [type(r) for r in result]
    assert JSONActionResultDefinition in result_types
    assert FileActionResultDefinition in result_types


def test_parse_results_with_action_tuple():
    """Test parse_results function with tuple of action types."""
    result = parse_results(dummy_function_with_action_tuple)
    assert len(result) == 4  # 2 JSON fields + 2 file fields

    # Check that we get the right mix of result types
    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 2
    assert len(file_results) == 2
