Module madsci.common.types.resource_types
=========================================
Types related to MADSci Resources.

Sub-modules
-----------
* madsci.common.types.resource_types.custom_types
* madsci.common.types.resource_types.definitions
* madsci.common.types.resource_types.resource_enums
* madsci.common.types.resource_types.server_types

Classes
-------

`Asset(**data: Any)`
:   Base class for all MADSci Assets. These are tracked resources that aren't consumed (things like samples, labware, etc.).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.Container

    ### Class variables

    `base_type: Literal[<AssetTypeEnum.asset: 'asset'>]`
    :

`Collection(**data: Any)`
:   Data Model for a Collection. A collection is a container that can hold other resources, and which supports random access.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.collection: 'collection'>]`
    :

    `children: dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the collection as a flat dictionary.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the collection.

`Consumable(**data: Any)`
:   Base class for all MADSci Consumables. These are resources that are consumed (things like reagents, pipette tips, etc.).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.ContinuousConsumable
    * madsci.common.types.resource_types.DiscreteConsumable

    ### Class variables

    `base_type: Literal[<ConsumableTypeEnum.consumable: 'consumable'>]`
    :

    `capacity: float | int | None`
    :

    `quantity: float | int`
    :

    `unit: str | None`
    :

    ### Methods

    `validate_consumable_quantity(self) ‑> Self`
    :   Validate that the quantity is less than or equal to the capacity.

`Container(**data: Any)`
:   Data Model for a Container. A container is a resource that can hold other resources.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.Collection
    * madsci.common.types.resource_types.Pool
    * madsci.common.types.resource_types.Queue
    * madsci.common.types.resource_types.Row
    * madsci.common.types.resource_types.Slot
    * madsci.common.types.resource_types.Stack

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.container: 'container'>]`
    :

    `capacity: int | None`
    :

    `children: dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    ### Instance variables

    `quantity: int`
    :   Calculate the quantity of assets in the container.

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the container as a flat dictionary.

    `get_child(self, key: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a child from the container.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the container.

    `validate_container_quantity(self) ‑> Self`
    :   Validate that the quantity is less than or equal to the capacity.

`ContinuousConsumable(**data: Any)`
:   Base class for all MADSci Continuous Consumables. These are consumables that are measured in continuous quantities (things like liquids, powders, etc.).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Consumable
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ConsumableTypeEnum.continuous_consumable: 'continuous_consumable'>]`
    :

    `capacity: float | int | None`
    :

    `quantity: float | int`
    :

`DiscreteConsumable(**data: Any)`
:   Base class for all MADSci Discrete Consumables. These are consumables that are counted in whole numbers (things like pipette tips, tubes, etc.).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Consumable
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ConsumableTypeEnum.discrete_consumable: 'discrete_consumable'>]`
    :

    `capacity: int | None`
    :

    `quantity: int`
    :

`Grid(**data: Any)`
:   Data Model for a Grid. A grid is a container that can hold other resources in two dimensions and supports random access. For example, a 96-well microplate. Grids are indexed by integers or letters.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Row
    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.VoxelGrid

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.grid: 'grid'>]`
    :

    `children: list[madsci.common.types.resource_types.Row | None]`
    :

    `rows: int`
    :

    ### Methods

    `get_child(self, key: str | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]] | int) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a child from the Grid.

    `initialize_grid(self) ‑> None`
    :   Creates a grid of the correct dimensions

    `set_child(self, key: str | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]] | int, child: ResourceDataModels) ‑> None`
    :   Get a child from the Grid.

    `split_index(self, key: str) ‑> tuple[int | str, int | str]`
    :   split an alphanumeric index string into a grid index tuple, uses is_one_indexed for the numerical index

`Pool(**data: Any)`
:   Data Model for a Pool. A pool is a container for holding consumables that can be mixed or collocated. For example, a single well in a microplate, or a reservoir. Pools are indexed by string key.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.pool: 'pool'>]`
    :

    `capacity: float | None`
    :

    `children: dict[str, madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable]`
    :

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the pool as a flat dictionary.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the pool.

`Queue(**data: Any)`
:   Data Model for a Queue. A queue is a container that can hold other resources in a single dimension and supports first-in, first-out (FIFO) access. For example, a conveyer belt. Queues are indexed by integers, with 0 being the front.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.queue: 'queue'>]`
    :

    `children: list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the stack as a flat dict.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the queue.

`Resource(**data: Any)`
:   Base class for all MADSci Resources. Used to track any resource that isn't well-modeled by a more specific type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Consumable
    * madsci.resource_manager.resource_tables.ResourceTableBase

    ### Class variables

    `attributes: dict`
    :

    `base_type: Literal[<ResourceTypeEnum.resource: 'resource'>]`
    :

    `created_at: datetime.datetime | None`
    :

    `key: str | None`
    :

    `parent_id: str | None`
    :

    `removed: bool`
    :

    `resource_id: str`
    :

    `resource_url: str | None`
    :

    `updated_at: datetime.datetime | None`
    :

    ### Static methods

    `discriminate(resource: dict | ForwardRef('Resource') | madsci.common.types.resource_types.definitions.ResourceDefinition) ‑> madsci.common.types.resource_types.Resource`
    :   Discriminate the resource based on its base type.

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`Row(**data: Any)`
:   Data Model for a Row. A row is a container that can hold other resources in a single dimension and supports random access. For example, a row of tubes in a rack or a single-row microplate. Rows are indexed by integers or letters.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.Grid

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.row: 'row'>]`
    :

    `children: list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None]`
    :

    `columns: int`
    :

    `is_one_indexed: bool`
    :

    ### Methods

    `check_key_bounds(self, key: str | int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]) ‑> bool`
    :   Check if the key is within the bounds of the grid.

    `extract_children(self) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   return all children

    `get_all_keys(self) ‑> list`
    :   get all keys of this object

    `get_child(self, key: int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a child from the Row.

    `numericize_index(self, key: str | int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]) ‑> int | str`
    :   Convert a key to a numeric value.

    `populate_children(self, children: dict[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], 'ResourceDataModels']) ‑> None`
    :   Populate the children of the grid.

    `set_child(self, key: int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], value: ResourceDataModels) ‑> None`
    :   set a child using a string or int

    `set_list(self) ‑> madsci.common.types.resource_types.Row`
    :   populates the children list with none values

`Slot(**data: Any)`
:   Data Model for a Slot. A slot is a container that can hold a single resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.slot: 'slot'>]`
    :

    `capacity: Literal[1]`
    :

    `children: list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    ### Instance variables

    `child: ResourceDataModels | None`
    :   Get the child from the slot.

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the stack as a flat dict.

    `get_child(self, key: int | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get the child from the slot.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the stack.

`Stack(**data: Any)`
:   Data Model for a Stack. A stack is a container that can hold other resources in a single dimension and supports last-in, first-out (LIFO) access. For example, a stack of plates in a vertical magazine. Stacks are indexed by integers, with 0 being the bottom.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.stack: 'stack'>]`
    :

    `children: list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    ### Methods

    `extract_children(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Extract the children from the stack as a flat dict.

    `populate_children(self, children: dict[str, 'ResourceDataModels']) ‑> None`
    :   Populate the children of the stack.

`VoxelGrid(**data: Any)`
:   Data Model for a Voxel Grid. A voxel grid is a container that can hold other resources in three dimensions and supports random access. Voxel grids are indexed by integers or letters.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.Grid
    * madsci.common.types.resource_types.Row
    * madsci.common.types.resource_types.Container
    * madsci.common.types.resource_types.Asset
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ContainerTypeEnum.voxel_grid: 'voxel_grid'>]`
    :

    `children: list[madsci.common.types.resource_types.Grid | None]`
    :

    `layers: int`
    :

    ### Methods

    `get_child(self, key: tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]]) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a child from the Voxel Grid.

    `initialize_grid(self) ‑> None`
    :   Creates a voxel grid of the correct dimension
