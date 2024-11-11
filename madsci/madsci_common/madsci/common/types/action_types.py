"""Types for MADSci Actions."""

import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic.functional_validators import field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
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

    name: str = Field(
        title="Action Name",
        description="The name of the action to perform.",
    )
    """Name of the action to perform"""
    args: Optional[Dict[str, Any]] = Field(
        title="Action Arguments",
        description="Arguments for the action.",
        default_factory=dict,
    )
    """Arguments for the action"""
    files: Dict[str, PathLike] = Field(
        title="Action Files",
        description="Files sent along with the action.",
        default_factory=dict,
    )
    """Files sent along with the action"""

    @field_validator("args", mode="before")
    @classmethod
    def validate_args(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate the args field of the action request. If it's a string, it's parsed as JSON."""
        if isinstance(v, str):
            v = json.loads(v)
        if v is None:
            return {}
        return v

    def failed(
        self,
        error: Optional[Error] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, PathLike]] = None,
    ) -> "ActionFailed":
        """Create an ActionFailed response"""
        return ActionFailed(
            action_id=self.action_id, error=error, data=data, files=files
        )

    def succeeded(
        self,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, PathLike]] = None,
    ) -> "ActionSucceeded":
        """Create an ActionSucceeded response"""
        return ActionSucceeded(action_id=self.action_id, data=data, files=files)

    def running(
        self,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, PathLike]] = None,
    ) -> "ActionRunning":
        """Create an ActionRunning response"""
        return ActionRunning(action_id=self.action_id, data=data, files=files)

    def not_ready(
        self,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, PathLike]] = None,
    ) -> "ActionNotReady":
        """Create an ActionNotReady response"""
        return ActionNotReady(action_id=self.action_id, data=data, files=files)

    def cancelled(
        self,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, PathLike]] = None,
    ) -> "ActionCancelled":
        """Create an ActionCancelled response"""
        return ActionCancelled(action_id=self.action_id, data=data, files=files)


class ActionResponse(BaseModel):
    """Response from an action."""

    action_id: str = Field(
        title="Action ID",
        description="The ID of the action.",
        default_factory=new_ulid_str,
    )
    status: ActionStatus = Field(
        title="Step Status",
        description="The status of the step.",
    )
    errors: List[Error] = Field(
        title="Step Error",
        description="An error message(s) if the step failed.",
        default=list,
    )
    data: Dict[str, Any] = Field(
        title="Step Result",
        description="The result of the step.",
        default_factory=dict,
    )
    files: Dict[str, PathLike] = Field(
        title="Step Files",
        description="A dictionary of files produced by the step.",
        default_factory=dict,
    )


class ActionSucceeded(ActionResponse):
    """Response from an action that succeeded."""

    status: Literal[ActionStatus.SUCCEEDED] = ActionStatus.SUCCEEDED


class ActionFailed(ActionResponse):
    """Response from an action that failed."""

    status: Literal[ActionStatus.FAILED] = ActionStatus.FAILED


class ActionCancelled(ActionResponse):
    """Response from an action that was cancelled."""

    status: Literal[ActionStatus.CANCELLED] = ActionStatus.CANCELLED


class ActionRunning(ActionResponse):
    """Response from an action that is running."""

    status: Literal[ActionStatus.RUNNING] = ActionStatus.RUNNING


class ActionNotReady(ActionResponse):
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
    args: Dict[str, "ActionArgumentDefinition"] = Field(
        title="Action Arguments",
        description="The arguments of the action.",
        default_factory=dict,
    )
    files: Dict[str, PathLike] = Field(
        title="Action File Arguments",
        description="The file arguments of the action.",
        default_factory=dict,
    )
    results: List["ActionResultDefinition"] = Field(
        title="Action Results",
        description="The results of the action.",
        default_factory=list,
    )
    blocking: bool = Field(
        title="Blocking",
        description="Whether the action is blocking.",
        default=False,
    )

    @model_validator(mode="after")
    @classmethod
    def ensure_name_uniqueness(cls, v: Any) -> Any:
        """Ensure that the names of the arguments and files are unique"""
        names = set()
        for arg in v.args:
            if arg.name in names:
                raise ValueError(f"Action name '{arg.name}' is not unique")
            names.add(arg.name)
        for file in v.files:
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