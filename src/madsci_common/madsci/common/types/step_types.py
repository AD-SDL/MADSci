"""Types for MADSci Steps."""

from datetime import datetime, timedelta
from typing import Any, Optional

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.base_types import BaseModel, PathLike, new_ulid_str
from sqlmodel.main import Field


class StepDefinition(BaseModel):
    """A definition of a step in a workflow."""

    name: str = Field(
        title="Step Name",
        description="The name of the step.",
    )
    description: Optional[str] = Field(
        title="Step Description",
        description="A description of the step.",
        default=None,
    )
    action: str = Field(
        title="Step Action",
        description="The action to perform in the step.",
    )
    args: dict[str, Any] = Field(
        title="Step Arguments",
        description="Arguments for the step action.",
        default_factory=dict,
    )
    files: dict[str, PathLike] = Field(
        title="Step Files",
        description="Files to be used in the step.",
        default_factory=dict,
    )
    data_labels: dict[str, str] = Field(
        title="Step Data Labels",
        description="Data labels for the results of the step. Maps from the names of the outputs of the action to the names of the data labels.",
        default_factory=dict,
    )


class Step(StepDefinition):
    """A runtime representation of a step in a workflow."""

    step_id: str = Field(
        title="Step ID",
        description="The ID of the step.",
        default_factory=new_ulid_str,
    )
    status: ActionStatus = Field(
        title="Step Status",
        description="The status of the step.",
        default=ActionStatus.NOT_STARTED,
    )
    results: dict[str, ActionResult] = Field(
        title="Step Results",
        description="The results of the step.",
        default_factory=dict,
    )
    start_time: Optional[datetime] = None
    """Time the step started running"""
    end_time: Optional[datetime] = None
    """Time the step finished running"""
    duration: Optional[timedelta] = None
    """Duration of the step's run"""
