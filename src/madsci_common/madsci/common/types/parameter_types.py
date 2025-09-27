"""Types for MADSci Worfklow parameters."""

from typing import Any, Literal, Optional, Union

from madsci.common.types.base_types import Annotated, MadsciBaseModel
from madsci.common.types.datapoint_types import DataPointTypeEnum
from pydantic import Discriminator


class WorkflowParameter(MadsciBaseModel):
    """Definition of a workflow parameter"""

    key: str
    """The unique key of the parameter"""
    description: Optional[str] = None
    """A description of the parameter"""


class ParameterInputJson(WorkflowParameter):
    """Definition of a workflow parameter input value"""

    parameter_type: Literal["json_input"] = "json_input"
    """The type of the parameter"""
    default: Optional[Any] = None
    """The default value of the parameter; if not provided, the parameter must be set when the workflow is run"""


class ParameterInputFile(WorkflowParameter):
    """Definition of a workflow parameter input file"""

    parameter_type: Literal["file_input"] = "file_input"
    """The type of the parameter"""


class ParameterFeedForwardJson(WorkflowParameter):
    """Definition of a workflow parameter that is fed forward from a previous step (JSON value).

    Notes
    -----
    - Either 'step' or 'label' must be provided.
    - If only 'step' is provided, the parameter value will be taken from the step with the matching index or key. If there are multiple datapoints, the first will be used.
    - If only 'label' is provided, the parameter value will be taken from the most recent datapoint with the matching label.
    - If both 'step' and 'label' are provided, the parameter value will be taken from the matching step and label.
    """

    parameter_type: Literal["feed_forward_json"] = "feed_forward_json"
    """The type of the parameter"""
    step: Union[int, str] = None
    """Index or key of the step to pull the parameter from."""
    label: Optional[str] = None
    """This must match the label of a return value from the step with the matching name or index. If not specified, the full json result will be used"""
    data_type: Literal[DataPointTypeEnum.JSON] = DataPointTypeEnum.JSON
    """This specifies that the parameter expects JSON data."""


class ParameterFeedForwardFile(WorkflowParameter):
    """Definition of a workflow parameter that is fed forward from a previous step (file).

    Notes
    -----
    - Either 'step' or 'label' must be provided.
    - If only 'step' is provided, the parameter value will be taken from the step with the matching index or key. If there are multiple datapoints, the first will be used.
    - If only 'label' is provided, the parameter value will be taken from the most recent datapoint with the matching label.
    - If both 'step' and 'label' are provided, the parameter value will be taken from the matching step and label.
    """

    parameter_type: Literal["feed_forward_file"] = "feed_forward_file"
    """The type of the parameter"""
    step: Union[int, str] = None
    """Index or key of the step to pull the parameter from."""
    label: Optional[str] = None
    """This must match the label of a datapoint from the step with the matching name or index. If not specified, the first datapoint will be used."""
    data_type: Literal[DataPointTypeEnum.FILE, DataPointTypeEnum.OBJECT_STORAGE] = (
        DataPointTypeEnum.FILE
    )
    """This specifies that the parameter expects file or object storage data."""


ParameterJsonTypes = Annotated[
    Union[ParameterInputJson, ParameterFeedForwardJson],
    Discriminator("parameter_type"),
]

ParameterInputFileTypes = Annotated[
    Union[ParameterInputFile, ParameterFeedForwardFile],
    Discriminator("parameter_type"),
]

ParameterTypes = Annotated[
    Union[
        ParameterInputJson,
        ParameterInputFile,
        ParameterFeedForwardJson,
        ParameterFeedForwardFile,
    ],
    Discriminator("parameter_type"),
]
