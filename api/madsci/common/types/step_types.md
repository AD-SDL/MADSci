Module madsci.common.types.step_types
=====================================
Types for MADSci Steps.

Classes
-------

`Step(**data: Any)`
:   A runtime representation of a step in a workflow.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.step_types.StepDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `duration: datetime.timedelta | None`
    :   Duration of the step's run

    `end_time: datetime.datetime | None`
    :   Time the step finished running

    `file_paths: dict[str, madsci.common.types.parameter_types.ParameterInputFile | str]`
    :

    `history: list[madsci.common.types.action_types.ActionResult]`
    :

    `last_status_update: datetime.datetime | None`
    :

    `model_config`
    :

    `result: madsci.common.types.action_types.ActionResult | None`
    :

    `start_time: datetime.datetime | None`
    :   Time the step started running

    `status: madsci.common.types.action_types.ActionStatus`
    :

    `step_id: str`
    :

`StepDefinition(**data: Any)`
:   A definition of a step in a workflow.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.step_types.Step

    ### Class variables

    `action: str | None`
    :

    `args: dict[str, typing.Any]`
    :

    `conditions: list[madsci.common.types.condition_types.ResourceInLocationCondition | madsci.common.types.condition_types.NoResourceInLocationCondition | madsci.common.types.condition_types.ResourceFieldCheckCondition | madsci.common.types.condition_types.ResourceChildFieldCheckCondition]`
    :

    `data_labels: dict[str, str]`
    :

    `description: str | None`
    :

    `files: dict[str, madsci.common.types.parameter_types.ParameterInputFile | madsci.common.types.parameter_types.ParameterFeedForwardFile | str]`
    :

    `key: str | None`
    :

    `locations: dict[str, str | madsci.common.types.location_types.LocationArgument | None]`
    :

    `model_config`
    :

    `name: str | None`
    :

    `node: str | None`
    :

    `use_parameters: madsci.common.types.step_types.StepParameters | None`
    :

    ### Methods

    `check_action_or_action_parameter(self) ‑> madsci.common.types.step_types.StepDefinition`
    :   Ensure that either an action or action parameter is provided.

`StepParameters(**data: Any)`
:   The set of values that are parameterized in the step, depending on either workflow inputs or outputs from prior steps.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `action: str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson | None`
    :

    `args: dict[str, str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson]`
    :

    `description: str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson | None`
    :

    `locations: dict[str, str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson]`
    :

    `model_config`
    :

    `name: str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson | None`
    :

    `node: str | madsci.common.types.parameter_types.ParameterInputJson | madsci.common.types.parameter_types.ParameterFeedForwardJson | None`
    :
