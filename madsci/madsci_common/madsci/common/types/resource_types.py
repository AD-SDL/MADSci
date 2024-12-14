"""Types related to MADSci Resources."""

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import Json
from pydantic.config import ConfigDict
from pydantic.functional_validators import field_validator, model_validator
from pydantic.types import Discriminator, Tag
from sqlmodel import Field, Column
from sqlalchemy.dialects.postgresql import JSON

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.validators import ulid_validator


class ResourceType(str, Enum):
    """Type for a MADSci Resource."""

    resource = "resource"
    """The root resource type. Used when a resource type is not known or any resource type is acceptable."""
    asset = "asset"
    consumable = "consumable"


class AssetType(str, Enum):
    """Type for a MADSci Asset."""

    container = "container"
    asset = "asset"


class ConsumableType(str, Enum):
    """Type for a MADSci Consumable."""

    discrete_consumable = "discrete_consumable"
    continuous_consumable = "continuous_consumable"


class ContainerType(str, Enum):
    """Type for a MADSci Container."""

    stack = "stack"
    queue = "queue"
    collection = "collection"
    grid = "grid"
    voxel_grid = "voxel_grid"
    pool = "pool"


ResourceTypes = Union[ResourceType, AssetType, ContainerType, ConsumableType]


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
    base_type: Literal[ResourceType.resource] = Field(
        default=ResourceType.resource,
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
    base_type: Literal[AssetType.container] = Field(
        default=AssetType.container,
        title="Container Base Type",
        description="The base type of the container.",
    )


class AssetResourceTypeDefinition(ResourceTypeDefinition):
    """Definition for a MADSci Asset Resource Type."""

    base_type: Literal[ResourceType.asset] = Field(
        default=ResourceType.asset,
        title="Asset Base Type",
        description="The base type of the asset.",
    )


class ConsumableResourceTypeDefinition(ResourceTypeDefinition):
    """Definition for a MADSci Consumable Resource Type."""

    base_type: Literal[ResourceType.consumable] = Field(
        default=ResourceType.consumable,
        title="Consumable Base Type",
        description="The base type of the consumable.",
    )


class DiscreteConsumableResourceTypeDefinition(ConsumableResourceTypeDefinition):
    """Definition for a MADSci Discrete Consumable Resource Type."""

    base_type: Literal[ConsumableType.discrete_consumable] = Field(
        default=ConsumableType.discrete_consumable,
        title="Discrete Consumable Base Type",
        description="The base type of the discrete consumable.",
    )


class ContinuousConsumableResourceTypeDefinition(ConsumableResourceTypeDefinition):
    """Definition for a MADSci Continuous Consumable Resource Type."""

    base_type: Literal[ConsumableType.continuous_consumable] = Field(
        default=ConsumableType.continuous_consumable,
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
    base_type: Literal[ContainerType.stack] = Field(
        default=ContainerType.stack,
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
    base_type: Literal[ContainerType.queue] = Field(
        default=ContainerType.queue,
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

    @field_validator("keys", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v

    base_type: Literal[ContainerType.collection] = Field(
        default=ContainerType.collection,
        title="Collection Base Type",
        description="The base type of the collection.",
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

    @field_validator("columns", "rows", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v

    base_type: Literal[ContainerType.grid] = Field(
        default=ContainerType.grid,
        title="Grid Base Type",
        description="The base type of the grid.",
    )


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

    @field_validator("columns", "rows", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str]]) -> list[str]:
        """Convert integer keys count to 1-indexed range."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v

    base_type: Literal[ContainerType.voxel_grid] = Field(
        default=ContainerType.voxel_grid,
        title="Voxel Grid Base Type",
        description="The base type of the voxel grid.",
    )


class PoolResourceTypeDefinition(ContainerResourceTypeDefinition):
    """Definition for a MADSci Pool Resource Type."""

    base_type: Literal[ContainerType.pool] = Field(
        default=ContainerType.pool,
        title="Pool Base Type",
        description="The base type of the pool.",
    )


class ResourceDefinition(BaseModel, extra="allow", table=False):
    """Definition for a MADSci Resource."""

    # model_config = ConfigDict(extra="allow") # Causes error with SQLModel and extra="allow" creates ambiguity because SQLAlchemy does not recognize undefined fields when table = True

    resource_name: str = Field(
        title="Resource Name",
        description="The name of the resource.",
    )
    resource_type: str = Field(
        title="Resource Type",
        description="The type of the resource.",
        default="", 
        nullable=False
    )
    base_type: Optional[str] = Field(
        default=None,
        title="Resource Base Type",
        description="The base type of the resource.",
    )
    resource_description: Optional[str] = Field(
        default=None,
        title="Resource Description",
        description="A description of the resource.",
    )
    resource_id: str = Field(
        title="Resource ID",
        description="The ID of the resource.",
        default_factory=new_ulid_str,
        primary_key=True
    )
    parent: Optional[str] = Field(
        default=None,
        title="Parent Resource",
        description="The parent resource ID or name. If None, defaults to the owning module or workcell.",
    )
    attributes: dict = Field(
        title="Resource Attributes",
        description="Additional attributes for the resource.",
        default_factory=dict,
    )

    is_ulid = field_validator("resource_id")(ulid_validator)


class AssetResourceDefinition(ResourceDefinition,table=False):
    """Definition for an asset resource."""


class ConsumableResourceDefinition(ResourceDefinition):
    """Definition for a consumable resource."""


class DiscreteConsumableResourceDefinition(ConsumableResourceDefinition):
    """Definition for a discrete consumable resource."""


class ContinuousConsumableResourceDefinition(ConsumableResourceDefinition):
    """Definition for a continuous consumable resource."""


class ContainerResourceDefinition(ResourceDefinition):
    """Definition for a container resource."""

    capacity: Optional[Union[int, float]] = Field(
        default=None,
        title="Container Capacity",
        description="The capacity of the container. If None, uses the type's default_capacity.",
    )
    default_children: Optional[
        Union[list[ResourceDefinition], dict[str, ResourceDefinition]]
    ] = Field(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the container. If None, use the type's default_children.",
    )
    default_child_template: Optional[ResourceDefinition] = Field(
        default=None,
        title="Default Child Template",
        description="Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.",
    )


class CollectionResourceDefinition(ContainerResourceDefinition):
    """Definition for a collection resource. Collections are used for resources that have a number of children, each with a unique key, which can be randomly accessed."""

    keys: Optional[Union[int, list[str]]] = Field(
        default=None,
        title="Collection Keys",
        description="The keys for the collection. Can be an integer (converted to 1-based range) or explicit list.",
    )
    default_children: Optional[
        Union[list[ResourceDefinition], dict[str, ResourceDefinition]]
    ] = Field(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the collection. If None, use the type's default_children.",
    )

    @field_validator("keys", mode="before")
    @classmethod
    def validate_keys(cls, v: Union[int, list[str], None]) -> Optional[list[str]]:
        """Convert integer keys to 1-based range if needed."""
        if isinstance(v, int):
            return [str(i) for i in range(1, v + 1)]
        return v


class GridResourceDefinition(ContainerResourceDefinition):
    """Definition for a grid resource. Grids are 2D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Resource]])."""

    default_children: Optional[dict[str, dict[str, ResourceDefinition]]] = Field(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the collection. If None, use the type's default_children.",
    )


class VoxelGridResourceDefinition(GridResourceDefinition):
    """Definition for a voxel grid resource. Voxel grids are 3D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Collection[Resource]]])."""

    default_children: Optional[dict[str, dict[str, dict[str, ResourceDefinition]]]] = (
        Field(
            default=None,
            title="Default Children",
            description="The default children to create when initializing the collection. If None, use the type's default_children.",
        )
    )


class StackResourceDefinition(ContainerResourceDefinition):
    """Definition for a stack resource."""

    default_child_quantity: Optional[int] = Field(
        default=None,
        title="Default Child Quantity",
        description="The number of children to create by default. If None, use the type's default_child_quantity.",
    )


class QueueResourceDefinition(ContainerResourceDefinition):
    """Definition for a queue resource."""

    default_child_quantity: Optional[int] = Field(
        default=None,
        title="Default Child Quantity",
        description="The number of children to create by default. If None, use the type's default_child_quantity.",
    )


class PoolResourceDefinition(ContainerResourceDefinition):
    """Definition for a pool resource. Pool resources are collections of consumables with no structure (used for wells, reservoirs, etc.)."""


ResourceTypeDefinitions = Union[
    ResourceTypeDefinition,
    ContainerResourceTypeDefinition,  # * container of resources: Container[Resource]
    AssetResourceTypeDefinition,  # * trackable resource: Asset
    ConsumableResourceTypeDefinition,  # * consumable resource: Consumable
    StackResourceTypeDefinition,  # * stack of resources: Container[Resource]
    QueueResourceTypeDefinition,  # * queue of resources: Container[Resource]
    CollectionResourceTypeDefinition,  # * collection of resources: Container[Resource]
    GridResourceTypeDefinition,  # * 2D grid of resources: Collection[Collection[Resource]]
    VoxelGridResourceTypeDefinition,  # * 3D grid of resources: Collection[Collection[Collection[Resource]]]
    PoolResourceTypeDefinition,  # * collection of consumables with no structure: Collection[Consumable]
]

ResourceDefinitions = Union[
    Annotated[ResourceDefinition, Tag("resource")],
    Annotated[AssetResourceDefinition, Tag("asset")],
    Annotated[ContainerResourceDefinition, Tag("container")],
    Annotated[CollectionResourceDefinition, Tag("collection")],
    Annotated[GridResourceDefinition, Tag("grid")],
    Annotated[VoxelGridResourceDefinition, Tag("voxel_grid")],
    Annotated[StackResourceDefinition, Tag("stack")],
    Annotated[QueueResourceDefinition, Tag("queue")],
    Annotated[PoolResourceDefinition, Tag("pool")],
]


def discriminate_default_resources(
    v: Union[ResourceDefinitions, dict[str, Any]],
) -> ResourceDefinitions:
    """Discriminate default resources. If the resource type is not explicitly defined, default to 'resource'."""
    if isinstance(v, dict):
        if v.get("resource_type") in RESOURCE_DEFINITION_MAP:
            return v.get("resource_type")
        return "resource"
    if v.resource_type in RESOURCE_DEFINITION_MAP:
        return v.resource_type
    return "resource"


class ResourceFile(BaseModel):
    """Definition for a MADSci Resource File."""

    resource_types: list[
        Annotated[ResourceTypeDefinitions, Field(discriminator="base_type")]
    ] = Field(
        title="Resource Types",
        description="The definitions of the resource types in the file.",
        default=[],
    )
    default_resources: list[
        Annotated[ResourceDefinitions, Discriminator(discriminate_default_resources)]
    ] = Field(
        title="Default Resources",
        description="The definitions of the default resources in the file.",
        default=[],
    )

    @model_validator(mode="after")
    def validate_resource_types(self) -> "ResourceFile":
        """Validate resource types."""
        for resource_type in self.resource_types:
            for parent_type in resource_type.parent_types:
                if (
                    parent_type not in RESOURCE_TYPE_DEFINITION_MAP
                    and parent_type
                    not in [
                        resource_type.type_name for resource_type in self.resource_types
                    ]
                ):
                    raise ValueError(
                        f"Unknown resource parent type: {parent_type}, parent type must be one of {RESOURCE_TYPE_DEFINITION_MAP.keys()} or a defined resource type.",
                    )
        return self

    @model_validator(mode="after")
    def validate_default_resources(self) -> "ResourceFile":
        """Validate default resources and their resource types."""
        default_resources = []
        for resource in self.default_resources:
            if resource.resource_type not in RESOURCE_DEFINITION_MAP:
                resource_type = next(
                    (
                        resource_type
                        for resource_type in self.resource_types
                        if resource_type.type_name == resource.resource_type
                    ),
                    None,
                )
                if resource_type is None:
                    default_resources.append(resource)
                else:
                    default_resources.append(
                        RESOURCE_DEFINITION_MAP[resource_type.base_type].model_validate(
                            resource,
                        ),
                    )
            else:
                default_resources.append(resource)
        self.__dict__["default_resources"] = default_resources
        return self


RESOURCE_BASE_TYPES = [
    ResourceType.resource,
    ResourceType.asset,
    ResourceType.consumable,
    ConsumableType.discrete_consumable,
    ConsumableType.continuous_consumable,
    AssetType.container,
    ContainerType.stack,
    ContainerType.queue,
    ContainerType.collection,
    ContainerType.grid,
    ContainerType.voxel_grid,
    ContainerType.pool,
]

RESOURCE_TYPE_DEFINITION_MAP: dict[str, type[ResourceTypeDefinition]] = {
    ResourceType.resource: ResourceTypeDefinition,
    ResourceType.asset: AssetResourceTypeDefinition,
    AssetType.container: ContainerResourceTypeDefinition,
    ResourceType.consumable: ConsumableResourceTypeDefinition,
    ConsumableType.discrete_consumable: DiscreteConsumableResourceTypeDefinition,
    ConsumableType.continuous_consumable: ContinuousConsumableResourceTypeDefinition,
    ContainerType.stack: StackResourceTypeDefinition,
    ContainerType.queue: QueueResourceTypeDefinition,
    ContainerType.collection: CollectionResourceTypeDefinition,
    ContainerType.grid: GridResourceTypeDefinition,
    ContainerType.voxel_grid: VoxelGridResourceTypeDefinition,
    ContainerType.pool: PoolResourceTypeDefinition,
}

RESOURCE_DEFINITION_MAP: dict[str, type[ResourceDefinition]] = {
    ResourceType.resource: ResourceDefinition,
    ResourceType.asset: AssetResourceDefinition,
    AssetType.container: ContainerResourceDefinition,
    ResourceType.consumable: ConsumableResourceDefinition,
    ConsumableType.discrete_consumable: DiscreteConsumableResourceDefinition,
    ConsumableType.continuous_consumable: ContinuousConsumableResourceDefinition,
    ContainerType.stack: StackResourceDefinition,
    ContainerType.queue: QueueResourceDefinition,
    ContainerType.collection: CollectionResourceDefinition,
    ContainerType.grid: GridResourceDefinition,
    ContainerType.voxel_grid: VoxelGridResourceDefinition,
    ContainerType.pool: PoolResourceDefinition,
}


class ResourceBase(ResourceDefinition, extra="allow"):
    """Base class for all MADSci Resources."""
    # Might be better to put this elsewhere
    # resource_url: str = Field(
    #     title="Resource URL",
    #     description="The URL of the resource.",
    # )
    ownership: Optional[OwnershipInfo] = Field(
        title="Ownership",
        description="Information about the ownership of the resource.",
        default_factory=OwnershipInfo,
        sa_column=Column(JSON),
    )
    owner: str = Field(
        title="Resource Type",
        description="The type of the resource.", 
        nullable=True
    )


class AssetBase(AssetResourceDefinition):
    """Base class for all MADSci Assets."""


class ConsumableBase(ResourceBase):
    """Base class for all MADSci Consumables."""

    quantity: Optional[Union[int, float]] = Field(
        title="Quantity",
        description="The quantity of the consumable.",
    )


class DiscreteConsumableBase(ConsumableBase):
    """Base class for all MADSci Discrete Consumables."""

    quantity: int = Field(
        title="Quantity",
        description="The quantity of the discrete consumable.",
    )


class ContinuousConsumableBase(ConsumableBase):
    """Base class for all MADSci Continuous Consumables."""

    quantity: float = Field(
        title="Quantity",
        description="The quantity of the continuous consumable.",
    )


class ContainerBase(ResourceBase):
    """Base class for all MADSci Containers."""

    children: Optional[list[ResourceBase]] = Field(
        title="Children",
        description="The children of the container.",
        default_factory=list,
        sa_column=Column(JSON),  # Use Column(JSON) to map to SQLAlchemy's JSON type
    )
    capacity: Optional[int] = Field(
        title="Capacity",
        description="The capacity of the container.",
    )


class CollectionBase(ContainerBase):
    """Base class for all MADSci Collections."""

    children: dict[str, ResourceBase] = Field(
        title="Keys",
        description="The keys of the collection.",
    )


class GridBase(ContainerBase):
    """Base class for all MADSci Grids."""

    children: dict[str, dict[str, ResourceBase]] = Field(
        title="Children",
        description="The children of the grid.",
    )


class VoxelGridBase(GridBase):
    """Base class for all MADSci Voxel Grids."""

    children: dict[str, dict[str, dict[str, ResourceBase]]] = Field(
        title="Children",
        description="The children of the voxel grid.",
    )


class StackBase(ContainerBase):
    """Base class for all MADSci Stacks."""


class QueueBase(ContainerBase):
    """Base class for all MADSci Queues."""


class PoolBase(ContainerBase):
    """Base class for all MADSci Pools."""

    children: dict[str, ConsumableBase] = Field(
        title="Children",
        description="The children of the pool.",
    )
    capacity: Optional[Union[int, float]] = Field(
        title="Capacity",
        description="The capacity of the pool.",
    )

if __name__ == "__main__":
    a = ConsumableBase(resource_name="Water",resource_type="pool",quantity=50.0,ownership=None,capacity=100)
    t = PoolBase(resource_name="Test Pool",resource_description="teststes",capacity=100,ownership=None,quantity=50,children={"A":a},resource_type="pool")
    print(t.children["A"])
    s = StackBase(resource_name="stack",capacity=10,ownership=None,resource_type="stack")
    print(s)