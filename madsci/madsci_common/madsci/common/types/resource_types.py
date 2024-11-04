"""Types related to MADSci Resources."""

from typing import List, Optional, Union

from aenum._enum import Enum
from pydantic.functional_validators import field_validator
from sqlmodel.main import Field

from madsci.common.types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator
from madsci.common.utils import new_name_str


class ResourceType(str, Enum):
    """Type for a MADSci Resource."""

    asset = "asset"
    consumable = "consumable"
    custom = "custom"
    unknown = "unknown"


class AssetType(str, Enum):
    """Type for a MADSci Asset."""

    container = "container"
    asset = "asset"


class ConsumableType(str, Enum):
    """Type for a MADSci Consumable."""

    discrete = "discrete"
    continuous = "continuous"


class ContainerType(str, Enum):
    """Type for a MADSci Container."""

    stack = "stack"
    queue = "queue"
    collection = "collection"


class CustomResourceType(BaseModel):
    """Type for a MADSci Custom Resource."""

    type_name: str = Field(
        title="Custom Type Name",
        description="The name of the custom type of the resource (i.e. 'plate_96_well_corningware', 'tube_rack_24', etc.).",
    )
    type_description: Optional[str] = Field(
        default=None,
        title="Custom Type Description",
        description="A description of the custom type of the resource.",
    )
    type_definition: Union[
        ResourceType, AssetType, ContainerType, ConsumableType, "CustomResourceType"
    ] = Field(
        title="Custom Type Definition",
        description="The definition of the custom type of the resource.",
    )


class ResourceDefinition(BaseModel, extra="allow"):
    """Definition for a MADSci Resource."""

    name: str = Field(title="Resource Name", description="The name of the resource.")
    resource_id: str = Field(
        title="Resource ID",
        description="The ID of the resource.",
        default_factory=new_ulid_str,
    )
    description: Optional[str] = Field(
        default=None,
        title="Resource Description",
        description="A description of the resource.",
    )
    resource_type: str = Field(
        title="Resource Type", description="The type of the resource."
    )
    custom_type: Optional[str] = Field(
        default=None,
        title="Custom Type",
        description="The custom type of the resource if it is a custom resource.",
    )

    is_ulid = field_validator("resource_id")(ulid_validator)


class ResourceBase(ResourceDefinition, extra="allow"):
    """Base class for all MADSci Resources."""

    resource_url: str = Field(
        title="Resource URL", description="The URL of the resource."
    )


class AssetBase(ResourceBase, extra="allow"):
    """Definition for a MADSci Asset."""

    name: str = Field(
        title="Asset Name",
        description="The name of the asset.",
        default_factory=lambda: new_name_str("asset"),
    )
    asset_type: AssetType = Field(
        title="Asset Type",
        description="The type of the asset.",
        default=AssetType.unknown,
    )
    description: Optional[str] = Field(
        default=None,
        title="Asset Description",
        description="A description of the asset.",
    )

    is_ulid = field_validator("asset_id")(ulid_validator)


class ContainerBase(AssetBase, extra="allow"):
    """Definition for a MADSci Container."""

    name: str = Field(
        title="Container Name",
        description="The name of the container.",
        default_factory=lambda: new_name_str("container"),
    )
    container_type: ContainerType = Field(
        title="Container Type",
        description="The type of the container.",
        default=ContainerType.collection,
    )
    children: List[ResourceBase] = Field(
        title="Container Children",
        description="The Resources contained in the container.",
    )


class ConsumableBase(AssetBase, extra="allow"):
    """Definition for a MADSci Consumable."""

    consumable_type: ConsumableType = Field(
        title="Consumable Type",
        description="The type of the consumable.",
        default=ConsumableType.continuous,
    )


class StackBase(ContainerBase, extra="allow"):
    """Definition for a MADSci Stack Container."""

    container_type: ContainerType = Field(
        title="Container Type",
        description="The type of the container.",
        default=ContainerType.stack,
    )


class CollectionBase(ContainerBase, extra="allow"):
    """Definition for a MADSci Collection Container."""

    container_type: ContainerType = Field(
        title="Container Type",
        description="The type of the container.",
        default=ContainerType.collection,
    )


class QueueBase(ContainerBase, extra="allow"):
    """Definition for a MADSci Queue Container."""

    container_type: ContainerType = Field(
        title="Container Type",
        description="The type of the container.",
        default=ContainerType.queue,
    )
