Module madsci.common.types.workflow_types
=========================================
Types for MADSci Worfklow running.

Classes
-------

`SchedulerMetadata(**data: Any)`
:   Scheduler information

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

    `priority: int`
    :   Used to rank workflows when deciding which to run next. Higher is more important

    `ready_to_run: bool`
    :   Whether or not the next step in the workflow is ready to run

    `reasons: list[str]`
    :   Allow the scheduler to provide reasons for its decisions

`Workflow(**data: Any)`
:   Container for a workflow run

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.workflow_types.WorkflowDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `end_time: datetime.datetime | None`
    :   Time the workflow finished running

    `file_input_ids: dict[str, str]`
    :   The datapoint ids of the input files

    `file_input_paths: dict[str, str]`
    :   The paths to the original input files on the experiment computer, used for records purposes

    `label: str | None`
    :   Label for the workflow run

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo`
    :   Ownership information for the workflow run

    `parameter_values: dict[str, typing.Any]`
    :   parameter values used in this workflow

    `scheduler_metadata: madsci.common.types.workflow_types.SchedulerMetadata`
    :   scheduler information for the workflow run

    `simulate: bool`
    :   Whether or not this workflow is being simulated

    `start_time: datetime.datetime | None`
    :   Time the workflow started running

    `status: madsci.common.types.workflow_types.WorkflowStatus`
    :   current status of the workflow

    `step_definitions: list[madsci.common.types.step_types.StepDefinition]`
    :   The original step definitions for the workflow

    `step_index: int`
    :   Index of the current step

    `submitted_time: datetime.datetime | None`
    :   Time workflow was submitted to the scheduler

    `workflow_id: str`
    :   ID of the workflow run

    ### Instance variables

    `completed_steps: int`
    :   Count of completed steps.

    `duration: datetime.timedelta | None`
    :   Calculate the duration of the workflow run

    `duration_seconds: float | None`
    :   Calculate the duration of the workflow in seconds.

    `failed_steps: int`
    :   Count of failed steps.

    `skipped_steps: int`
    :   Count of skipped steps.

    `step_statistics: dict[str, int]`
    :   Complete step statistics.

    ### Methods

    `get_datapoint(self, step_key: str | None = None, label: str | None = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Return the first datapoint in a workflow run matching the given step key and/or label.

    `get_datapoint_id(self, step_key: str | None = None, label: str | None = None) ‑> str`
    :   Return the ID of the first datapoint in a workflow run matching the given step key and/or label.

    `get_step_by_id(self, id: str) ‑> madsci.common.types.step_types.Step`
    :   Return the step object indexed by its id

    `get_step_by_key(self, key: str) ‑> madsci.common.types.step_types.Step`
    :   Return the step object by its name

    `get_step_by_name(self, name: str) ‑> madsci.common.types.step_types.Step`
    :   Return the step object by its name

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`WorkflowDefinition(**data: Any)`
:   Grand container that pulls all info of a workflow together

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.workflow_types.Workflow

    ### Class variables

    `definition_metadata: madsci.common.types.workflow_types.WorkflowMetadata`
    :   Information about the flow

    `model_config`
    :

    `name: str`
    :   Name of the workflow

    `parameters: madsci.common.types.workflow_types.WorkflowParameters | list[madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterInputFile | madsci.common.types.parameter_types.ParameterFeedForwardJson | madsci.common.types.parameter_types.ParameterFeedForwardFile]`
    :   Parameters used in the workflow

    `steps: list[madsci.common.types.step_types.StepDefinition]`
    :   User Submitted Steps of the flow

    `workflow_definition_id: str`
    :   ID of the workflow definition

    ### Static methods

    `ensure_step_key_uniqueness(v: Any) ‑> Any`
    :   Ensure that the names of the data labels are unique

    `promote_parameters_list_to_data_model(v: Any) ‑> Any`
    :   Promote parameters to data model form

    ### Methods

    `ensure_all_param_keys_have_matching_parameters(self) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Ensures that all step parameters have matching workflow parameters.

    `ensure_param_key_uniqueness(self) ‑> Any`
    :   Ensure that all parameter keys are unique

    `promote_inline_step_parameters(self) ‑> Any`
    :   Promote inline step parameters to workflow level parameters.

`WorkflowMetadata(**data: Any)`
:   Metadata container

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `author: str | None`
    :   Who wrote this workflow definition

    `description: str | None`
    :   Description of the workflow definition

    `model_config`
    :

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo | None`
    :   OwnershipInfo for this workflow definition

    `version: float | str`
    :   Version of the workflow definition

`WorkflowParameters(**data: Any)`
:   container for all of the workflow parameters

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `feed_forward: list[madsci.common.types.parameter_types.ParameterFeedForwardJson | madsci.common.types.parameter_types.ParameterFeedForwardFile]`
    :   Parameters based on datapoints generated during execution of the workflow

    `file_inputs: list[madsci.common.types.parameter_types.ParameterInputFile]`
    :   Required file inputs to the workflow

    `json_inputs: list[madsci.common.types.parameter_types.ParameterInputJson]`
    :   JSON serializable value inputs to the workflow

    `model_config`
    :

`WorkflowStatus(**data: Any)`
:   Representation of the status of a Workflow

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `cancelled: bool`
    :   Whether or not the workflow has been cancelled

    `completed: bool`
    :   Whether or not the workflow has completed successfully

    `current_step_index: int`
    :   Index of the current step

    `failed: bool`
    :   Whether or not the workflow has failed

    `has_started: bool`
    :   Whether or not at least one step of the workflow has been run

    `model_config`
    :

    `paused: bool`
    :   Whether or not the workflow is paused

    `running: bool`
    :   Whether or not the workflow is currently running

    ### Instance variables

    `active: bool`
    :   Whether or not the workflow is actively being scheduled

    `description: str`
    :   Description of the workflow's status

    `ok: bool`
    :   Whether or not the workflow is ok (i.e. not failed or cancelled)

    `queued: bool`
    :   Whether or not the workflow is queued

    `started: bool`
    :   Whether or not the workflow has started

    `terminal: bool`
    :   Whether or not the workflow is in a terminal state

    ### Methods

    `reset(self, step_index: int = 0) ‑> None`
    :   Reset the workflow status
