"""Types for MADSci Actions."""

from __future__ import annotations

import inspect
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union, get_args, get_origin

from madsci.common.types.base_types import Error, MadsciBaseModel
from madsci.common.types.datapoint_types import DataPoint
from madsci.common.utils import localnow, new_ulid_str
from pydantic import Field, create_model
from pydantic.functional_validators import field_validator, model_validator
from pydantic.types import Discriminator, Tag


class ActionStatus(str, Enum):
    """Status for a step of a workflow"""

    NOT_STARTED = "not_started"
    NOT_READY = "not_ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    UNKNOWN = "unknown"

    @property
    def is_terminal(self) -> bool:
        """Check if the status is terminal"""
        return self in [
            ActionStatus.SUCCEEDED,
            ActionStatus.FAILED,
            ActionStatus.CANCELLED,
            ActionStatus.NOT_READY,
        ]


class ActionRequest(MadsciBaseModel):
    """Request to perform an action on a node"""

    action_id: str = Field(
        title="Action ID",
        description="The ID of the action.",
        default_factory=new_ulid_str,
    )
    action_name: str = Field(
        title="Action Name",
        description="The name of the action to perform.",
    )
    """Name of the action to perform"""
    args: Optional[dict[str, Any]] = Field(
        title="Action Arguments",
        description="Arguments for the action.",
        default_factory=dict,
    )
    """Arguments for the action"""
    files: dict[str, Union[Path, list[Path]]] = Field(
        title="Action Files",
        description="Files sent along with the action. Can be single files (Path) or multiple files (list[Path]).",
        default_factory=dict,
    )
    """Files sent along with the action"""
    var_args: Optional[list[Any]] = Field(
        title="Variable Arguments",
        description="Additional positional arguments (*args) for actions that accept them.",
        default=None,
    )
    """Additional positional arguments for the action"""
    var_kwargs: Optional[dict[str, Any]] = Field(
        title="Variable Keyword Arguments",
        description="Additional keyword arguments (**kwargs) for actions that accept them.",
        default=None,
    )
    """Additional keyword arguments for the action"""

    def failed(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Path]] = None,
    ) -> ActionFailed:
        """Create an ActionFailed response"""
        return ActionFailed(
            action_id=self.action_id,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def succeeded(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionSucceeded:
        """Create an ActionSucceeded response"""
        return ActionSucceeded(
            action_id=self.action_id,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def running(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionRunning:
        """Create an ActionRunning response"""
        return ActionRunning(
            action_id=self.action_id,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def not_ready(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionNotReady:
        """Create an ActionNotReady response"""
        return ActionNotReady(
            action_id=self.action_id,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def cancelled(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionCancelled:
        """Create an ActionCancelled response"""
        return ActionCancelled(
            action_id=self.action_id,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def paused(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionResult:
        """Create an ActionResult response"""
        return ActionResult(
            action_id=self.action_id,
            status=ActionStatus.PAUSED,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def not_started(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionResult:
        """Create an ActionResult response"""
        return ActionResult(
            action_id=self.action_id,
            status=ActionStatus.NOT_STARTED,
            errors=errors,
            json_result=json_result,
            files=files,
        )

    def unknown(
        self,
        errors: Union[Error, list[Error], str] = [],
        json_result: Any = None,
        files: Optional[Union[Path, ActionFiles]] = None,
    ) -> ActionResult:
        """Create an ActionResult response"""
        return ActionResult(
            action_id=self.action_id,
            status=ActionStatus.UNKNOWN,
            errors=errors,
            json_result=json_result,
            files=files,
        )


class ActionJSON(MadsciBaseModel, extra="allow"):
    """Data returned from an action as JSON"""

    type: Literal["json"] = Field(
        title="Data Type",
        description="The type of the data.",
        default="json",
    )


class ActionFiles(MadsciBaseModel, extra="allow"):
    """Files returned from an action"""

    @model_validator(mode="before")
    @classmethod
    def ensure_files_are_path(cls: Any, v: Any) -> Any:
        """Ensure that the files are Path"""
        for key, value in v.items():
            if not isinstance(value, Path):
                try:
                    v[key] = Path(value)
                except Exception:
                    raise ValueError(
                        f"File '{key}' is not a valid Path: {value}"
                    ) from None
        return v


class ActionDatapoints(MadsciBaseModel, extra="allow"):
    """Datapoint IDs returned from an action.

    This class stores only ULID strings (datapoint IDs) for efficient storage and workflow management.
    Full DataPoint objects can be fetched just-in-time when needed using the data client.

    Values can be:
    - str: Single datapoint ID (ULID)
    - list[str]: List of datapoint IDs (ULIDs)
    """

    @model_validator(mode="before")
    @classmethod
    def ensure_datapoints_are_strings(cls: Any, v: Any) -> Any:
        """Convert DataPoint objects to ULID strings, support both single items and lists"""
        for key, value in v.items():
            if isinstance(value, str):
                # Already a string ID, validate it's ULID-like
                if not cls._is_valid_ulid(value):
                    raise ValueError(
                        f"Datapoint ID '{key}' must be a valid ULID string, got: {value}"
                    )
            elif isinstance(value, list):
                # Handle list of datapoints/IDs
                converted_list = []
                for i, item in enumerate(value):
                    converted_id = cls._convert_to_datapoint_id(item, f"{key}[{i}]")
                    converted_list.append(converted_id)
                v[key] = converted_list
            else:
                # Handle single datapoint object/dict
                v[key] = cls._convert_to_datapoint_id(value, key)
        return v

    @classmethod
    def _convert_to_datapoint_id(cls, value: Any, field_name: str) -> str:
        """Convert a single value to a datapoint ID"""
        if isinstance(value, str):
            if not cls._is_valid_ulid(value):
                raise ValueError(
                    f"Datapoint ID '{field_name}' must be a valid ULID string, got: {value}"
                )
            return value
        if hasattr(value, "datapoint_id"):
            # DataPoint object, extract the ID
            return value.datapoint_id
        if isinstance(value, dict):
            # Dict representation of DataPoint, extract the ID
            try:
                datapoint = DataPoint.model_validate(value)
                return datapoint.datapoint_id
            except Exception:
                raise ValueError(
                    f"Datapoint '{field_name}' dict must be a valid DataPoint representation"
                ) from None
        raise ValueError(
            f"Datapoint '{field_name}' must be a ULID string, DataPoint object, or DataPoint dict, got: {type(value).__name__}"
        ) from None

    @staticmethod
    def _is_valid_ulid(value: str) -> bool:
        """Basic ULID validation - 26 characters, alphanumeric + some special chars"""
        if not isinstance(value, str) or len(value) != 26:
            return False
        # ULID uses Crockford's Base32: 0-9, A-Z (excluding I, L, O, U)
        allowed_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        return all(c.upper() in allowed_chars for c in value)


class ActionResult(MadsciBaseModel):
    """Result of an action."""

    action_id: str = Field(
        title="Action ID",
        description="The ID of the action.",
        default_factory=new_ulid_str,
    )
    status: ActionStatus = Field(
        title="Step Status",
        description="The status of the step.",
    )
    errors: list[Error] = Field(
        title="Step Error",
        description="An error message(s) if the step failed.",
        default_factory=list,
    )
    json_result: Any = Field(
        title="Step Data",
        description="The combined JSON-serializable data generated by the step.",
        default=None,
    )
    files: Optional[Union[Path, ActionFiles]] = Field(
        title="Step Files",
        description="A dictionary of files produced by the step.",
        default=None,
    )
    datapoints: Optional[ActionDatapoints] = Field(
        title="Data Point IDs",
        description="A dictionary of datapoint IDs (ULID strings) for datapoints sent to the data manager by the step.",
        default=None,
    )
    history_created_at: Optional[datetime] = Field(
        title="History Created At",
        description="The time the history was updated.",
        default_factory=localnow,
    )

    @field_validator("errors", mode="before")
    @classmethod
    def ensure_list_of_errors(cls: Any, v: Any) -> Any:
        """Ensure that errors is a list of MADSci Errors"""
        if isinstance(v, str):
            return [Error(message=v)]
        if isinstance(v, Error):
            return [v]
        if isinstance(v, Exception):
            return [Error.from_exception(v)]
        if isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str):
                    v[i] = Error(message=item)
                elif isinstance(item, Exception):
                    v[i] = Error.from_exception(item)
        return v


class RestActionResult(ActionResult):
    """Result of an action, returned over REST API."""

    files: Optional[list[str]] = Field(
        title="Step File Keys",
        description="A list of file keys, which informs the client what files to request to build the final ActionResult object.",
        default=None,
    )


class ActionSucceeded(ActionResult):
    """Response from an action that succeeded."""

    status: Literal[ActionStatus.SUCCEEDED] = ActionStatus.SUCCEEDED


class ActionFailed(ActionResult):
    """Response from an action that failed."""

    status: Literal[ActionStatus.FAILED] = ActionStatus.FAILED


class ActionCancelled(ActionResult):
    """Response from an action that was cancelled."""

    status: Literal[ActionStatus.CANCELLED] = ActionStatus.CANCELLED


class ActionRunning(ActionResult):
    """Response from an action that is running."""

    status: Literal[ActionStatus.RUNNING] = ActionStatus.RUNNING


class ActionNotReady(ActionResult):
    """Response from an action that is not ready to be run."""

    status: Literal[ActionStatus.NOT_READY] = ActionStatus.NOT_READY


class ActionPaused(ActionResult):
    """Response from an action that is paused."""

    status: Literal[ActionStatus.PAUSED] = ActionStatus.PAUSED


class ActionNotStarted(ActionResult):
    """Response from an action that has not started."""

    status: Literal[ActionStatus.NOT_STARTED] = ActionStatus.NOT_STARTED


class ActionUnknown(ActionResult):
    """Response from an action that has an unknown status."""

    status: Literal[ActionStatus.UNKNOWN] = ActionStatus.UNKNOWN


class ActionDefinition(MadsciBaseModel):
    """Definition of an action."""

    name: str = Field(
        title="Action Name",
        description="The name of the action.",
    )
    description: str = Field(
        title="Action Description",
        description="A description of the action.",
        default="",
    )

    @field_validator("description", mode="before")
    @classmethod
    def none_to_empty_str(cls, v: Any) -> str:
        """Convert None to empty string"""
        if v is None:
            return ""
        return v

    args: Union[dict[str, ArgumentDefinition], list[ArgumentDefinition]] = Field(
        title="Action Arguments",
        description="The arguments of the action.",
        default_factory=dict,
    )
    locations: Union[
        dict[str, LocationArgumentDefinition], list[LocationArgumentDefinition]
    ] = Field(
        title="Action Location Arguments",
        description="The location arguments of the action.",
        default_factory=dict,
    )
    files: Union[dict[str, FileArgumentDefinition], list[FileArgumentDefinition]] = (
        Field(
            title="Action File Arguments",
            description="The file arguments of the action.",
            default_factory=dict,
        )
    )
    results: Union[
        dict[str, ActionResultDefinitions], list[ActionResultDefinitions]
    ] = Field(
        title="Action Results",
        description="The results of the action.",
        default_factory=dict,
    )
    blocking: bool = Field(
        title="Blocking",
        description="Whether the action is blocking.",
        default=False,
    )
    asynchronous: bool = Field(
        title="Asynchronous",
        description="Whether the action is asynchronous, and will return a 'running' status immediately rather than waiting for the action to complete before returning. This should be used for long-running actions (e.g. actions that take more than a few seconds to complete).",
        default=True,
    )
    accepts_var_args: bool = Field(
        title="Accepts Variable Arguments",
        description="Whether the action accepts additional positional arguments (*args).",
        default=False,
    )
    accepts_var_kwargs: bool = Field(
        title="Accepts Variable Keyword Arguments",
        description="Whether the action accepts additional keyword arguments (**kwargs).",
        default=False,
    )
    var_args_schema: Optional[dict[str, Any]] = Field(
        title="Variable Arguments Schema",
        description="JSON schema for validating additional positional arguments when accepts_var_args is True.",
        default=None,
    )
    var_kwargs_schema: Optional[dict[str, Any]] = Field(
        title="Variable Keyword Arguments Schema",
        description="JSON schema for validating additional keyword arguments when accepts_var_kwargs is True.",
        default=None,
    )

    @field_validator("args", mode="after")
    @classmethod
    def ensure_args_are_dict(cls: Any, v: Any) -> Any:
        """Ensure that the args are a dictionary"""
        if isinstance(v, list):
            return {arg.name: arg for arg in v}
        return v

    @field_validator("files", mode="after")
    @classmethod
    def ensure_files_are_dict(cls: Any, v: Any) -> Any:
        """Ensure that the files are a dictionary"""
        if isinstance(v, list):
            return {file.name: file for file in v}
        return v

    @field_validator("locations", mode="after")
    @classmethod
    def ensure_locations_are_dict(cls: Any, v: Any) -> Any:
        """Ensure that the locations are a dictionary"""
        if isinstance(v, list):
            return {location.name: location for location in v}
        return v

    @field_validator("results", mode="after")
    @classmethod
    def ensure_results_are_dict(cls: Any, v: Any) -> Any:
        """Ensure that the results are a dictionary"""
        if isinstance(v, list):
            return {result.result_label: result for result in v}
        return v

    @model_validator(mode="after")
    @classmethod
    def ensure_name_uniqueness(cls: Any, v: Any) -> Any:
        """Ensure that the names of the arguments and files are unique"""
        names = set()
        for arg in v.args.values():
            if arg.name in names:
                raise ValueError(f"Action name '{arg.name}' is not unique")
            names.add(arg.name)
        for file in v.files.values():
            if file.name in names:
                raise ValueError(f"File name '{file.name}' is not unique")
            names.add(file.name)
        for location in v.locations.values():
            if location.name in names:
                raise ValueError(f"Location name '{location.name}' is not unique")
            names.add(location.name)
        return v


class ArgumentDefinition(MadsciBaseModel):
    """Defines an argument for a node action"""

    name: str = Field(
        title="Argument Name",
        description="The name of the argument.",
    )
    description: str = Field(
        title="Argument Description",
        description="A description of the argument.",
    )
    argument_type: str = Field(
        title="Argument Type", description="Any type information about the argument"
    )
    required: bool = Field(
        title="Argument Required",
        description="Whether the argument is required.",
    )
    default: Optional[Any] = Field(
        title="Argument Default",
        description="The default value of the argument.",
        default=None,
    )


class LocationArgumentDefinition(ArgumentDefinition):
    """Location Argument Definition for use in NodeInfo"""

    argument_type: Literal["location"] = Field(
        title="Location Argument Type",
        description="The type of the location argument.",
        default="location",
    )


class FileArgumentDefinition(ArgumentDefinition):
    """Defines a file for a node action"""

    argument_type: Literal["file"] = Field(
        title="File Argument Type",
        description="The type of the file argument.",
        default="file",
    )


class ActionResultDefinition(MadsciBaseModel):
    """Defines a result for a node action"""

    result_label: str = Field(
        title="Result Label",
        description="The label of the result.",
    )
    description: Optional[str] = Field(
        title="Result Description",
        description="A description of the result.",
        default=None,
    )
    result_type: str = Field(
        title="Result Type",
        description="The type of the result.",
    )


class FileActionResultDefinition(ActionResultDefinition):
    """Defines a file result for a node action"""

    result_type: Literal["file"] = Field(
        title="Result Type",
        description="The type of the result.",
        default="file",
    )


class DatapointActionResultDefinition(ActionResultDefinition):
    """Defines a file result for a node action"""

    result_type: Literal["datapoint"] = Field(
        title="Result Type",
        description="The type of the result.",
        default="datapoint",
    )


class JSONActionResultDefinition(ActionResultDefinition):
    """Defines a JSON result for a node action"""

    result_type: Literal["json"] = Field(
        title="Result Type",
        description="The type of the result.",
        default="json",
    )
    json_schema: Optional[dict[str, Any]] = Field(
        title="JSON Schema",
        description="The JSON schema that validates the result data.",
        default=None,
    )


ActionResultDefinitions = Annotated[
    Union[
        Annotated[FileActionResultDefinition, Tag("file")],
        Annotated[DatapointActionResultDefinition, Tag("datapoint")],
        Annotated[JSONActionResultDefinition, Tag("json")],
    ],
    Discriminator("result_type"),
]


def create_action_request_model(action_function: Any) -> type[MadsciBaseModel]:
    """Create a dynamic action request model based on function signature."""
    signature = inspect.signature(action_function)
    fields = {}
    has_var_args = False
    has_var_kwargs = False

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue

        # Check for *args and **kwargs
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            has_var_args = True
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            has_var_kwargs = True
            continue

        # Determine field type and default
        field_type = (
            param.annotation if param.annotation != inspect.Parameter.empty else Any
        )

        # Handle file parameters - skip them as they're handled separately in file upload endpoints
        file_type_info = _analyze_file_parameter_type(field_type)
        if file_type_info["is_file_param"]:
            # For file parameters, we'll handle them separately in the API
            continue

        # Process regular parameter
        _add_parameter_field(fields, param_name, param, field_type, action_function)

    # Add variable argument fields
    _add_variable_argument_fields(fields, has_var_args, has_var_kwargs)

    # Create the dynamic model with a descriptive docstring
    model_name = f"{action_function.__name__.title()}Request"
    model_docstring = f"Request parameters for the {action_function.__name__} action."
    if action_function.__doc__:
        model_docstring = f"{model_docstring}\n\n{action_function.__doc__.strip()}"

    return create_model(
        model_name, __base__=MadsciBaseModel, __doc__=model_docstring, **fields
    )


def _add_parameter_field(
    fields: dict,
    param_name: str,
    param: inspect.Parameter,
    field_type: Any,
    action_function: Any,
) -> None:
    """Add a parameter field to the fields dictionary."""
    # Set up default value and description
    if param.default != inspect.Parameter.empty:
        default_value = param.default
    else:
        default_value = ... if field_type != Optional[Any] else None

    # Create a descriptive field with title and description
    field_title = param_name.replace("_", " ").title()
    field_description = f"Parameter: {param_name}"

    # Try to extract parameter description from docstring
    if action_function.__doc__:
        doc_lines = action_function.__doc__.strip().split("\n")
        for line in doc_lines:
            if param_name in line.lower() and ":" in line:
                field_description = line.strip()
                break

    fields[param_name] = (
        field_type,
        Field(default=default_value, title=field_title, description=field_description),
    )


def _add_variable_argument_fields(
    fields: dict, has_var_args: bool, has_var_kwargs: bool
) -> None:
    """Add variable argument fields to the fields dictionary."""
    # Add var_args field if function accepts *args
    if has_var_args:
        fields["var_args"] = (
            list[Any],
            Field(
                default_factory=list,
                title="Variable Arguments",
                description="Additional positional arguments (*args) for this action.",
            ),
        )

    # Add var_kwargs field if function accepts **kwargs
    if has_var_kwargs:
        fields["var_kwargs"] = (
            dict[str, Any],
            Field(
                default_factory=dict,
                title="Variable Keyword Arguments",
                description="Additional keyword arguments (**kwargs) for this action.",
            ),
        )


def create_action_result_model(action_function: Any) -> type[ActionResult]:
    """Create a dynamic ActionResult model based on function return type."""
    # Parse the return type to determine what fields should be documented
    fields = {}

    # Get result definitions from the function metadata
    if hasattr(action_function, "__madsci_action_result_definitions__"):
        result_definitions = action_function.__madsci_action_result_definitions__

        if result_definitions:
            fields.update(_create_result_fields(action_function, result_definitions))

    # Add documentation from the function
    model_description = f"Result for {action_function.__name__} action"
    if action_function.__doc__:
        model_description = f"{model_description}: {action_function.__doc__.strip()}"

    # Create the dynamic model
    model_name = f"{action_function.__name__.title()}ActionResult"

    # Create model with specific fields or base ActionResult
    return create_model(
        model_name,
        __base__=ActionResult,
        __module__=action_function.__module__,
        **fields,
    )


def extract_file_parameters(action_function: Any) -> dict[str, dict[str, Any]]:
    """Extract file parameter information from action function signature.

    Returns:
        Dictionary mapping parameter names to their metadata including:
        - required: bool indicating if the parameter is required
        - description: str describing the parameter
        - annotation: type annotation of the parameter
        - is_list: bool indicating if this is a list[Path] parameter
    """
    signature = inspect.signature(action_function)
    file_parameters = {}

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue

        # Check if this is a file parameter
        file_type_info = _analyze_file_parameter_type(param.annotation)

        if file_type_info["is_file_param"]:
            is_required = param.default == inspect.Parameter.empty

            # Extract description from docstring if available
            description = f"File parameter: {param_name}"
            if action_function.__doc__:
                # Simple docstring parsing - could be enhanced later
                doc_lines = action_function.__doc__.strip().split("\n")
                for line in doc_lines:
                    if param_name in line.lower() and ":" in line:
                        description = line.strip()
                        break

            file_parameters[param_name] = {
                "required": is_required,
                "description": description,
                "annotation": param.annotation,
                "is_list": file_type_info["is_list"],
                "is_optional": file_type_info["is_optional"],
                "default": param.default
                if param.default != inspect.Parameter.empty
                else None,
            }

    return file_parameters


def _analyze_file_parameter_type(annotation: Any) -> dict[str, Any]:
    """Analyze a type annotation to determine if it's a file parameter.

    Supports:
    - Path
    - list[Path]
    - Optional[Path]
    - Optional[list[Path]]
    - Union[Path, None] (equivalent to Optional[Path])
    - Union[list[Path], None] (equivalent to Optional[list[Path]])

    Returns:
        Dict with keys: is_file_param, is_list, is_optional
    """
    result = {
        "is_file_param": False,
        "is_list": False,
        "is_optional": False,
    }

    # Direct Path type
    if annotation == Path:
        result["is_file_param"] = True
        return result

    # Handle generic types (list, Optional, Union)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list:
        if args and args[0] == Path:
            result["is_file_param"] = True
            result["is_list"] = True
        return result

    if origin is Union:
        non_none_args = [arg for arg in args if arg is not type(None)]

        if len(non_none_args) == 1 and type(None) in args:
            inner_type = non_none_args[0]
            result["is_optional"] = True

            if inner_type == Path:
                result["is_file_param"] = True
                return result
            if get_origin(inner_type) is list:
                inner_args = get_args(inner_type)
                if inner_args and inner_args[0] == Path:
                    result["is_file_param"] = True
                    result["is_list"] = True
                    return result
        elif Path in args:
            result["is_file_param"] = True
            result["is_optional"] = type(None) in args
            return result

    return result


def extract_file_result_definitions(action_function: Any) -> dict[str, str]:
    """Extract file result information from action function metadata.

    Returns:
        Dictionary mapping result labels to their descriptions for file results
    """
    file_results = {}

    if hasattr(action_function, "__madsci_action_result_definitions__"):
        result_definitions = action_function.__madsci_action_result_definitions__

        for result_def in result_definitions:
            if hasattr(result_def, "result_type") and result_def.result_type == "file":
                description = f"File result: {result_def.result_label}"
                if hasattr(result_def, "description") and result_def.description:
                    description = f"File result: {result_def.description}"

                file_results[result_def.result_label] = description

    return file_results


def _create_result_fields(action_function: Any, result_definitions: list) -> dict:
    """Create fields for dynamic result models based on result definitions."""
    fields = {}
    json_data_fields = {}
    files_fields = {}
    datapoints_fields = {}

    for result_def in result_definitions:
        if isinstance(result_def, FileActionResultDefinition):
            files_fields[result_def.result_label] = (
                str,
                Field(description=f"File: {result_def.result_label}"),
            )
        elif isinstance(result_def, JSONActionResultDefinition):
            json_data_fields[result_def.result_label] = (
                str,  # Will be the actual data type
                Field(description=f"JSON data: {result_def.result_label}"),
            )
        elif isinstance(result_def, DatapointActionResultDefinition):
            datapoints_fields[result_def.result_label] = (
                str,  # Will be the datapoint ID (ULID string)
                Field(description=f"Datapoint ID: {result_def.result_label}"),
            )

    # If we have specific result types, create custom fields
    if json_data_fields:
        json_data_model = create_model(
            f"{action_function.__name__.title()}JsonData", **json_data_fields
        )
        fields["json_result"] = (
            Optional[json_data_model],
            Field(description="JSON data returned by the action"),
        )

    if files_fields:
        files_model = create_model(
            f"{action_function.__name__.title()}Files", **files_fields
        )
        fields["files"] = (
            Optional[files_model],
            Field(description="Files returned by the action"),
        )

    if datapoints_fields:
        datapoints_model = create_model(
            f"{action_function.__name__.title()}Datapoints", **datapoints_fields
        )
        fields["datapoints"] = (
            Optional[datapoints_model],
            Field(description="Datapoint IDs returned by the action"),
        )

    return fields


def create_dynamic_model(
    action_name: str,
    json_result_type: Optional[type] = None,
    action_function: Optional[Any] = None,
) -> type[RestActionResult]:
    """Create a dynamic RestActionResult model for a specific action.

    Args:
        action_name: Name of the action
        json_result_type: Type to use for the json_result field (None for file-only actions)
        action_function: Optional action function for extracting additional metadata

    Returns:
        Dynamic RestActionResult subclass with properly typed json_result field
    """
    fields = {}

    # Always override json_result field for proper OpenAPI documentation
    if json_result_type is not None:
        # Specific type for json_result
        fields["json_result"] = (
            json_result_type,
            Field(
                description=f"JSON result data for {action_name} action", default=None
            ),
        )
    else:
        # For file-only actions, explicitly set json_result as nullable
        fields["json_result"] = (
            Optional[Any],
            Field(
                description=f"JSON result data for {action_name} action (null for file-only actions)",
                default=None,
            ),
        )

    # Extract additional metadata from the action function if available
    model_docstring = f"Result of {action_name} action, returned over REST API."
    if action_function and action_function.__doc__:
        model_docstring = f"{model_docstring} {action_function.__doc__.strip()}"

    # Create the dynamic model class name
    class_name = (
        f"{''.join(word.capitalize() for word in action_name.split('_'))}ActionResult"
    )

    return create_model(
        class_name, __base__=RestActionResult, __doc__=model_docstring, **fields
    )
