Module madsci.common.types.parameter_types
==========================================
Types for MADSci Worfklow parameters.

Classes
-------

`ParameterFeedForwardFile(**data: Any)`
:   Definition of a workflow parameter that is fed forward from a previous step (file).

    Notes
    -----
    - Either 'step' or 'label' must be provided.
    - If only 'step' is provided, the parameter value will be taken from the step with the matching index or key. If there are multiple datapoints, the first will be used.
    - If only 'label' is provided, the parameter value will be taken from the most recent datapoint with the matching label.
    - If both 'step' and 'label' are provided, the parameter value will be taken from the matching step and label.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `data_type: Literal[<DataPointTypeEnum.FILE: 'file'>, <DataPointTypeEnum.OBJECT_STORAGE: 'object_storage'>]`
    :   This specifies that the parameter expects file or object storage data.

    `label: str | None`
    :   This must match the label of a datapoint from the step with the matching name or index. If not specified, the first datapoint will be used.

    `model_config`
    :

    `parameter_type: Literal['feed_forward_file']`
    :   The type of the parameter

    `step: int | str`
    :   Index or key of the step to pull the parameter from.

`ParameterFeedForwardJson(**data: Any)`
:   Definition of a workflow parameter that is fed forward from a previous step (JSON value).

    Notes
    -----
    - Either 'step' or 'label' must be provided.
    - If only 'step' is provided, the parameter value will be taken from the step with the matching index or key. If there are multiple datapoints, the first will be used.
    - If only 'label' is provided, the parameter value will be taken from the most recent datapoint with the matching label.
    - If both 'step' and 'label' are provided, the parameter value will be taken from the matching step and label.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `data_type: Literal[<DataPointTypeEnum.JSON: 'json'>]`
    :   This specifies that the parameter expects JSON data.

    `label: str | None`
    :   This must match the label of a return value from the step with the matching name or index. If not specified, the full json result will be used

    `model_config`
    :

    `parameter_type: Literal['feed_forward_json']`
    :   The type of the parameter

    `step: int | str`
    :   Index or key of the step to pull the parameter from.

`ParameterInputFile(**data: Any)`
:   Definition of a workflow parameter input file

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `parameter_type: Literal['file_input']`
    :   The type of the parameter

`ParameterInputJson(**data: Any)`
:   Definition of a workflow parameter input value

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.parameter_types.WorkflowParameter
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `default: Any | None`
    :   The default value of the parameter; if not provided, the parameter must be set when the workflow is run

    `model_config`
    :

    `parameter_type: Literal['json_input']`
    :   The type of the parameter

`WorkflowParameter(**data: Any)`
:   Definition of a workflow parameter

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.parameter_types.ParameterFeedForwardFile
    * madsci.common.types.parameter_types.ParameterFeedForwardJson
    * madsci.common.types.parameter_types.ParameterInputFile
    * madsci.common.types.parameter_types.ParameterInputJson

    ### Class variables

    `description: str | None`
    :   A description of the parameter

    `key: str`
    :   The unique key of the parameter

    `model_config`
    :
