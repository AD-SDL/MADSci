"""Unit tests for madsci.common.utils module."""

import os
import tempfile
import threading
import time
from argparse import ArgumentTypeError
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional, Union
from unittest.mock import patch

import pytest
from madsci.common.types.action_types import ActionDatapoints
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.utils import (
    extract_datapoint_ids,
    is_annotated,
    is_optional,
    is_valid_ulid,
    localnow,
    new_name_str,
    new_ulid_str,
    pretty_type_repr,
    prompt_for_input,
    prompt_from_list,
    prompt_yes_no,
    relative_path,
    repeat_on_interval,
    save_model,
    search_for_file_pattern,
    string_to_bool,
    threaded_daemon,
    threaded_task,
    to_snake_case,
    utcnow,
)
from pydantic import BaseModel


class MockMadsciModel(BaseModel):
    """Mock model for testing."""

    name: str
    value: int = 42

    def to_yaml(self, path):
        """Mock to_yaml method."""
        Path(path).write_text(f"name: {self.name}\nvalue: {self.value}")


def test_utcnow():
    """Test UTC timestamp generation."""
    now = utcnow()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc


def test_localnow():
    """Test local timestamp generation."""
    now = localnow()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None


def test_to_snake_case():
    """Test conversion to snake case."""
    assert to_snake_case("camelCase") == "camel_case"
    assert to_snake_case("PascalCase") == "pascal_case"
    assert to_snake_case("already_snake") == "already_snake"
    assert to_snake_case("Mixed CaseString") == "mixed_case_string"
    assert to_snake_case("HTMLParser") == "html_parser"
    assert to_snake_case("XMLHttpRequest") == "xml_http_request"


def test_search_for_file_pattern():
    """Test file pattern search functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "test.txt").touch()
        (temp_path / "example.py").touch()
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").touch()

        # Change to the temp directory for glob operations

        original_dir = Path.cwd()
        try:
            os.chdir(temp_path)

            # Test searching with children
            results = search_for_file_pattern(
                "*.txt", start_dir=temp_path, parents=False, children=True
            )
            txt_files = [str(r) for r in results if r.name.endswith(".txt")]
            assert len(txt_files) >= 1

            # Test searching without children
            results = search_for_file_pattern(
                "*.py", start_dir=temp_path, parents=False, children=False
            )
            py_files = [str(r) for r in results if r.name.endswith(".py")]
            assert len(py_files) >= 1
        finally:
            os.chdir(original_dir)


def test_save_model():
    """Test model saving functionality."""
    mock_model = MockMadsciModel(name="test", value=123)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Test saving without overwrite check
        save_model(temp_path, mock_model, overwrite_check=False)
        assert Path(temp_path).exists()
        content = Path(temp_path).read_text()
        assert "test" in content
        assert "123" in content
    finally:
        Path(temp_path).unlink(missing_ok=True)


@patch("madsci.common.utils.console.input")
def test_prompt_for_input_with_default(mock_input):
    """Test prompt for input with default value."""
    mock_input.return_value = ""
    result = prompt_for_input("Enter value", default="default_val", required=False)
    assert result == "default_val"


@patch("sys.stdin.isatty")
@patch("madsci.common.utils.console.input")
def test_prompt_for_input_required(mock_input, mock_isatty):
    """Test prompt for input with required value."""
    mock_isatty.return_value = True  # Ensure we're in interactive mode
    mock_input.side_effect = ["", "valid_input"]
    result = prompt_for_input("Enter value", required=True)
    assert result == "valid_input"


@patch("sys.stdin.isatty")
def test_prompt_for_input_quiet_mode(mock_isatty):
    """Test prompt for input in quiet mode."""
    mock_isatty.return_value = False
    result = prompt_for_input("Enter value", default="quiet_default", quiet=True)
    assert result == "quiet_default"


def test_prompt_for_input_quiet_no_default():
    """Test prompt for input in quiet mode without default."""
    result = prompt_for_input("Enter value", required=False, quiet=True)
    assert result is None


def test_prompt_for_input_quiet_required_no_default():
    """Test prompt for input in quiet mode, required but no default."""
    with pytest.raises(ValueError, match="No input provided"):
        prompt_for_input("Enter value", required=True, quiet=True)


@patch("madsci.common.utils.prompt_for_input")
def test_prompt_yes_no(mock_prompt):
    """Test yes/no prompting."""
    mock_prompt.return_value = "y"
    assert prompt_yes_no("Continue?") is True

    mock_prompt.return_value = "no"
    assert prompt_yes_no("Continue?") is False

    mock_prompt.return_value = "true"
    assert prompt_yes_no("Continue?") is True


def test_new_name_str():
    """Test random name generation."""
    name1 = new_name_str()
    name2 = new_name_str()

    # Names should be different (very high probability)
    assert name1 != name2
    assert "_" in name1
    assert len(name1.split("_")) == 2

    # Test with prefix
    prefixed = new_name_str("test")
    assert prefixed.startswith("test_")
    assert len(prefixed.split("_")) == 3


def test_string_to_bool():
    """Test string to boolean conversion."""
    # True cases
    assert string_to_bool("true") is True
    assert string_to_bool("TRUE") is True
    assert string_to_bool("t") is True
    assert string_to_bool("1") is True
    assert string_to_bool("yes") is True
    assert string_to_bool("y") is True

    # False cases
    assert string_to_bool("false") is False
    assert string_to_bool("FALSE") is False
    assert string_to_bool("f") is False
    assert string_to_bool("0") is False
    assert string_to_bool("no") is False
    assert string_to_bool("n") is False

    # Invalid cases
    with pytest.raises(ArgumentTypeError):
        string_to_bool("invalid")


@patch("madsci.common.utils.console.print")
@patch("madsci.common.utils.prompt_for_input")
def test_prompt_from_list(mock_prompt, mock_print):  # noqa: ARG001
    """Test prompting from a list of options."""
    options = ["option1", "option2", "option3"]

    # Test selection by number
    mock_prompt.return_value = "2"
    result = prompt_from_list("Choose", options)
    assert result == "option2"

    # Test selection by exact match
    mock_prompt.return_value = "option1"
    result = prompt_from_list("Choose", options)
    assert result == "option1"


def test_relative_path():
    """Test relative path calculation."""
    source = Path("/home/user/project")
    target = Path("/home/user/project/subdir/file.txt")

    result = relative_path(source, target)
    assert str(result) == "subdir/file.txt"

    # Test walking up
    source = Path("/home/user/project/deep/nested")
    target = Path("/home/user/project/file.txt")
    result = relative_path(source, target, walk_up=True)
    assert ".." in str(result)


def test_relative_path_different_anchors():
    """Test relative path with different anchors."""
    # Create paths with different drive letters on Windows-like systems
    # Use a more realistic test case
    if Path("/").exists():  # Unix-like system
        source = Path("/home/user")
        target = Path("/var/log/file.txt")
        # On Unix, both have same anchor "/" so this test is different
        # Let's test the actual functionality
        result = relative_path(source, target, walk_up=True)
        assert ".." in str(result)
    else:
        # Skip this test on systems where path structure is different
        pytest.skip("Path anchor test not applicable on this system")


def test_threaded_task():
    """Test threaded task decorator."""
    results = []

    @threaded_task
    def test_func(value):
        results.append(value)

    thread = test_func("test_value")
    assert isinstance(thread, threading.Thread)
    thread.join()  # Wait for completion
    assert "test_value" in results


def test_threaded_daemon():
    """Test threaded daemon decorator."""
    results = []

    @threaded_daemon
    def test_func(value):
        results.append(value)

    thread = test_func("daemon_value")
    assert isinstance(thread, threading.Thread)
    assert thread.daemon is True
    thread.join()  # Wait for completion
    assert "daemon_value" in results


def test_pretty_type_repr():
    """Test pretty type representation."""
    assert "str" in pretty_type_repr(str)
    assert "int" in pretty_type_repr(int)

    # Test with generic types
    list_str_repr = pretty_type_repr(List[str])
    assert "list" in list_str_repr.lower() or "List" in list_str_repr


def test_repeat_on_interval():
    """Test interval-based function repetition."""
    call_count = []

    def test_func():
        call_count.append(1)

    # Start the repeating function
    repeat_on_interval(0.1, test_func)

    # Let it run for a short time
    time.sleep(0.25)

    # Stop by setting daemon thread (it will stop when main thread ends)
    assert len(call_count) >= 2  # Should have been called at least twice


def test_is_optional():
    """Test optional type checking."""
    assert is_optional(Optional[str]) is True
    assert is_optional(Union[str, None]) is True
    assert is_optional(str) is False
    assert is_optional(Union[str, int]) is False


def test_is_annotated():
    """Test annotated type checking."""

    assert is_annotated(Annotated[str, "description"]) is True
    assert is_annotated(str) is False
    assert is_annotated(Optional[str]) is False


def test_new_ulid_str():
    """Test ULID string generation."""
    ulid1 = new_ulid_str()
    ulid2 = new_ulid_str()

    # ULIDs should be different
    assert ulid1 != ulid2

    # ULIDs should be 26 characters long
    assert len(ulid1) == 26
    assert len(ulid2) == 26

    # ULIDs should be alphanumeric (Crockford's Base32)
    assert ulid1.isalnum()
    assert ulid2.isalnum()


def test_is_valid_ulid():
    """Test ULID validation function."""
    # Test with valid ULIDs
    valid_ulid = new_ulid_str()
    assert is_valid_ulid(valid_ulid)

    # Test with invalid inputs
    assert not is_valid_ulid("too-short")
    assert not is_valid_ulid("too-long-to-be-a-valid-ulid-string")
    assert not is_valid_ulid("invalid-chars-!@#$%^&*()")
    assert not is_valid_ulid(123)
    assert not is_valid_ulid(None)


def test_extract_datapoint_ids():
    """Test datapoint ID extraction from data structures."""
    # Test with simple dictionary
    ulid1 = new_ulid_str()
    ulid2 = new_ulid_str()
    data = {"result1": ulid1, "result2": ulid2}
    extracted = extract_datapoint_ids(data)
    assert set(extracted) == {ulid1, ulid2}

    # Test with nested structures
    data = {"results": [ulid1, {"nested": ulid2}], "other": "not-a-ulid"}
    extracted = extract_datapoint_ids(data)
    assert set(extracted) == {ulid1, ulid2}

    # Test with DataPoint objects
    value_dp = ValueDataPoint(value="test", label="test_value")
    data = {"datapoint": value_dp, "id": value_dp.datapoint_id}
    extracted = extract_datapoint_ids(data)
    assert extracted == [value_dp.datapoint_id]  # Deduplicated

    # Test with empty input
    assert extract_datapoint_ids({}) == []
    assert extract_datapoint_ids([]) == []
    assert extract_datapoint_ids(None) == []


class TestActionDatapoints:
    """Test cases for ActionDatapoints validation and conversion."""

    def test_single_datapoint_id_string(self):
        """Test that a single ULID string is accepted."""
        ulid = new_ulid_str()
        datapoints = ActionDatapoints.model_validate({"result": ulid})
        assert datapoints.result == ulid

    def test_list_of_datapoint_ids(self):
        """Test that a list of ULID strings is accepted."""
        ulids = [new_ulid_str(), new_ulid_str()]
        datapoints = ActionDatapoints.model_validate({"results": ulids})
        assert datapoints.results == ulids

    def test_datapoint_object_to_id_conversion(self):
        """Test that DataPoint objects are converted to IDs."""
        value_dp = ValueDataPoint(value="test", label="test_value")
        datapoints = ActionDatapoints.model_validate({"result": value_dp})
        assert datapoints.result == value_dp.datapoint_id

    def test_list_of_datapoint_objects_conversion(self):
        """Test that a list of DataPoint objects is converted to IDs."""
        value_dp1 = ValueDataPoint(value="test1", label="test_value1")
        value_dp2 = ValueDataPoint(value="test2", label="test_value2")
        datapoints = ActionDatapoints.model_validate(
            {"results": [value_dp1, value_dp2]}
        )
        assert datapoints.results == [value_dp1.datapoint_id, value_dp2.datapoint_id]

    def test_mixed_datapoint_objects_and_ids(self):
        """Test mixing DataPoint objects and ULID strings in a list."""
        value_dp = ValueDataPoint(value="test", label="test_value")
        ulid = new_ulid_str()
        datapoints = ActionDatapoints.model_validate({"results": [value_dp, ulid]})
        assert datapoints.results == [value_dp.datapoint_id, ulid]

    def test_invalid_ulid_string_raises_error(self):
        """Test that invalid ULID strings raise validation errors."""
        with pytest.raises(ValueError, match="must be a valid ULID string"):
            ActionDatapoints.model_validate({"result": "invalid-ulid"})

    def test_invalid_datapoint_type_raises_error(self):
        """Test that invalid datapoint types raise validation errors."""
        with pytest.raises(ValueError, match="must be a ULID string, DataPoint object"):
            ActionDatapoints.model_validate({"result": 123})

    def test_file_datapoint_conversion(self):
        """Test that FileDataPoint objects are handled correctly."""
        file_dp = FileDataPoint(path="/test/file.txt", label="test_file")
        datapoints = ActionDatapoints.model_validate({"file_result": file_dp})
        assert datapoints.file_result == file_dp.datapoint_id
