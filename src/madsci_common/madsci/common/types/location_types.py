"""Location types for MADSci."""

from datetime import datetime
from typing import Any, Literal, Optional

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from madsci.common.types.resource_types.definitions import ResourceDefinitions
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import AnyUrl, Field
from pydantic.functional_validators import field_validator


class LocationArgument(MadsciBaseModel):
    """Location Argument to be used by MADSCI nodes."""

    location: Any
    """Details about the Location relevant to this node"""
    resource_id: Optional[str] = None
    """The ID of the corresponding resource, if any"""
    location_name: Optional[str] = None
    """the name of the given location"""
    reservation: Optional["LocationReservation"] = None
    """whether existing location is reserved"""


class LocationDefinition(MadsciBaseModel):
    """The Definition of a Location in a setup."""

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
    references: dict[str, Any] = Field(
        title="Location Representation Map",
        description="A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).",
        default={},
    )
    resource_definition: Optional[ResourceDefinitions] = Field(
        title="Resource",
        description="Definition of the Resource to be associated with this location (if any) on location initialization.",
        default=None,
        discriminator="base_type",
    )

    is_ulid = field_validator("location_id")(ulid_validator)


class Location(MadsciBaseModel):
    """A location in the lab."""

    location_id: str = Field(
        title="Location ID",
        description="The ID of the location.",
        default_factory=new_ulid_str,
    )
    name: str = Field(
        title="Location Name",
        description="The name of the location.",
    )
    description: Optional[str] = Field(
        title="Location Description",
        description="A description of the location.",
        default=None,
    )
    references: Optional[dict[str, Any]] = Field(
        title="Location References",
        description="A dictionary of node-specific references for the location.",
        default=None,
    )
    reservation: Optional["LocationReservation"] = Field(
        title="Location Reservation",
        description="The reservation for the location.",
        default=None,
    )
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The ID of an existing Resource associated with the location, if any (deprecated, use resource_ids).",
        default=None,
    )

    is_ulid = field_validator("location_id")(ulid_validator)


class LocationReservation(MadsciBaseModel):
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


class LocationManagerSettings(
    ManagerSettings,
    env_prefix="LOCATION_",
    env_file=(".env", "location.env"),
    toml_file=("settings.toml", "location.settings.toml"),
    yaml_file=("settings.yaml", "location.settings.yaml"),
    json_file=("settings.json", "location.settings.json"),
):
    """Settings for the LocationManager."""

    server_host: str = Field(
        title="Server Host",
        description="The host to run the server on.",
        default="localhost",
    )
    server_port: int = Field(
        title="Server Port",
        description="The port to run the server on.",
        default=8006,
    )
    server_url: AnyUrl = Field(
        title="Server URL",
        description="The URL where this manager's server runs.",
        default="http://localhost:8006/",
    )
    manager_id: str = Field(
        title="Manager ID",
        description="The unique identifier for this manager instance.",
        default_factory=new_ulid_str,
    )
    redis_host: str = Field(
        title="Redis Host",
        description="The host of the Redis server for state storage.",
        default="localhost",
    )
    redis_port: int = Field(
        title="Redis Port",
        description="The port of the Redis server for state storage.",
        default=6379,
    )
    redis_password: Optional[str] = Field(
        title="Redis Password",
        description="The password for the Redis server (if required).",
        default=None,
    )


class LocationManagerDefinition(ManagerDefinition):
    """Definition for a LocationManager."""

    manager_type: Literal[ManagerType.LOCATION_MANAGER] = Field(
        title="Manager Type",
        description="The type of manager",
        default=ManagerType.LOCATION_MANAGER,
    )
    locations: list[LocationDefinition] = Field(
        title="Locations",
        description="The locations managed by this LocationManager.",
        default_factory=list,
    )


class LocationManagerHealth(ManagerHealth):
    """Health status for the Location Manager."""

    redis_connected: Optional[bool] = Field(
        title="Redis Connection Status",
        description="Whether the Location Manager is connected to the Redis server.",
        default=None,
    )
    num_locations: int = Field(
        title="Number of Locations",
        description="The number of locations managed by the Location Manager.",
        default=0,
    )
