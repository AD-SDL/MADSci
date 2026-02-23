"""
Validators for E2E test framework.

Provides various validation types for checking command output,
file existence, HTTP endpoints, JSON content, etc.
"""

import ast
import contextlib
import json
import re
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from madsci.common.testing.types import (
    ValidationConfig,
    ValidationResult,
    ValidationType,
)


class Validator(ABC):
    """Base class for all validators."""

    @property
    @abstractmethod
    def validation_type(self) -> ValidationType:
        """The type of validation this validator performs."""
        ...

    @abstractmethod
    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """
        Perform the validation.

        Args:
            config: The validation configuration
            context: Execution context containing:
                - exit_code: Exit code of the last command
                - stdout: Standard output of the last command
                - stderr: Standard error of the last command
                - working_dir: Current working directory

        Returns:
            ValidationResult with pass/fail status and details
        """
        ...

    def _make_result(
        self,
        passed: bool,
        message: str,
        expected: Any = None,
        actual: Any = None,
        details: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Helper to create a ValidationResult."""
        return ValidationResult(
            validation_type=self.validation_type,
            passed=passed,
            message=message,
            expected=expected,
            actual=actual,
            details=details or {},
        )


class ExitCodeValidator(Validator):
    """Validates command exit code."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for exit code checks."""
        return ValidationType.EXIT_CODE

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the exit code matches the expected value."""
        exit_code = context.get("exit_code")
        expected = config.expected

        if expected is None:
            expected = 0  # Default: expect success

        passed = exit_code == expected
        if config.negate:
            passed = not passed

        return self._make_result(
            passed=passed,
            message=f"Exit code: {exit_code} (expected: {expected})",
            expected=expected,
            actual=exit_code,
        )


class FileExistsValidator(Validator):
    """Validates that a file exists."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for file existence checks."""
        return ValidationType.FILE_EXISTS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the specified file exists."""
        working_dir = Path(context.get("working_dir", "."))
        file_path = working_dir / (config.path or "")

        exists = file_path.exists()
        passed = exists if not config.negate else not exists

        return self._make_result(
            passed=passed,
            message=f"File {'exists' if exists else 'does not exist'}: {config.path}",
            expected="exists" if not config.negate else "does not exist",
            actual="exists" if exists else "does not exist",
            details={"path": str(file_path.absolute())},
        )


class FileNotExistsValidator(Validator):
    """Validates that a file does not exist."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for file non-existence checks."""
        return ValidationType.FILE_NOT_EXISTS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the specified file does not exist."""
        working_dir = Path(context.get("working_dir", "."))
        file_path = working_dir / (config.path or "")

        exists = file_path.exists()
        passed = not exists

        return self._make_result(
            passed=passed,
            message=f"File {'does not exist' if not exists else 'exists'}: {config.path}",
            expected="does not exist",
            actual="exists" if exists else "does not exist",
            details={"path": str(file_path.absolute())},
        )


class DirectoryExistsValidator(Validator):
    """Validates that a directory exists."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for directory existence checks."""
        return ValidationType.DIRECTORY_EXISTS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the specified directory exists."""
        working_dir = Path(context.get("working_dir", "."))
        dir_path = working_dir / (config.path or "")

        exists = dir_path.is_dir()
        passed = exists if not config.negate else not exists

        return self._make_result(
            passed=passed,
            message=f"Directory {'exists' if exists else 'does not exist'}: {config.path}",
            expected="exists" if not config.negate else "does not exist",
            actual="exists" if exists else "does not exist",
            details={"path": str(dir_path.absolute())},
        )


class FileContainsValidator(Validator):
    """Validates that a file contains a pattern."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for file content checks."""
        return ValidationType.FILE_CONTAINS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the file contains the specified pattern."""
        working_dir = Path(context.get("working_dir", "."))
        file_path = working_dir / (config.path or "")

        if not file_path.exists():
            return self._make_result(
                passed=False,
                message=f"File does not exist: {config.path}",
                expected=config.pattern,
                actual=None,
                details={"error": "file_not_found"},
            )

        try:
            content = file_path.read_text()
        except Exception as e:
            return self._make_result(
                passed=False,
                message=f"Could not read file: {e}",
                expected=config.pattern,
                actual=None,
                details={"error": str(e)},
            )

        pattern = config.pattern or ""
        # Check if pattern is a regex or plain string
        try:
            compiled = re.compile(pattern)
            found = compiled.search(content) is not None
        except re.error:
            # Treat as plain string
            found = pattern in content

        passed = found if not config.negate else not found

        return self._make_result(
            passed=passed,
            message=f"Pattern {'found' if found else 'not found'} in {config.path}",
            expected=config.pattern,
            actual="found" if found else "not found",
            details={"path": str(file_path.absolute())},
        )


class OutputContainsValidator(Validator):
    """Validates that command output contains a pattern."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for output content checks."""
        return ValidationType.OUTPUT_CONTAINS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that command output contains the specified pattern."""
        stdout = context.get("stdout", "")
        stderr = context.get("stderr", "")
        combined = stdout + stderr

        pattern = config.pattern or ""
        # Check if pattern is a regex or plain string
        try:
            compiled = re.compile(pattern)
            found = compiled.search(combined) is not None
        except re.error:
            # Treat as plain string
            found = pattern in combined

        passed = found if not config.negate else not found

        return self._make_result(
            passed=passed,
            message=f"Pattern {'found' if found else 'not found'} in output",
            expected=config.pattern,
            actual="found" if found else "not found",
            details={"stdout_preview": stdout[:200] if stdout else ""},
        )


class OutputNotContainsValidator(Validator):
    """Validates that command output does not contain a pattern."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for output exclusion checks."""
        return ValidationType.OUTPUT_NOT_CONTAINS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that command output does not contain the specified pattern."""
        stdout = context.get("stdout", "")
        stderr = context.get("stderr", "")
        combined = stdout + stderr

        pattern = config.pattern or ""
        # Check if pattern is a regex or plain string
        try:
            compiled = re.compile(pattern)
            found = compiled.search(combined) is not None
        except re.error:
            # Treat as plain string
            found = pattern in combined

        passed = not found

        return self._make_result(
            passed=passed,
            message=f"Pattern {'not found' if not found else 'found'} in output",
            expected="not present",
            actual="found" if found else "not found",
        )


class RegexMatchValidator(Validator):
    """Validates that command output matches a regex pattern."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for regex matching."""
        return ValidationType.REGEX_MATCH

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that command output matches the regex pattern."""
        stdout = context.get("stdout", "")
        pattern = config.pattern or ""

        try:
            compiled = re.compile(pattern)
            match = compiled.search(stdout)
            found = match is not None
        except re.error as e:
            return self._make_result(
                passed=False,
                message=f"Invalid regex pattern: {e}",
                expected=config.pattern,
                actual=None,
                details={"error": str(e)},
            )

        passed = found if not config.negate else not found

        return self._make_result(
            passed=passed,
            message=f"Regex {'matched' if found else 'did not match'}",
            expected=config.pattern,
            actual=match.group(0) if match else None,
        )


class HttpHealthValidator(Validator):
    """Validates that an HTTP endpoint is healthy."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for HTTP health checks."""
        return ValidationType.HTTP_HEALTH

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the HTTP endpoint returns a healthy response."""
        del context  # Unused - HTTP validators don't need execution context
        url = config.url
        if not url:
            return self._make_result(
                passed=False,
                message="No URL specified for HTTP health check",
                expected="healthy endpoint",
                actual=None,
            )

        try:
            with httpx.Client(timeout=config.timeout) as client:
                response = client.get(url)
                is_healthy = response.status_code == 200
        except httpx.RequestError as e:
            return self._make_result(
                passed=False,
                message=f"HTTP request failed: {e}",
                expected="status 200",
                actual=f"error: {e}",
                details={"url": url},
            )

        passed = is_healthy if not config.negate else not is_healthy

        return self._make_result(
            passed=passed,
            message=f"HTTP health check: {response.status_code}",
            expected=200,
            actual=response.status_code,
            details={"url": url},
        )


class HttpStatusValidator(Validator):
    """Validates HTTP response status code."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for HTTP status checks."""
        return ValidationType.HTTP_STATUS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the HTTP response has the expected status code."""
        del context  # Unused - HTTP validators don't need execution context
        url = config.url
        expected_status = config.expected or 200

        if not url:
            return self._make_result(
                passed=False,
                message="No URL specified for HTTP status check",
                expected=expected_status,
                actual=None,
            )

        try:
            with httpx.Client(timeout=config.timeout) as client:
                response = client.get(url)
                status_code = response.status_code
        except httpx.RequestError as e:
            return self._make_result(
                passed=False,
                message=f"HTTP request failed: {e}",
                expected=expected_status,
                actual=f"error: {e}",
                details={"url": url},
            )

        passed = status_code == expected_status
        if config.negate:
            passed = not passed

        return self._make_result(
            passed=passed,
            message=f"HTTP status: {status_code} (expected: {expected_status})",
            expected=expected_status,
            actual=status_code,
            details={"url": url},
        )


class JsonContainsValidator(Validator):
    """Validates that JSON output contains expected values."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for JSON content checks."""
        return ValidationType.JSON_CONTAINS

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that JSON output contains the expected values."""
        stdout = context.get("stdout", "")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            return self._make_result(
                passed=False,
                message=f"Invalid JSON: {e}",
                expected=config.expected,
                actual=stdout[:100] if stdout else None,
                details={"error": str(e)},
            )

        expected = config.expected
        if isinstance(expected, str):
            with contextlib.suppress(json.JSONDecodeError):
                expected = json.loads(expected)

        # Check if expected is a subset of data
        if isinstance(expected, dict):
            passed = self._dict_contains(data, expected)
        else:
            passed = expected in str(data)

        if config.negate:
            passed = not passed

        return self._make_result(
            passed=passed,
            message=f"JSON {'contains' if passed else 'does not contain'} expected values",
            expected=expected,
            actual=data,
        )

    def _dict_contains(self, data: dict, subset: dict) -> bool:
        """Check if data contains all key-value pairs from subset."""
        for key, value in subset.items():
            if key not in data:
                return False
            if isinstance(value, dict) and isinstance(data[key], dict):
                if not self._dict_contains(data[key], value):
                    return False
            elif data[key] != value:
                return False
        return True


class JsonFieldValidator(Validator):
    """Validates a specific field in JSON output."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for JSON field checks."""
        return ValidationType.JSON_FIELD

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that a specific JSON field has the expected value."""
        stdout = context.get("stdout", "")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            return self._make_result(
                passed=False,
                message=f"Invalid JSON: {e}",
                expected=config.expected,
                actual=None,
                details={"error": str(e)},
            )

        # Navigate to the field using dot notation (e.g., "user.name")
        json_path = config.json_path or config.path
        if not json_path:
            return self._make_result(
                passed=False,
                message="No JSON path specified",
                expected=config.expected,
                actual=None,
            )

        try:
            actual = self._get_nested_value(data, json_path)
        except (KeyError, IndexError, TypeError) as e:
            return self._make_result(
                passed=False,
                message=f"JSON path '{json_path}' not found: {e}",
                expected=config.expected,
                actual=None,
                details={
                    "available_keys": list(data.keys())
                    if isinstance(data, dict)
                    else None
                },
            )

        passed = actual == config.expected
        if config.negate:
            passed = not passed

        return self._make_result(
            passed=passed,
            message=f"JSON field '{json_path}': {actual}",
            expected=config.expected,
            actual=actual,
        )

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Get a nested value using dot notation."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
            else:
                raise TypeError(f"Cannot navigate into {type(current)}")
        return current


class PythonSyntaxValidator(Validator):
    """Validates that a Python file has valid syntax."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for Python syntax checks."""
        return ValidationType.PYTHON_SYNTAX

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the Python file has valid syntax."""
        working_dir = Path(context.get("working_dir", "."))
        file_path = working_dir / (config.path or "")

        if not file_path.exists():
            return self._make_result(
                passed=False,
                message=f"File does not exist: {config.path}",
                expected="valid Python syntax",
                actual=None,
            )

        try:
            source = file_path.read_text()
            ast.parse(source)
            passed = True
            message = f"Valid Python syntax: {config.path}"
            error = None
        except SyntaxError as e:
            passed = False
            message = f"Python syntax error in {config.path}: {e}"
            error = str(e)

        return self._make_result(
            passed=passed,
            message=message,
            expected="valid Python syntax",
            actual="valid" if passed else error,
            details={"path": str(file_path.absolute())},
        )


class RuffCheckValidator(Validator):
    """Validates that a file/directory passes ruff linting."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for ruff linting checks."""
        return ValidationType.RUFF_CHECK

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate that the file/directory passes ruff linting."""
        working_dir = Path(context.get("working_dir", "."))
        target = working_dir / (config.path or "")

        if not target.exists():
            return self._make_result(
                passed=False,
                message=f"Target does not exist: {config.path}",
                expected="passes ruff check",
                actual=None,
            )

        try:
            result = subprocess.run(  # noqa: S603
                ["ruff", "check", str(target)],  # noqa: S607
                check=False,
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=30,
            )
            passed = result.returncode == 0
            output = result.stdout + result.stderr
        except FileNotFoundError:
            return self._make_result(
                passed=False,
                message="ruff is not installed",
                expected="passes ruff check",
                actual="ruff not found",
            )
        except subprocess.TimeoutExpired:
            return self._make_result(
                passed=False,
                message="ruff check timed out",
                expected="passes ruff check",
                actual="timeout",
            )

        return self._make_result(
            passed=passed,
            message=f"ruff check {'passed' if passed else 'failed'}: {config.path}",
            expected="no lint errors",
            actual="passed" if passed else output[:500],
            details={"path": str(target.absolute())},
        )


class CommandValidator(Validator):
    """Runs a command and checks its exit code as validation."""

    @property
    def validation_type(self) -> ValidationType:
        """Return the validation type for command execution checks."""
        return ValidationType.EXIT_CODE

    def __init__(self, command: str) -> None:
        """Initialize the validator with the command to run."""
        self.command = command

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Validate by running a command and checking its exit code."""
        working_dir = Path(context.get("working_dir", "."))
        expected = config.expected if config.expected is not None else 0

        try:
            result = subprocess.run(  # noqa: S602
                self.command,
                check=False,
                shell=True,  # Required for running user-provided shell commands
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=config.timeout,
            )
            passed = result.returncode == expected
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            return self._make_result(
                passed=False,
                message=f"Command timed out: {self.command}",
                expected=expected,
                actual="timeout",
            )

        if config.negate:
            passed = not passed

        return self._make_result(
            passed=passed,
            message=f"Command '{self.command}' exited with {exit_code}",
            expected=expected,
            actual=exit_code,
        )


class ValidatorRegistry:
    """Registry of available validators."""

    def __init__(self) -> None:
        """Initialize the validator registry with default validators."""
        self._validators: dict[ValidationType, type[Validator]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all default validators."""
        self.register(ValidationType.EXIT_CODE, ExitCodeValidator)
        self.register(ValidationType.FILE_EXISTS, FileExistsValidator)
        self.register(ValidationType.FILE_NOT_EXISTS, FileNotExistsValidator)
        self.register(ValidationType.FILE_CONTAINS, FileContainsValidator)
        self.register(ValidationType.DIRECTORY_EXISTS, DirectoryExistsValidator)
        self.register(ValidationType.OUTPUT_CONTAINS, OutputContainsValidator)
        self.register(ValidationType.OUTPUT_NOT_CONTAINS, OutputNotContainsValidator)
        self.register(ValidationType.REGEX_MATCH, RegexMatchValidator)
        self.register(ValidationType.HTTP_HEALTH, HttpHealthValidator)
        self.register(ValidationType.HTTP_STATUS, HttpStatusValidator)
        self.register(ValidationType.JSON_CONTAINS, JsonContainsValidator)
        self.register(ValidationType.JSON_FIELD, JsonFieldValidator)
        self.register(ValidationType.PYTHON_SYNTAX, PythonSyntaxValidator)
        self.register(ValidationType.RUFF_CHECK, RuffCheckValidator)

    def register(
        self, validation_type: ValidationType, validator_class: type[Validator]
    ) -> None:
        """Register a validator class for a validation type."""
        self._validators[validation_type] = validator_class

    def get(self, validation_type: ValidationType) -> Validator:
        """Get a validator instance for a validation type."""
        if validation_type not in self._validators:
            raise ValueError(f"Unknown validation type: {validation_type}")
        return self._validators[validation_type]()

    def validate(
        self,
        config: ValidationConfig,
        context: dict[str, Any],
    ) -> ValidationResult:
        """Perform a validation using the appropriate validator."""
        validator = self.get(config.type)
        return validator.validate(config, context)


# Global registry instance
_registry_lock = threading.Lock()
_default_registry: ValidatorRegistry | None = None


def get_validator_registry() -> ValidatorRegistry:
    """Get the default validator registry."""
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = ValidatorRegistry()
    return _default_registry


def wait_for_condition(
    config: ValidationConfig,
    context: dict[str, Any],
    timeout: float = 60.0,
    poll_interval: float = 1.0,
) -> bool:
    """
    Wait for a validation condition to be met.

    Args:
        config: Validation configuration (type and parameters)
        context: Execution context
        timeout: Maximum time to wait
        poll_interval: Time between checks

    Returns:
        True if condition was met, False if timeout
    """
    registry = get_validator_registry()
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = registry.validate(config, context)
            if result.passed:
                return True
        except Exception:  # noqa: S110
            pass  # Ignore exceptions during polling - condition not yet met
        time.sleep(poll_interval)

    return False
