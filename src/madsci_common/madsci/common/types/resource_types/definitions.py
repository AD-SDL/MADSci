"""Pydantic Models for Resource Definitions, used to define default resources for a node or workcell."""

from typing import Annotated, Any, Literal, Optional, Union

from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import (
    ConfigDict,
    MadsciBaseSettings,
    MadsciSQLModel,
    PathLike,
    PositiveInt,
    PositiveNumber,
)
from madsci.common.types.lab_types import ManagerDefinition, ManagerType
from madsci.common.types.resource_types.resource_enums import ResourceTypeEnum
from madsci.common.utils import new_name_str, new_ulid_str
from pydantic import AfterValidator, AnyUrl, Field
from pydantic.functional_validators import field_validator
from pydantic.types import Discriminator, Tag
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field as SQLField


def single_letter_or_digit_validator(value: str) -> str:
    """Validate that the value is a single letter or digit."""
    if not (value.isalpha() and len(value) == 1) or value.isdigit():
        raise ValueError("Value must be a single letter or digit.")
    return value


GridIndex = Union[
    int,
    Annotated[str, AfterValidator(single_letter_or_digit_validator)],
]
GridIndex2D = tuple[GridIndex, GridIndex]
GridIndex3D = tuple[GridIndex, GridIndex, GridIndex]


class ResourceManagerSettings(
    MadsciBaseSettings,
    env_file=(".env", "resources.env"),
    toml_file=("settings.toml", "resources.settings.toml"),
    yaml_file=("settings.yaml", "resources.settings.yaml"),
    json_file=("settings.json", "resources.settings.json"),
    env_prefix="RESOURCES_",
):
    """Settings for the MADSci Resource Manager."""

    resource_server_url: AnyUrl = Field(
        title="Resource Server URL",
        description="The URL of the resource manager server.",
        default="http://localhost:8003",
        alias="resource_server_url",  # * Don't double prefix
    )
    resource_manager_definition: PathLike = Field(
        title="Resource Manager Definition File",
        description="Path to the resource manager definition file to use.",
        default="resource.manager.yaml",
        alias="resource_manager_definition",  # * Don't double prefix
    )
    db_url: str = Field(
        title="Database URL",
        description="The URL of the database for the resource manager.",
        default="postgresql://madsci:madsci@localhost:5432/resources",
    )


class ResourceManagerDefinition(ManagerDefinition):
    """Definition for a Resource Manager's Configuration"""

    name: str = SQLField(
        title="Manager Name",
        description="The name of this resource manager instance.",
        default="Resource Manager",
    )
    resource_manager_id: str = Field(
        title="Resource Manager ID",
        description="The ID of the resource manager.",
        default_factory=new_ulid_str,
    )
    manager_type: Literal[ManagerType.RESOURCE_MANAGER] = SQLField(
        title="Manager Type",
        description="The type of the resource manager",
        default=ManagerType.RESOURCE_MANAGER,
    )
    custom_types: dict[str, "ResourceDefinitions"] = Field(
        default_factory=dict,
        title="Custom Types",
        description="Custom Types for this resource manager",
    )


class CustomResourceAttributeDefinition(MadsciSQLModel, extra="allow"):
    """Definition for a MADSci Custom Resource Attribute."""

    attribute_name: str = SQLField(
        title="Attribute Name",
        description="The name of the attribute.",
    )
    attribute_description: Optional[str] = SQLField(
        default=None,
        title="Attribute Description",
        description="A description of the attribute.",
    )
    optional: bool = SQLField(
        default=False,
        title="Optional",
        description="Whether the attribute is optional.",
    )
    default_value: Any = SQLField(
        default=None,
        title="Default Value",
        description="The default value of the attribute.",
        sa_type=JSON,
    )


class ResourceDefinition(MadsciSQLModel, table=False, extra="allow"):
    """Definition for a MADSci Resource."""

    model_config = ConfigDict(extra="allow")
    resource_name: str = SQLField(
        title="Resource Name",
        description="The name of the resource.",
        default_factory=new_name_str,
    )

    resource_name_prefix: Optional[str] = SQLField(
        title="Resource Name Prefix",
        description="A prefix to append the key of the object to for machine instanciated resources",
        default=None,
    )
    resource_class: str = SQLField(
        title="Resource Class",
        description="The class of the resource. Must match a class defined in the resource manager.",
        default="",
        nullable=False,
    )
    base_type: Literal[ResourceTypeEnum.resource] = SQLField(
        default=ResourceTypeEnum.resource,
        title="Resource Base Type",
        description="The base type of the resource.",
    )
    resource_description: Optional[str] = SQLField(
        default=None,
        title="Resource Description",
        description="A description of the resource.",
    )
    owner: OwnershipInfo = SQLField(
        default_factory=get_current_ownership_info,
        title="Ownership Info",
        description="The owner of this resource",
        sa_type=JSON,
    )
    custom_attributes: Optional[list["CustomResourceAttributeDefinition"]] = SQLField(
        default=None,
        title="Custom Attributes",
        description="Custom attributes used by resources of this type.",
        sa_type=JSON,
    )

    @classmethod
    def discriminate(cls, resource: dict) -> "ResourceDefinition":
        """Discriminate the resource definition based on its base type."""
        from madsci.common.types.resource_types import (  # noqa: PLC0415
            RESOURCE_TYPE_MAP,
        )

        if isinstance(resource, dict):
            resource_type = resource.get("base_type")
        else:
            resource_type = resource.base_type
        return RESOURCE_TYPE_MAP[resource_type]["definition"].model_validate(resource)


class AssetResourceDefinition(ResourceDefinition, table=False):
    """Definition for an asset resource."""

    base_type: Literal[ResourceTypeEnum.asset] = SQLField(
        default=ResourceTypeEnum.asset,
        title="Resource Base Type",
        description="The base type of the asset.",
    )


class ConsumableResourceDefinition(ResourceDefinition):
    """Definition for a consumable resource."""

    base_type: Literal[ResourceTypeEnum.consumable] = SQLField(
        default=ResourceTypeEnum.consumable,
        title="Resource Base Type",
        description="The base type of the consumable.",
    )
    unit: Optional[str] = SQLField(
        default=None,
        title="Resource Unit",
        description="The unit used to measure the quantity of the consumable.",
    )
    quantity: PositiveNumber = SQLField(
        default=0.0,
        title="Default Resource Quantity",
        description="The initial quantity of the consumable.",
    )
    capacity: Optional[PositiveNumber] = SQLField(
        default=None,
        title="Resource Capacity",
        description="The initial capacity of the consumable.",
    )


class DiscreteConsumableResourceDefinition(ConsumableResourceDefinition):
    """Definition for a discrete consumable resource."""

    base_type: Literal[ResourceTypeEnum.discrete_consumable] = SQLField(
        default=ResourceTypeEnum.discrete_consumable,
        title="Resource Base Type",
        description="The base type of the consumable.",
    )
    quantity: PositiveInt = SQLField(
        default=0,
        title="Default Resource Quantity",
        description="The initial quantity of the consumable.",
    )
    capacity: Optional[PositiveInt] = SQLField(
        default=None,
        title="Resource Capacity",
        description="The initial capacity of the consumable.",
    )


class ContinuousConsumableResourceDefinition(ConsumableResourceDefinition):
    """Definition for a continuous consumable resource."""

    base_type: Literal[ResourceTypeEnum.continuous_consumable] = SQLField(
        default=ResourceTypeEnum.continuous_consumable,
        title="Resource Base Type",
        description="The base type of the continuous consumable.",
    )


class ContainerResourceDefinition(ResourceDefinition):
    """Definition for a container resource."""

    base_type: Literal[ResourceTypeEnum.container] = SQLField(
        default=ResourceTypeEnum.container,
        title="Resource Base Type",
        description="The base type of the container.",
    )
    capacity: Optional[Union[int, float]] = SQLField(
        default=None,
        title="Container Capacity",
        description="The capacity of the container. If None, uses the type's default_capacity.",
    )
    default_children: Optional[
        Union[list[ResourceDefinition], dict[str, ResourceDefinition]]
    ] = SQLField(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the container. If None, use the type's default_children.",
    )
    default_child_template: Optional["ResourceDefinitions"] = SQLField(
        default=None,
        title="Default Child Template",
        description="Template for creating child resources, supporting variable substitution. If None, use the type's default_child_template.",
    )


class CollectionResourceDefinition(ContainerResourceDefinition):
    """Definition for a collection resource. Collections are used for resources that have a number of children, each with a unique key, which can be randomly accessed."""

    base_type: Literal[ResourceTypeEnum.collection] = SQLField(
        default=ResourceTypeEnum.collection,
        title="Resource Base Type",
        description="The base type of the collection.",
    )
    keys: Optional[Union[int, list[str]]] = SQLField(
        default=None,
        title="Collection Keys",
        description="The keys for the collection. Can be an integer (converted to 1-based range) or explicit list.",
    )
    default_children: Optional[
        Union[list[ResourceDefinition], dict[str, ResourceDefinition]]
    ] = SQLField(
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


class RowResourceDefinition(ContainerResourceDefinition):
    """Definition for a row resource. Rows are 1D collections of resources. They are treated as single collections (i.e. Collection[Resource])."""

    base_type: Literal[ResourceTypeEnum.row] = SQLField(
        default=ResourceTypeEnum.row,
        title="Resource Base Type",
        description="The base type of the row.",
    )
    default_children: Optional[dict[str, ResourceDefinition]] = SQLField(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the collection. If None, use the type's default_children.",
    )
    fill: bool = SQLField(
        default=False,
        title="Fill",
        description="Whether to populate every empty key with a default child",
    )
    columns: int = SQLField(
        title="Number of Columns",
        description="The number of columns in the row.",
        ge=0,
    )
    is_one_indexed: bool = SQLField(
        title="One Indexed",
        description="Whether the numeric index of the object start at 0 or 1",
        default=True,
    )


class GridResourceDefinition(RowResourceDefinition):
    """Definition for a grid resource. Grids are 2D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Resource]])."""

    base_type: Literal[ResourceTypeEnum.grid] = SQLField(
        default=ResourceTypeEnum.grid,
        title="Resource Base Type",
        description="The base type of the grid.",
    )
    default_children: Optional[dict[str, dict[str, ResourceDefinition]]] = SQLField(
        default=None,
        title="Default Children",
        description="The default children to create when initializing the collection. If None, use the type's default_children.",
    )
    rows: int = SQLField(
        default=None,
        title="Number of Rows",
        description="The number of rows in the grid. If None, use the type's rows.",
    )


class VoxelGridResourceDefinition(GridResourceDefinition):
    """Definition for a voxel grid resource. Voxel grids are 3D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Collection[Resource]]])."""

    base_type: Literal[ResourceTypeEnum.voxel_grid] = SQLField(
        default=ResourceTypeEnum.voxel_grid,
        title="Resource Base Type",
        description="The base type of the voxel grid.",
    )
    default_children: Optional[dict[str, dict[str, dict[str, ResourceDefinition]]]] = (
        SQLField(
            default=None,
            title="Default Children",
            description="The default children to create when initializing the collection. If None, use the type's default_children.",
        )
    )
    layers: int = SQLField(
        title="Number of Layers",
        description="The number of layers in the voxel grid. If None, use the type's layers.",
    )

    def get_all_keys(self) -> list:
        """get all keys of this object"""
        return [
            GridIndex3D((i, j, k))
            for i in range(self.columns)
            for j in range(self.rows)
            for k in range(self.layers)
        ]


class SlotResourceDefinition(ContainerResourceDefinition):
    """Definition for a slot resource."""

    base_type: Literal[ResourceTypeEnum.slot] = SQLField(
        default=ResourceTypeEnum.slot,
        title="Resource Base Type",
        description="The base type of the slot.",
    )

    default_child_quantity: Optional[int] = SQLField(
        default=None,
        title="Default Child Quantity",
        description="The number of children to create by default. If None, use the type's default_child_quantity.",
        ge=0,
        le=1,
    )
    capacity: Literal[1] = SQLField(
        title="Capacity",
        description="The capacity of the slot.",
        default=1,
        const=1,
    )


class StackResourceDefinition(ContainerResourceDefinition):
    """Definition for a stack resource."""

    base_type: Literal[ResourceTypeEnum.stack] = SQLField(
        default=ResourceTypeEnum.stack,
        title="Resource Base Type",
        description="The base type of the stack.",
    )
    default_child_quantity: Optional[int] = SQLField(
        default=None,
        title="Default Child Quantity",
        description="The number of children to create by default. If None, use the type's default_child_quantity.",
    )


class QueueResourceDefinition(ContainerResourceDefinition):
    """Definition for a queue resource."""

    base_type: Literal[ResourceTypeEnum.queue] = SQLField(
        default=ResourceTypeEnum.queue,
        title="Resource Base Type",
        description="The base type of the queue.",
    )
    default_child_quantity: Optional[int] = SQLField(
        default=None,
        title="Default Child Quantity",
        description="The number of children to create by default. If None, use the type's default_child_quantity.",
    )


class PoolResourceDefinition(ContainerResourceDefinition):
    """Definition for a pool resource. Pool resources are collections of consumables with no structure (used for wells, reservoirs, etc.)."""

    base_type: Literal[ResourceTypeEnum.pool] = SQLField(
        default=ResourceTypeEnum.pool,
        title="Resource Base Type",
        description="The base type of the pool.",
    )
    capacity: Optional[PositiveNumber] = SQLField(
        title="Capacity",
        description="The default capacity of the pool as a whole.",
        default=None,
    )
    unit: Optional[str] = SQLField(
        default=None,
        title="Resource Unit",
        description="The unit used to measure the quantity of the pool.",
    )


ResourceDefinitions = Annotated[
    Union[
        Annotated[ResourceDefinition, Tag("resource")],
        Annotated[AssetResourceDefinition, Tag("asset")],
        Annotated[ContainerResourceDefinition, Tag("container")],
        Annotated[CollectionResourceDefinition, Tag("collection")],
        Annotated[RowResourceDefinition, Tag("row")],
        Annotated[GridResourceDefinition, Tag("grid")],
        Annotated[VoxelGridResourceDefinition, Tag("voxel_grid")],
        Annotated[StackResourceDefinition, Tag("stack")],
        Annotated[QueueResourceDefinition, Tag("queue")],
        Annotated[PoolResourceDefinition, Tag("pool")],
        Annotated[SlotResourceDefinition, Tag("slot")],
        Annotated[ConsumableResourceDefinition, Tag("consumable")],
        Annotated[DiscreteConsumableResourceDefinition, Tag("discrete_consumable")],
        Annotated[ContinuousConsumableResourceDefinition, Tag("continuous_consumable")],
    ],
    Discriminator("base_type"),
]
