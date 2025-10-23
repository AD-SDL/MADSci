"""Test case to reproduce the bug with Annotated[Path, "description"] being treated as JSON argument."""

from pathlib import Path
from typing import Annotated, Optional

from madsci.common.types.action_types import (
    _analyze_file_parameter_type,
    extract_file_parameters,
)


def test_annotated_path_recognized_as_file_parameter():
    """Test that Annotated[Path, "description"] is correctly recognized as a file parameter."""
    # Test plain Path
    result = _analyze_file_parameter_type(Path)
    assert result["is_file_param"] is True
    assert result["is_list"] is False
    assert result["is_optional"] is False

    # Test Annotated[Path, "description"] - this should also be a file parameter
    result = _analyze_file_parameter_type(Annotated[Path, "A file path description"])
    assert result["is_file_param"] is True, "Annotated[Path, ...] should be recognized as a file parameter"
    assert result["is_list"] is False
    assert result["is_optional"] is False


def test_annotated_path_list_recognized_as_file_parameter():
    """Test that Annotated[list[Path], "description"] is correctly recognized as a file list parameter."""
    # Test plain list[Path]
    result = _analyze_file_parameter_type(list[Path])
    assert result["is_file_param"] is True
    assert result["is_list"] is True
    assert result["is_optional"] is False

    # Test Annotated[list[Path], "description"] - this should also be a file list parameter
    result = _analyze_file_parameter_type(Annotated[list[Path], "Multiple file paths"])
    assert result["is_file_param"] is True, "Annotated[list[Path], ...] should be recognized as a file list parameter"
    assert result["is_list"] is True
    assert result["is_optional"] is False


def test_extract_file_parameters_with_annotated_path():
    """Test that extract_file_parameters correctly identifies Annotated[Path] parameters."""

    def action_with_annotated_path(
        config_file: Annotated[Path, "Configuration file path"],
        data_files: Annotated[list[Path], "List of data files"],
        optional_file: Optional[Annotated[Path, "Optional file"]] = None,
    ) -> None:
        """Test action with annotated path parameters."""

    file_params = extract_file_parameters(action_with_annotated_path)

    # Check that all path parameters are recognized
    assert "config_file" in file_params, "config_file should be recognized as a file parameter"
    assert file_params["config_file"]["required"] is True
    assert file_params["config_file"]["is_list"] is False

    assert "data_files" in file_params, "data_files should be recognized as a file parameter"
    assert file_params["data_files"]["required"] is True
    assert file_params["data_files"]["is_list"] is True

    assert "optional_file" in file_params, "optional_file should be recognized as a file parameter"
    assert file_params["optional_file"]["required"] is False
    assert file_params["optional_file"]["is_list"] is False
