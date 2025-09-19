"""Types for MADSci Steps."""

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.condition_types import Conditions
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.parameter_types import (
    ParameterInputFile,
    ParameterInputFileTypes,
    ParameterJsonTypes,
)
from madsci.common.utils import new_ulid_str
from pydantic import AliasChoices, Field, model_validator


class StepParameters(MadsciBaseModel):
    """The set of values that are parameterized in the step, depending on either workflow inputs or outputs from prior steps."""

    name: Optional[Union[str, ParameterJsonTypes]] = Field(
        title="Step Name", description="The name of the step.", default=None
    )
    description: Optional[Union[str, ParameterJsonTypes]] = Field(
        title="Step Description",
        description="A description of the step.",
        default=None,
    )
    action: Optional[Union[str, ParameterJsonTypes]] = Field(
        title="Step Action",
        description="The action to perform in the step.",
        default=None,
    )
    node: Optional[Union[str, ParameterJsonTypes]] = Field(
        title="Node Name", description="Name of the node to run on", default=None
    )
    args: dict[str, Union[str, ParameterJsonTypes]] = Field(
        title="Step Arguments",
        description="Arguments for the step action.",
        default_factory=dict,
    )
    locations: dict[str, Union[str, ParameterJsonTypes]] = Field(
        title="Step Location Arguments",
        description="Locations to be used in the step. Key is the name of the argument, value is the name of the location, or a Location object.",
        default_factory=dict,
    )


class StepDefinition(MadsciBaseModel):
    """A definition of a step in a workflow."""

    name: Optional[str] = Field(
        title="Step Name",
        description="The name of the step.",
        default=None,
    )
    key: Optional[str] = Field(
        title="Step Key", description="A unique key for the step.", default=None
    )
    description: Optional[str] = Field(
        title="Step Description",
        description="A description of the step.",
        default=None,
    )
    action: Optional[str] = Field(
        title="Step Action",
        description="The action to perform in this step.",
        default=None,
    )
    node: Optional[str] = Field(
        title="Node Name",
        description="Name of the target node to run on. Omit for built-in workcell actions.",
        default=None,
    )
    args: dict[str, Any] = Field(
        title="Step Arguments",
        description="Arguments for the step action.",
        default_factory=dict,
    )
    files: dict[str, Union[ParameterInputFileTypes, str]] = Field(
        title="Step File Arguments",
        description="Files to be used in the step. Key is the name of the argument, value is a file parameter key or definition",
        default_factory=dict,
    )
    locations: dict[str, Optional[Union[str, LocationArgument]]] = Field(
        title="Step Location Arguments",
        description="Locations to be used in the step. Key is the name of the argument, value is the name of the location, or a Location object.",
        default_factory=dict,
    )
    conditions: list[Conditions] = Field(
        title="Step Conditions",
        description="Conditions that must be met before running the step",
        default_factory=list,
    )
    data_labels: dict[str, str] = Field(
        title="Step Data Labels",
        description="Data labels for the results of the step. Maps from the names of the outputs of the action to the names of the data labels.",
        default_factory=dict,
    )
    use_parameters: Optional[StepParameters] = Field(
        title="Workflow Parameters in Step",
        description="Parameters from the workflow to use in this step.",
        default=None,
        alias=AliasChoices("use_parameters", "use_params", "params", "parameters"),
    )

    @model_validator(mode="after")
    def check_action_or_action_parameter(self) -> "StepDefinition":
        """Ensure that either an action or action parameter is provided."""
        if not self.action and (
            not self.use_parameters or not self.use_parameters.action
        ):
            raise ValueError(
                f"Step {self.name} ({self.key}) must have either an action or action parameter"
            )
        return self


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

    file_paths: dict[str, Union[ParameterInputFile, str]] = Field(
        title="Step File Paths",
        description="File paths to be used in the step. path is a temp path on the workcell manager",
        default_factory=dict,
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
    last_status_update: Optional[datetime] = Field(
        title="Last Status Update Time",
        description="The time the status was last updated.",
        default=None,
    )
    start_time: Optional[datetime] = None
    """Time the step started running"""
    end_time: Optional[datetime] = None
    """Time the step finished running"""
    duration: Optional[timedelta] = None
    """Duration of the step's run"""
