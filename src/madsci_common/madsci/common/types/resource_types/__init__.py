"""Types related to MADSci Resources."""

import re
import string
from typing import Annotated, Any, Literal, Optional, Union

from madsci.common.types.base_types import PositiveInt, PositiveNumber
from madsci.common.types.resource_types.definitions import (
    AssetResourceDefinition,
    CollectionResourceDefinition,
    ConsumableResourceDefinition,
    ContainerResourceDefinition,
    ContinuousConsumableResourceDefinition,
    CustomResourceAttributeDefinition,  # noqa: F401
    DiscreteConsumableResourceDefinition,
    GridIndex,
    GridIndex2D,
    GridIndex3D,
    GridResourceDefinition,
    PoolResourceDefinition,
    QueueResourceDefinition,
    ResourceDefinition,
    RowResourceDefinition,
    SlotResourceDefinition,
    StackResourceDefinition,
    VoxelGridResourceDefinition,
)
from madsci.common.types.resource_types.resource_enums import (
    AssetTypeEnum,
    ConsumableTypeEnum,
    ContainerTypeEnum,
    ResourceTypeEnum,
)
from madsci.common.utils import new_ulid_str
from madsci.common.validators import ulid_validator
from pydantic import (
    AnyUrl,  # noqa: F401
    computed_field,
    model_validator,
)
from pydantic.functional_validators import field_validator
from pydantic.types import Discriminator, Tag, datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql.sqltypes import String
from sqlmodel import Field
from typing_extensions import Self  # type: ignore


class Resource(ResourceDefinition, extra="allow", table=False):
    """Base class for all MADSci Resources. Used to track any resource that isn't well-modeled by a more specific type."""

    resource_id: str = Field(
        title="Resource ID",
        description="The ID of the resource.",
        nullable=False,
        default_factory=new_ulid_str,
        primary_key=True,
        sa_type=String,
    )
    resource_url: Optional[str] = (
        Field(  # Change from AnyUrl to str to fix serialization issues with new Client Context Manager
            title="Resource URL",
            description="The URL of the resource.",
            nullable=True,
            default=None,
        )
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
    is_ulid = field_validator("resource_id")(ulid_validator)

    @classmethod
    def discriminate(
        cls, resource: Union[dict, "Resource", ResourceDefinition]
    ) -> "Resource":
        """Discriminate the resource based on its base type."""
        if isinstance(resource, dict):
            resource_type = resource.get("base_type")
        elif isinstance(resource, (Resource, ResourceDefinition)):
            resource_type = resource.base_type
        else:
            raise ValueError(f"Resource cannot be {type(resource)}.")
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
        default=0,
    )
    capacity: Optional[PositiveNumber] = Field(
        title="Capacity",
        description="The maximum capacity of the consumable.",
        default=None,
    )
    unit: Optional[str] = Field(
        default=None,
        title="Resource Unit",
        description="The unit used to measure the quantity of the consumable.",
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
        default=0,
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
        default=0.0,
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
    children: dict[str, "ResourceDataModels"] = Field(
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
    children: dict[str, "ResourceDataModels"] = Field(
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


class Row(Container):
    """Data Model for a Row. A row is a container that can hold other resources in a single dimension and supports random access. For example, a row of tubes in a rack or a single-row microplate. Rows are indexed by integers or letters."""

    base_type: Literal[ContainerTypeEnum.row] = Field(
        title="Container Base Type",
        description="The base type of the row.",
        default=ContainerTypeEnum.row,
        const=True,
    )
    columns: int = Field(
        title="Number of Columns",
        description="The number of columns in the row.",
        ge=0,
    )

    children: list[Union["ResourceDataModels", None]] = Field(
        title="Children", description="The children of the row container.", default=[]
    )

    is_one_indexed: bool = Field(
        title="One Indexed",
        description="Whether the numeric index of the object start at 0 or 1, only used with string keys",
        default=True,
    )

    @model_validator(mode="after")
    def set_list(self) -> "Row":
        """populates the children list with none values"""
        if self.children == []:
            self.children = [None] * self.columns
        return self

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for child in self.children:
            if getattr(child, "quantity", None) is not None:
                quantity += child.quantity
        return quantity

    def extract_children(self) -> list["ResourceDataModels"]:
        """return all children"""
        return_dict = {}
        for index, item in enumerate(self.children):
            return_dict[str(index)] = item
        return return_dict

    def get_child(self, key: GridIndex) -> Optional["ResourceDataModels"]:
        """Get a child from the Row."""
        if isinstance(key, str):
            return self.children[int(key) - self.is_one_indexed]
        return self.children[key]

    def numericize_index(self, key: Union[str, GridIndex]) -> GridIndex:
        """Convert a key to a numeric value."""
        if isinstance(key, int):
            return int(key)
        if key.isdigit():
            return int(key) - self.is_one_indexed
        return string.ascii_lowercase.index(key.lower())

    def set_child(self, key: GridIndex, value: "ResourceDataModels") -> None:
        """set a child using a string or int"""
        if isinstance(key, str):
            key = self.numericize_index(key)
        self.children[key] = value
        value.key = str(key)

    def __getitem__(self, index: GridIndex) -> Resource:
        """retrieve a child using an alphanumeric key, if index is a string, uses self.is_one_indexed, otherwise uses normal array rules"""
        return self.get_child(index)

    def __setitem__(self, key: GridIndex, value: Any) -> None:
        """set an item using an alphanumeric key"""
        self.set_child(key, value)

    def check_key_bounds(self, key: Union[str, GridIndex]) -> bool:
        """Check if the key is within the bounds of the grid."""
        return not (int(key) < 0 or int(key) >= self.columns)

    def get_all_keys(self) -> list:
        """get all keys of this object"""
        return list(range(self.columns))

    def populate_children(
        self, children: dict[GridIndex, "ResourceDataModels"]
    ) -> None:
        """Populate the children of the grid."""
        for key, value in children.items():
            self[int(key)] = value


class Grid(Row):
    """Data Model for a Grid. A grid is a container that can hold other resources in two dimensions and supports random access. For example, a 96-well microplate. Grids are indexed by integers or letters."""

    base_type: Literal[ContainerTypeEnum.grid] = Field(
        title="Container Base Type",
        description="The base type of the grid.",
        default=ContainerTypeEnum.grid,
        const=True,
    )
    rows: int = Field(
        title="Number of Rows",
        description="The number of rows in the grid.",
        ge=0,
    )

    children: list[Optional[Row]] = Field(
        title="Children", description="The children of the grid container.", default=[]
    )

    @model_validator(mode="after")
    def initialize_grid(self) -> None:
        """Creates a grid of the correct dimensions"""
        for i in range(self.rows):
            if i >= len(self.children):
                self.children.append(
                    Row(
                        columns=self.columns,
                        resource_name=self.resource_name + "_row_" + str(i),
                    )
                )
            if self.children[i] is None:
                self.children[i] = Row(
                    columns=self.columns,
                    resource_name=self.resource_name + "_row_" + str(i),
                )
        return self

    def split_index(self, key: str) -> GridIndex2D:
        """split an alphanumeric index string into a grid index tuple, uses is_one_indexed for the numerical index"""
        match = re.search(r"(\d)", key)
        if match:
            index = match.start()
            return (
                self.numericize_index(key[:index]),
                self.numericize_index(key[index:]),
            )
        raise (ValueError("Key is in the wrong format!"))

    def get_all_keys(self) -> list:
        """get all keys of this object"""
        return [
            GridIndex2D(i, j) for i in range(self.columns) for j in range(self.rows)
        ]

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for row in self.children:
            if getattr(row, "quantity", None) is not None:
                quantity += row.quantity
        return quantity

    def get_child(
        self, key: Union[str, GridIndex2D, int]
    ) -> Optional["ResourceDataModels"]:
        """Get a child from the Grid."""
        if isinstance(key, str):
            key = self.split_index(key)
        if isinstance(key, int):
            return self.children[key]
        row = self.children[key[0]]
        return row[key[1]]

    def set_child(
        self, key: Union[str, GridIndex2D, int], child: "ResourceDataModels"
    ) -> None:
        """Get a child from the Grid."""
        if isinstance(key, int):
            self.children[key] = child
        else:
            if isinstance(key, str):
                key = self.split_index(key)
            row = self.children[key[0]]
            row[key[1]] = child
            child.key = str(key[1])

    def __getitem__(self, key: Union[str, GridIndex2D, int]) -> Resource:
        """get an item using alphanumeric keys"""

        return self.get_child(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """set an item using alphanumeric keys"""
        self.set_child(key, value)

    def check_key_bounds(self, key: Union[str, GridIndex2D]) -> bool:
        """Check if the key is within the bounds of the grid."""
        if isinstance(key, str):
            key = self.split_index(key)
        elif not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("Key must be a string or a 2-tuple.")
        return not (key[0] < 0 or key[0] >= self.rows) and not (
            key[1] < 0 or key[1] >= self.columns
        )


class VoxelGrid(Grid):
    """Data Model for a Voxel Grid. A voxel grid is a container that can hold other resources in three dimensions and supports random access. Voxel grids are indexed by integers or letters."""

    base_type: Literal[ContainerTypeEnum.voxel_grid] = Field(
        title="Container Base Type",
        description="The base type of the voxel grid.",
        default=ContainerTypeEnum.voxel_grid,
        const=True,
    )
    layers: int = Field(
        title="Number of Layers",
        description="The number of layers in the voxel grid.",
        ge=0,
    )
    children: list[Optional[Grid]] = Field(
        title="Children",
        description="The children of the voxel grid container.",
        default=[],
    )

    @model_validator(mode="after")
    def initialize_grid(self) -> None:
        """Creates a voxel grid of the correct dimension"""
        for i in range(self.layers):
            if i >= len(self.children):
                self.children.append(
                    Grid(
                        resource_name=self.resource_name + "_layer_" + str(i),
                        rows=self.rows,
                        columns=self.columns,
                        children=[
                            Row(
                                columns=self.columns,
                                resource_name=self.resource_name
                                + "_layer_"
                                + str(i)
                                + "_row_"
                                + str(j),
                            )
                            for j in range(self.rows)
                        ],
                    )
                )
            if self.children[i] is None:
                self.children[i] = Grid(
                    resource_name=self.resource_name + "_layer_" + str(i),
                    rows=self.rows,
                    columns=self.columns,
                    children=[
                        Row(
                            columns=self.columns,
                            resource_name=self.resource_name
                            + "_layer_"
                            + str(i)
                            + "_row_"
                            + str(j),
                        )
                        for j in range(self.rows)
                    ],
                )
        return self

    @computed_field
    def quantity(self) -> int:
        """Calculate the quantity of assets in the container."""
        quantity = 0
        for grid_value in self:
            if getattr(grid_value, "quantity", None) is not None:
                quantity += grid_value.quantity
        return quantity

    def get_child(self, key: GridIndex3D) -> Optional["ResourceDataModels"]:
        """Get a child from the Voxel Grid."""
        grid = self.children[key[2]]
        return grid[(key[0], key[1])]

    def set_child(
        self, key: Union[GridIndex3D, int], child: "ResourceDataModels"
    ) -> None:
        """Get a child from the Grid."""
        if isinstance(key, int):
            self.children[key] = child
        else:
            grid = self.children[key[2]]
            if not isinstance(grid, Grid):
                grid = Grid(
                    resource_name=self.resource_name + "_layer_" + str(key[2]),
                    rows=self.rows,
                    columns=self.columns,
                    children=[
                        Row(
                            columns=self.columns,
                            resource_name=self.resource_name
                            + "_layer_"
                            + str(key[2])
                            + "_row_"
                            + str(j),
                        )
                        for j in range(self.rows)
                    ],
                )
                self.children[key[2]] = grid
            row = grid[key[0]]
            if not isinstance(row, Row):
                row = Row(
                    resource_name=self.resource_name
                    + "_layer_"
                    + str(key[2])
                    + "_row_"
                    + str(key[0]),
                    columns=self.columns,
                    children=list([None] * self.columns),
                )
                grid.children[key[0]] = row
            row[key[1]] = child
            child.key = str(key[2])

    def check_key_bounds(self, key: GridIndex3D) -> bool:
        """Check if the key is within the bounds of the grid."""

        if not isinstance(key, tuple) or len(key) != 3:
            raise ValueError("Key must be a 3-tuple.")
        return (
            not (key[2] < 0 or key[2] >= self.layers)
            and not (key[1] < 0 or key[1] >= self.rows)
            and not (key[0] < 0 or key[0] >= self.columns)
        )


class Slot(Container):
    """Data Model for a Slot. A slot is a container that can hold a single resource."""

    base_type: Literal[ContainerTypeEnum.slot] = Field(
        title="Container Base Type",
        description="The base type of the slot.",
        default=ContainerTypeEnum.slot,
        const=True,
    )
    children: list["ResourceDataModels"] = Field(
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
    children: list["ResourceDataModels"] = Field(
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
    children: list["ResourceDataModels"] = Field(
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
    children: dict[str, "ConsumableDataModels"] = Field(
        title="Children",
        description="The children of the pool.",
        default_factory=dict,
    )
    capacity: Optional[float] = Field(
        title="Capacity",
        description="The capacity of the pool as a whole.",
        default=None,
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
