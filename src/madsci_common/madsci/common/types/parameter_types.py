"""Types for MADSci Worfklow parameters."""

from enum import Enum
from typing import Any, Optional

from madsci.common.types.base_types import MadsciBaseModel
from pydantic.functional_validators import model_validator


class InputValue(MadsciBaseModel):
    """container for a workflow input value"""

    key: str
    """The key of the parameter in the parameters dictionary"""
    description: Optional[str] = None
    """A description of the parameter file"""
    default: Optional[Any] = None
    """The default value of a parameter, if not provided, the parameter must be provided when the workflow is run"""
    
   

class InputFile(MadsciBaseModel):
    """Input files for the workflow"""

    key: str
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

    key: str
    """The name of the parameter"""
    description: Optional[str] = None
    """A description of the input file"""
    step_key: Optional[str] = None
    """Key of a step in the workflow; this will use the value of a datapoint from the step with the matching name as the value for this parameter"""
    step_index: Optional[str] = None
    """Index of a step in the workflow; this will use the value of a datapoint from the step with the matching index as the value for this parameter"""
    value_type: Optional[FeedForwardValueType] = None
    """The python type of the parameter value"""
    label: str
    """This will use the value of a datapoint from a previous step with the matching label."""

    @model_validator(mode="after")
    def validate_feedforward_parameters(self) -> "FeedForwardValue":
        """Assert that at most one of step_name, step_index, and label are set."""
        if self.step_key and self.step_index:
            raise ValueError("Cannot set both step_name and step_index for a parameter")

        return self
