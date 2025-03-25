"""Types for MADSci Worfklow running."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Union

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.step_types import Step, StepDefinition
from madsci.common.validators import ulid_validator
from pydantic import Field, field_validator


class WorkflowStatus(str, Enum):
    """Status for a workflow run"""

    QUEUED = "queued"
    """Workflow run is queued, hasn't started yet"""
    RUNNING = "running"
    """Workflow is currently running a step"""
    IN_PROGRESS = "in_progress"
    """Workflow has started, but is not actively running a step"""
    COMPLETED = "completed"
    """Workflow has completed"""
    FAILED = "failed"
    """Workflow has failed"""
    UNKNOWN = "unknown"
    """Workflow status is unknown"""
    CANCELLED = "cancelled"
    """Workflow has been cancelled"""

    @property
    def is_active(self) -> bool:
        """Whether or not the workflow run is active"""
        return self in [
            WorkflowStatus.QUEUED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.IN_PROGRESS,
        ]


class WorkflowParameter(BaseModel):
    """container for a workflow parameter"""

    name: str
    """the name of the parameter"""
    default: Optional[Any] = None
    """ the default value of the parameter"""


class WorkflowMetadata(BaseModel, extra="allow"):
    """Metadata container"""

    author: Optional[str] = None
    """Who wrote this object"""
    description: Optional[str] = None
    """Description of the object"""
    version: Union[float, str] = ""
    """Version of the object"""


class WorkflowDefinition(BaseModel):
    """Grand container that pulls all info of a workflow together"""

    name: str
    """Name of the workflow"""
    workflow_metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    """Information about the flow"""
    parameters: Optional[list[WorkflowParameter]] = Field(default_factory=list)
    """Inputs to the workflow"""
    steps: list[StepDefinition] = Field(default_factory=list)
    """User Submitted Steps of the flow"""

    @field_validator("steps", mode="after")
    @classmethod
    def ensure_data_label_uniqueness(cls, v: Any) -> Any:
        """Ensure that the names of the arguments and files are unique"""
        labels = []
        for step in v:
            if step.data_labels:
                for key in step.data_labels:
                    if step.data_labels[key] in labels:
                        raise ValueError("Data labels must be unique across workflow")
                    labels.append(step.data_labels[key])
        return v


class SchedulerMetadata(BaseModel):
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
    ownership_info: OwnershipInfo = Field(default_factory=OwnershipInfo)
    """ID of the experiment this workflow is a part of"""
    status: WorkflowStatus = Field(default=WorkflowStatus.QUEUED)
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
    duration: Optional[timedelta] = None
    """Duration of the workflow's run"""
    paused: Optional[bool] = False
    """whether or not the workflow is paused"""
    step_definitions: list[StepDefinition] = Field(default_factory=list)
    """The original step definitions for the workflow"""

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

    is_ulid = field_validator("workflow_id")(ulid_validator)
