"""
Type definitions for the MADSci E2E testing framework.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field


class TestMode(str, Enum):
    """Execution mode for E2E tests."""

    PYTHON = "python"  # Pure Python mode, no Docker
    DOCKER = "docker"  # Docker Compose mode
    HYBRID = "hybrid"  # Some services in Docker, some local


class ValidationType(str, Enum):
    """Types of validations that can be performed."""

    EXIT_CODE = "exit_code"
    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    FILE_NOT_EXISTS = "file_not_exists"
    HTTP_HEALTH = "http_health"
    HTTP_STATUS = "http_status"
    JSON_CONTAINS = "json_contains"
    JSON_FIELD = "json_field"
    REGEX_MATCH = "regex_match"
    OUTPUT_CONTAINS = "output_contains"
    OUTPUT_NOT_CONTAINS = "output_not_contains"
    DIRECTORY_EXISTS = "directory_exists"
    PYTHON_SYNTAX = "python_syntax"
    RUFF_CHECK = "ruff_check"


class ValidationConfig(MadsciBaseModel):
    """Configuration for a single validation."""

    type: ValidationType = Field(
        description="The type of validation to perform",
    )
    # Common fields
    path: str | None = Field(
        default=None,
        description="File or directory path for file-related validations",
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern or search string",
    )
    expected: Any = Field(
        default=None,
        description="Expected value (for exit_code, http_status, json_field, etc.)",
    )
    url: str | None = Field(
        default=None,
        description="URL for HTTP-related validations",
    )
    timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for HTTP requests",
    )
    json_path: str | None = Field(
        default=None,
        description="JSON path expression for json_field validation",
    )
    negate: bool = Field(
        default=False,
        description="If True, the validation passes when the condition is NOT met",
    )


class WaitConfig(MadsciBaseModel):
    """Configuration for waiting on a condition before proceeding."""

    type: ValidationType = Field(
        description="The type of condition to wait for",
    )
    url: str | None = Field(
        default=None,
        description="URL for HTTP-related waits",
    )
    timeout: float = Field(
        default=60.0,
        description="Maximum time to wait in seconds",
    )
    poll_interval: float = Field(
        default=1.0,
        description="Time between checks in seconds",
    )
    path: str | None = Field(
        default=None,
        description="File path for file-related waits",
    )


class E2ETestStep(MadsciBaseModel):
    """A single step in an E2E test."""

    name: str = Field(
        description="Human-readable name for this step",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of what this step does",
    )
    command: str | None = Field(
        default=None,
        description="Shell command to execute",
    )
    python_code: str | None = Field(
        default=None,
        description="Python code to execute instead of shell command",
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for the command (relative to test root)",
    )
    background: bool = Field(
        default=False,
        description="Run this command in the background",
    )
    wait_for: WaitConfig | None = Field(
        default=None,
        description="Condition to wait for after starting a background command",
    )
    validations: list[ValidationConfig] = Field(
        default_factory=list,
        description="List of validations to perform after the step",
    )
    timeout: float = Field(
        default=300.0,
        description="Maximum time for this step to complete in seconds",
    )
    continue_on_error: bool = Field(
        default=False,
        description="Continue to next step even if this step fails",
    )
    skip_if: str | None = Field(
        default=None,
        description="Python expression that if True, skips this step",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables for this step",
    )


class E2ETestRequirements(MadsciBaseModel):
    """Requirements for running an E2E test."""

    python: str | None = Field(
        default=None,
        description="Python version requirement (e.g., '>=3.10')",
    )
    docker: bool = Field(
        default=False,
        description="Whether Docker is required",
    )
    docker_compose: bool = Field(
        default=False,
        description="Whether Docker Compose is required",
    )
    packages: list[str] = Field(
        default_factory=list,
        description="Required Python packages",
    )
    services: list[str] = Field(
        default_factory=list,
        description="Required running services (e.g., ['mongodb', 'redis'])",
    )


class E2ETestCleanup(MadsciBaseModel):
    """Cleanup actions to perform after test completion."""

    commands: list[str] = Field(
        default_factory=list,
        description="Shell commands to run for cleanup",
    )
    files: list[str] = Field(
        default_factory=list,
        description="Files/directories to remove",
    )
    stop_background: bool = Field(
        default=True,
        description="Stop all background processes started during the test",
    )


class E2ETestDefinition(MadsciBaseModel):
    """Complete definition of an E2E test."""

    name: str = Field(
        description="Name of the test",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of what this test validates",
    )
    version: str = Field(
        default="1.0",
        description="Version of this test definition",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering tests (e.g., ['docker', 'quick', 'tutorial'])",
    )
    requirements: E2ETestRequirements = Field(
        default_factory=E2ETestRequirements,
        description="Requirements for running this test",
    )
    mode: TestMode = Field(
        default=TestMode.PYTHON,
        description="Execution mode for this test",
    )
    setup: list[E2ETestStep] = Field(
        default_factory=list,
        description="Setup steps to run before the main test",
    )
    steps: list[E2ETestStep] = Field(
        default_factory=list,
        description="Main test steps",
    )
    cleanup: E2ETestCleanup = Field(
        default_factory=E2ETestCleanup,
        description="Cleanup actions after test completion",
    )
    timeout: float = Field(
        default=600.0,
        description="Total timeout for the entire test in seconds",
    )


class ValidationResult(MadsciBaseModel):
    """Result of a single validation."""

    validation_type: ValidationType = Field(
        description="Type of validation performed",
    )
    passed: bool = Field(
        description="Whether the validation passed",
    )
    message: str = Field(
        description="Human-readable result message",
    )
    expected: Any = Field(
        default=None,
        description="Expected value",
    )
    actual: Any = Field(
        default=None,
        description="Actual value observed",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details about the validation",
    )


class StepResult(MadsciBaseModel):
    """Result of executing a single test step."""

    step_name: str = Field(
        description="Name of the step",
    )
    passed: bool = Field(
        description="Whether the step passed overall",
    )
    skipped: bool = Field(
        default=False,
        description="Whether the step was skipped",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason the step was skipped",
    )
    exit_code: int | None = Field(
        default=None,
        description="Exit code of the command (if applicable)",
    )
    stdout: str = Field(
        default="",
        description="Standard output from the command",
    )
    stderr: str = Field(
        default="",
        description="Standard error from the command",
    )
    duration_seconds: float = Field(
        description="Time taken to execute this step",
    )
    started_at: datetime = Field(
        description="When the step started",
    )
    completed_at: datetime = Field(
        description="When the step completed",
    )
    validation_results: list[ValidationResult] = Field(
        default_factory=list,
        description="Results of all validations for this step",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the step failed",
    )


class E2ETestResult(MadsciBaseModel):
    """Complete result of an E2E test run."""

    test_name: str = Field(
        description="Name of the test",
    )
    passed: bool = Field(
        description="Whether the test passed overall",
    )
    mode: TestMode = Field(
        description="Execution mode used",
    )
    started_at: datetime = Field(
        description="When the test started",
    )
    completed_at: datetime = Field(
        description="When the test completed",
    )
    duration_seconds: float = Field(
        description="Total duration of the test",
    )
    setup_results: list[StepResult] = Field(
        default_factory=list,
        description="Results of setup steps",
    )
    step_results: list[StepResult] = Field(
        default_factory=list,
        description="Results of main test steps",
    )
    cleanup_executed: bool = Field(
        default=False,
        description="Whether cleanup was executed",
    )
    error: str | None = Field(
        default=None,
        description="Overall error message if the test failed",
    )
    logs_path: Path | None = Field(
        default=None,
        description="Path to captured logs",
    )

    @property
    def steps_passed(self) -> int:
        """Count of passed steps."""
        return sum(1 for r in self.step_results if r.passed)

    @property
    def steps_failed(self) -> int:
        """Count of failed steps."""
        return sum(1 for r in self.step_results if not r.passed and not r.skipped)

    @property
    def steps_skipped(self) -> int:
        """Count of skipped steps."""
        return sum(1 for r in self.step_results if r.skipped)

    def summary(self) -> str:
        """Generate a human-readable summary of the test result."""
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"Test: {self.test_name}",
            f"Status: {status}",
            f"Duration: {self.duration_seconds:.2f}s",
            f"Steps: {self.steps_passed} passed, {self.steps_failed} failed, {self.steps_skipped} skipped",
        ]
        if self.error:
            lines.append(f"Error: {self.error}")
        return "\n".join(lines)
