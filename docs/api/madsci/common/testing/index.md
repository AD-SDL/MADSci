Module madsci.common.testing
============================
MADSci Testing Framework.

This module provides tools for end-to-end testing, template validation,
and tutorial execution for MADSci components.

Components:
    - E2ETestRunner: Run end-to-end tests from YAML definitions
    - TemplateValidator: Validate MADSci templates
    - TutorialRunner: Execute tutorial steps and validate outcomes
    - Validators: Various validation helpers (file, HTTP, JSON, etc.)

Sub-modules
-----------
* madsci.common.testing.runner
* madsci.common.testing.template_validator
* madsci.common.testing.types
* madsci.common.testing.validators

Classes
-------

`CommandValidator(command: str)`
:   Runs a command and checks its exit code as validation.
    
    Initialize the validator with the command to run.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for command execution checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate by running a command and checking its exit code.

`E2ETestDefinition(**data: Any)`
:   Complete definition of an E2E test.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `cleanup: madsci.common.testing.types.E2ETestCleanup`
    :

    `description: str | None`
    :

    `mode: madsci.common.testing.types.TestMode`
    :

    `model_config`
    :

    `name: str`
    :

    `requirements: madsci.common.testing.types.E2ETestRequirements`
    :

    `setup: list[madsci.common.testing.types.E2ETestStep]`
    :

    `steps: list[madsci.common.testing.types.E2ETestStep]`
    :

    `tags: list[str]`
    :

    `timeout: float`
    :

    `version: str`
    :

`E2ETestResult(**data: Any)`
:   Complete result of an E2E test run.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `cleanup_executed: bool`
    :

    `completed_at: datetime.datetime`
    :

    `duration_seconds: float`
    :

    `error: str | None`
    :

    `logs_path: pathlib.Path | None`
    :

    `mode: madsci.common.testing.types.TestMode`
    :

    `model_config`
    :

    `passed: bool`
    :

    `setup_results: list[madsci.common.testing.types.StepResult]`
    :

    `started_at: datetime.datetime`
    :

    `step_results: list[madsci.common.testing.types.StepResult]`
    :

    `test_name: str`
    :

    ### Instance variables

    `steps_failed: int`
    :   Count of failed steps.

    `steps_passed: int`
    :   Count of passed steps.

    `steps_skipped: int`
    :   Count of skipped steps.

    ### Methods

    `summary(self) ‑> str`
    :   Generate a human-readable summary of the test result.

`E2ETestRunner(working_dir: pathlib.Path | None = None, mode: madsci.common.testing.types.TestMode | None = None, console: rich.console.Console | None = None, verbose: bool = False, capture_logs: bool = True)`
:   Executes E2E test definitions.
    
    Supports both pure Python mode (no Docker) and Docker mode.
    
    Initialize the test runner.
    
    Args:
        working_dir: Base directory for test execution. If None, uses a temp dir.
        mode: Test execution mode (PYTHON, DOCKER, HYBRID). If None, uses test's mode.
        console: Rich console for output. If None, creates one.
        verbose: If True, print verbose output.
        capture_logs: If True, capture all logs to a file.

    ### Methods

    `run(self, test_definition: madsci.common.testing.types.E2ETestDefinition, env: dict[str, str] | None = None) ‑> madsci.common.testing.types.E2ETestResult`
    :   Run an E2E test.
        
        Args:
            test_definition: The test to run
            env: Additional environment variables
        
        Returns:
            E2ETestResult with the test outcome

    `run_from_yaml(self, yaml_path: pathlib.Path, **kwargs: Any) ‑> madsci.common.testing.types.E2ETestResult`
    :   Load and run a test from a YAML file.
        
        Args:
            yaml_path: Path to the test definition YAML file
            **kwargs: Additional arguments passed to run()
        
        Returns:
            E2ETestResult with the test outcome

`E2ETestStep(**data: Any)`
:   A single step in an E2E test.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `background: bool`
    :

    `command: str | None`
    :

    `continue_on_error: bool`
    :

    `description: str | None`
    :

    `env: dict[str, str]`
    :

    `model_config`
    :

    `name: str`
    :

    `python_code: str | None`
    :

    `skip_if: str | None`
    :

    `timeout: float`
    :

    `validations: list[madsci.common.testing.types.ValidationConfig]`
    :

    `wait_for: madsci.common.testing.types.WaitConfig | None`
    :

    `working_dir: str | None`
    :

`ExitCodeValidator()`
:   Validates command exit code.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for exit code checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the exit code matches the expected value.

`FileContainsValidator()`
:   Validates that a file contains a pattern.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for file content checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the file contains the specified pattern.

`FileExistsValidator()`
:   Validates that a file exists.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for file existence checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the specified file exists.

`HttpHealthValidator()`
:   Validates that an HTTP endpoint is healthy.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for HTTP health checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the HTTP endpoint returns a healthy response.

`JsonContainsValidator()`
:   Validates that JSON output contains expected values.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for JSON content checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that JSON output contains the expected values.

`StepResult(**data: Any)`
:   Result of executing a single test step.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `completed_at: datetime.datetime`
    :

    `duration_seconds: float`
    :

    `error: str | None`
    :

    `exit_code: int | None`
    :

    `model_config`
    :

    `passed: bool`
    :

    `skip_reason: str | None`
    :

    `skipped: bool`
    :

    `started_at: datetime.datetime`
    :

    `stderr: str`
    :

    `stdout: str`
    :

    `step_name: str`
    :

    `validation_results: list[madsci.common.testing.types.ValidationResult]`
    :

`TemplateValidator(console: rich.console.Console | None = None, verbose: bool = False)`
:   Validates MADSci templates by instantiating them and checking output.
    
    Performs the following validations:
    - Template renders without errors
    - Generated Python files have valid syntax
    - Generated code passes ruff linting
    - (Optional) Generated code can be imported
    
    Initialize the template validator.
    
    Args:
        console: Rich console for output. If None, creates one.
        verbose: If True, print verbose output.

    ### Methods

    `print_results(self, results: list[madsci.common.testing.template_validator.TemplateValidationResult]) ‑> None`
    :   Print validation results in a formatted table.

    `validate_all_templates(self, templates_dir: pathlib.Path, **kwargs: Any) ‑> list[madsci.common.testing.template_validator.TemplateValidationResult]`
    :   Validate all templates in a directory.
        
        Args:
            templates_dir: Directory containing template subdirectories
            **kwargs: Additional arguments passed to validate_template
        
        Returns:
            List of validation results

    `validate_template(self, template_path: pathlib.Path, test_values: dict[str, typing.Any] | None = None, output_dir: pathlib.Path | None = None, check_ruff: bool = True, check_imports: bool = False) ‑> madsci.common.testing.template_validator.TemplateValidationResult`
    :   Validate a template by instantiating it with test values.
        
        Args:
            template_path: Path to the template directory (containing template.yaml)
            test_values: Values to use for template parameters. If None, uses defaults.
            output_dir: Directory for generated output. If None, uses temp dir.
            check_ruff: If True, run ruff check on generated code.
            check_imports: If True, attempt to import generated Python modules.
        
        Returns:
            TemplateValidationResult with details of the validation.

`TestMode(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Execution mode for E2E tests.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `DOCKER`
    :

    `HYBRID`
    :

    `PYTHON`
    :

`ValidationResult(**data: Any)`
:   Result of a single validation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `actual: Any`
    :

    `details: dict[str, typing.Any]`
    :

    `expected: Any`
    :

    `message: str`
    :

    `model_config`
    :

    `passed: bool`
    :

    `validation_type: madsci.common.testing.types.ValidationType`
    :

`ValidationType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Types of validations that can be performed.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `DIRECTORY_EXISTS`
    :

    `EXIT_CODE`
    :

    `FILE_CONTAINS`
    :

    `FILE_EXISTS`
    :

    `FILE_NOT_EXISTS`
    :

    `HTTP_HEALTH`
    :

    `HTTP_STATUS`
    :

    `JSON_CONTAINS`
    :

    `JSON_FIELD`
    :

    `OUTPUT_CONTAINS`
    :

    `OUTPUT_NOT_CONTAINS`
    :

    `PYTHON_SYNTAX`
    :

    `REGEX_MATCH`
    :

    `RUFF_CHECK`
    :

`Validator()`
:   Base class for all validators.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.testing.validators.CommandValidator
    * madsci.common.testing.validators.DirectoryExistsValidator
    * madsci.common.testing.validators.ExitCodeValidator
    * madsci.common.testing.validators.FileContainsValidator
    * madsci.common.testing.validators.FileExistsValidator
    * madsci.common.testing.validators.FileNotExistsValidator
    * madsci.common.testing.validators.HttpHealthValidator
    * madsci.common.testing.validators.HttpStatusValidator
    * madsci.common.testing.validators.JsonContainsValidator
    * madsci.common.testing.validators.JsonFieldValidator
    * madsci.common.testing.validators.OutputContainsValidator
    * madsci.common.testing.validators.OutputNotContainsValidator
    * madsci.common.testing.validators.PythonSyntaxValidator
    * madsci.common.testing.validators.RegexMatchValidator
    * madsci.common.testing.validators.RuffCheckValidator

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   The type of validation this validator performs.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Perform the validation.
        
        Args:
            config: The validation configuration
            context: Execution context containing:
                - exit_code: Exit code of the last command
                - stdout: Standard output of the last command
                - stderr: Standard error of the last command
                - working_dir: Current working directory
        
        Returns:
            ValidationResult with pass/fail status and details

`ValidatorRegistry()`
:   Registry of available validators.
    
    Initialize the validator registry with default validators.

    ### Methods

    `get(self, validation_type: madsci.common.testing.types.ValidationType) ‑> madsci.common.testing.validators.Validator`
    :   Get a validator instance for a validation type.

    `register(self, validation_type: madsci.common.testing.types.ValidationType, validator_class: type[madsci.common.testing.validators.Validator]) ‑> None`
    :   Register a validator class for a validation type.

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Perform a validation using the appropriate validator.