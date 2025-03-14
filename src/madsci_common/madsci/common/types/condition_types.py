"""Types for MADSci Conditions."""

from enum import Enum
from typing import Annotated, Literal, Optional, Union

from madsci.common.types.base_types import BaseModel
from madsci.common.types.resource_types import GridIndex, GridIndex2D, GridIndex3D
from pydantic import Discriminator
from sqlmodel.main import Field


class ConditionTypeEnum(str, Enum):
    """Types of conditional check for a step"""

    RESOURCE_PRESENT = "resource_present"
    NO_RESOURCE_PRESENT = "no_resource_present"

    @classmethod
    def _missing_(cls, value: str) -> "ConditionTypeEnum":
        """Convert the value to lowercase"""
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ConditionType: {value}")


class Condition(BaseModel, extra="allow"):
    """A model for the conditions a step needs to be run"""


class ResourceInLocationCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.RESOURCE_PRESENT] = Field(
        title="Condition Type",
        description="The type of condition to check",
        const=ConditionTypeEnum.RESOURCE_PRESENT,
    )
    location: Optional[str] = Field(
        title="Location",
        description="The name or ID of the location to check for a resource in",
        default=None,
    )
    key: Optional[Union[str, int, GridIndex, GridIndex2D, GridIndex3D]] = Field(
        title="Key",
        description="The key to check in the location's container resource",
        default=None,
    )


class NoResourceInLocationCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.NO_RESOURCE_PRESENT] = Field(
        title="Condition Type",
        description="The type of condition to check",
        const=ConditionTypeEnum.NO_RESOURCE_PRESENT,
    )
    location: Optional[str] = Field(
        title="Location",
        description="The name or ID of the location to check for a resource in",
        default=None,
    )
    key: Optional[Union[str, int, GridIndex, GridIndex2D, GridIndex3D]] = Field(
        title="Key",
        description="The key to check in the location's container resource",
        default=None,
    )


Conditions = Annotated[
    Union[ResourceInLocationCondition, NoResourceInLocationCondition],
    Discriminator(
        discriminator="condition_type",
    ),
]
