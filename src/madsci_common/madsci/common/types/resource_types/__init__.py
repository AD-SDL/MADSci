"""Types related to MADSci Resources."""

from typing import Annotated, Literal, Optional, Union

from madsci.common.types.resource_types.custom_types import (
    AssetTypeEnum,
    ConsumableTypeEnum,
    ContainerTypeEnum,
    ResourceBaseTypeEnum,
    ResourceTypeEnum,
)
from madsci.common.types.resource_types.definitions import (
    AssetResourceDefinition,
    CollectionResourceDefinition,
    ConsumableResourceDefinition,
    ContainerResourceDefinition,
    ContinuousConsumableResourceDefinition,
    DiscreteConsumableResourceDefinition,
    GridResourceDefinition,
    PoolResourceDefinition,
    QueueResourceDefinition,
    ResourceDefinition,
    StackResourceDefinition,
    VoxelGridResourceDefinition,
)
from pydantic import computed_field
from pydantic.functional_validators import field_validator, model_validator
from pydantic.types import Discriminator, Tag, datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql.sqltypes import String
from sqlmodel import Field

ResourceBaseTypes = Annotated[
    Union[
        Annotated["ResourceBase", Tag("resource")],
        Annotated["AssetBase", Tag("asset")],
        Annotated["ConsumableBase", Tag("consumable")],
        Annotated["DiscreteConsumableBase", Tag("discrete_consumable")],
        Annotated["ContinuousConsumableBase", Tag("continuous_consumable")],
        Annotated["ContainerBase", Tag("container")],
        Annotated["CollectionBase", Tag("collection")],
        Annotated["GridBase", Tag("grid")],
        Annotated["VoxelGridBase", Tag("voxel_grid")],
        Annotated["StackBase", Tag("stack")],
        Annotated["QueueBase", Tag("queue")],
        Annotated["PoolBase", Tag("pool")],
    ],
    Discriminator("base_type"),
]

ResourceDataModels = Union[
    Annotated["Resource", Tag("resource")],
    Annotated["Asset", Tag("asset")],
    Annotated["Consumable", Tag("consumable")],
    Annotated["DiscreteConsumable", Tag("discrete_consumable")],
    Annotated["ContinuousConsumable", Tag("continuous_consumable")],
    Annotated["Container", Tag("container")],
    Annotated["Collection", Tag("collection")],
    Annotated["Grid", Tag("grid")],
    Annotated["VoxelGrid", Tag("voxel_grid")],
    Annotated["Stack", Tag("stack")],
    Annotated["Queue", Tag("queue")],
    Annotated["Pool", Tag("pool")],
]

ResourceTypes = Union[
    ResourceBaseTypes,
    ResourceDataModels,
]


class ResourceBase(ResourceDefinition, extra="allow", table=False):
    """Base class for all MADSci Resources."""

    resource_url: Optional[str] = Field(
        title="Resource URL",
        description="The URL of the resource.",
        nullable=True,
        default=None,
    )
    base_type: Literal[ResourceBaseTypeEnum.resource] = Field(
        title="Resource Base Type",
        description="The base type of the resource.",
        nullable=False,
        default=ResourceBaseTypeEnum.resource,
        sa_type=String,
    )
    owner: Optional[str] = Field(
        title="Resource owner",
        description="The owner of the resource.",
        nullable=True,
        default=None,
    )
    attributes: dict = Field(
        default_factory=dict,
        sa_type=JSON,
        title="Attributes",
        description="Custom attributes for the asset.",
    )
    created_at: Optional[datetime] = Field(
        title="Created Datetime",
        description="The timestamp of when the resource was created.",
        default=None,
    )
    updated_at: Optional[datetime] = Field(
        title="Updated Datetime",
        description="The timestamp of when the resource was last updated.",
        default=None,
    )
    removed: bool = Field(
        title="Removed",
        description="Whether the resource has been removed from the lab.",
        nullable=False,
        default=False,
    )

    @model_validator(mode="after")
    def validate_subtype(self) -> "ResourceBaseTypes":
        """Validate the resource data."""
        if (
            self.base_type
            and self.base_type in RESOURCE_TYPE_MAP
            and RESOURCE_TYPE_MAP[self.base_type]["base"] != self.__class__
        ):
            return RESOURCE_TYPE_MAP[self.base_type]["base"].model_validate(self)
        return self


class Resource(ResourceBase):
    """Data Model for a Resource."""

    parent_id: Optional[str] = Field(
        default=None,
        title="Parent Resource",
        description="The parent resource ID, if any.",
    )


class AssetBase(ResourceBase):
    """Base class for all MADSci Assets."""

    base_type: Literal[AssetTypeEnum.asset] = Field(
        title="Asset Base Type",
        description="The base type of the asset.",
        nullable=False,
        default=AssetTypeEnum.asset,
    )


class Asset(Resource, AssetBase):
    """Data Model for an Asset."""


class ConsumableBase(ResourceBase):
    """Base class for all MADSci Consumables."""

    base_type: Literal[ConsumableTypeEnum.consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the consumable.",
        nullable=False,
        default=ConsumableTypeEnum.consumable,
    )
    quantity: Optional[Union[float, int]] = Field(
        title="Quantity",
        description="The quantity of the consumable.",
        default=None,
    )


class Consumable(Resource, ConsumableBase):
    """Data Model for a Consumable."""


class DiscreteConsumableBase(ConsumableBase):
    """Base class for all MADSci Discrete Consumables."""

    base_type: Literal[ConsumableTypeEnum.discrete_consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the discrete consumable.",
        default=ConsumableTypeEnum.discrete_consumable,
        const=True,
    )
    quantity: int = Field(
        title="Quantity",
        description="The quantity of the discrete consumable.",
    )


class DiscreteConsumable(Resource, DiscreteConsumableBase):
    """Data Model for a Discrete Consumable."""


class ContinuousConsumableBase(ConsumableBase):
    """Base class for all MADSci Continuous Consumables."""

    base_type: Literal[ConsumableTypeEnum.continuous_consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the continuous consumable.",
        default=ConsumableTypeEnum.continuous_consumable,
        const=True,
    )
    quantity: float = Field(
        title="Quantity",
        description="The quantity of the continuous consumable.",
    )


class ContinuousConsumable(Resource, ContinuousConsumableBase):
    """Data Model for a Continuous Consumable."""


class ContainerBase(AssetBase, table=False):
    """Base class for all MADSci Containers."""

    base_type: Literal[ContainerTypeEnum.container] = Field(
        title="Container Base Type",
        description="The base type of the container.",
        nullable=False,
        default=ContainerTypeEnum.container,
    )
    capacity: Optional[int] = Field(
        title="Capacity",
        description="The capacity of the container.",
    )


class Container(Resource, ContainerBase):
    """Data Model for a Container."""

    children: Optional[dict[str, ResourceBaseTypes]] = Field(
        title="Children",
        description="The children of the container.",
        default_factory=dict,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, ResourceBaseTypes]:
        """Extract the children from the container as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the container."""
        self.children = children


class CollectionBase(ContainerBase):
    """Base class for all MADSci Collections."""

    base_type: Literal[ContainerTypeEnum.collection] = Field(
        title="Container Base Type",
        description="The base type of the collection.",
        default=ContainerTypeEnum.collection,
        const=True,
    )


class Collection(Resource, CollectionBase):
    """Data Model for a Collection."""

    children: Optional[dict[str, ResourceBaseTypes]] = Field(
        title="Children",
        description="The children of the collection.",
        default_factory=dict,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, ResourceBaseTypes]:
        """Extract the children from the collection as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the collection."""
        self.children = children


class GridBase(ContainerBase):
    """Base class for all MADSci Grids."""

    base_type: Literal[ContainerTypeEnum.grid] = Field(
        title="Container Base Type",
        description="The base type of the grid.",
        default=ContainerTypeEnum.grid,
        const=True,
    )
    row_dimension: int = Field(
        title="Row Dimension",
        description="The number of rows in the grid.",
    )
    column_dimension: int = Field(
        title="Column Dimension",
        description="The number of columns in the grid.",
    )


class Grid(Resource, GridBase):
    """Data Model for a Grid."""

    children: Optional[dict[str, dict[str, ResourceBaseTypes]]] = Field(
        title="Children",
        description="The children of the grid container.",
        default_factory=dict,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for _, row_value in self.children.items():
            quantity += len(row_value)
        return quantity

    @field_validator("children", mode="after")
    @classmethod
    def validate_children_keys_no_underscores(cls, value: dict) -> dict:
        """Validate that the children keys do not contain underscores."""
        for key, item in value.items():
            if "_" in key:
                raise ValueError("Children keys cannot contain underscores.")
            for sub_key in item:
                if "_" in sub_key:
                    raise ValueError("Children keys cannot contain underscores.")
        return value

    def extract_children(self) -> dict[str, dict[str, ResourceBaseTypes]]:
        """Extract the children from the grid as a flat dictionary."""
        children_dict = {}
        for row_key, row_value in self.children.items():
            for col_key, col_value in row_value.items():
                children_dict[f"{row_key}_{col_key}"] = col_value

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the grid."""
        for key, value in children.items():
            row_key, col_key = key.split("_")
            if row_key not in self.children:
                self.children[row_key] = {}
            self.children[row_key][col_key] = value


class VoxelGridBase(GridBase):
    """Base class for all MADSci Voxel Grids."""

    base_type: Literal[ContainerTypeEnum.voxel_grid] = Field(
        title="Container Base Type",
        description="The base type of the voxel grid.",
        default=ContainerTypeEnum.voxel_grid,
        const=True,
    )
    row_dimension: int = Field(
        title="Row Dimension",
        description="The number of rows in the grid.",
    )
    column_dimension: int = Field(
        title="Column Dimension",
        description="The number of columns in the grid.",
    )
    layer_dimension: int = Field(
        title="Layer Dimension",
        description="The number of layers in the grid.",
    )


class VoxelGrid(Resource, VoxelGridBase):
    """Data Model for a Voxel Grid."""

    children: Optional[dict[str, dict[str, dict[str, ResourceBaseTypes]]]] = Field(
        title="Children",
        description="The children of the voxel grid container.",
        default_factory=dict,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for _, row_value in self.children.items():
            for _, col_value in row_value.items():
                quantity += len(col_value)
        return quantity

    @field_validator("children", mode="after")
    @classmethod
    def validate_children_keys_no_underscores(cls, value: dict) -> dict:
        """Validate that the children keys do not contain underscores."""
        for key, item in value.items():
            if "_" in key:
                raise ValueError("Children keys cannot contain underscores.")
            for sub_key, sub_value in item.items():
                if "_" in sub_key:
                    raise ValueError("Children keys cannot contain underscores.")
                for sub_sub_key in sub_value:
                    if "_" in sub_sub_key:
                        raise ValueError("Children keys cannot contain underscores.")
        return value

    def extract_children(self) -> dict[str, dict[str, ResourceBaseTypes]]:
        """Extract the children from the grid as a flat dictionary."""
        children_dict = {}
        for row_key, row_value in self.children.items():
            for col_key, col_value in row_value.items():
                for depth_key, depth_value in col_value.items():
                    children_dict[f"{row_key}_{col_key}_{depth_key}"] = depth_value

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the grid."""
        for key, value in children.items():
            row_key, col_key, depth_key = key.split("_")
            if row_key not in self.children:
                self.children[row_key] = {}
            if col_key not in self.children[row_key]:
                self.children[row_key][col_key] = {}
            self.children[row_key][col_key][depth_key] = value


class StackBase(ContainerBase, table=False):
    """Base class for all MADSci Stacks."""

    base_type: Literal[ContainerTypeEnum.stack] = Field(
        title="Container Base Type",
        description="The base type of the stack.",
        default=ContainerTypeEnum.stack,
        const=True,
    )


class Stack(Resource, StackBase):
    """Data Model for a Stack."""

    children: Optional[list[ResourceBaseTypes]] = Field(
        title="Children",
        description="The children of the stack.",
        default_factory=list,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[ResourceBaseTypes]:
        """Extract the children from the stack as a flat dict."""
        children_dict = {}
        for i in range(len(self.children)):
            children_dict[str(i)] = self.children[i]
        return children_dict

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the stack."""
        ordered_children = sorted(children.items(), key=lambda x: int(x[0]))
        self.children = [child[1] for child in ordered_children]


class QueueBase(ContainerBase, table=False):
    """Base class for all MADSci Queues."""

    base_type: Literal[ContainerTypeEnum.queue] = Field(
        title="Container Base Type",
        description="The base type of the queue.",
        default=ContainerTypeEnum.queue,
        const=True,
    )


class Queue(Resource, QueueBase):
    """Data Model for a Queue."""

    children: Optional[list[ResourceBaseTypes]] = Field(
        title="Children",
        description="The children of the queue.",
        default_factory=list,
        discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[ResourceBaseTypes]:
        """Extract the children from the stack as a flat dict."""
        children_dict = {}
        for i in range(len(self.children)):
            children_dict[str(i)] = self.children[i]
        return children_dict

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the queue."""
        ordered_children = sorted(children.items(), key=lambda x: int(x[0]))
        self.children = [child[1] for child in ordered_children]


class PoolBase(ContainerBase):
    """Base class for all MADSci Pools."""

    base_type: Literal[ContainerTypeEnum.pool] = Field(
        title="Container Base Type",
        description="The base type of the pool.",
        default=ContainerTypeEnum.pool,
        const=True,
    )
    capacity: Optional[float] = Field(
        title="Capacity",
        description="The capacity of the pool as a whole.",
    )


class Pool(Resource, PoolBase):
    """Data Model for a Pool."""

    children: Optional[dict[str, ResourceBaseTypes]] = Field(
        title="Children",
        description="The children of the pool.",
        default_factory=dict,
        # discriminator="base_type",
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return sum(
            [
                child.quantity
                for child in self.children.values()
                if hasattr(child, "quantity")
            ]
        )

    def extract_children(self) -> dict[str, ResourceBaseTypes]:
        """Extract the children from the pool as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, ResourceBaseTypes]) -> None:
        """Populate the children of the pool."""
        self.children = children


RESOURCE_TYPE_MAP = {
    ResourceTypeEnum.resource: {
        "definition": ResourceDefinition,
        "base": ResourceBase,
        "model": Resource,
    },
    ResourceTypeEnum.asset: {
        "definition": AssetResourceDefinition,
        "base": AssetBase,
        "model": Asset,
    },
    ResourceTypeEnum.consumable: {
        "definition": ConsumableResourceDefinition,
        "base": ConsumableBase,
        "model": Consumable,
    },
    ConsumableTypeEnum.discrete_consumable: {
        "definition": DiscreteConsumableResourceDefinition,
        "base": DiscreteConsumableBase,
        "model": DiscreteConsumable,
    },
    ConsumableTypeEnum.continuous_consumable: {
        "definition": ContinuousConsumableResourceDefinition,
        "base": ContinuousConsumableBase,
        "model": ContinuousConsumable,
    },
    AssetTypeEnum.container: {
        "definition": ContainerResourceDefinition,
        "base": ContainerBase,
        "model": Container,
    },
    ContainerTypeEnum.stack: {
        "definition": StackResourceDefinition,
        "base": StackBase,
        "model": Stack,
    },
    ContainerTypeEnum.queue: {
        "definition": QueueResourceDefinition,
        "base": QueueBase,
        "model": Queue,
    },
    ContainerTypeEnum.collection: {
        "definition": CollectionResourceDefinition,
        "base": CollectionBase,
        "model": Collection,
    },
    ContainerTypeEnum.grid: {
        "definition": GridResourceDefinition,
        "base": GridBase,
        "model": Grid,
    },
    ContainerTypeEnum.voxel_grid: {
        "definition": VoxelGridResourceDefinition,
        "base": VoxelGridBase,
        "model": VoxelGrid,
    },
    ContainerTypeEnum.pool: {
        "definition": PoolResourceDefinition,
        "base": PoolBase,
        "model": Pool,
    },
}
