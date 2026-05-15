"""Location types for MADSci."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import (
    MadsciBaseModel,
    prefixed_alias_generator,
    prefixed_model_validator,
)
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
    ManagerType,
)
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator, url_safe_name_validator
from pydantic import AliasChoices, AnyUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import SettingsConfigDict


class LocationManagement(str, Enum):
    """How a location is managed — determines lifecycle and visibility."""

    NODE = "node"
    """Created/owned by a node. Lifecycle tied to node registration."""
    LAB = "lab"
    """Created by lab config or API. Lifecycle managed by operator/integrator."""


class LocationRepresentationTemplate(MadsciBaseModel):
    """A named, versioned template for node-specific location representation data.

    Registered by nodes during startup or by operators via API. Defines the
    schema, defaults, and required overrides for a particular node type's
    representation of locations.

    Example: A robot arm registers ``"robotarm_deck_access"`` with defaults
    ``{"gripper_config": "standard", "max_payload": 2.0}`` and
    ``required_overrides=["position"]``.
    """

    template_id: str = Field(
        title="Template ID",
        description="Unique identifier for this template.",
        default_factory=new_ulid_str,
    )
    template_name: str = Field(
        title="Template Name",
        description="Unique name for this representation template (e.g. 'robotarm_deck_access').",
    )
    description: Optional[str] = Field(
        title="Description",
        description="Human-readable description of this representation template.",
        default=None,
    )
    default_values: dict[str, Any] = Field(
        title="Default Values",
        description="Default field values for this representation. Merged with overrides at instantiation.",
        default_factory=dict,
    )
    schema_def: Optional[dict[str, Any]] = Field(
        title="JSON Schema",
        description="Optional JSON Schema for validating representation data.",
        default=None,
        alias="schema_def",
        validation_alias=AliasChoices("schema_def", "schema"),
    )
    required_overrides: list[str] = Field(
        title="Required Overrides",
        description="Fields that must be provided when instantiating a location from this template.",
        default_factory=list,
    )
    tags: list[str] = Field(
        title="Tags",
        description="Tags for categorization and discovery.",
        default_factory=list,
    )
    created_by: Optional[str] = Field(
        title="Created By",
        description="ID of the node or operator that created this template.",
        default=None,
    )
    version: str = Field(
        title="Version",
        description="Semantic version of this template.",
        default="1.0.0",
    )
    created_at: datetime = Field(
        title="Created At",
        description="When this template was created.",
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: Optional[datetime] = Field(
        title="Updated At",
        description="When this template was last updated.",
        default=None,
    )

    is_ulid = field_validator("template_id")(ulid_validator)


class LocationTemplate(MadsciBaseModel):
    """A named, versioned blueprint for creating locations.

    Maps abstract role names to representation template names. Resource-free
    and node-free — no specific node instances or resource IDs. At instantiation
    time, node bindings map roles to concrete node names.

    Example: ``"ot2_deck_slot"`` with
    ``representation_templates: {"deck_controller": "lh_deck_repr", "transfer_arm": "robotarm_deck_access"}``
    """

    template_id: str = Field(
        title="Template ID",
        description="Unique identifier for this template.",
        default_factory=new_ulid_str,
    )
    template_name: str = Field(
        title="Template Name",
        description="Unique name for this location template (e.g. 'ot2_deck_slot').",
    )
    description: Optional[str] = Field(
        title="Description",
        description="Human-readable description of this location template.",
        default=None,
    )
    resource_template_name: Optional[str] = Field(
        title="Resource Template Name",
        description="Name of the ResourceTemplate to use for creating a resource on instantiation.",
        default=None,
    )
    resource_template_overrides: Optional[dict[str, Any]] = Field(
        title="Resource Template Overrides",
        description="Default overrides to apply when creating a resource from the template.",
        default=None,
    )
    representation_templates: dict[str, str] = Field(
        title="Representation Templates",
        description="Mapping of abstract role names to representation template names.",
        default_factory=dict,
    )
    default_allow_transfers: bool = Field(
        title="Default Allow Transfers",
        description="Default value for allow_transfers when creating locations from this template.",
        default=True,
    )
    tags: list[str] = Field(
        title="Tags",
        description="Tags for categorization and discovery.",
        default_factory=list,
    )
    created_by: Optional[str] = Field(
        title="Created By",
        description="ID of the node or operator that created this template.",
        default=None,
    )
    version: str = Field(
        title="Version",
        description="Semantic version of this template.",
        default="1.0.0",
    )
    created_at: datetime = Field(
        title="Created At",
        description="When this template was created.",
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: Optional[datetime] = Field(
        title="Updated At",
        description="When this template was last updated.",
        default=None,
    )

    is_ulid = field_validator("template_id")(ulid_validator)


class CreateLocationFromTemplateRequest(MadsciBaseModel):
    """Request to create a location from a LocationTemplate.

    Requires node bindings to map abstract roles to concrete node instance names.
    """

    location_name: str = Field(
        title="Location Name",
        description="Name for the new location.",
    )
    template_name: str = Field(
        title="Template Name",
        description="Name of the LocationTemplate to instantiate.",
    )
    node_bindings: dict[str, str] = Field(
        title="Node Bindings",
        description="Mapping of abstract role names to concrete node instance names.",
        default_factory=dict,
    )
    representation_overrides: dict[str, dict[str, Any]] = Field(
        title="Representation Overrides",
        description="Per-role overrides to merge with representation template defaults. Key is role name.",
        default_factory=dict,
    )
    resource_template_overrides: Optional[dict[str, Any]] = Field(
        title="Resource Template Overrides",
        description="Overrides for resource template fields (merged with template defaults).",
        default=None,
    )
    description: Optional[str] = Field(
        title="Description",
        description="Optional description for the new location.",
        default=None,
    )
    allow_transfers: Optional[bool] = Field(
        title="Allow Transfers",
        description="Override the template default for allow_transfers.",
        default=None,
    )

    is_url_safe_name = field_validator("location_name")(url_safe_name_validator)


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

    @location.setter
    def location_setter(self, value: Any) -> None:
        """Set the representation of the location."""
        self.representation = value

    @property
    def name(self) -> Optional[str]:
        """Return the name of the location, if available."""
        return self.location_name


class Location(MadsciBaseModel):
    """A location in the lab."""

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
    resource_id: Optional[str] = Field(
        title="Resource ID",
        description="The ID of the resource associated with the Location.",
        default=None,
    )
    description: Optional[str] = Field(
        title="Location Description",
        description="A description of the location.",
        default=None,
    )
    representations: dict[str, Any] = Field(
        title="Location Representation Map",
        description="A dictionary of different representations of the location. Allows creating an association between a specific key (like a node name or id) and a relevant representation of the location (like joint angles, a specific actuator, etc).",
        default_factory=dict,
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
        description="Whether this location can be used as a source or target in transfers. Non-transfer locations are excluded from transfer graph construction.",
        default=True,
    )
    reservation: Optional["LocationReservation"] = Field(
        title="Reservation",
        description="The current reservation on this location, if any.",
        default=None,
    )
    location_template_name: Optional[str] = Field(
        title="Location Template Name",
        description="Name of the LocationTemplate used to create this location (for traceability).",
        default=None,
    )
    node_bindings: Optional[dict[str, str]] = Field(
        title="Node Bindings",
        description="Mapping of abstract role names to concrete node instance names (for traceability).",
        default=None,
    )
    managed_by: LocationManagement = Field(
        title="Managed By",
        description="Whether this location is managed by a node or by the lab configuration.",
        default=LocationManagement.LAB,
    )
    owner: Optional[OwnershipInfo] = Field(
        title="Owner",
        description="Ownership provenance for this location. For node-managed locations, "
        "includes node_id. For lab-managed locations, may include user_id.",
        default=None,
    )

    is_ulid = field_validator("location_id")(ulid_validator)
    is_url_safe_name = field_validator("location_name")(url_safe_name_validator)

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
    expires: datetime = Field(
        title="Expires Datetime",
        description="When the reservation ends.",
    )

    def check(self, ownership: OwnershipInfo) -> bool:
        """Check if the reservation is 1.) active or not, and 2.) owned by the given ownership."""
        is_owner = self.owned_by.check(ownership)
        now = datetime.now(timezone.utc)
        is_active = self.created <= now <= self.expires
        return is_owner or not is_active


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
    additional_args: dict[str, Any] = Field(
        title="Additional Standard Arguments",
        description="Additional standard arguments to include in the transfer step",
        default_factory=dict,
    )
    additional_location_args: dict[str, str] = Field(
        title="Additional Location Arguments",
        description="Additional location arguments to include in the transfer step. Key is argument name, value is location name to use.",
        default_factory=dict,
    )


class TransferGraphEdge(MadsciBaseModel):
    """Represents a transfer path between two locations."""

    source_location_id: str = Field(
        title="Source Location ID", description="ID of the source location"
    )
    target_location_id: str = Field(
        title="Target Location ID", description="ID of the target location"
    )
    transfer_template: TransferStepTemplate = Field(
        title="Transfer Template", description="Template for executing the transfer"
    )
    cost: float = Field(
        title="Transfer Cost",
        description="Cost/weight for shortest path calculation",
        default=1.0,
    )


class TransferGraphDetailedEdge(MadsciBaseModel):
    """A transfer edge with all node names that can execute the transfer."""

    source_location_id: str = Field(
        title="Source Location ID",
        description="ID of the source location.",
    )
    target_location_id: str = Field(
        title="Target Location ID",
        description="ID of the target location.",
    )
    node_names: list[str] = Field(
        title="Node Names",
        description="Names of all nodes that can execute a transfer between these locations.",
        default_factory=list,
    )
    min_cost: float = Field(
        title="Minimum Cost",
        description="Lowest cost among available transfer templates for this edge.",
        default=1.0,
    )


class TransferGraphDetailedResponse(MadsciBaseModel):
    """Response containing the detailed transfer graph with node information per edge."""

    edges: list[TransferGraphDetailedEdge] = Field(
        title="Edges",
        description="List of transfer edges with node names and costs.",
        default_factory=list,
    )


class TransferTemplateOverrides(MadsciBaseModel):
    """Override transfer templates for specific source/destination patterns."""

    source_overrides: Optional[dict[str, list[TransferStepTemplate]]] = Field(
        title="Source Location Overrides",
        description="Override templates for specific source locations. Key is location_name or location_id.",
        default=None,
    )
    target_overrides: Optional[dict[str, list[TransferStepTemplate]]] = Field(
        title="Target Location Overrides",
        description="Override templates for specific target locations. Key is location_name or location_id.",
        default=None,
    )
    pair_overrides: Optional[dict[str, dict[str, list[TransferStepTemplate]]]] = Field(
        title="Source-Target Pair Overrides",
        description="Override templates for specific (source, target) pairs. Outer key is source location_name or location_id, inner key is target location_name or location_id.",
        default=None,
    )


class CapacityCostConfig(MadsciBaseModel):
    """Configuration for capacity-aware cost adjustments."""

    enabled: bool = Field(
        title="Capacity Cost Enabled",
        description="Whether to enable capacity-aware cost adjustments",
        default=False,
    )
    high_capacity_threshold: float = Field(
        title="High Capacity Threshold",
        description="Utilization ratio (quantity/capacity) above which to apply high capacity multiplier",
        default=0.8,
        ge=0.0,
        le=1.0,
    )
    full_capacity_threshold: float = Field(
        title="Full Capacity Threshold",
        description="Utilization ratio (quantity/capacity) above which to apply full capacity multiplier",
        default=1.0,
        ge=0.0,
        le=1.0,
    )
    high_capacity_multiplier: float = Field(
        title="High Capacity Cost Multiplier",
        description="Cost multiplier when destination resource capacity utilization is high",
        default=2.0,
        ge=1.0,
    )
    full_capacity_multiplier: float = Field(
        title="Full Capacity Cost Multiplier",
        description="Cost multiplier when destination resource capacity is at or above capacity",
        default=10.0,
        ge=1.0,
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
    capacity_cost_config: Optional[CapacityCostConfig] = Field(
        title="Capacity Cost Configuration",
        description="Configuration for capacity-aware cost adjustments when planning transfers",
        default=None,
    )


class RepresentationTrainingEntry(MadsciBaseModel):
    """Add a node's representation to an existing location ('training').

    Used to teach a node (e.g., robot arm) how to access a location it doesn't own
    (e.g., a liquid handler deck slot).
    """

    location_name: str = Field(
        title="Location Name",
        description="Name of the existing location to add a representation to.",
    )
    node_name: str = Field(
        title="Node Name",
        description="Name of the node providing the representation.",
    )
    representation_template_name: Optional[str] = Field(
        title="Representation Template Name",
        description="Optional representation template to use for defaults/schema.",
        default=None,
    )
    overrides: dict[str, Any] = Field(
        title="Overrides",
        description="Representation values merged with template defaults.",
        default_factory=dict,
    )


class LabLocationConfig(MadsciBaseModel):
    """Schema for the lab-level location configuration file.

    This is a reconcilable living document. The Location Manager re-reads it
    on each reconciliation cycle and merges contents with the live database.
    """

    representation_templates: list[LocationRepresentationTemplate] = Field(
        default_factory=list,
        title="Representation Templates",
        description="Lab-level representation templates.",
    )
    location_templates: list[LocationTemplate] = Field(
        default_factory=list,
        title="Location Templates",
        description="Reusable location blueprints.",
    )
    training: list[RepresentationTrainingEntry] = Field(
        default_factory=list,
        title="Training",
        description="Cross-node representation additions.",
    )
    locations: list[Location] = Field(
        default_factory=list,
        title="Locations",
        description="Lab-managed locations.",
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

    model_config = SettingsConfigDict(
        alias_generator=prefixed_alias_generator("location"),
        populate_by_name=True,
    )
    _accept_prefixed_keys = prefixed_model_validator("location")

    transfer_capabilities: Optional["LocationTransferCapabilities"] = Field(
        default=None,
        title="Transfer Capabilities",
        description="Transfer capabilities configuration for this LocationManager.",
    )

    reconciliation_interval_seconds: float = Field(
        title="Reconciliation Interval",
        description="Interval in seconds between background reconciliation cycles for lazy template resolution.",
        default=30.0,
    )
    reconciliation_enabled: bool = Field(
        title="Reconciliation Enabled",
        description="Whether to enable background reconciliation of unresolved template references.",
        default=True,
    )
    lab_config_file: Optional[str] = Field(
        default="locations.yaml",
        title="Lab Config File",
        description="Path to a YAML file defining lab-level locations and training. "
        "Re-read on each reconciliation cycle with desired-state semantics. "
        "All locations created from this file are tagged as lab-managed.",
    )

    server_url: AnyUrl = Field(
        title="Server URL",
        description="The URL where this manager's server runs.",
        default="http://localhost:8006/",
    )
    manager_type: Optional[ManagerType] = Field(
        title="Manager Type",
        description="The type of manager.",
        default=ManagerType.LOCATION_MANAGER,
    )

    # MongoDB / document storage settings
    document_db_url: AnyUrl = Field(
        title="Document DB URL",
        description="URL for the document database (MongoDB/FerretDB) used for persistent location storage.",
        default="mongodb://localhost:27017/",
        validation_alias=AliasChoices("document_db_url", "mongo_db_url"),
        json_schema_extra={"secret": True},
    )
    database_name: str = Field(
        title="Database Name",
        description="Name of the database for persistent location storage.",
        default="madsci_locations",
    )

    # Cache settings (transient state only: locks, change counters)
    cache_host: str = Field(
        title="Cache Host",
        description="The host of the cache server (Valkey/Redis-compatible) for transient state (locks, change counters).",
        default="localhost",
        validation_alias=AliasChoices("cache_host", "redis_host"),
    )
    cache_port: int = Field(
        title="Cache Port",
        description="The port of the cache server (Valkey/Redis-compatible) for transient state.",
        default=6379,
        validation_alias=AliasChoices("cache_port", "redis_port"),
    )
    cache_password: Optional[str] = Field(
        title="Cache Password",
        description="The password for the cache server (Valkey/Redis-compatible) (if required).",
        default=None,
        json_schema_extra={"secret": True},
        validation_alias=AliasChoices("cache_password", "redis_password"),
    )


class LocationManagerDefinition(ManagerDefinition):
    """Definition for a LocationManager."""

    manager_type: Literal[ManagerType.LOCATION_MANAGER] = Field(
        title="Manager Type",
        description="The type of manager",
        default=ManagerType.LOCATION_MANAGER,
    )
    locations: list[Location] = Field(
        title="Locations",
        description="The locations managed by this LocationManager.",
        default_factory=list,
    )
    transfer_capabilities: Optional[LocationTransferCapabilities] = Field(
        title="Transfer Capabilities",
        description="Transfer workflow templates and capabilities",
        default=None,
    )

    @field_validator("locations", mode="after")
    @classmethod
    def sort_locations(cls, locations: list[Location]) -> list[Location]:
        """Sort locations by name after validation."""
        return sorted(locations, key=lambda loc: loc.location_name)


class LocationImportResult(MadsciBaseModel):
    """Result of a bulk location import operation."""

    imported: int = Field(
        title="Imported Count",
        description="Number of locations successfully imported.",
        default=0,
    )
    skipped: int = Field(
        title="Skipped Count",
        description="Number of locations skipped (e.g. duplicates).",
        default=0,
    )
    errors: list[str] = Field(
        title="Errors",
        description="List of error messages for locations that failed to import.",
        default_factory=list,
    )
    locations: list[Location] = Field(
        title="Locations",
        description="List of locations that were successfully imported.",
        default_factory=list,
    )


class LocationManagerHealth(ManagerHealth):
    """Health status for the Location Manager."""

    document_db_connected: Optional[bool] = Field(
        title="Document DB Connection Status",
        description="Whether the Location Manager is connected to the document database (MongoDB/FerretDB).",
        default=None,
    )
    cache_connected: Optional[bool] = Field(
        title="Cache Connection Status",
        description="Whether the Location Manager is connected to the cache server (Valkey/Redis-compatible).",
        default=None,
    )
    num_locations: int = Field(
        title="Number of Locations",
        description="The number of locations managed by the Location Manager.",
        default=0,
    )
    num_representation_templates: int = Field(
        title="Number of Representation Templates",
        description="The number of representation templates registered with the Location Manager.",
        default=0,
    )
    num_location_templates: int = Field(
        title="Number of Location Templates",
        description="The number of location templates registered with the Location Manager.",
        default=0,
    )
    num_unresolved_locations: int = Field(
        title="Number of Unresolved Locations",
        description="The number of locations with unresolved template references (resource_id is null but resource_template_name is set).",
        default=0,
    )
    num_node_managed_locations: int = Field(
        title="Node-Managed Locations",
        description="Number of locations managed by nodes (managed_by='node').",
        default=0,
    )
    num_lab_managed_locations: int = Field(
        title="Lab-Managed Locations",
        description="Number of locations managed by the lab config (managed_by='lab').",
        default=0,
    )
    last_reconciliation_at: Optional[str] = Field(
        title="Last Reconciliation",
        description="ISO timestamp of the last reconciliation cycle.",
        default=None,
    )
