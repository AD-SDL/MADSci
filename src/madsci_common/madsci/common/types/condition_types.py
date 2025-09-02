"""Types for MADSci Conditions."""

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.resource_types import GridIndex, GridIndex2D, GridIndex3D
from pydantic import Discriminator, Field


class ConditionTypeEnum(str, Enum):
    """Types of conditional check for a step"""

    RESOURCE_PRESENT = "resource_present"
    NO_RESOURCE_PRESENT = "no_resource_present"
    RESOURCE_FIELD_CHECK = "resource_field_check"
    RESOURCE_CHILD_FIELD_CHECK = "resource_child_field_check"

    @classmethod
    def _missing_(cls, value: str) -> "ConditionTypeEnum":
        """Convert the value to lowercase"""
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        raise ValueError(f"Invalid ConditionType: {value}")


class OperatorTypeEnum(str, Enum):
    """Comparison operators for value checks"""

    IS_GREATER_THAN = ("is_greater_than",)
    IS_LESS_THAN = ("is_less_than",)
    IS_EQUAL_TO = ("is_equal_to",)
    IS_GREQUAL_TO = "is_greater_than_or_equal_to"
    IS_LEQUAL_TO = "is_less_than_or_equal_to"


class Condition(MadsciBaseModel, extra="allow"):
    """A model for the conditions a step needs to be run"""

    condition_type: Optional[ConditionTypeEnum] = Field(
        title="Condition Type",
        description="The type of condition to check",
        default=None,
    )
    condition_name: str = Field(
        title="Condition Name",
        description="Name of the Condition",
        default="A Condition",
    )


class ResourceInLocationCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.RESOURCE_PRESENT] = Field(
        title="Condition Type",
        description="The type of condition to check",
        default=ConditionTypeEnum.RESOURCE_PRESENT,
    )
    location_id: Optional[str] = Field(
        title="Location",
        description="The ID of the location to check for a resource in",
        default=None,
    )

    location_name: Optional[str] = Field(
        title="Location",
        description="The name of the location to check for a resource in",
        default=None,
    )
    key: Union[str, int, GridIndex, GridIndex2D, GridIndex3D] = Field(
        title="Key",
        description="The key to check in the location's container resource",
        default=0,
    )
    resource_class: Optional[str] = Field(
        title="Resource Class",
        description="Check that the resource in this location is of a certain class",
        default=None,
    )


class NoResourceInLocationCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.NO_RESOURCE_PRESENT] = Field(
        title="Condition Type",
        description="The type of condition to check",
        default=ConditionTypeEnum.NO_RESOURCE_PRESENT,
    )

    location_id: Optional[str] = Field(
        title="Location",
        description="The ID of the location to check for a resource in",
        default=None,
    )

    location_name: str = Field(
        title="Location",
        description="The name of the location to check for a resource in",
    )
    key: Union[str, int, GridIndex, GridIndex2D, GridIndex3D] = Field(
        title="Key",
        description="The key to check in the location's container resource",
        default=0,
    )


class ResourceFieldCheckCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.RESOURCE_FIELD_CHECK] = Field(
        title="Condition Type",
        description="The type of condition to check",
        default=ConditionTypeEnum.RESOURCE_FIELD_CHECK,
    )
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The id of the resource to check a quality of",
        default=None,
    )

    resource_name: Optional[str] = Field(
        title="Resource Name",
        description="The name of the resource to check a quality of",
        default=None,
    )
    field: str = Field(
        title="Field", description="The field to evaluate against the operator"
    )
    operator: OperatorTypeEnum = Field(
        title="Operator",
        description="The check (is_greater_than, is_less_than or is_equal_to etc.) to evaluate the field by",
    )
    target_value: Any = Field(
        title="Target Value", description="the target value for the field"
    )


class ResourceChildFieldCheckCondition(Condition):
    """A condition that checks if a resource is present"""

    condition_type: Literal[ConditionTypeEnum.RESOURCE_CHILD_FIELD_CHECK] = Field(
        title="Condition Type",
        description="The type of condition to check",
        default=ConditionTypeEnum.RESOURCE_CHILD_FIELD_CHECK,
    )
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The id of the resource to check a quality of",
        default=None,
    )

    resource_name: Optional[str] = Field(
        title="Resource Name",
        description="The name of the resource to check a quality of",
        default=None,
    )
    field: str = Field(
        title="Field", description="The field to evaluate against the operator"
    )
    operator: OperatorTypeEnum = Field(
        title="Operator",
        description="The check (is_greater_than, is_less_than or is_equal_to etc.) to evaluate the field by",
    )
    key: Union[str, int, GridIndex, GridIndex2D, GridIndex3D] = Field(
        title="Key",
        description="The key to check in the container resource",
        default=0,
    )
    target_value: Any = Field(
        title="Target Value", description="the target value for the field"
    )


Conditions = Annotated[
    Union[
        ResourceInLocationCondition,
        NoResourceInLocationCondition,
        ResourceFieldCheckCondition,
        ResourceChildFieldCheckCondition,
    ],
    Discriminator(
        discriminator="condition_type",
    ),
]
