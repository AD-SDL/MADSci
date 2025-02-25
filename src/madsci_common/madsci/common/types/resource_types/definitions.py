"""Pydantic Models for Resource Definitions, used to define default resources for a module or workcell."""

from typing import Annotated, Literal, Optional, Union

from madsci.common.types.base_types import BaseModel, new_ulid_str
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.types.resource_types.custom_types import (
    CustomResourceTypes,
    ResourceTypeEnum,
)
from madsci.common.utils import new_name_str
from madsci.common.validators import ulid_validator
from pydantic.functional_validators import field_validator, model_validator
from pydantic.types import Tag
from sqlmodel import Field


class ResourceManagerDefinition(ManagerDefinition):
    """Definition for a Resource Manager's Configuration"""

    manager_type: Literal[ManagerType.RESOURCE_MANAGER] = Field(
        title="Manager Type",
        description="The type of the resource manager",
        default=ManagerType.RESOURCE_MANAGER,
    )
    host: str = Field(
        default="127.0.0.1",
        title="Server Host",
        description="The hostname or IP address of the Resource Manager server.",
    )
    port: int = Field(
        default=8004,
        title="Server Port",
        description="The port number of the Resource Manager server.",
    )
    db_url: str = Field(
        default="postgresql://rpl:rpl@localhost:5432/resources",
        title="Database URL",
        description="The URL of the database used by the Resource Manager.",
    )


class ResourceDefinition(BaseModel, table=False):
    """Definition for a MADSci Resource."""

    resource_id: str = Field(
        title="Resource ID",
        description="The ID of the resource.",
        default_factory=new_ulid_str,
        primary_key=True,
    )
    resource_name: str = Field(
        title="Resource Name",
        description="The name of the resource.",
        default_factory=new_name_str,
    )
    resource_type: str = Field(
        title="Resource Type",
        description="The type of the resource. Either a custom type name or a resource base type.",
        default="",
        nullable=False,
    )
    base_type: Optional[ResourceTypeEnum] = Field(
        default=None,
        title="Resource Base Type",
        description="The base type of the resource.",
    )
    resource_description: Optional[str] = Field(
        default=None,
        title="Resource Description",
        description="A description of the resource.",
    )
    is_ulid = field_validator("resource_id")(ulid_validator)


class AssetResourceDefinition(ResourceDefinition, table=False):
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
    row_dimension: int = Field(
        default=None,
        title="Row Dimension",
        description="The number of rows in the grid. If None, use the type's row_dimension.",
    )
    column_dimension: int = Field(
        default=None,
        title="Column Dimension",
        description="The number of columns in the grid. If None, use the type's column_dimension.",
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
    layer_dimension: int = Field(
        title="Layer Dimension",
        description="The number of layers in the voxel grid. If None, use the type's layer_dimension.",
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


class ResourceFile(BaseModel):
    """Definition for a MADSci Resource File."""

    resource_types: list[
        Annotated[CustomResourceTypes, Field(discriminator="base_type")]
    ] = Field(
        title="Resource Types",
        description="The definitions of the resource types in the file.",
        default=[],
    )
    default_resources: list[ResourceDefinitions] = Field(
        title="Default Resources",
        description="The definitions of the default resources in the file.",
        default=[],
        discriminator="base_type",
    )

    @model_validator(mode="after")
    def validate_resource_types(self) -> "ResourceFile":
        """Validate resource types."""
        for resource_type in self.resource_types:
            for parent_type in resource_type.parent_types:
                if parent_type not in ResourceTypeEnum and parent_type not in [
                    resource_type.type_name for resource_type in self.resource_types
                ]:
                    raise ValueError(
                        f"Unknown resource parent type: {parent_type}, parent type must be one of {list(ResourceTypeEnum)} or a custom defined resource type.",
                    )
        return self
