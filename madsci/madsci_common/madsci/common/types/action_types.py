"""Types for MADSci Actions."""

import json
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic.functional_validators import field_validator, model_validator
from sqlmodel.main import Field

from madsci.common.types.base_types import BaseModel, Error, PathLike, new_ulid_str


class ActionStatus(str, Enum):
    """Status for a step of a workflow"""

    NOT_STARTED = "not_started"
    NOT_READY = "not_ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ActionRequest(BaseModel):
    """Request to perform an action on a module"""

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
    files: dict[str, PathLike] = Field(
        title="Action Files",
        description="Files sent along with the action.",
        default_factory=dict,
    )
    """Files sent along with the action"""

    @field_validator("args", mode="before")
    @classmethod
    def validate_args(cls, v: Any) -> Any:
        """Validate the args field of the action request. If it's a string, it's parsed as JSON."""
        if isinstance(v, str):
            v = json.loads(v)
        if v is None:
            return {}
        return v

    def failed(
        self,
        errors: Union[Error, list[Error], str] = [],
        data: dict[str, Any] = {},
        files: dict[str, PathLike] = {},
    ) -> "ActionFailed":
        """Create an ActionFailed response"""
        # * Convert errors to a list of errors if they are a single error or a string
        if isinstance(errors, str):
            errors = [Error(message=errors)]
        elif isinstance(errors, Error):
            errors = [errors]
        return ActionFailed(
            action_id=self.action_id,
            errors=errors,
            data=data,
            files=files,
        )

    def succeeded(
        self,
        data: dict[str, Any] = {},
        files: dict[str, PathLike] = {},
        errors: Union[Error, list[Error], str] = [],
    ) -> "ActionSucceeded":
        """Create an ActionSucceeded response"""
        return ActionSucceeded(
            action_id=self.action_id,
            errors=errors,
            data=data,
            files=files,
        )

    def running(
        self,
        data: dict[str, Any] = {},
        files: dict[str, PathLike] = {},
        errors: Union[Error, list[Error], str] = [],
    ) -> "ActionRunning":
        """Create an ActionRunning response"""
        return ActionRunning(
            action_id=self.action_id,
            errors=errors,
            data=data,
            files=files,
        )

    def not_ready(
        self,
        errors: Union[Error, list[Error], str] = [],
        data: dict[str, Any] = {},
        files: dict[str, PathLike] = {},
    ) -> "ActionNotReady":
        """Create an ActionNotReady response"""
        return ActionNotReady(
            action_id=self.action_id,
            errors=errors,
            data=data,
            files=files,
        )

    def cancelled(
        self,
        errors: Union[Error, list[Error], str] = [],
        data: dict[str, Any] = {},
        files: dict[str, PathLike] = {},
    ) -> "ActionCancelled":
        """Create an ActionCancelled response"""
        return ActionCancelled(
            action_id=self.action_id,
            errors=errors,
            data=data,
            files=files,
        )


class ActionResult(BaseModel):
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
        default=list,
    )
    data: dict[str, Any] = Field(
        title="Step Result",
        description="The result of the step.",
        default_factory=dict,
    )
    files: dict[str, PathLike] = Field(
        title="Step Files",
        description="A dictionary of files produced by the step.",
        default_factory=dict,
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


class ActionDefinition(BaseModel):
    """Definition of an action."""

    name: str = Field(
        title="Action Name",
        description="The name of the action.",
    )
    description: str = Field(
        title="Action Description",
        description="A description of the action.",
    )
    args: Union[
        dict[str, "ActionArgumentDefinition"],
        list["ActionArgumentDefinition"],
    ] = Field(
        title="Action Arguments",
        description="The arguments of the action.",
        default_factory=dict,
    )
    files: Union[dict[str, PathLike], list[PathLike]] = Field(
        title="Action File Arguments",
        description="The file arguments of the action.",
        default_factory=dict,
    )
    results: Union[
        dict[str, "ActionResultDefinition"],
        list["ActionResultDefinition"],
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

    @field_validator("args", mode="after")
    @classmethod
    def ensure_args_are_dict(cls, v: Any) -> Any:
        """Ensure that the args are a dictionary"""
        if isinstance(v, list):
            return {arg.name: arg for arg in v}
        return v

    @field_validator("files", mode="after")
    @classmethod
    def ensure_files_are_dict(cls, v: Any) -> Any:
        """Ensure that the files are a dictionary"""
        if isinstance(v, list):
            return {file.name: file for file in v}
        return v

    @field_validator("results", mode="after")
    @classmethod
    def ensure_results_are_dict(cls, v: Any) -> Any:
        """Ensure that the results are a dictionary"""
        if isinstance(v, list):
            return {result.result_label: result for result in v}
        return v

    @model_validator(mode="after")
    @classmethod
    def ensure_name_uniqueness(cls, v: Any) -> Any:
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
        return v


class ActionArgumentDefinition(BaseModel):
    """Defines an argument for a module action"""

    name: str = Field(
        title="Argument Name",
        description="The name of the argument.",
    )
    description: str = Field(
        title="Argument Description",
        description="A description of the argument.",
    )
    type: str = Field(
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


class ActionFileDefinition(BaseModel):
    """Defines a file for a module action"""

    name: str = Field(
        title="File Name",
        description="The name of the file.",
    )
    required: bool = Field(
        title="File Required",
        description="Whether the file is required.",
    )
    description: str = Field(
        title="File Description",
        description="A description of the file.",
    )


class ActionResultDefinition(BaseModel):
    """Defines a result for a module action"""

    result_label: str = Field(
        title="Result Label",
        description="The label of the result.",
    )
    description: str = Field(
        title="Result Description",
        description="A description of the result.",
        default=None,
    )
    result_type: str = Field(
        title="Result Type",
        description="The type of the result.",
    )


class FileActionResultDefinition(ActionResultDefinition):
    """Defines a file result for a module action"""

    result_type: Literal["file"] = Field(
        title="Result Type",
        description="The type of the result.",
        default="file",
    )


class JSONActionResultDefinition(ActionResultDefinition):
    """Defines a JSON result for a module action"""

    result_type: Literal["json"] = Field(
        title="Result Type",
        description="The type of the result.",
        default="json",
    )
