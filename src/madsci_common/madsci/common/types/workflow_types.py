"""Types for MADSci Worfklow running."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal, Optional, Union

from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel, PathLike
from madsci.common.types.step_types import Step, StepDefinition
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import (
    Field,
    PositiveInt,
    computed_field,
    field_validator,
    model_validator,
)


class WorkflowStatus(MadsciBaseModel):
    """Representation of the status of a Workflow"""

    current_step_index: int = 0
    """Index of the current step"""
    paused: bool = False
    """Whether or not the workflow is paused"""
    completed: bool = False
    """Whether or not the workflow has completed successfully"""
    failed: bool = False
    """Whether or not the workflow has failed"""
    cancelled: bool = False
    """Whether or not the workflow has been cancelled"""
    running: bool = False
    """Whether or not the workflow is currently running"""
    has_started: bool = False
    """Whether or not at least one step of the workflow has been run"""

    def reset(self, step_index: int = 0) -> None:
        """Reset the workflow status"""
        self.current_step_index = step_index
        self.paused = False
        self.completed = False
        self.failed = False
        self.cancelled = False
        self.running = False
        self.has_started = False

    @computed_field
    @property
    def queued(self) -> bool:
        """Whether or not the workflow is queued"""
        return self.active and not self.running

    @computed_field
    @property
    def active(self) -> bool:
        """Whether or not the workflow is actively being scheduled"""
        return not (self.terminal or self.paused)

    @computed_field
    @property
    def terminal(self) -> bool:
        """Whether or not the workflow is in a terminal state"""
        return self.completed or self.failed or self.cancelled

    @computed_field
    @property
    def started(self) -> bool:
        """Whether or not the workflow has started"""
        return self.current_step_index > 0

    @computed_field
    @property
    def ok(self) -> bool:
        """Whether or not the workflow is ok (i.e. not failed or cancelled)"""
        return not (self.failed or self.cancelled)

    @computed_field
    @property
    def description(self) -> str:  # noqa: PLR0911
        """Description of the workflow's status"""
        if self.completed:
            return "Completed Successfully"
        if self.failed:
            return f"Failed on step {self.current_step_index}"
        if self.cancelled:
            return f"Cancelled on step {self.current_step_index}"
        if self.paused:
            return f"Paused on step {self.current_step_index}"
        if self.running:
            return f"Running step {self.current_step_index}"
        if self.active:
            return f"Queued on step {self.current_step_index}"
        return "Unknown"


class WorkflowParameterType(str, Enum):
    """Enum for the type of workflow parameter"""

    VALUE = "value"
    """A simple value parameter"""
    FILE = "file"
    """A file parameter, which is a parameter whose value is a file path"""
    DATA = "data"
    """A data flow parameter, which is a parameter that is used to pass data between steps"""


class WorkflowValueParameter(MadsciBaseModel):
    """Container for a workflow parameter"""

    name: str
    """The name of the parameter"""
    type: Literal[WorkflowParameterType.VALUE] = Field(
        default=WorkflowParameterType.VALUE
    )
    """The type of the parameter, which is always 'value'. This will be assumed if not provided."""
    default: Optional[Any] = None
    """The default value of a parameter; if not provided, the parameter must be provided when the workflow is run"""


class WorkflowFileParameter(MadsciBaseModel):
    """Container for a file parameter, which is a parameter whose value is a file path"""

    name: str
    """The name of the parameter"""
    type: Literal[WorkflowParameterType.FILE]
    """The type of the parameter, which is always 'file'. This must be provided to indicate that this is a file parameter."""
    default: Optional[PathLike] = None
    """The default value of the parameter; if not provided, the parameter must be provided when the workflow is run"""


class WorkflowDataParameter(MadsciBaseModel):
    """Container for a data flow parameter, which is a parameter that is used to pass data between steps in a workflow"""

    name: str
    """The name of the parameter"""
    type: Literal[WorkflowParameterType.DATA] = Field(
        default=WorkflowParameterType.DATA
    )
    """The type of the parameter, which is always 'data'. This will be assumed if not provided."""
    label: str
    """The label of the data point used for this parameter"""
    step_identifier: Optional[Union[PositiveInt, str]] = None
    """Name or index of the step that produces this data point"""
    datapoint_id: Optional[str] = None
    """ID of the data point, if known. This is used to reference the data point"""

    @model_validator(mode="after")
    def validate_step_identifier(self) -> "WorkflowDataParameter":
        """Validate that the step identifier is either a positive integer or a string"""
        if not (self.step_identifier is None) ^ (self.datapoint_id is None):
            raise ValueError(
                "WorkflowDataParameter {self.name} must have one of a step_identifier or a datapoint_id"
            )
        return self


class WorkflowMetadata(MadsciBaseModel, extra="allow"):
    """Metadata container"""

    author: Optional[str] = None
    """Who wrote this object"""
    description: Optional[str] = None
    """Description of the object"""
    version: Union[float, str] = ""
    """Version of the object"""


class WorkflowDefinition(MadsciBaseModel):
    """Grand container that pulls all info of a workflow together"""

    name: str
    """Name of the workflow"""
    workflow_metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    """Information about the flow"""
    parameters: list[
        Union[WorkflowValueParameter, WorkflowFileParameter, WorkflowDataParameter]
    ] = Field(default_factory=list)
    """A list of parameterized inputs to the workflow"""
    steps: list[StepDefinition] = Field(default_factory=list)
    """User Submitted Steps of the flow"""

    @field_validator("steps", mode="after")
    @classmethod
    def ensure_data_label_uniqueness(cls, v: list[StepDefinition]) -> Any:
        """Ensure that the names of the arguments and files are unique"""
        labels = []
        for step in v:
            if step.data_labels:
                for key in step.data_labels:
                    if step.data_labels[key] in labels:
                        raise ValueError("Data labels must be unique across workflow")
                    labels.append(step.data_labels[key])
        return v

    @model_validator(mode="after")
    def validate_dataflow_parameters(self) -> "WorkflowDefinition":
        """Validate that all parameters are provided"""
        for param in self.parameters:
            if isinstance(param, WorkflowDataParameter) and (
                (
                    isinstance(param.step_identifier, int)
                    and param.step_identifier >= len(self.steps)
                )
                or (
                    isinstance(param.step_identifier, str)
                    and not any(
                        step.name == param.step_identifier for step in self.steps
                    )
                )
            ):
                raise ValueError(
                    f"WorkflowDataParameter {param.name} must be a positive integer less than the number of steps in the workflow, or a valid step name"
                )
        return self


class WorkflowSubmission(WorkflowDefinition):
    """Container for a workflow being submitted to run on the workcell"""

    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """Parameter values used in this workflow run"""

    @model_validator(mode="after")
    def validate_workflow_parameters(self) -> "WorkflowSubmission":
        """Validate that all parameters are provided and valid"""
        for param in self.parameters:
            if (
                isinstance(param, WorkflowValueParameter)
                and param.default is None
                and param.name not in self.parameter_values
            ):
                raise ValueError(
                    f"Workflow Parameter {param.name} must be provided when running the workflow"
                )
            if (
                isinstance(param, WorkflowFileParameter)
                and param.default is None
                and param.name not in self.parameter_values
            ):
                raise ValueError(
                    f"Workflow File parameter {param.name} must be provided when running the workflow"
                )
        return self


class SchedulerMetadata(MadsciBaseModel):
    """Scheduler information"""

    ready_to_run: bool = False
    """Whether or not the next step in the workflow is ready to run"""
    priority: int = 0
    """Used to rank workflows when deciding which to run next. Higher is more important"""
    reasons: list[str] = Field(default_factory=list)
    """Allow the scheduler to provide reasons for its decisions"""


class Workflow(WorkflowDefinition):
    """Container for a workflow run"""

    scheduler_metadata: SchedulerMetadata = Field(default_factory=SchedulerMetadata)
    """scheduler information for the workflow run"""
    label: Optional[str] = None
    """Label for the workflow run"""
    workflow_id: str = Field(default_factory=new_ulid_str)
    """ID of the workflow run"""
    steps: list[Step] = Field(default_factory=list)
    """Processed Steps of the flow"""
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """parameter values used in this workflow"""
    ownership_info: OwnershipInfo = Field(default_factory=get_current_ownership_info)
    """Ownership information for the workflow run"""
    status: WorkflowStatus = Field(default_factory=WorkflowStatus)
    """current status of the workflow"""
    step_index: int = 0
    """Index of the current step"""
    simulate: bool = False
    """Whether or not this workflow is being simulated"""
    submitted_time: Optional[datetime] = None
    """Time workflow was submitted to the scheduler"""
    start_time: Optional[datetime] = None
    """Time the workflow started running"""
    end_time: Optional[datetime] = None
    """Time the workflow finished running"""
    step_definitions: list[StepDefinition] = Field(default_factory=list)
    """The original step definitions for the workflow"""

    @model_validator(mode="after")
    def validate_workflow_parameters(self) -> "Workflow":
        """Validate that all parameters are provided"""
        for param in self.parameters:
            if (
                isinstance(param, WorkflowValueParameter)
                and param.default is None
                and param.name not in self.parameter_values
            ):
                raise ValueError(
                    f"Parameter {param.name} must be provided when running the workflow"
                )
            if (
                isinstance(param, WorkflowFileParameter)
                and param.default is None
                and param.name not in self.parameter_values
            ):
                raise ValueError(
                    f"File parameter {param.name} must be provided when running the workflow"
                )
        return self

    def get_step_by_name(self, name: str) -> Step:
        """Return the step object by its name"""
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(f"Step {name} not found in workflow run {self.run_id}")

    def get_step_by_id(self, id: str) -> Step:
        """Return the step object indexed by its id"""
        for step in self.steps:
            if step.id == id:
                return step
        raise KeyError(f"Step {id} not found in workflow run {self.run_id}")

    def get_datapoint_id_by_label(self, label: str) -> str:
        """Return the ID of the first datapoint with the given label in a workflow run"""
        for step in self.steps:
            if step.result.data:
                for key in step.result.data:
                    if key == label:
                        return step.result.data[key]
        raise KeyError(f"Label {label} not found in workflow run {self.run_id}")

    def get_all_datapoint_ids_by_label(self, label: str) -> list[str]:
        """Return the IDs of all datapoints with the given label in a workflow run"""
        ids = []
        for step in self.steps:
            if step.result.data:
                for key in step.result.data:
                    if key == label:
                        ids.append(step.result.data[key])
        if not ids:
            raise KeyError(f"Label {label} not found in workflow run {self.run_id}")
        return ids

    @computed_field
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate the duration of the workflow run"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    is_ulid = field_validator("workflow_id")(ulid_validator)

    @computed_field
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate the duration of the workflow in seconds."""
        if self.duration:
            return self.duration.total_seconds()
        return None

    @computed_field
    @property
    def completed_steps(self) -> int:
        """Count of completed steps."""
        return sum(1 for step in self.steps if step.status == ActionStatus.SUCCEEDED)

    @computed_field
    @property
    def failed_steps(self) -> int:
        """Count of failed steps."""
        return sum(1 for step in self.steps if step.status == ActionStatus.FAILED)

    @computed_field
    @property
    def skipped_steps(self) -> int:
        """Count of skipped steps."""
        return sum(1 for step in self.steps if step.status == ActionStatus.CANCELLED)

    @computed_field
    @property
    def step_statistics(self) -> dict[str, int]:
        """Complete step statistics."""
        return {
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "total_steps": len(self.steps),
        }
