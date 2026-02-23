Module madsci.common.testing.types
==================================
Type definitions for the MADSci E2E testing framework.

Classes
-------

`E2ETestCleanup(**data: Any)`
:   Cleanup actions to perform after test completion.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `commands: list[str]`
    :

    `files: list[str]`
    :

    `model_config`
    :

    `stop_background: bool`
    :

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

`E2ETestRequirements(**data: Any)`
:   Requirements for running an E2E test.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `docker: bool`
    :

    `docker_compose: bool`
    :

    `model_config`
    :

    `packages: list[str]`
    :

    `python: str | None`
    :

    `services: list[str]`
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

`ValidationConfig(**data: Any)`
:   Configuration for a single validation.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `expected: Any`
    :

    `json_path: str | None`
    :

    `model_config`
    :

    `negate: bool`
    :

    `path: str | None`
    :

    `pattern: str | None`
    :

    `timeout: float`
    :

    `type: madsci.common.testing.types.ValidationType`
    :

    `url: str | None`
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

`WaitConfig(**data: Any)`
:   Configuration for waiting on a condition before proceeding.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `path: str | None`
    :

    `poll_interval: float`
    :

    `timeout: float`
    :

    `type: madsci.common.testing.types.ValidationType`
    :

    `url: str | None`
    :
