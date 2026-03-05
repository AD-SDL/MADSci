"""Tests for E2E validators."""

import json
from pathlib import Path

import pytest
from madsci.common.testing.types import ValidationConfig, ValidationType
from madsci.common.testing.validators import (
    DirectoryExistsValidator,
    ExitCodeValidator,
    FileContainsValidator,
    FileExistsValidator,
    JsonContainsValidator,
    JsonFieldValidator,
    OutputContainsValidator,
    PythonSyntaxValidator,
    ValidatorRegistry,
    get_validator_registry,
)


class TestExitCodeValidator:
    """Tests for ExitCodeValidator."""

    def test_exit_code_zero_passes(self):
        """Test that exit code 0 passes by default."""
        validator = ExitCodeValidator()
        config = ValidationConfig(type=ValidationType.EXIT_CODE)
        context = {"exit_code": 0}

        result = validator.validate(config, context)

        assert result.passed is True
        assert result.expected == 0
        assert result.actual == 0

    def test_exit_code_nonzero_fails(self):
        """Test that non-zero exit code fails by default."""
        validator = ExitCodeValidator()
        config = ValidationConfig(type=ValidationType.EXIT_CODE)
        context = {"exit_code": 1}

        result = validator.validate(config, context)

        assert result.passed is False
        assert result.expected == 0
        assert result.actual == 1

    def test_expected_exit_code(self):
        """Test custom expected exit code."""
        validator = ExitCodeValidator()
        config = ValidationConfig(type=ValidationType.EXIT_CODE, expected=42)
        context = {"exit_code": 42}

        result = validator.validate(config, context)

        assert result.passed is True
        assert result.expected == 42

    def test_negate_exit_code(self):
        """Test negated exit code validation."""
        validator = ExitCodeValidator()
        config = ValidationConfig(
            type=ValidationType.EXIT_CODE, expected=0, negate=True
        )
        context = {"exit_code": 0}

        result = validator.validate(config, context)

        assert result.passed is False  # 0 == 0, but negated


class TestFileExistsValidator:
    """Tests for FileExistsValidator."""

    def test_existing_file_passes(self, tmp_path: Path):
        """Test that existing file passes validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        validator = FileExistsValidator()
        config = ValidationConfig(type=ValidationType.FILE_EXISTS, path="test.txt")
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is True

    def test_nonexistent_file_fails(self, tmp_path: Path):
        """Test that nonexistent file fails validation."""
        validator = FileExistsValidator()
        config = ValidationConfig(type=ValidationType.FILE_EXISTS, path="missing.txt")
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False

    def test_negate_file_exists(self, tmp_path: Path):
        """Test negated file exists validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        validator = FileExistsValidator()
        config = ValidationConfig(
            type=ValidationType.FILE_EXISTS, path="test.txt", negate=True
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False  # File exists, but we want it not to


class TestDirectoryExistsValidator:
    """Tests for DirectoryExistsValidator."""

    def test_existing_directory_passes(self, tmp_path: Path):
        """Test that existing directory passes validation."""
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()

        validator = DirectoryExistsValidator()
        config = ValidationConfig(type=ValidationType.DIRECTORY_EXISTS, path="subdir")
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is True

    def test_file_not_directory_fails(self, tmp_path: Path):
        """Test that file (not directory) fails directory validation."""
        test_file = tmp_path / "file"
        test_file.write_text("hello")

        validator = DirectoryExistsValidator()
        config = ValidationConfig(type=ValidationType.DIRECTORY_EXISTS, path="file")
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False


class TestFileContainsValidator:
    """Tests for FileContainsValidator."""

    def test_file_contains_pattern(self, tmp_path: Path):
        """Test that file containing pattern passes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        validator = FileContainsValidator()
        config = ValidationConfig(
            type=ValidationType.FILE_CONTAINS,
            path="test.txt",
            pattern="World",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is True

    def test_file_not_contains_pattern(self, tmp_path: Path):
        """Test that file not containing pattern fails."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        validator = FileContainsValidator()
        config = ValidationConfig(
            type=ValidationType.FILE_CONTAINS,
            path="test.txt",
            pattern="Universe",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False

    def test_file_contains_regex(self, tmp_path: Path):
        """Test regex pattern matching."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("class MyClass(Base):")

        validator = FileContainsValidator()
        config = ValidationConfig(
            type=ValidationType.FILE_CONTAINS,
            path="test.txt",
            pattern=r"class\s+\w+\(",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is True

    def test_nonexistent_file_fails(self, tmp_path: Path):
        """Test that nonexistent file fails."""
        validator = FileContainsValidator()
        config = ValidationConfig(
            type=ValidationType.FILE_CONTAINS,
            path="missing.txt",
            pattern="anything",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False
        assert "does not exist" in result.message


class TestOutputContainsValidator:
    """Tests for OutputContainsValidator."""

    def test_output_contains_pattern(self):
        """Test that output containing pattern passes."""
        validator = OutputContainsValidator()
        config = ValidationConfig(
            type=ValidationType.OUTPUT_CONTAINS,
            pattern="success",
        )
        context = {
            "stdout": "Operation completed with success!",
            "stderr": "",
        }

        result = validator.validate(config, context)

        assert result.passed is True

    def test_output_not_contains_pattern(self):
        """Test that output not containing pattern fails."""
        validator = OutputContainsValidator()
        config = ValidationConfig(
            type=ValidationType.OUTPUT_CONTAINS,
            pattern="error",
        )
        context = {
            "stdout": "All good!",
            "stderr": "",
        }

        result = validator.validate(config, context)

        assert result.passed is False

    def test_pattern_in_stderr(self):
        """Test that pattern in stderr is found."""
        validator = OutputContainsValidator()
        config = ValidationConfig(
            type=ValidationType.OUTPUT_CONTAINS,
            pattern="warning",
        )
        context = {
            "stdout": "",
            "stderr": "Some warning message",
        }

        result = validator.validate(config, context)

        assert result.passed is True


class TestJsonContainsValidator:
    """Tests for JsonContainsValidator."""

    def test_json_contains_key_value(self):
        """Test JSON contains key-value pair."""
        validator = JsonContainsValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_CONTAINS,
            expected={"name": "test"},
        )
        context = {
            "stdout": json.dumps({"name": "test", "version": "1.0"}),
        }

        result = validator.validate(config, context)

        assert result.passed is True

    def test_json_missing_key(self):
        """Test JSON missing expected key fails."""
        validator = JsonContainsValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_CONTAINS,
            expected={"missing": "value"},
        )
        context = {
            "stdout": json.dumps({"name": "test"}),
        }

        result = validator.validate(config, context)

        assert result.passed is False

    def test_json_nested_values(self):
        """Test JSON nested value matching."""
        validator = JsonContainsValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_CONTAINS,
            expected={"config": {"enabled": True}},
        )
        context = {
            "stdout": json.dumps({"config": {"enabled": True, "debug": False}}),
        }

        result = validator.validate(config, context)

        assert result.passed is True

    def test_invalid_json_fails(self):
        """Test invalid JSON fails."""
        validator = JsonContainsValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_CONTAINS,
            expected={"any": "value"},
        )
        context = {
            "stdout": "not valid json",
        }

        result = validator.validate(config, context)

        assert result.passed is False
        assert "Invalid JSON" in result.message


class TestJsonFieldValidator:
    """Tests for JsonFieldValidator."""

    def test_json_field_matches(self):
        """Test JSON field value matches."""
        validator = JsonFieldValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_FIELD,
            json_path="name",
            expected="test",
        )
        context = {
            "stdout": json.dumps({"name": "test", "version": "1.0"}),
        }

        result = validator.validate(config, context)

        assert result.passed is True

    def test_nested_json_field(self):
        """Test nested JSON field access."""
        validator = JsonFieldValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_FIELD,
            json_path="config.timeout",
            expected=30,
        )
        context = {
            "stdout": json.dumps({"config": {"timeout": 30}}),
        }

        result = validator.validate(config, context)

        assert result.passed is True

    def test_json_field_mismatch(self):
        """Test JSON field value mismatch fails."""
        validator = JsonFieldValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_FIELD,
            json_path="name",
            expected="expected",
        )
        context = {
            "stdout": json.dumps({"name": "actual"}),
        }

        result = validator.validate(config, context)

        assert result.passed is False

    def test_missing_json_path(self):
        """Test missing JSON path fails."""
        validator = JsonFieldValidator()
        config = ValidationConfig(
            type=ValidationType.JSON_FIELD,
            json_path="missing.path",
            expected="any",
        )
        context = {
            "stdout": json.dumps({"other": "value"}),
        }

        result = validator.validate(config, context)

        assert result.passed is False
        assert "not found" in result.message


class TestPythonSyntaxValidator:
    """Tests for PythonSyntaxValidator."""

    def test_valid_python_passes(self, tmp_path: Path):
        """Test valid Python syntax passes."""
        test_file = tmp_path / "valid.py"
        test_file.write_text(
            """
def hello():
    return "world"
"""
        )

        validator = PythonSyntaxValidator()
        config = ValidationConfig(
            type=ValidationType.PYTHON_SYNTAX,
            path="valid.py",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is True

    def test_invalid_python_fails(self, tmp_path: Path):
        """Test invalid Python syntax fails."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text(
            """
def broken(
    return "missing close paren"
"""
        )

        validator = PythonSyntaxValidator()
        config = ValidationConfig(
            type=ValidationType.PYTHON_SYNTAX,
            path="invalid.py",
        )
        context = {"working_dir": str(tmp_path)}

        result = validator.validate(config, context)

        assert result.passed is False
        assert "syntax error" in result.message.lower()


class TestValidatorRegistry:
    """Tests for ValidatorRegistry."""

    def test_default_registry(self):
        """Test default registry has all validators."""
        registry = get_validator_registry()

        # Check that all validation types are registered
        for vtype in [
            ValidationType.EXIT_CODE,
            ValidationType.FILE_EXISTS,
            ValidationType.FILE_CONTAINS,
            ValidationType.HTTP_HEALTH,
            ValidationType.JSON_CONTAINS,
        ]:
            validator = registry.get(vtype)
            assert validator is not None

    def test_registry_validate(self, tmp_path: Path):
        """Test registry validate method."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        registry = ValidatorRegistry()
        config = ValidationConfig(
            type=ValidationType.FILE_EXISTS,
            path="test.txt",
        )
        context = {"working_dir": str(tmp_path)}

        result = registry.validate(config, context)

        assert result.passed is True

    def test_unknown_validation_type_raises(self):
        """Test that unknown validation type raises."""
        registry = ValidatorRegistry()

        with pytest.raises(ValueError, match="Unknown validation type"):
            registry.get("not_a_real_type")  # type: ignore
