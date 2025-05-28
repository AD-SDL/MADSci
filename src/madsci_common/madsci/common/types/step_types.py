"""Types for MADSci Steps."""

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.base_types import MadsciBaseModel, PathLike
from madsci.common.types.condition_types import Conditions
from madsci.common.types.location_types import LocationArgument
from madsci.common.utils import new_ulid_str
from pydantic import Field


class StepDefinition(MadsciBaseModel):
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
    node: str = Field(title="Node Name", description="Name of the node to run on")
    args: dict[str, Any] = Field(
        title="Step Arguments",
        description="Arguments for the step action.",
        default_factory=dict,
    )
    files: dict[str, Optional[PathLike]] = Field(
        title="Step File Arguments",
        description="Files to be used in the step. Key is the name of the file argument, value is the path to the file.",
        default_factory=dict,
    )
    locations: dict[str, Optional[Union[str, LocationArgument]]] = Field(
        title="Step Location Arguments",
        description="Locations to be used in the step. Key is the name of the argument, value is the name of the location, or a Location object.",
        default_factory=dict,
    )
    conditions: list[Conditions] = Field(
        title="Step Conditions",
        description="Conditions for running the step",
        default_factory=list,
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
    result: Optional[ActionResult] = Field(
        title="Latest Step Result",
        description="The result of the latest action run.",
        default=None,
    )
    history: list[ActionResult] = Field(
        title="Step History",
        description="The history of the results of the step.",
        default_factory=list,
    )
    start_time: Optional[datetime] = None
    """Time the step started running"""
    end_time: Optional[datetime] = None
    """Time the step finished running"""
    duration: Optional[timedelta] = None
    """Duration of the step's run"""
