"""Types related to MADSci Resources."""

import string
from typing import Annotated, Literal, Optional, Union

from pydantic import (
    AfterValidator,
    AnyUrl,
    computed_field,
    model_validator,
)
from pydantic.types import Discriminator, Tag, datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql.sqltypes import String
from sqlmodel import Field
from typing_extensions import Self  # type: ignore

from madsci.common.types.resource_types.custom_types import (
    AssetTypeEnum,
    ConsumableTypeEnum,
    ContainerTypeEnum,
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
    RowResourceDefinition,
    StackResourceDefinition,
    VoxelGridResourceDefinition,
)

PositiveInt = Annotated[int, Field(ge=0)]
PositiveNumber = Annotated[Union[float, int], Field(ge=0)]


class Resource(ResourceDefinition, extra="allow", table=False):
    """Base class for all MADSci Resources."""

    resource_url: Optional[AnyUrl] = Field(
        title="Resource URL",
        description="The URL of the resource.",
        nullable=True,
        default=None,
        sa_type=String,
    )
    base_type: Literal[ResourceTypeEnum.resource] = Field(
        title="Resource Base Type",
        description="The base type of the resource.",
        nullable=False,
        default=ResourceTypeEnum.resource,
        sa_type=String,
    )
    parent_id: Optional[str] = Field(
        default=None,
        title="Parent Resource",
        description="The parent resource ID, if any.",
    )
    key: Optional[str] = Field(
        default=None,
        title="Key",
        description="The key of the resource in the parent container, if any.",
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

    @classmethod
    def discriminate(cls, resource: "ResourceDataModels") -> "ResourceDataModels":
        """Discriminate the resource based on its base type."""
        if isinstance(resource, dict):
            resource_type = resource.get("base_type")
        else:
            resource_type = resource.base_type
        return RESOURCE_TYPE_MAP[resource_type]["model"].model_validate(resource)


class Asset(Resource):
    """Base class for all MADSci Assets."""

    base_type: Literal[AssetTypeEnum.asset] = Field(
        title="Asset Base Type",
        description="The base type of the asset.",
        nullable=False,
        default=AssetTypeEnum.asset,
    )


class Consumable(Resource):
    """Base class for all MADSci Consumables."""

    base_type: Literal[ConsumableTypeEnum.consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the consumable.",
        nullable=False,
        default=ConsumableTypeEnum.consumable,
    )
    quantity: PositiveNumber = Field(
        title="Quantity",
        description="The quantity of the consumable.",
    )
    capacity: Optional[PositiveNumber] = Field(
        title="Capacity",
        description="The maximum capacity of the consumable.",
        default=None,
    )

    @model_validator(mode="after")
    def validate_consumable_quantity(self) -> Self:
        """Validate that the quantity is less than or equal to the capacity."""
        if self.capacity is not None and self.quantity > self.capacity:
            raise ValueError("Quantity cannot be greater than capacity.")
        return self


class DiscreteConsumable(Consumable):
    """Base class for all MADSci Discrete Consumables."""

    base_type: Literal[ConsumableTypeEnum.discrete_consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the discrete consumable.",
        default=ConsumableTypeEnum.discrete_consumable,
        const=True,
    )
    quantity: PositiveInt = Field(
        title="Quantity",
        description="The quantity of the discrete consumable.",
    )
    capacity: Optional[PositiveInt] = Field(
        title="Capacity",
        description="The maximum capacity of the discrete consumable.",
        default=None,
    )


class ContinuousConsumable(Consumable):
    """Base class for all MADSci Continuous Consumables."""

    base_type: Literal[ConsumableTypeEnum.continuous_consumable] = Field(
        title="Consumable Base Type",
        description="The base type of the continuous consumable.",
        default=ConsumableTypeEnum.continuous_consumable,
        const=True,
    )
    quantity: PositiveNumber = Field(
        title="Quantity",
        description="The quantity of the continuous consumable.",
    )
    capacity: Optional[PositiveNumber] = Field(
        title="Capacity",
        description="The maximum capacity of the continuous consumable.",
        default=None,
    )


class Container(Asset):
    """Data Model for a Container."""

    base_type: Literal[ContainerTypeEnum.container] = Field(
        title="Container Base Type",
        description="The base type of the container.",
        nullable=False,
        default=ContainerTypeEnum.container,
    )
    capacity: Optional[PositiveInt] = Field(
        title="Capacity",
        description="The capacity of the container.",
        default=None,
    )
    children: Optional[dict[str, "ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the container.",
        default_factory=dict,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the container as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the container."""
        self.children = children

    @model_validator(mode="after")
    def validate_container_quantity(self) -> Self:
        """Validate that the quantity is less than or equal to the capacity."""
        if self.capacity is not None and self.quantity > self.capacity:
            raise ValueError("Quantity cannot be greater than capacity.")
        return self


class Collection(Container):
    """Data Model for a Collection."""

    base_type: Literal[ContainerTypeEnum.collection] = Field(
        title="Container Base Type",
        description="The base type of the collection.",
        default=ContainerTypeEnum.collection,
        const=True,
    )
    children: Optional[dict[str, "ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the collection.",
        default_factory=dict,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the collection as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the collection."""
        self.children = children


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


class Row(Container):
    """Data Model for a Row"""

    children: Optional[dict[GridIndex, "ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the row container.",
        default_factory=dict,
    )
    base_type: Literal[ContainerTypeEnum.row] = Field(
        title="Container Base Type",
        description="The base type of the row.",
        default=ContainerTypeEnum.row,
        const=True,
    )
    row_dimension: int = Field(
        title="Row Dimension",
        description="The number of rows in the row.",
        ge=0,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    @staticmethod
    def flatten_key(key: GridIndex) -> str:
        """Flatten the key to a string."""
        return str(key)

    @staticmethod
    def expand_key(key: str) -> GridIndex:
        """Expand the key to a 2-tuple."""
        if key.isdigit():
            return int(key)
        return key

    def check_key_bounds(self, key: Union[str, GridIndex]) -> bool:
        """Check if the key is within the bounds of the grid."""
        if isinstance(key, int) or str(key).isdigit():
            key = int(key)
        else:
            key = string.ascii_lowercase.index(key.lower())
        return not (key < 0 or key >= self.row_dimension)


class Grid(Row):
    """Data Model for a Grid."""

    children: Optional[dict[GridIndex, dict[GridIndex, "ResourceDataModels"]]] = Field(
        title="Children",
        description="The children of the grid container.",
        default_factory=dict,
    )
    base_type: Literal[ContainerTypeEnum.grid] = Field(
        title="Container Base Type",
        description="The base type of the grid.",
        default=ContainerTypeEnum.grid,
        const=True,
    )
    column_dimension: int = Field(
        title="Column Dimension",
        description="The number of columns in the grid.",
        ge=0,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for _, row_value in self.children.items():
            quantity += len(row_value)
        return quantity

    @staticmethod
    def flatten_key(key: GridIndex2D) -> str:
        """Flatten the key to a string."""
        return "_".join([str(index) for index in key])

    @staticmethod
    def expand_key(key: str) -> GridIndex2D:
        """Expand the key to a 2-tuple."""
        expanded_key = key.split("_")
        final_keys = []
        for index in expanded_key:
            if index.isdigit():
                final_keys.append(int(index))
            else:
                final_keys.append(index)
        return tuple(final_keys)

    def check_key_bounds(self, key: Union[str, GridIndex2D]) -> bool:
        """Check if the key is within the bounds of the grid."""
        if isinstance(key, str):
            key = self.expand_key(key)
        elif not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("Key must be a string or a 2-tuple.")
        numeric_key = []
        for index in key:
            if isinstance(index, int) or str(index).isdigit():
                numeric_key.append(int(index))
            else:
                numeric_key.append(string.ascii_lowercase.index(index.lower()))
        key = numeric_key
        return not (key[0] < 0 or key[0] >= self.row_dimension) and not (
            key[1] < 0 or key[1] >= self.column_dimension
        )

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the grid as a flat dictionary."""
        children_dict = {}
        for row_key, row_value in self.children.items():
            for col_key, col_value in row_value.items():
                children_dict[self.flatten_key((row_key, col_key))] = col_value

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the grid."""
        for key, value in children.items():
            row_key, col_key = self.expand_key(key)
            if row_key not in self.children:
                self.children[row_key] = {}
            self.children[row_key][col_key] = value


class VoxelGrid(Grid):
    """Data Model for a Voxel Grid."""

    base_type: Literal[ContainerTypeEnum.voxel_grid] = Field(
        title="Container Base Type",
        description="The base type of the voxel grid.",
        default=ContainerTypeEnum.voxel_grid,
        const=True,
    )
    layer_dimension: int = Field(
        title="Layer Dimension",
        description="The number of layers in the grid.",
        ge=0,
    )
    children: Optional[
        dict[GridIndex, dict[GridIndex, dict[GridIndex, "ResourceDataModels"]]]
    ] = Field(
        title="Children",
        description="The children of the voxel grid container.",
        default_factory=dict,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for _, row_value in self.children.items():
            for _, col_value in row_value.items():
                quantity += len(col_value)
        return quantity

    @staticmethod
    def flatten_key(key: GridIndex3D) -> str:
        """Flatten the key to a string."""
        return "_".join([str(index) for index in key])

    @staticmethod
    def expand_key(key: str) -> GridIndex3D:
        """Expand the key to a tuple."""
        expanded_key = key.split("_")
        final_keys = []
        for index in expanded_key:
            if index.isdigit():
                final_keys.append(int(index))
            else:
                final_keys.append(index)
        return final_keys

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the grid as a flat dictionary."""
        children_dict = {}
        for row_key, row_value in self.children.items():
            for col_key, col_value in row_value.items():
                for depth_key, depth_value in col_value.items():
                    children_dict[self.flatten_key((row_key, col_key, depth_key))] = (
                        depth_value
                    )

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the grid."""
        for key, value in children.items():
            row_key, col_key, depth_key = self.expand_key(key)
            if row_key not in self.children:
                self.children[row_key] = {}
            if col_key not in self.children[row_key]:
                self.children[row_key][col_key] = {}
            self.children[row_key][col_key][depth_key] = value

    def check_key_bounds(self, key: Union[str, GridIndex3D]) -> bool:
        """Check if the key is within the bounds of the grid."""
        if isinstance(key, str):
            key = self.expand_key(key)
        elif not isinstance(key, tuple) or len(key) != 3:
            raise ValueError("Key must be a string or a 3-tuple.")
        numeric_key = []
        for index in key:
            if isinstance(index, int) or str(index).isdigit():
                numeric_key.append(int(index))
            else:
                numeric_key.append(string.ascii_lowercase.index(index.lower()))
        key = numeric_key
        return (
            not (key[0] < 0 or key[0] >= self.row_dimension)
            and not (key[1] < 0 or key[1] >= self.column_dimension)
            and not (key[2] < 0 or key[2] >= self.layer_dimension)
        )


class Stack(Container):
    """Data Model for a Stack."""

    base_type: Literal[ContainerTypeEnum.stack] = Field(
        title="Container Base Type",
        description="The base type of the stack.",
        default=ContainerTypeEnum.stack,
        const=True,
    )
    children: Optional[list["ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the stack.",
        default_factory=list,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the stack as a flat dict."""
        children_dict = {}
        for i in range(len(self.children)):
            children_dict[str(i)] = self.children[i]
        return children_dict

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the stack."""
        ordered_children = sorted(children.items(), key=lambda x: int(x[0]))
        self.children = [child[1] for child in ordered_children]


class Queue(Container):
    """Data Model for a Queue."""

    base_type: Literal[ContainerTypeEnum.queue] = Field(
        title="Container Base Type",
        description="The base type of the queue.",
        default=ContainerTypeEnum.queue,
        const=True,
    )
    children: Optional[list["ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the queue.",
        default_factory=list,
    )

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the stack as a flat dict."""
        children_dict = {}
        for i in range(len(self.children)):
            children_dict[str(i)] = self.children[i]
        return children_dict

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the queue."""
        ordered_children = sorted(children.items(), key=lambda x: int(x[0]))
        self.children = [child[1] for child in ordered_children]


class Pool(Container):
    """Data Model for a Pool."""

    base_type: Literal[ContainerTypeEnum.pool] = Field(
        title="Container Base Type",
        description="The base type of the pool.",
        default=ContainerTypeEnum.pool,
        const=True,
    )
    children: Optional[dict[str, "ConsumableDataModels"]] = Field(
        title="Children",
        description="The children of the pool.",
        default_factory=dict,
    )
    capacity: Optional[float] = Field(
        title="Capacity",
        description="The capacity of the pool as a whole.",
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

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the pool as a flat dictionary."""
        return self.children

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the pool."""
        self.children = children


RESOURCE_TYPE_MAP = {
    ResourceTypeEnum.resource: {
        "definition": ResourceDefinition,
        "model": Resource,
    },
    ResourceTypeEnum.asset: {
        "definition": AssetResourceDefinition,
        "model": Asset,
    },
    ResourceTypeEnum.consumable: {
        "definition": ConsumableResourceDefinition,
        "model": Consumable,
    },
    ConsumableTypeEnum.discrete_consumable: {
        "definition": DiscreteConsumableResourceDefinition,
        "model": DiscreteConsumable,
    },
    ConsumableTypeEnum.continuous_consumable: {
        "definition": ContinuousConsumableResourceDefinition,
        "model": ContinuousConsumable,
    },
    AssetTypeEnum.container: {
        "definition": ContainerResourceDefinition,
        "model": Container,
    },
    ContainerTypeEnum.stack: {
        "definition": StackResourceDefinition,
        "model": Stack,
    },
    ContainerTypeEnum.queue: {
        "definition": QueueResourceDefinition,
        "model": Queue,
    },
    ContainerTypeEnum.collection: {
        "definition": CollectionResourceDefinition,
        "model": Collection,
    },
    ContainerTypeEnum.row: {
        "definition": RowResourceDefinition,
        "model": Row,
    },
    ContainerTypeEnum.grid: {
        "definition": GridResourceDefinition,
        "model": Grid,
    },
    ContainerTypeEnum.voxel_grid: {
        "definition": VoxelGridResourceDefinition,
        "model": VoxelGrid,
    },
    ContainerTypeEnum.pool: {
        "definition": PoolResourceDefinition,
        "model": Pool,
    },
}

ResourceDataModels = Annotated[
    Union[
        Annotated[Resource, Tag("resource")],
        Annotated[Asset, Tag("asset")],
        Annotated[Consumable, Tag("consumable")],
        Annotated[DiscreteConsumable, Tag("discrete_consumable")],
        Annotated[ContinuousConsumable, Tag("continuous_consumable")],
        Annotated[Container, Tag("container")],
        Annotated[Collection, Tag("collection")],
        Annotated[Row, Tag("row")],
        Annotated[Grid, Tag("grid")],
        Annotated[VoxelGrid, Tag("voxel_grid")],
        Annotated[Stack, Tag("stack")],
        Annotated[Queue, Tag("queue")],
        Annotated[Pool, Tag("pool")],
    ],
    Discriminator("base_type"),
]

ConsumableDataModels = Annotated[
    Union[
        Annotated[Consumable, Tag("consumable")],
        Annotated[DiscreteConsumable, Tag("discrete_consumable")],
        Annotated[ContinuousConsumable, Tag("continuous_consumable")],
    ],
    Discriminator("base_type"),
]

ContainerDataModels = Annotated[
    Union[
        Annotated[Container, Tag("container")],
        Annotated[Collection, Tag("collection")],
        Annotated[Row, Tag("row")],
        Annotated[Grid, Tag("grid")],
        Annotated[VoxelGrid, Tag("voxel_grid")],
        Annotated[Stack, Tag("stack")],
        Annotated[Queue, Tag("queue")],
        Annotated[Pool, Tag("pool")],
    ],
    Discriminator("base_type"),
]
