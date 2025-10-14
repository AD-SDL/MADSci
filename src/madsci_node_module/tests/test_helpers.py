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


class CustomPydanticModel(BaseModel):
    """Example custom pydantic model for testing."""

    name: str
    value: int
    metadata: dict[str, str] = {}


class ComplexPydanticModel(BaseModel):
    """Complex custom pydantic model for testing."""

    id: str
    data: list[float]
    config: dict[str, Union[str, int]]
    nested: Optional[CustomPydanticModel] = None


def test_parse_result_basic_types():
    """Test parse_result with basic types."""
    # Test int
    result = parse_result(int)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None
    assert "properties" in result[0].json_schema

    # Test str
    result = parse_result(str)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None

    # Test dict
    result = parse_result(dict)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None


def test_parse_result_path():
    """Test parse_result with Path type."""
    result = parse_result(Path)
    assert len(result) == 1
    assert isinstance(result[0], FileActionResultDefinition)
    assert result[0].result_label == "file"


def test_parse_result_action_json():
    """Test parse_result with ActionJSON subclass."""
    result = parse_result(ExampleJSONData)
    assert len(result) == 1

    # Check that we get a single json_result with schema
    assert result[0].result_label == "json_result"
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].json_schema is not None

    # Check that the schema includes the fields from the ActionJSON subclass
    schema = result[0].json_schema
    assert "properties" in schema
    assert "data" in schema["properties"]


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

    # Should get two JSON result definitions with schemas
    assert all(isinstance(r, JSONActionResultDefinition) for r in result)
    assert all(r.result_label == "json_result" for r in result)
    assert all(r.json_schema is not None for r in result)


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
    assert len(result) == 3  # 1 JSON result + 2 file fields

    # Check that we get the right mix of result types
    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 1  # Single json_result with schema
    assert len(file_results) == 2  # file1 and file2


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
    assert len(result) == 3  # 1 JSON result + 2 file fields

    # Check that we get the right mix of result types
    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 1  # Single json_result with schema
    assert len(file_results) == 2  # file1 and file2


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


def test_parse_result_custom_pydantic_model():
    """Test parse_result with custom pydantic model."""
    result = parse_result(CustomPydanticModel)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None

    # Check that the schema includes the fields from the custom model
    schema = result[0].json_schema
    assert "properties" in schema
    assert "name" in schema["properties"]
    assert "value" in schema["properties"]
    assert "metadata" in schema["properties"]


def test_parse_result_complex_pydantic_model():
    """Test parse_result with complex custom pydantic model."""
    result = parse_result(ComplexPydanticModel)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None

    # Check that the schema includes all fields
    schema = result[0].json_schema
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "data" in schema["properties"]
    assert "config" in schema["properties"]
    assert "nested" in schema["properties"]


def test_parse_result_tuple_with_custom_pydantic():
    """Test parse_result with tuple containing custom pydantic model."""
    result = parse_result(tuple[CustomPydanticModel, Path])
    assert len(result) == 2

    # Should get one JSON result definition and one file result definition
    result_types = [type(r) for r in result]
    assert JSONActionResultDefinition in result_types
    assert FileActionResultDefinition in result_types

    # Check the JSON result has the schema
    json_result = next(r for r in result if isinstance(r, JSONActionResultDefinition))
    assert json_result.result_label == "json_result"
    assert json_result.json_schema is not None


def test_parse_result_tuple_mixed_custom_pydantic():
    """Test parse_result with tuple containing multiple custom models."""
    result = parse_result(tuple[CustomPydanticModel, ComplexPydanticModel])
    assert len(result) == 2

    # Should get two JSON result definitions
    assert all(isinstance(r, JSONActionResultDefinition) for r in result)
    assert all(r.result_label == "json_result" for r in result)
    assert all(r.json_schema is not None for r in result)


def dummy_function_with_custom_pydantic() -> CustomPydanticModel:
    """Dummy function for testing parse_results with custom pydantic model."""
    return CustomPydanticModel(name="test", value=42)


def dummy_function_with_mixed_custom() -> tuple[CustomPydanticModel, ExampleFileData]:
    """Dummy function for testing parse_results with mixed custom types."""
    return (
        CustomPydanticModel(name="test", value=42),
        ExampleFileData(file1=Path("/test1"), file2=Path("/test2")),
    )


def test_parse_results_with_custom_pydantic():
    """Test parse_results function with custom pydantic model return annotation."""
    result = parse_results(dummy_function_with_custom_pydantic)
    assert len(result) == 1
    assert isinstance(result[0], JSONActionResultDefinition)
    assert result[0].result_label == "json_result"
    assert result[0].json_schema is not None


def test_parse_results_with_mixed_custom_types():
    """Test parse_results function with tuple of custom model and ActionFiles."""
    result = parse_results(dummy_function_with_mixed_custom)
    assert len(result) == 3  # 1 JSON result + 2 file fields

    # Check that we get the right mix of result types
    json_results = [r for r in result if isinstance(r, JSONActionResultDefinition)]
    file_results = [r for r in result if isinstance(r, FileActionResultDefinition)]

    assert len(json_results) == 1  # Single json_result with schema
    assert len(file_results) == 2  # file1 and file2
