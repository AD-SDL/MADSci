Module madsci.common.types.action_types
=======================================
Types for MADSci Actions.

Functions
---------

`create_action_request_model(action_function: Any) ‑> type[madsci.common.types.action_types.RestActionRequest]`
:   Create a dynamic action request model that extends RestActionRequest with typed args.

`create_action_result_model(action_function: Any) ‑> type[madsci.common.types.action_types.ActionResult]`
:   Create a dynamic ActionResult model based on function return type.

`create_dynamic_model(action_name: str, json_result_type: Optional[type] = None, action_function: Optional[Any] = None) ‑> type[madsci.common.types.action_types.RestActionResult]`
:   Create a dynamic RestActionResult model for a specific action.
    
    Args:
        action_name: Name of the action
        json_result_type: Type to use for the json_result field (None for file-only actions)
        action_function: Optional action function for extracting additional metadata
    
    Returns:
        Dynamic RestActionResult subclass with properly typed json_result field

`extract_file_parameters(action_function: Any) ‑> dict[str, dict[str, typing.Any]]`
:   Extract file parameter information from action function signature.
    
    Returns:
        Dictionary mapping parameter names to their metadata including:
        - required: bool indicating if the parameter is required
        - description: str describing the parameter
        - annotation: type annotation of the parameter
        - is_list: bool indicating if this is a list[Path] parameter

`extract_file_result_definitions(action_function: Any) ‑> dict[str, str]`
:   Extract file result information from action function metadata.
    
    Returns:
        Dictionary mapping result labels to their descriptions for file results

Classes
-------

`ActionCancelled(**data: Any)`
:   Response from an action that was cancelled.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.CANCELLED: 'cancelled'>]`
    :

`ActionDatapoints(**data: Any)`
:   Datapoint IDs returned from an action.
    
    This class stores only ULID strings (datapoint IDs) for efficient storage and workflow management.
    Full DataPoint objects can be fetched just-in-time when needed using the data client.
    
    Values can be:
    - str: Single datapoint ID (ULID)
    - list[str]: List of datapoint IDs (ULIDs)
    
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

    ### Static methods

    `ensure_datapoints_are_strings(v: Any) ‑> Any`
    :   Convert DataPoint objects to ULID strings, support both single items and lists

`ActionDefinition(**data: Any)`
:   Definition of an action.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `accepts_var_args: bool`
    :

    `accepts_var_kwargs: bool`
    :

    `args: dict[str, madsci.common.types.action_types.ArgumentDefinition] | list[madsci.common.types.action_types.ArgumentDefinition]`
    :

    `asynchronous: bool`
    :

    `blocking: bool`
    :

    `description: str`
    :

    `files: dict[str, madsci.common.types.action_types.FileArgumentDefinition] | list[madsci.common.types.action_types.FileArgumentDefinition]`
    :

    `locations: dict[str, madsci.common.types.action_types.LocationArgumentDefinition] | list[madsci.common.types.action_types.LocationArgumentDefinition]`
    :

    `model_config`
    :

    `name: str`
    :

    `results: dict[str, madsci.common.types.action_types.FileActionResultDefinition | madsci.common.types.action_types.DatapointActionResultDefinition | madsci.common.types.action_types.JSONActionResultDefinition] | list[madsci.common.types.action_types.FileActionResultDefinition | madsci.common.types.action_types.DatapointActionResultDefinition | madsci.common.types.action_types.JSONActionResultDefinition]`
    :

    `var_args_schema: dict[str, typing.Any] | None`
    :

    `var_kwargs_schema: dict[str, typing.Any] | None`
    :

    ### Static methods

    `ensure_args_are_dict(v: Any) ‑> Any`
    :   Ensure that the args are a dictionary

    `ensure_files_are_dict(v: Any) ‑> Any`
    :   Ensure that the files are a dictionary

    `ensure_locations_are_dict(v: Any) ‑> Any`
    :   Ensure that the locations are a dictionary

    `ensure_results_are_dict(v: Any) ‑> Any`
    :   Ensure that the results are a dictionary

    `none_to_empty_str(v: Any) ‑> str`
    :   Convert None to empty string

    ### Methods

    `ensure_name_uniqueness(self) ‑> Any`
    :   Ensure that the names of the arguments and files are unique

`ActionFailed(**data: Any)`
:   Response from an action that failed.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.FAILED: 'failed'>]`
    :

`ActionFiles(**data: Any)`
:   Files returned from an action
    
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

    ### Static methods

    `ensure_files_are_path(v: Any) ‑> Any`
    :   Ensure that the files are Path

`ActionJSON(**data: Any)`
:   Data returned from an action as JSON
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.workcell_manager.workcell_actions.WorkcellTransferJSON

    ### Class variables

    `model_config`
    :

    `type: Literal['json']`
    :

`ActionNotReady(**data: Any)`
:   Response from an action that is not ready to be run.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.NOT_READY: 'not_ready'>]`
    :

`ActionNotStarted(**data: Any)`
:   Response from an action that has not started.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.NOT_STARTED: 'not_started'>]`
    :

`ActionPaused(**data: Any)`
:   Response from an action that is paused.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.PAUSED: 'paused'>]`
    :

`ActionRequest(**data: Any)`
:   Request to perform an action on a node
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `action_id: str`
    :

    `action_name: str`
    :   Name of the action to perform

    `args: dict[str, typing.Any] | None`
    :   Arguments for the action

    `files: dict[str, pathlib.Path | list[pathlib.Path]]`
    :   Files sent along with the action

    `model_config`
    :

    `var_args: list[typing.Any] | None`
    :   Additional positional arguments for the action

    `var_kwargs: dict[str, typing.Any] | None`
    :   Additional keyword arguments for the action

    ### Methods

    `cancelled(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionCancelled`
    :   Create an ActionCancelled response

    `failed(self, errors: Union[Error, list[Error], str] = [], json_result: Optional[dict[str, Any]] = None, files: Optional[dict[str, Path]] = None) ‑> madsci.common.types.action_types.ActionFailed`
    :   Create an ActionFailed response

    `not_ready(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionNotReady`
    :   Create an ActionNotReady response

    `not_started(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Create an ActionResult response

    `paused(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Create an ActionResult response

    `running(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionRunning`
    :   Create an ActionRunning response

    `succeeded(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionSucceeded`
    :   Create an ActionSucceeded response

    `unknown(self, errors: Union[Error, list[Error], str] = [], json_result: Any = None, files: Optional[Union[Path, ActionFiles]] = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Create an ActionResult response

`ActionResult(**data: Any)`
:   Result of an action.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.action_types.ActionCancelled
    * madsci.common.types.action_types.ActionFailed
    * madsci.common.types.action_types.ActionNotReady
    * madsci.common.types.action_types.ActionNotStarted
    * madsci.common.types.action_types.ActionPaused
    * madsci.common.types.action_types.ActionRunning
    * madsci.common.types.action_types.ActionSucceeded
    * madsci.common.types.action_types.ActionUnknown
    * madsci.common.types.action_types.RestActionResult

    ### Class variables

    `action_id: str`
    :

    `datapoints: madsci.common.types.action_types.ActionDatapoints | None`
    :

    `errors: list[madsci.common.types.base_types.Error]`
    :

    `files: pathlib.Path | madsci.common.types.action_types.ActionFiles | None`
    :

    `history_created_at: datetime.datetime | None`
    :

    `json_result: Any`
    :

    `model_config`
    :

    `status: madsci.common.types.action_types.ActionStatus`
    :

    ### Static methods

    `ensure_list_of_errors(v: Any) ‑> Any`
    :   Ensure that errors is a list of MADSci Errors

`ActionResultDefinition(**data: Any)`
:   Defines a result for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.action_types.DatapointActionResultDefinition
    * madsci.common.types.action_types.FileActionResultDefinition
    * madsci.common.types.action_types.JSONActionResultDefinition

    ### Class variables

    `description: str | None`
    :

    `model_config`
    :

    `result_label: str`
    :

    `result_type: str`
    :

`ActionRunning(**data: Any)`
:   Response from an action that is running.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.RUNNING: 'running'>]`
    :

`ActionStatus(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Status for a step of a workflow

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `CANCELLED`
    :

    `FAILED`
    :

    `NOT_READY`
    :

    `NOT_STARTED`
    :

    `PAUSED`
    :

    `RUNNING`
    :

    `SUCCEEDED`
    :

    `UNKNOWN`
    :

    ### Instance variables

    `is_terminal: bool`
    :   Check if the status is terminal

`ActionSucceeded(**data: Any)`
:   Response from an action that succeeded.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.SUCCEEDED: 'succeeded'>]`
    :

`ActionUnknown(**data: Any)`
:   Response from an action that has an unknown status.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `status: Literal[<ActionStatus.UNKNOWN: 'unknown'>]`
    :

`ArgumentDefinition(**data: Any)`
:   Defines an argument for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.action_types.FileArgumentDefinition
    * madsci.common.types.action_types.LocationArgumentDefinition

    ### Class variables

    `argument_type: str`
    :

    `default: Any | None`
    :

    `description: str`
    :

    `model_config`
    :

    `name: str`
    :

    `required: bool`
    :

`DatapointActionResultDefinition(**data: Any)`
:   Defines a file result for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResultDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `result_type: Literal['datapoint']`
    :

`FileActionResultDefinition(**data: Any)`
:   Defines a file result for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResultDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `result_type: Literal['file']`
    :

`FileArgumentDefinition(**data: Any)`
:   Defines a file for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ArgumentDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `argument_type: Literal['file']`
    :

    `model_config`
    :

`JSONActionResultDefinition(**data: Any)`
:   Defines a JSON result for a node action
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResultDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `json_schema: dict[str, typing.Any] | None`
    :

    `model_config`
    :

    `result_type: Literal['json']`
    :

`LocationArgumentDefinition(**data: Any)`
:   Location Argument Definition for use in NodeInfo
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ArgumentDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `argument_type: Literal['location']`
    :

    `model_config`
    :

`RestActionRequest(**data: Any)`
:   Base REST action request model with nested args structure.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `args: dict[str, typing.Any]`
    :   Arguments for the action

    `model_config`
    :

    `var_args: list[typing.Any] | None`
    :   Additional positional arguments for *args

    `var_kwargs: dict[str, typing.Any] | None`
    :   Additional keyword arguments for **kwargs

`RestActionResult(**data: Any)`
:   Result of an action, returned over REST API.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.action_types.ActionResult
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `files: list[str] | None`
    :

    `model_config`
    :