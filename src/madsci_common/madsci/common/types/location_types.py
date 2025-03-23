"""Location types for MADSci."""

from datetime import datetime
from typing import Any, Optional, Union

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.resource_types import ResourceDataModels
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
    resource: Optional[Union[ResourceDataModels, str]] = Field(
        title="Resource",
        description="The Resource associated with the location",
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
