"""Types for MADSci Worfklow running."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from madsci.client.data_client import DataPointTypeEnum
else:
    try:
        from madsci.client.data_client import DataPointTypeEnum
    except ImportError:
        # Fallback for circular import situations
        class DataPointTypeEnum:
            """Fallback enum for data point types during import resolution."""

            FILE = "FILE"
            JSON = "JSON"
            OBJECT_STORAGE = "OBJECT_STORAGE"


from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.action_types import ActionStatus
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.parameter_types import (
    ParameterFeedForwardFile,
    ParameterFeedForwardJson,
    ParameterInputFile,
    ParameterInputJson,
    ParameterTypes,
)
from madsci.common.types.step_types import Step, StepDefinition
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic.functional_validators import model_validator


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


class WorkflowParameters(MadsciBaseModel):
    """container for all of the workflow parameters"""

    json_inputs: list[ParameterInputJson] = Field(
        default_factory=list,
        alias=AliasChoices("json_inputs", "value_inputs", "json", "inputs"),
    )
    """JSON serializable value inputs to the workflow"""

    file_inputs: list[ParameterInputFile] = Field(
        default_factory=list, alias=AliasChoices("file_inputs", "files")
    )
    """Required file inputs to the workflow"""

    feed_forward: list[Union[ParameterFeedForwardJson, ParameterFeedForwardFile]] = (
        Field(default_factory=list)
    )
    """Parameters based on datapoints generated during execution of the workflow"""


class WorkflowMetadata(MadsciBaseModel, extra="allow"):
    """Metadata container"""

    author: Optional[str] = None
    """Who wrote this workflow definition"""
    description: Optional[str] = None
    """Description of the workflow definition"""
    version: Union[float, str] = ""
    """Version of the workflow definition"""
    ownership_info: Optional[OwnershipInfo] = None
    """OwnershipInfo for this workflow definition"""


class WorkflowDefinition(MadsciBaseModel):
    """Grand container that pulls all info of a workflow together"""

    name: str
    """Name of the workflow"""
    workflow_definition_id: str = Field(default_factory=new_ulid_str)
    """ID of the workflow definition"""
    definition_metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    """Information about the flow"""
    parameters: Union[WorkflowParameters, list[ParameterTypes]] = Field(
        default_factory=WorkflowParameters,
        alias=AliasChoices(
            "parameters", "params", "workflow_params", "workflow_parameters"
        ),
    )
    """Parameters used in the workflow"""

    steps: list[StepDefinition] = Field(default_factory=list)
    """User Submitted Steps of the flow"""

    @field_validator("steps", mode="after")
    @classmethod
    def ensure_data_label_and_step_key_uniqueness(cls, v: Any) -> Any:
        """Ensure that the names of the data labels are unique"""
        labels = []
        keys = []
        for step in v:
            if step.key:
                if step.key in keys:
                    raise ValueError("Step keys must be unique across workflow")
                keys.append(step.key)
            if step.data_labels:
                for key in step.data_labels:
                    if step.data_labels[key] in labels:
                        raise ValueError("Data labels must be unique across workflow")
                    labels.append(step.data_labels[key])
        return v

    @field_validator("parameters", mode="after")
    @classmethod
    def promote_parameters_list_to_data_model(cls, v: Any) -> Any:
        """Promote parameters to data model form"""
        if isinstance(v, list):
            new_parameters = WorkflowParameters()
            for param in v:
                if isinstance(param, ParameterInputJson):
                    new_parameters.json_inputs.append(param)
                elif isinstance(param, ParameterInputFile):
                    new_parameters.file_inputs.append(param)
                elif isinstance(
                    param,
                    (
                        ParameterFeedForwardJson,
                        ParameterFeedForwardFile,
                    ),
                ):
                    new_parameters.feed_forward.append(param)
            return new_parameters
        return v

    @model_validator(mode="after")
    def promote_inline_step_parameters(self) -> Any:
        """Promote inline step parameters to workflow level parameters."""
        # Ensure parameters is a WorkflowParameters object
        if isinstance(self.parameters, list):
            raise ValueError(
                "Parameters should be WorkflowParameters object by this point"
            )

        promoted_params = {}

        # Process each step to find inline parameters
        for step in self.steps:
            # Check step files field for inline file parameters
            for file_key, file_value in list(step.files.items()):
                if isinstance(
                    file_value,
                    (ParameterInputFile, ParameterFeedForwardFile),
                ):
                    param_key = file_value.key
                    promoted_params[param_key] = file_value
                    step.files[file_key] = param_key

            if step.use_parameters:
                self._extract_inline_params_from_step_fields(step, promoted_params)
                self._extract_inline_params_from_step_dicts(step, promoted_params)

        # Add promoted parameters to workflow parameters
        self._add_promoted_params_to_workflow(promoted_params)

        return self

    def _extract_inline_params_from_step_fields(
        self, step: StepDefinition, promoted_params: dict[str, ParameterTypes]
    ) -> None:
        """Extract inline parameters from step fields."""
        param_types = (
            ParameterInputJson,
            ParameterFeedForwardJson,
            ParameterFeedForwardFile,
            ParameterInputFile,
        )

        for field_name, field_value in [
            ("name", step.use_parameters.name),
            ("description", step.use_parameters.description),
            ("action", step.use_parameters.action),
            ("node", step.use_parameters.node),
        ]:
            if isinstance(field_value, param_types):
                param_key = field_value.key
                promoted_params[param_key] = field_value
                setattr(step.use_parameters, field_name, param_key)

    def _extract_inline_params_from_step_dicts(
        self, step: StepDefinition, promoted_params: dict[str, ParameterTypes]
    ) -> None:
        """Extract inline parameters from step args and locations dicts."""
        param_types = (
            ParameterInputJson,
            ParameterFeedForwardJson,
            ParameterFeedForwardFile,
            ParameterInputFile,
        )

        # Check args dict
        for arg_key, arg_value in list(step.use_parameters.args.items()):
            if isinstance(arg_value, param_types):
                param_key = arg_value.key
                promoted_params[param_key] = arg_value
                step.use_parameters.args[arg_key] = param_key

        # Check locations dict
        for loc_key, loc_value in list(step.use_parameters.locations.items()):
            if isinstance(loc_value, param_types):
                param_key = loc_value.key
                promoted_params[param_key] = loc_value
                step.use_parameters.locations[loc_key] = param_key

    def _add_promoted_params_to_workflow(
        self, promoted_params: dict[str, ParameterTypes]
    ) -> None:
        """Add promoted parameters to workflow parameters."""
        for param in promoted_params.values():
            if isinstance(param, ParameterInputJson):
                self.parameters.json_inputs.append(param)
            elif isinstance(param, ParameterInputFile):
                self.parameters.file_inputs.append(param)
            elif isinstance(
                param,
                (ParameterFeedForwardJson, ParameterFeedForwardFile),
            ):
                self.parameters.feed_forward.append(param)

    @model_validator(mode="after")
    def ensure_param_key_uniqueness(self) -> Any:
        """Ensure that all parameter keys are unique"""
        labels = []
        error = ValueError("Input value keys must be unique across workflow definition")
        for json_input in self.parameters.json_inputs:
            if json_input.key in labels:
                raise error
            labels.append(json_input.key)
        for ffv in self.parameters.feed_forward:
            if ffv.key in labels:
                raise error
            labels.append(ffv.key)
        for file_input in self.parameters.file_inputs:
            if file_input.key in labels:
                raise error
            labels.append(file_input.key)
        return self

    @model_validator(mode="after")
    def ensure_all_param_keys_have_matching_parameters(self) -> "WorkflowDefinition":
        """Ensures that all step parameters have matching workflow parameters."""

        file_param_keys = [param.key for param in self.parameters.file_inputs] + [
            param.key
            for param in self.parameters.feed_forward
            if param.data_type
            in [DataPointTypeEnum.FILE, DataPointTypeEnum.OBJECT_STORAGE]
        ]
        json_param_keys = [param.key for param in self.parameters.json_inputs] + [
            param.key
            for param in self.parameters.feed_forward
            if param.data_type == DataPointTypeEnum.JSON
        ]

        def validate_keys(
            keys: list[Optional[str]], valid_keys: list[str], error_msg: str
        ) -> None:
            """Validate that all keys are in the list of valid keys."""
            for key in keys:
                if key is not None and key not in valid_keys:
                    raise ValueError(error_msg.format(key=key, step=step.name))

        for step in self.steps:
            if step.files:
                validate_keys(
                    step.files.values(),
                    file_param_keys,
                    "Step {step}: File Parameter {key} not found in workflow parameters",
                )

            if step.use_parameters is not None:
                validate_keys(
                    step.use_parameters.args.values(),
                    json_param_keys,
                    "Step {step}: Argument Parameter {key} not found in workflow parameters",
                )
                validate_keys(
                    step.use_parameters.locations.values(),
                    json_param_keys,
                    "Step {step}: Location Parameter {key} not found in workflow parameters",
                )
                for field_name, field_value in [
                    ("name", step.use_parameters.name),
                    ("description", step.use_parameters.description),
                    ("action", step.use_parameters.action),
                    ("node", step.use_parameters.node),
                ]:
                    if field_value is not None and field_value not in json_param_keys:
                        raise ValueError(
                            f"Parameter {field_value} for field {field_name} of step {step.name} not found in workflow parameters"
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
    file_input_paths: dict[str, str] = Field(default_factory=dict)
    """The paths to the original input files on the experiment computer, used for records purposes"""
    file_input_ids: dict[str, str] = Field(default_factory=dict)
    """The datapoint ids of the input files """
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
