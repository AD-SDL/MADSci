"""Types related to MADSci Resources."""

import string
from typing import Annotated, Literal, Optional, Union

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
    SlotResourceDefinition,
    StackResourceDefinition,
    VoxelGridResourceDefinition,
)
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

PositiveInt = Annotated[int, Field(ge=0)]
PositiveNumber = Annotated[Union[float, int], Field(ge=0)]


class Resource(ResourceDefinition, extra="allow", table=False):
    """Base class for all MADSci Resources. Used to track any resource that isn't well-modeled by a more specific type."""

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
    """Base class for all MADSci Assets. These are tracked resources that aren't consumed (things like samples, labware, etc.)."""

    base_type: Literal[AssetTypeEnum.asset] = Field(
        title="Asset Base Type",
        description="The base type of the asset.",
        nullable=False,
        default=AssetTypeEnum.asset,
    )


class Consumable(Resource):
    """Base class for all MADSci Consumables. These are resources that are consumed (things like reagents, pipette tips, etc.)."""

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
    """Base class for all MADSci Discrete Consumables. These are consumables that are counted in whole numbers (things like pipette tips, tubes, etc.)."""

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
    """Base class for all MADSci Continuous Consumables. These are consumables that are measured in continuous quantities (things like liquids, powders, etc.)."""

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
    """Data Model for a Container. A container is a resource that can hold other resources."""

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

    def get_child(self, key: str) -> Optional["ResourceDataModels"]:
        """Get a child from the container."""
        return self.children.get(key, None)

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
    """Data Model for a Collection. A collection is a container that can hold other resources, and which supports random access."""

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

    def get_child(self, key: str) -> Optional["ResourceDataModels"]:
        """Get a child from the container."""
        return self.children.get(key, None)

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


def numericize_index(key: Union[str, GridIndex]) -> GridIndex:
    """Convert a key to a numeric value."""
    if isinstance(key, int) or str(key).isdigit():
        return int(key)
    return string.ascii_lowercase.index(key.lower())


class Row(Container):
    """Data Model for a Row. A row is a container that can hold other resources in a single dimension and supports random access. For example, a row of tubes in a rack or a single-row microplate. Rows are indexed by integers or letters."""

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

    def get_child(self, key: GridIndex) -> Optional["ResourceDataModels"]:
        """Get a child from the Row."""
        return self.children.get(numericize_index(key), None)

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
        key = numericize_index(key)
        return not (key < 0 or key >= self.row_dimension)


class Grid(Row):
    """Data Model for a Grid. A grid is a container that can hold other resources in two dimensions and supports random access. For example, a 96-well microplate. Grids are indexed by integers or letters."""

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

    def get_child(self, key: GridIndex2D) -> Optional["ResourceDataModels"]:
        """Get a child from the Grid."""
        row = self.children.get(numericize_index(key[0]), None)
        if row is None:
            return None
        return row.get(numericize_index(key[1]), None)

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
            numeric_key.append(numericize_index(index))
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
    """Data Model for a Voxel Grid. A voxel grid is a container that can hold other resources in three dimensions and supports random access. Voxel grids are indexed by integers or letters."""

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

    def get_child(self, key: GridIndex3D) -> Optional["ResourceDataModels"]:
        """Get a child from the Voxel Grid."""
        row = self.children.get(numericize_index(key[0]), None)
        if row is None:
            return None
        col = row.get(numericize_index(key[1]), None)
        if col is None:
            return None
        return col.get(numericize_index(key[2]), None)

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
            numeric_key.append(numericize_index(index))
        key = numeric_key
        return (
            not (key[0] < 0 or key[0] >= self.row_dimension)
            and not (key[1] < 0 or key[1] >= self.column_dimension)
            and not (key[2] < 0 or key[2] >= self.layer_dimension)
        )


class Slot(Container):
    """Data Model for a Slot. A slot is a container that can hold a single resource."""

    base_type: Literal[ContainerTypeEnum.slot] = Field(
        title="Container Base Type",
        description="The base type of the slot.",
        default=ContainerTypeEnum.slot,
        const=True,
    )
    children: Optional[list["ResourceDataModels"]] = Field(
        title="Children",
        description="The children of the slot.",
        default_factory=list,
    )
    capacity: Literal[1] = Field(
        title="Capacity",
        description="The capacity of the slot.",
        default=1,
        const=1,
    )

    def get_child(self, key: Optional[int] = None) -> Optional["ResourceDataModels"]:
        """Get the child from the slot."""
        if key is not None and key != 0:
            return None
        return self.child

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        return len(self.children)

    @property
    def child(self) -> Optional["ResourceDataModels"]:
        """Get the child from the slot."""
        return self.children[0] if self.children else None

    def extract_children(self) -> dict[str, "ResourceDataModels"]:
        """Extract the children from the stack as a flat dict."""
        return {"0": self.child} if self.child else {}

    def populate_children(self, children: dict[str, "ResourceDataModels"]) -> None:
        """Populate the children of the stack."""
        self.children = [children["0"]] if "0" in children else []


class Stack(Container):
    """Data Model for a Stack. A stack is a container that can hold other resources in a single dimension and supports last-in, first-out (LIFO) access. For example, a stack of plates in a vertical magazine. Stacks are indexed by integers, with 0 being the bottom."""

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

    def get_child(self, key: int) -> Optional["ResourceDataModels"]:
        """Get a child from the container."""
        key = int(key)
        if key < 0 or key >= len(self.children):
            return None
        return self.children[key]

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
    """Data Model for a Queue. A queue is a container that can hold other resources in a single dimension and supports first-in, first-out (FIFO) access. For example, a conveyer belt. Queues are indexed by integers, with 0 being the front."""

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

    def get_child(self, key: int) -> Optional["ResourceDataModels"]:
        """Get a child from the container."""
        key = int(key)
        if key < 0 or key >= len(self.children):
            return None
        return self.children[key]

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
    """Data Model for a Pool. A pool is a container for holding consumables that can be mixed or collocated. For example, a single well in a microplate, or a reservoir. Pools are indexed by string key."""

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

    def get_child(self, key: str) -> Optional["ResourceDataModels"]:
        """Get a child from the container."""
        return self.children.get(key, None)

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
    ContainerTypeEnum.slot: {
        "definition": SlotResourceDefinition,
        "model": Slot,
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
        Annotated[Slot, Tag("slot")],
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
        Annotated[Slot, Tag("slot")],
    ],
    Discriminator("base_type"),
]
