"""Unit tests for madsci.common.validators module."""

import pytest
from madsci.common.utils import new_ulid_str
from madsci.common.validators import (
    alphanumeric_with_underscores_validator,
    create_dict_promoter,
    optional_ulid_validator,
    ulid_validator,
)


class MockValidationInfo:
    """Mock ValidationInfo for testing."""

    def __init__(self, field_name: str = "test_field"):
        self.field_name = field_name


def test_ulid_validator_valid():
    """Test ULID validator with valid ULIDs."""
    # Generate a valid ULID
    valid_ulid = new_ulid_str()
    info = MockValidationInfo("test_field")

    result = ulid_validator(valid_ulid, info)
    assert result == valid_ulid


def test_ulid_validator_invalid():
    """Test ULID validator with invalid ULIDs."""
    info = MockValidationInfo("test_field")

    # Test invalid ULID format
    with pytest.raises(ValueError, match=r"Invalid ULID.*for field test_field"):
        ulid_validator("invalid_ulid", info)

    # Test empty string
    with pytest.raises(ValueError, match=r"Invalid ULID.*for field test_field"):
        ulid_validator("", info)

    # Test wrong length
    with pytest.raises(ValueError, match=r"Invalid ULID.*for field test_field"):
        ulid_validator("01H4T5F9J8K7L6M3N2", info)  # Too short


def test_ulid_validator_field_name_in_error():
    """Test that ULID validator includes field name in error message."""
    info = MockValidationInfo("my_custom_field")

    with pytest.raises(ValueError, match=r"Invalid ULID.*for field my_custom_field"):
        ulid_validator("invalid", info)


def test_optional_ulid_validator_none():
    """Test optional ULID validator with None value."""
    info = MockValidationInfo("optional_field")

    result = optional_ulid_validator(None, info)
    assert result is None


def test_optional_ulid_validator_valid():
    """Test optional ULID validator with valid ULID."""
    valid_ulid = new_ulid_str()
    info = MockValidationInfo("optional_field")

    result = optional_ulid_validator(valid_ulid, info)
    assert result == valid_ulid


def test_optional_ulid_validator_invalid():
    """Test optional ULID validator with invalid ULID."""
    info = MockValidationInfo("optional_field")

    with pytest.raises(ValueError, match=r"Invalid ULID.*for field optional_field"):
        optional_ulid_validator("invalid_ulid", info)


def test_alphanumeric_with_underscores_validator_valid():
    """Test alphanumeric with underscores validator with valid inputs."""
    info = MockValidationInfo("name_field")

    # Test basic alphanumeric
    result = alphanumeric_with_underscores_validator("test123", info)
    assert result == "test123"

    # Test with underscores
    result = alphanumeric_with_underscores_validator("test_name_123", info)
    assert result == "test_name_123"

    # Test only letters
    result = alphanumeric_with_underscores_validator("testname", info)
    assert result == "testname"

    # Test only numbers
    result = alphanumeric_with_underscores_validator("123456", info)
    assert result == "123456"

    # Test mixed case
    result = alphanumeric_with_underscores_validator("TestName123", info)
    assert result == "TestName123"


def test_alphanumeric_with_underscores_validator_invalid():
    """Test alphanumeric with underscores validator with invalid inputs."""
    info = MockValidationInfo("name_field")

    # Test with spaces
    with pytest.raises(
        ValueError,
        match="Field name_field must contain only alphanumeric characters and underscores",
    ):
        alphanumeric_with_underscores_validator("test name", info)

    # Test with special characters
    with pytest.raises(
        ValueError,
        match="Field name_field must contain only alphanumeric characters and underscores",
    ):
        alphanumeric_with_underscores_validator("test-name", info)

    # Test with dots
    with pytest.raises(
        ValueError,
        match="Field name_field must contain only alphanumeric characters and underscores",
    ):
        alphanumeric_with_underscores_validator("test.name", info)

    # Test with symbols
    with pytest.raises(
        ValueError,
        match="Field name_field must contain only alphanumeric characters and underscores",
    ):
        alphanumeric_with_underscores_validator("test@name", info)


def test_alphanumeric_with_underscores_validator_non_string():
    """Test alphanumeric with underscores validator with non-string input."""
    info = MockValidationInfo("name_field")

    # Test with integer (should be converted to string)
    result = alphanumeric_with_underscores_validator(123, info)
    assert result == 123

    # Test with float that becomes invalid when stringified
    with pytest.raises(ValueError):
        alphanumeric_with_underscores_validator(12.34, info)


def test_create_dict_promoter_with_list():
    """Test creating dict promoter and using it with a list."""
    # Create a promoter that uses 'name' attribute as key
    promoter = create_dict_promoter(lambda item: item["name"])

    # Test with list of dictionaries
    input_list = [
        {"name": "item1", "value": 10},
        {"name": "item2", "value": 20},
        {"name": "item3", "value": 30},
    ]

    result = promoter(input_list)

    assert isinstance(result, dict)
    assert len(result) == 3
    assert result["item1"] == {"name": "item1", "value": 10}
    assert result["item2"] == {"name": "item2", "value": 20}
    assert result["item3"] == {"name": "item3", "value": 30}


def test_create_dict_promoter_with_dict():
    """Test that dict promoter passes through existing dictionaries."""
    promoter = create_dict_promoter(lambda item: item["name"])

    # Test with existing dictionary
    input_dict = {
        "key1": {"name": "item1", "value": 10},
        "key2": {"name": "item2", "value": 20},
    }

    result = promoter(input_dict)

    # Should return the same dictionary unchanged
    assert result is input_dict
    assert result == input_dict


def test_create_dict_promoter_with_objects():
    """Test dict promoter with objects that have attributes."""

    class TestObject:
        def __init__(self, name, value):
            self.name = name
            self.value = value

    # Create promoter that uses object attribute
    promoter = create_dict_promoter(lambda item: item.name)

    # Test with list of objects
    input_list = [
        TestObject("obj1", 100),
        TestObject("obj2", 200),
        TestObject("obj3", 300),
    ]

    result = promoter(input_list)

    assert isinstance(result, dict)
    assert len(result) == 3
    assert result["obj1"].name == "obj1"
    assert result["obj1"].value == 100
    assert result["obj2"].name == "obj2"
    assert result["obj2"].value == 200


def test_create_dict_promoter_custom_key_function():
    """Test dict promoter with custom key function."""
    # Create promoter that uses index as key
    promoter = create_dict_promoter(lambda item: f"item_{item['id']}")

    input_list = [
        {"id": 1, "data": "first"},
        {"id": 2, "data": "second"},
        {"id": 3, "data": "third"},
    ]

    result = promoter(input_list)

    assert result["item_1"] == {"id": 1, "data": "first"}
    assert result["item_2"] == {"id": 2, "data": "second"}
    assert result["item_3"] == {"id": 3, "data": "third"}


def test_create_dict_promoter_empty_list():
    """Test dict promoter with empty list."""
    promoter = create_dict_promoter(lambda item: item["name"])

    result = promoter([])

    assert result == {}


def test_create_dict_promoter_duplicate_keys():
    """Test dict promoter behavior with duplicate keys (last one wins)."""
    promoter = create_dict_promoter(lambda item: item["category"])

    input_list = [
        {"category": "A", "value": 1},
        {"category": "B", "value": 2},
        {"category": "A", "value": 3},  # This should overwrite the first A
    ]

    result = promoter(input_list)

    assert len(result) == 2  # Only A and B
    assert result["A"] == {"category": "A", "value": 3}  # Last value wins
    assert result["B"] == {"category": "B", "value": 2}
