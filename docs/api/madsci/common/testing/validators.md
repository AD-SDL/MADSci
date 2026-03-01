Module madsci.common.testing.validators
=======================================
Validators for E2E test framework.

Provides various validation types for checking command output,
file existence, HTTP endpoints, JSON content, etc.

Functions
---------

`get_validator_registry() ‑> madsci.common.testing.validators.ValidatorRegistry`
:   Get the default validator registry.

`wait_for_condition(config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any], timeout: float = 60.0, poll_interval: float = 1.0) ‑> bool`
:   Wait for a validation condition to be met.
    
    Args:
        config: Validation configuration (type and parameters)
        context: Execution context
        timeout: Maximum time to wait
        poll_interval: Time between checks
    
    Returns:
        True if condition was met, False if timeout

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

`DirectoryExistsValidator()`
:   Validates that a directory exists.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for directory existence checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the specified directory exists.

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

`FileNotExistsValidator()`
:   Validates that a file does not exist.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for file non-existence checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the specified file does not exist.

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

`HttpStatusValidator()`
:   Validates HTTP response status code.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for HTTP status checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the HTTP response has the expected status code.

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

`JsonFieldValidator()`
:   Validates a specific field in JSON output.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for JSON field checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that a specific JSON field has the expected value.

`OutputContainsValidator()`
:   Validates that command output contains a pattern.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for output content checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that command output contains the specified pattern.

`OutputNotContainsValidator()`
:   Validates that command output does not contain a pattern.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for output exclusion checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that command output does not contain the specified pattern.

`PythonSyntaxValidator()`
:   Validates that a Python file has valid syntax.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for Python syntax checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the Python file has valid syntax.

`RegexMatchValidator()`
:   Validates that command output matches a regex pattern.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for regex matching.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that command output matches the regex pattern.

`RuffCheckValidator()`
:   Validates that a file/directory passes ruff linting.

    ### Ancestors (in MRO)

    * madsci.common.testing.validators.Validator
    * abc.ABC

    ### Instance variables

    `validation_type: madsci.common.testing.types.ValidationType`
    :   Return the validation type for ruff linting checks.

    ### Methods

    `validate(self, config: madsci.common.testing.types.ValidationConfig, context: dict[str, typing.Any]) ‑> madsci.common.testing.types.ValidationResult`
    :   Validate that the file/directory passes ruff linting.

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