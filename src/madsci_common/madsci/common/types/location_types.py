"""Location types for MADSci."""

from datetime import datetime
from typing import Any, Optional

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import Field
from pydantic.functional_validators import field_validator


class Location(BaseModel):
    """A location in the lab."""

    location_name: str = Field(
        title="Location Name",
        description="The name of the location.",
    )
    location_id: str = Field(
        title="Location ID",
        description="The ID of the location.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        title="Location Description",
        description="A description of the location.",
        default=None,
    )
    lookup: dict[str, Any] = Field(
        title="Location Representation Map",
        description="A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).",
        default={},
    )
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The resource ID linked to the location, typically a container.",
        default=None,
    )
    reservation: Optional["LocationReservation"] = Field(
        title="Location Reservation",
        description="The reservation for the location.",
        default=None,
    )

    is_ulid = field_validator("location_id")(ulid_validator)


class LocationReservation(BaseModel):
    """Reservation of a MADSci Location."""

    owned_by: OwnershipInfo = Field(
        title="Owned By",
        description="Who has ownership of the reservation.",
    )
    created: datetime = Field(
        title="Created Datetime",
        description="When the reservation was created.",
    )
    start: datetime = Field(
        title="Start Datetime",
        description="When the reservation starts.",
    )
    end: datetime = Field(
        title="End Datetime",
        description="When the reservation ends.",
    )

    def check(self, ownership: OwnershipInfo) -> bool:
        """Check if the reservation is 1.) active or not, and 2.) owned by the given ownership."""
        return not (
            not self.owned_by.check(ownership)
            and self.start <= datetime.now()
            and self.end >= datetime.now()
        )


class LocationArgumentDefinition(BaseModel):
    """Location Argument Definition for use in NodeInfo"""

    name: str = Field(
        title="Location Argument Name",
        description="The name of the location argument.",
    )
    description: str = Field(
        title="Location Argument Description",
        description="A description of the location argument.",
    )
    required: bool = Field(
        title="Location Argument Required",
        description="Whether the location argument is required.",
    )
    default: Optional[Any] = Field(
        title="Location Argument Default",
        description="The default value of the location argument.",
        default=None,
    )


class LocationArgument(BaseModel):
    """Location Argument to be used by MADSCI nodes."""

    location: Any
    """Details about the Location relevant to this node"""
    resource_id: Optional[str] = None
    """The ID of the corresponding resource, if any"""
