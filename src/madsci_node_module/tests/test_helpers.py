"""Tests for the helpers module."""

from pathlib import Path
from typing import Dict, List, Optional, Union

import pytest
from madsci.common.types.action_types import (
    ActionFiles,
    ActionJSON,
    FileActionResultDefinition,
    JSONActionResultDefinition,
)
from madsci.node_module.helpers import create_dynamic_model, parse_result, parse_results
from pydantic import BaseModel, ValidationError


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


def test_create_dynamic_model_basic_types():
    """Test create_dynamic_model with basic types."""
    # Test int
    model_class = create_dynamic_model(int)
    assert issubclass(model_class, BaseModel)
    instance = model_class(data=42)
    assert instance.data == 42

    # Test str
    model_class = create_dynamic_model(str)
    instance = model_class(data="test")
    assert instance.data == "test"

    # Test dict
    model_class = create_dynamic_model(dict)
    instance = model_class(data={"key": "value"})
    assert instance.data == {"key": "value"}


def test_create_dynamic_model_optional_types():
    """Test create_dynamic_model with Optional types."""
    model_class = create_dynamic_model(Optional[int])

    # Test with value
    instance = model_class(data=42)
    assert instance.data == 42

    # Test with None
    instance = model_class(data=None)
    assert instance.data is None


def test_create_dynamic_model_list_types():
    """Test create_dynamic_model with List types."""
    model_class = create_dynamic_model(List[int])
    instance = model_class(data=[1, 2, 3])
    assert instance.data == [1, 2, 3]


def test_create_dynamic_model_dict_types():
    """Test create_dynamic_model with Dict types."""
    model_class = create_dynamic_model(Dict[str, int])
    instance = model_class(data={"a": 1, "b": 2})
    assert instance.data == {"a": 1, "b": 2}


def test_create_dynamic_model_union_types():
    """Test create_dynamic_model with Union types."""
    model_class = create_dynamic_model(Union[int, str])

    # Test with int
    instance = model_class(data=42)
    assert instance.data == 42

    # Test with str
    instance = model_class(data="test")
    assert instance.data == "test"


def test_create_dynamic_model_tuple_types():
    """Test create_dynamic_model with tuple types."""
    model_class = create_dynamic_model(tuple[int, str, bool])
    instance = model_class(data=(42, "test", True))
    assert instance.data == (42, "test", True)


def test_create_dynamic_model_nested_types():
    """Test create_dynamic_model with nested generic types."""
    model_class = create_dynamic_model(List[Dict[str, int]])
    instance = model_class(data=[{"a": 1}, {"b": 2}])
    assert instance.data == [{"a": 1}, {"b": 2}]


def test_create_dynamic_model_custom_pydantic_model():
    """Test create_dynamic_model with custom Pydantic model."""

    class CustomModel(BaseModel):
        name: str
        age: int

    model_class = create_dynamic_model(CustomModel)
    instance = model_class(data=CustomModel(name="John", age=30))
    assert instance.data.name == "John"
    assert instance.data.age == 30


def test_create_dynamic_model_with_custom_field_name():
    """Test create_dynamic_model with custom field name."""
    model_class = create_dynamic_model(int, field_name="value")
    instance = model_class(value=42)
    assert instance.value == 42


def test_create_dynamic_model_with_custom_model_name():
    """Test create_dynamic_model with custom model name."""
    model_class = create_dynamic_model(str, model_name="CustomStringModel")
    assert model_class.__name__ == "CustomStringModel"


def test_create_dynamic_model_validation():
    """Test that the dynamic model performs proper validation."""
    model_class = create_dynamic_model(int)

    # Valid data should work
    instance = model_class(data=42)
    assert instance.data == 42

    # Invalid data should raise validation error
    with pytest.raises(ValidationError):  # Pydantic validation error
        model_class(data="not an int")


def test_create_dynamic_model_complex_example():
    """Test create_dynamic_model with a complex real-world example."""
    complex_type = Dict[str, List[Union[int, str]]]
    model_class = create_dynamic_model(complex_type)

    test_data = {
        "numbers": [1, 2, 3],
        "mixed": [1, "two", 3, "four"],
        "strings": ["a", "b", "c"],
    }

    instance = model_class(data=test_data)
    assert instance.data == test_data
