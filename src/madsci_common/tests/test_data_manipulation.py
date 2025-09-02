"""Unit tests for madsci.common.data_manipulation module."""

import pytest
from madsci.common.data_manipulation import (
    check_for_parameters,
    value_substitution,
    walk_and_replace,
)


def test_value_substitution_simple_parameter():
    """Test simple parameter substitution with $ prefix."""
    parameters = {"param1": "value1", "param2": 42}

    # Test simple parameter substitution
    result = value_substitution("$param1", parameters)
    assert result == "value1"

    # Test parameter not in dict (should return original)
    result = value_substitution("$missing", parameters)
    assert result == "$missing"

    # Test numeric parameter
    result = value_substitution("$param2", parameters)
    assert result == 42


def test_value_substitution_braced_parameter():
    """Test parameter substitution with ${} syntax."""
    parameters = {"param1": "value1", "param_with_underscore": "underscore_value"}

    # Test braced parameter substitution
    result = value_substitution("${param1}", parameters)
    assert result == "value1"

    # Test parameter with underscore
    result = value_substitution("${param_with_underscore}", parameters)
    assert result == "underscore_value"

    # Test missing parameter (should return original)
    result = value_substitution("${missing}", parameters)
    assert result == "${missing}"


def test_value_substitution_embedded_parameters():
    """Test parameter substitution embedded in strings."""
    parameters = {"name": "John", "age": 25, "city": "Boston"}

    # Test simple parameter in string
    result = value_substitution("Hello $name", parameters)
    assert result == "Hello John"

    # Test braced parameter in string
    result = value_substitution("Age is ${age} years", parameters)
    assert result == "Age is 25 years"

    # Test multiple parameters
    result = value_substitution("$name from ${city}", parameters)
    assert result == "John from Boston"


def test_value_substitution_malformed_syntax():
    """Test error handling for malformed parameter syntax."""
    parameters = {"param": "value"}

    # Test missing opening brace
    with pytest.raises(SyntaxError, match="Missing opening { in parameter insertion"):
        value_substitution("$param}", parameters)


def test_value_substitution_edge_cases():
    """Test edge cases for parameter substitution."""
    parameters = {"param": "value", "123": "numeric_name"}

    # Test escaped dollar signs (should not substitute)
    result = value_substitution("$$param", parameters)
    assert result == "$$param"

    # Test parameter names with numbers
    result = value_substitution("$123", parameters)
    assert result == "numeric_name"

    # Test empty string
    result = value_substitution("", parameters)
    assert result == ""

    # Test string with no parameters
    result = value_substitution("no parameters here", parameters)
    assert result == "no parameters here"


def test_walk_and_replace_simple_dict():
    """Test walking and replacing parameters in a simple dictionary."""
    input_dict = {"key1": "$param1", "key2": "static_value", "key3": "${param2}"}
    parameters = {"param1": "replaced1", "param2": "replaced2"}

    result = walk_and_replace(input_dict, parameters)

    assert result["key1"] == "replaced1"
    assert result["key2"] == "static_value"
    assert result["key3"] == "replaced2"


def test_walk_and_replace_nested_dict():
    """Test walking and replacing parameters in nested dictionaries."""
    input_dict = {
        "level1": {
            "level2": {"deep_param": "$deep_value"},
            "param": "${surface_value}",
        },
        "simple": "$simple_param",
    }
    parameters = {
        "deep_value": "deep_replaced",
        "surface_value": "surface_replaced",
        "simple_param": "simple_replaced",
    }

    result = walk_and_replace(input_dict, parameters)

    assert result["level1"]["level2"]["deep_param"] == "deep_replaced"
    assert result["level1"]["param"] == "surface_replaced"
    assert result["simple"] == "simple_replaced"


def test_walk_and_replace_parameter_keys():
    """Test walking and replacing parameters in dictionary keys."""
    input_dict = {
        "$key_param": "value1",
        "static_key": "$value_param",
        "${another_key}": "static_value",
    }
    parameters = {
        "key_param": "replaced_key",
        "value_param": "replaced_value",
        "another_key": "another_replaced_key",
    }

    result = walk_and_replace(input_dict, parameters)

    # Original key should be removed, new key should have the value
    assert "replaced_key" in result
    assert result["replaced_key"] == "value1"
    assert "$key_param" not in result

    # Value replacement should work
    assert result["static_key"] == "replaced_value"

    # Braced key replacement should work
    assert "another_replaced_key" in result
    assert result["another_replaced_key"] == "static_value"
    assert "${another_key}" not in result


def test_walk_and_replace_mixed_types():
    """Test walking and replacing with mixed data types."""
    input_dict = {
        "string": "$param",
        "number": 42,
        "boolean": True,
        "nested": {"inner_string": "${inner_param}", "inner_number": 3.14},
    }
    parameters = {"param": "replaced", "inner_param": "inner_replaced"}

    result = walk_and_replace(input_dict, parameters)

    assert result["string"] == "replaced"
    assert result["number"] == 42  # Should remain unchanged
    assert result["boolean"] is True  # Should remain unchanged
    assert result["nested"]["inner_string"] == "inner_replaced"
    assert result["nested"]["inner_number"] == 3.14  # Should remain unchanged


def test_walk_and_replace_preserves_original():
    """Test that walk_and_replace doesn't modify the original dictionary."""
    original_dict = {"key": "$param"}
    parameters = {"param": "replaced"}

    result = walk_and_replace(original_dict, parameters)

    # Original should be unchanged
    assert original_dict["key"] == "$param"
    # Result should be modified
    assert result["key"] == "replaced"


def test_check_for_parameters_simple():
    """Test checking for simple parameter patterns."""
    parameter_names = ["param1", "param2", "other"]

    # Test simple parameter pattern
    assert check_for_parameters("$param1", parameter_names) is True
    assert check_for_parameters("$param2 in string", parameter_names) is True
    assert check_for_parameters("text $other more text", parameter_names) is True

    # Test parameters not in list
    assert check_for_parameters("$missing", parameter_names) is False


def test_check_for_parameters_braced():
    """Test checking for braced parameter patterns."""
    parameter_names = ["param1", "param_name", "test"]

    # Test braced parameter pattern
    assert check_for_parameters("${param1}", parameter_names) is True
    assert check_for_parameters("text ${param_name} more", parameter_names) is True
    assert (
        check_for_parameters("multiple ${test} and ${param1}", parameter_names) is True
    )

    # Test parameters not in list
    assert check_for_parameters("${missing}", parameter_names) is False


def test_check_for_parameters_edge_cases():
    """Test edge cases for parameter checking."""
    parameter_names = ["param", "test_param"]

    # Test no parameters
    assert check_for_parameters("no parameters here", parameter_names) is False

    # Test empty string
    assert check_for_parameters("", parameter_names) is False

    # Test parameter names with special characters
    assert check_for_parameters("$test_param", parameter_names) is True

    # Test escaped parameters (the function doesn't handle escaping, so it matches)
    assert check_for_parameters("$$param", parameter_names) is True


def test_check_for_parameters_word_boundaries():
    """Test that parameter checking respects word boundaries."""
    parameter_names = ["param", "p"]

    # Should match exact parameter names
    assert check_for_parameters("$param", parameter_names) is True
    assert check_for_parameters("$p", parameter_names) is True

    # Should not match partial parameter names
    assert check_for_parameters("$parameter", parameter_names) is False
    assert check_for_parameters("$params", parameter_names) is False


def test_value_substitution_special_characters():
    """Test parameter substitution with special characters in values."""
    parameters = {
        "special": "value with spaces",
        "symbols": "!@#$%^&*()",
        "path": "/path/to/file.txt",
    }

    result = value_substitution("$special", parameters)
    assert result == "value with spaces"

    result = value_substitution("${symbols}", parameters)
    assert result == "!@#$%^&*()"

    result = value_substitution("File: ${path}", parameters)
    assert result == "File: /path/to/file.txt"


def test_walk_and_replace_empty_dict():
    """Test walking and replacing with empty dictionaries."""
    # Empty input dict
    result = walk_and_replace({}, {"param": "value"})
    assert result == {}

    # Empty parameters
    input_dict = {"key": "$param"}
    result = walk_and_replace(input_dict, {})
    assert result["key"] == "$param"  # Should remain unchanged


def test_walk_and_replace_none_values():
    """Test walking and replacing with None values."""
    input_dict = {
        "string": "$param",
        "none_val": None,
        "nested": {"inner": "$inner_param", "inner_none": None},
    }
    parameters = {"param": "replaced", "inner_param": "inner_replaced"}

    result = walk_and_replace(input_dict, parameters)

    assert result["string"] == "replaced"
    assert result["none_val"] is None
    assert result["nested"]["inner"] == "inner_replaced"
    assert result["nested"]["inner_none"] is None
