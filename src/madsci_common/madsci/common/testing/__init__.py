"""
MADSci Testing Framework.

This module provides tools for end-to-end testing, template validation,
and tutorial execution for MADSci components.

Components:
    - E2ETestRunner: Run end-to-end tests from YAML definitions
    - TemplateValidator: Validate MADSci templates
    - TutorialRunner: Execute tutorial steps and validate outcomes
    - Validators: Various validation helpers (file, HTTP, JSON, etc.)
"""

from madsci.common.testing.runner import E2ETestRunner
from madsci.common.testing.template_validator import TemplateValidator
from madsci.common.testing.types import (
    E2ETestDefinition,
    E2ETestResult,
    E2ETestStep,
    StepResult,
    TestMode,
    ValidationResult,
    ValidationType,
)
from madsci.common.testing.validators import (
    CommandValidator,
    ExitCodeValidator,
    FileContainsValidator,
    FileExistsValidator,
    HttpHealthValidator,
    JsonContainsValidator,
    Validator,
    ValidatorRegistry,
)

__all__ = [
    "CommandValidator",
    "E2ETestDefinition",
    "E2ETestResult",
    "E2ETestRunner",
    "E2ETestStep",
    "ExitCodeValidator",
    "FileContainsValidator",
    "FileExistsValidator",
    "HttpHealthValidator",
    "JsonContainsValidator",
    "StepResult",
    "TemplateValidator",
    "TestMode",
    "ValidationResult",
    "ValidationType",
    "Validator",
    "ValidatorRegistry",
]
