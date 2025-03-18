"""Data Models for validating Custom Resource Type Definitions"""

from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, Union

from madsci.common.types.base_types import BaseModel

if TYPE_CHECKING:
    from madsci.common.types.resource_types.definitions import ResourceDefinition
from pydantic import Json, Tag
from pydantic.config import ConfigDict
from pydantic.functional_validators import field_validator
from sqlmodel import Field


class AssetTypeEnum(str, Enum):
    """Type for a MADSci Asset."""

    container = "container"
    asset = "asset"


class ConsumableTypeEnum(str, Enum):
    """Type for a MADSci Consumable."""

    consumable = "consumable"
    discrete_consumable = "discrete_consumable"
    continuous_consumable = "continuous_consumable"


class ContainerTypeEnum(str, Enum):
    """Type for a MADSci Container."""

    container = "container"
    slot = "slot"
    stack = "stack"
    queue = "queue"
    collection = "collection"
    row = "row"
    grid = "grid"
    voxel_grid = "voxel_grid"
    pool = "pool"


class ResourceTypeEnum(str, Enum):
    """Enum for all resource base types."""

    """Resource Base Types"""
    resource = "resource"

    """Asset Resource Base Types"""
    asset = "asset"
    container = "container"

    """Consumable Resource Base Types"""
    consumable = "consumable"
    discrete_consumable = "discrete_consumable"
    continuous_consumable = "continuous_consumable"

    """Container Resource Base Types"""
    slot = "slot"
    stack = "stack"
    queue = "queue"
    collection = "collection"
    row = "row"
    grid = "grid"
    voxel_grid = "voxel_grid"
    pool = "pool"


class CustomResourceAttributeDefinition(BaseModel, extra="allow"):
    """Definition for a MADSci Custom Resource Attribute."""

    attribute_name: str = Field(
        title="Attribute Name",
        description="The name of the attribute.",
    )
    attribute_description: Optional[str] = Field(
        default=None,
        title="Attribute Description",
        description="A description of the attribute.",
    )
    optional: bool = Field(
        default=False,
        title="Optional",
        description="Whether the attribute is optional.",
    )
    default_value: Json[Any] = Field(
        default=None,
        title="Default Value",
        description="The default value of the attribute.",
    )


class ResourceTypeDefinition(BaseModel):
    """Definition for a MADSci Resource Type."""

    model_config = ConfigDict(extra="allow")

    type_name: str = Field(
        title="Resource Type Name",
        description="The name of the type of resource (i.e. 'plate_96_well_corningware', 'tube_rack_24', etc.).",
    )
    type_description: str = Field(
        title="Resource Type Description",
        description="A description of the custom type of the resource.",
    )
    base_type: Literal[ResourceTypeEnum.resource] = Field(
        default=ResourceTypeEnum.resource,
        title="Resource Base Type",
        description="The base type of the resource.",
    )
    parent_types: list[str] = Field(
        default=["resource"],
        title="Resource Parent Types",
        description="The parent types of the resource.",
    )
    custom_attributes: Optional[list["CustomResourceAttributeDefinition"]] = Field(
        default=None,
        title="Custom Attributes",
        description="Custom attributes used by resources of this type.",
    )

    @field_validator("parent_types", mode="before")
    @classmethod
    def validate_parent_types(cls, v: Union[list[str], str]) -> list[str]:
        """Validate parent types."""
        if isinstance(v, str):
            return [v]
        return v


class ContainerResourceTypeDefinition(ResourceTypeDefinition):
    """Definition for a MADSci Container Resource Type."""

    supported_child_types: list[str] = Field(
        title="Supported Child Types",
        description="The resource types for children supported by the container. If `resource` is included, the container can contain any resource type.",
    )
    default_capacity: Optional[Union[int, float]] = Field(
        title="Default Capacity",
        description="The default maximum capacity of the container. If None, the container has no capacity limit.",
        default=None,
    )
    resizeable: bool = Field(
        default=False,
        title="Resizeable",
        description="Whether containers of this type support different sizes. If True, the container can be resized. If False, the container is fixed size.",
    )
    default_children: Optional[
        Union[list["ResourceDefinition"], dict[str, "ResourceDefinition"]]
    ] = Field(
        default=None,
        title="Default Children",
        description="The default children to create when populating the container. Takes precedence over default_child_template.",
    )
    default_child_template: Optional[list["ResourceDefinition"]] = Field(
        default=None,
        title="Default Child Template",
        description="The default template for children to create when populating the container.",
    )
    base_type: Literal[ResourceTypeEnum.container] = Field(
        default=ResourceTypeEnum.container,
        title="Container Base Type",
        description="The base type of the container.",
    )


class AssetResourceTypeDefinition(ResourceTypeDefinition):
    """Definition for a MADSci Asset Resource Type."""

    base_type: Literal[ResourceTypeEnum.asset] = Field(
        default=ResourceTypeEnum.asset,
        title="Asset Base Type",
        description="The base type of the asset.",
    )


class ConsumableResourceTypeDefinition(ResourceTypeDefinition):
    """Definition for a MADSci Consumable Resource Type."""

    base_type: Literal[ResourceTypeEnum.consumable] = Field(
        default=ResourceTypeEnum.consumable,
        title="Consumable Base Type",
        description="The base type of the consumable.",
    )


class DiscreteConsumableResourceTypeDefinition(ConsumableResourceTypeDefinition):
    """Definition for a MADSci Discrete Consumable Resource Type."""

    base_type: Literal[ResourceTypeEnum.discrete_consumable] = Field(
        default=ResourceTypeEnum.discrete_consumable,
        title="Discrete Consumable Base Type",
        description="The base type of the discrete consumable.",
    )


class ContinuousConsumableResourceTypeDefinition(ConsumableResourceTypeDefinition):
    """Definition for a MADSci Continuous Consumable Resource Type."""

    base_type: Literal[ResourceTypeEnum.continuous_consumable] = Field(
        default=ResourceTypeEnum.continuous_consumable,
        title="Continuous Consumable Base Type",
        description="The base type of the continuous consumable.",
    )


class StackResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Stack Resource Type."""

    default_child_quantity: Optional[int] = Field(
        default=None,
        title="Default Child Quantity",
        description="The default number of children to create when populating the container. If None, the container will be populated with a single child.",
    )
    base_type: Literal[ResourceTypeEnum.stack] = Field(
        default=ResourceTypeEnum.stack,
        title="Stack Base Type",
        description="The base type of the stack.",
    )


class QueueResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Queue Resource Type."""

    default_child_quantity: Optional[int] = Field(
        default=None,
        title="Default Child Quantity",
        description="The default number of children to create when populating the container. If None, the container will be populated with a single child.",
    )
    base_type: Literal[ResourceTypeEnum.queue] = Field(
        default=ResourceTypeEnum.queue,
        title="Queue Base Type",
        description="The base type of the queue.",
    )


class CollectionResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Collection Resource Type."""

    keys: Optional[list[str]] = Field(
        title="Collection Keys",
        description="The keys of the collection.",
    )
    default_children: Optional[
        Union[list["ResourceDefinition"], dict[str, "ResourceDefinition"]]
    ] = Field(
        default=None,
        title="Default Children",
        description="The default children to create when populating the container.",
    )
    base_type: Literal[ResourceTypeEnum.collection] = Field(
        default=ResourceTypeEnum.collection,
        title="Collection Base Type",
        description="The base type of the collection.",
    )

    @field_validator("keys", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v


class RowResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Row Resource Type."""

    base_type: Literal[ResourceTypeEnum.row] = Field(
        default=ResourceTypeEnum.row,
        title="Row Base Type",
        description="The base type of the row.",
    )


class GridResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Grid Resource Type."""

    rows: list[str] = Field(
        title="Grid Rows",
        description="The row labels for the grid.",
    )
    columns: list[str] = Field(
        title="Grid Columns",
        description="The column labels for the grid.",
    )
    base_type: Literal[ResourceTypeEnum.grid] = Field(
        default=ResourceTypeEnum.grid,
        title="Grid Base Type",
        description="The base type of the grid.",
    )

    @field_validator("columns", "rows", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v


class VoxelGridResourceTypeDefinition(GridResourceTypeDefinition):
    """Definition for a MADSci Voxel Grid Resource Type."""

    capacity: Optional[int] = Field(
        title="Collection Capacity",
        description="The maximum capacity of each element in the grid.",
    )
    planes: list[str] = Field(
        title="Voxel Grid Planes",
        description="The keys of the planes in the grid.",
    )
    base_type: Literal[ResourceTypeEnum.voxel_grid] = Field(
        default=ResourceTypeEnum.voxel_grid,
        title="Voxel Grid Base Type",
        description="The base type of the voxel grid.",
    )

    @field_validator("columns", "rows", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v


class PoolResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Pool Resource Type."""

    base_type: Literal[ResourceTypeEnum.pool] = Field(
        default=ResourceTypeEnum.pool,
        title="Pool Base Type",
        description="The base type of the pool.",
    )


class SlotTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Slot Resource Type."""

    base_type: Literal[ResourceTypeEnum.slot] = Field(
        default=ResourceTypeEnum.slot,
        title="Slot Base Type",
        description="The base type of the slot.",
    )


CustomResourceTypes = Union[
    Annotated[ResourceTypeDefinition, Tag("resource")],  # * resource: Resource
    Annotated[
        ContainerResourceTypeDefinition, Tag("container")
    ],  # * container of resources: Container[Resource]
    Annotated[AssetResourceTypeDefinition, Tag("asset")],  # * trackable resource: Asset
    Annotated[
        ConsumableResourceTypeDefinition, Tag("consumable")
    ],  # * consumable resource: Consumable
    Annotated[
        StackResourceTypeDefinition, Tag("stack")
    ],  # * stack of resources: Container[Resource]
    Annotated[
        QueueResourceTypeDefinition, Tag("queue")
    ],  # * queue of resources: Container[Resource]
    Annotated[
        CollectionResourceTypeDefinition, Tag("collection")
    ],  # * collection of resources: Container[Resource]
    Annotated[
        RowResourceTypeDefinition, Tag("row")
    ],  # * row of resources: Collection[Resource]
    Annotated[
        GridResourceTypeDefinition, Tag("grid")
    ],  # * 2D grid of resources: Collection[Collection[Resource]]
    Annotated[
        VoxelGridResourceTypeDefinition, Tag("voxel_grid")
    ],  # * 3D grid of resources: Collection[Collection[Collection[Resource]]]
    Annotated[
        PoolResourceTypeDefinition, Tag("pool")
    ],  # * collection of consumables with no structure: Collection[Consumable]
    Annotated[
        SlotTypeDefinition, Tag("slot")
    ],  # * slot for a single resource: Container[Resource]
]
