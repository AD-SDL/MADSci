"""Types for MADSci Worfklow parameters."""

from enum import Enum
from typing import Any, Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic.functional_validators import model_validator


class WorkflowInputValue(MadsciBaseModel):
    """container for a workflow input value"""

    input_key: str
    """The key of the parameter in the parameters dictionary"""
    description: Optional[str] = None
    """A description of the parameter file"""
    default: Optional[Any] = None
    """The default value of a parameter, if not provided, the parameter must be provided when the workflow is run"""
    parameter_type: Optional[str] = None
    """The python type of the parameter value"""

    @model_validator(mode="after")
    def validate_value_parameters(self) -> "WorkflowInputValue":
        """Assert that at most one of step_name, step_index, and label are set."""
        if self.parameter_type is not None and self.default is not None:
            if not type(self.default).__name__ == self.parameter_type or (
                "Union" in self.parameter_type
                and type(self.default).__name__ not in str(self.parameter_type)
            ):
                return ValueError("Default value is of the wrong type")
        return self


class InputFile(MadsciBaseModel):
    """Input files for the workflow"""

    input_file_key: str
    """The key of the input file in the files input dictionary"""
    description: Optional[str] = None
    """A description of the input file"""


class FeedForwardValueType(str, Enum):
    """The type of a MADSci node."""

    VALUE = "value"
    FILE = "file"
    OBJECT = "object"


class FeedForwardValue(MadsciBaseModel):
    """container for a workflow parameter"""

    name: str
    """The name of the parameter"""
    step_name: Optional[str] = None
    """Name of a step in the workflow; this will use the value of a datapoint from the step with the matching name as the value for this parameter"""
    step_index: Optional[str] = None
    """Index of a step in the workflow; this will use the value of a datapoint from the step with the matching index as the value for this parameter"""
    value_type: Optional[FeedForwardValueType] = None
    """The python type of the parameter value"""
    label: str
    """This will use the value of a datapoint from a previous step with the matching label."""

    @model_validator(mode="after")
    def validate_feedforward_parameters(self) -> "FeedForwardValue":
        """Assert that at most one of step_name, step_index, and label are set."""
        if self.step_name and self.step_index:
            raise ValueError("Cannot set both step_name and step_index for a parameter")

        return self
