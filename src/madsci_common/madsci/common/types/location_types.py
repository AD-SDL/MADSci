"""Location types for MADSci."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import MadsciBaseModel
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import AliasChoices, AnyUrl, Field
from pydantic.functional_validators import field_validator

# Avoid circular imports
if TYPE_CHECKING:
    pass


class LocationArgument(MadsciBaseModel):
    """Location Argument to be used by MADSCI nodes."""

    representation: Any = Field(
        title="Location Representation",
        description="The representation of the location specific to the node.",
        alias=AliasChoices(
            "representation", "location"
        ),  # for backwards compatibility with older versions
    )
    """Representation of the location specific to the node."""
    resource_id: Optional[str] = None
    """The ID of the corresponding resource, if any"""
    location_name: Optional[str] = None
    """the name of the given location"""
    reservation: Optional["LocationReservation"] = None
    """whether existing location is reserved"""

    @property
    def location(self) -> Any:
        """Return the representation of the location."""
        return self.representation

    @property
    def name(self) -> Optional[str]:
        """Return the name of the location, if available."""
        return self.location_name


class LocationDefinition(MadsciBaseModel):
    """The Definition of a Location in a setup."""

    location_name: str = Field(
        title="Location Name",
        description="The name of the location.",
        alias=AliasChoices("location_name", "name"),
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
    representations: dict[str, Any] = Field(
        title="Location Representation Map",
        description="A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).",
        default={},
    )
    resource_template_name: Optional[str] = Field(
        title="Resource Template Name",
        description="Name of the Resource Template to be used for creating a resource associated with this location (if any) on location initialization.",
        default=None,
    )
    resource_template_overrides: Optional[dict[str, Any]] = Field(
        title="Resource Template Overrides",
        description="Optional overrides to apply when creating a resource from the template for this specific location.",
        default=None,
    )
    allow_transfers: bool = Field(
        title="Allow Transfers",
        description="Whether this location can be used as a source or destination in transfers. Non-transfer locations are excluded from transfer graph construction.",
        default=True,
    )

    is_ulid = field_validator("location_id")(ulid_validator)

    @property
    def name(self) -> str:
        """Get the name of the location."""
        return self.location_name


class Location(MadsciBaseModel):
    """A location in the lab."""

    location_id: str = Field(
        title="Location ID",
        description="The ID of the location.",
        default_factory=new_ulid_str,
    )
    location_name: str = Field(
        title="Location Name",
        description="The name of the location.",
        alias=AliasChoices("location_name", "name"),
    )
    description: Optional[str] = Field(
        title="Location Description",
        description="A description of the location.",
        default=None,
    )
    representations: Optional[dict[str, Any]] = Field(
        title="Location Representations",
        description="A dictionary of node-specific representations for the location.",
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
    allow_transfers: bool = Field(
        title="Allow Transfers",
        description="Whether this location can be used as a source or destination in transfers. Non-transfer locations are excluded from transfer graph construction.",
        default=True,
    )

    is_ulid = field_validator("location_id")(ulid_validator)

    @property
    def name(self) -> str:
        """Get the name of the location."""
        return self.location_name


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


class TransferStepTemplate(MadsciBaseModel):
    """Template for transfer steps between compatible locations."""

    node_name: str = Field(
        title="Node Name", description="Name of the node that can perform this transfer"
    )
    action: str = Field(
        title="Action Name",
        description="Name of the action to perform for this transfer",
    )
    source_argument_name: str = Field(
        title="Source Argument Name",
        description="Name of the location argument for the source location",
        default="source_location",
    )
    target_argument_name: str = Field(
        title="Target Argument Name",
        description="Name of the location argument for the target location",
        default="target_location",
    )
    cost_weight: Optional[float] = Field(
        title="Cost Weight",
        description="Weight for shortest path calculation (default: 1.0)",
        default=1.0,
    )


class TransferGraphEdge(MadsciBaseModel):
    """Represents a transfer path between two locations."""

    source_location_id: str = Field(
        title="Source Location ID", description="ID of the source location"
    )
    destination_location_id: str = Field(
        title="Destination Location ID", description="ID of the destination location"
    )
    transfer_template: TransferStepTemplate = Field(
        title="Transfer Template", description="Template for executing the transfer"
    )
    cost: float = Field(
        title="Transfer Cost",
        description="Cost/weight for shortest path calculation",
        default=1.0,
    )


class TransferTemplateOverrides(MadsciBaseModel):
    """Override transfer templates for specific source/destination patterns."""

    source_overrides: Optional[dict[str, list[TransferStepTemplate]]] = Field(
        title="Source Location Overrides",
        description="Override templates for specific source locations. Key is location_name or location_id.",
        default=None,
    )
    destination_overrides: Optional[dict[str, list[TransferStepTemplate]]] = Field(
        title="Destination Location Overrides",
        description="Override templates for specific destination locations. Key is location_name or location_id.",
        default=None,
    )
    pair_overrides: Optional[dict[str, dict[str, list[TransferStepTemplate]]]] = Field(
        title="Source-Destination Pair Overrides",
        description="Override templates for specific (source, destination) pairs. Outer key is source location_name or location_id, inner key is destination location_name or location_id.",
        default=None,
    )


class LocationTransferCapabilities(MadsciBaseModel):
    """Transfer capabilities for a location manager."""

    transfer_templates: list[TransferStepTemplate] = Field(
        title="Transfer Templates",
        description="Available transfer step templates",
        default_factory=list,
    )
    override_transfer_templates: Optional[TransferTemplateOverrides] = Field(
        title="Override Transfer Templates",
        description="Override transfer templates for specific source, destination, or (source, destination) pairs",
        default=None,
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
    transfer_capabilities: Optional[LocationTransferCapabilities] = Field(
        title="Transfer Capabilities",
        description="Transfer workflow templates and capabilities",
        default=None,
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
