Module madsci.common.types.resource_types.definitions
=====================================================
Pydantic Models for Resource Definitions, used to define default resources for a node or workcell.

Functions
---------

`single_letter_or_digit_validator(value: str) ‑> str`
:   Validate that the value is a single letter or digit.

Classes
-------

`AssetResourceDefinition(**data: Any)`
:   Definition for an asset resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.asset: 'asset'>]`
    :

`CollectionResourceDefinition(**data: Any)`
:   Definition for a collection resource. Collections are used for resources that have a number of children, each with a unique key, which can be randomly accessed.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.collection: 'collection'>]`
    :

    `default_children: list[madsci.common.types.resource_types.definitions.ResourceDefinition] | dict[str, madsci.common.types.resource_types.definitions.ResourceDefinition] | None`
    :

    `keys: int | list[str] | None`
    :

    ### Static methods

    `validate_keys(v: int | list[str] | None) ‑> list[str] | None`
    :   Convert integer keys to 1-based range if needed.

`ConsumableResourceDefinition(**data: Any)`
:   Definition for a consumable resource.

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

    * madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition
    * madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.consumable: 'consumable'>]`
    :

    `capacity: float | int | None`
    :

    `quantity: float | int`
    :

    `unit: str | None`
    :

`ContainerResourceDefinition(**data: Any)`
:   Definition for a container resource.

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

    * madsci.common.types.resource_types.definitions.CollectionResourceDefinition
    * madsci.common.types.resource_types.definitions.PoolResourceDefinition
    * madsci.common.types.resource_types.definitions.QueueResourceDefinition
    * madsci.common.types.resource_types.definitions.RowResourceDefinition
    * madsci.common.types.resource_types.definitions.SlotResourceDefinition
    * madsci.common.types.resource_types.definitions.StackResourceDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.container: 'container'>]`
    :

    `capacity: float | int | None`
    :

    `default_child_template: madsci.common.types.resource_types.definitions.ResourceDefinition | madsci.common.types.resource_types.definitions.AssetResourceDefinition | madsci.common.types.resource_types.definitions.ContainerResourceDefinition | madsci.common.types.resource_types.definitions.CollectionResourceDefinition | madsci.common.types.resource_types.definitions.RowResourceDefinition | madsci.common.types.resource_types.definitions.GridResourceDefinition | madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition | madsci.common.types.resource_types.definitions.StackResourceDefinition | madsci.common.types.resource_types.definitions.QueueResourceDefinition | madsci.common.types.resource_types.definitions.PoolResourceDefinition | madsci.common.types.resource_types.definitions.SlotResourceDefinition | madsci.common.types.resource_types.definitions.ConsumableResourceDefinition | madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition | madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition | None`
    :

    `default_children: list[madsci.common.types.resource_types.definitions.ResourceDefinition] | dict[str, madsci.common.types.resource_types.definitions.ResourceDefinition] | None`
    :

`ContinuousConsumableResourceDefinition(**data: Any)`
:   Definition for a continuous consumable resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ConsumableResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.continuous_consumable: 'continuous_consumable'>]`
    :

`CustomResourceAttributeDefinition(**data: Any)`
:   Definition for a MADSci Custom Resource Attribute.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `attribute_description: str | None`
    :

    `attribute_name: str`
    :

    `default_value: Any`
    :

    `optional: bool`
    :

`DiscreteConsumableResourceDefinition(**data: Any)`
:   Definition for a discrete consumable resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ConsumableResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.discrete_consumable: 'discrete_consumable'>]`
    :

    `capacity: int | None`
    :

    `quantity: int`
    :

`GridResourceDefinition(**data: Any)`
:   Definition for a grid resource. Grids are 2D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Resource]]).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.RowResourceDefinition
    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.grid: 'grid'>]`
    :

    `default_children: dict[str, dict[str, madsci.common.types.resource_types.definitions.ResourceDefinition]] | None`
    :

    `rows: int`
    :

`PoolResourceDefinition(**data: Any)`
:   Definition for a pool resource. Pool resources are collections of consumables with no structure (used for wells, reservoirs, etc.).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.pool: 'pool'>]`
    :

    `capacity: float | int | None`
    :

    `unit: str | None`
    :

`QueueResourceDefinition(**data: Any)`
:   Definition for a queue resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.queue: 'queue'>]`
    :

    `default_child_quantity: int | None`
    :

`ResourceDefinition(**data: Any)`
:   Definition for a MADSci Resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.AssetResourceDefinition
    * madsci.common.types.resource_types.definitions.ConsumableResourceDefinition
    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.resource: 'resource'>]`
    :

    `custom_attributes: list[madsci.common.types.resource_types.definitions.CustomResourceAttributeDefinition] | None`
    :

    `owner: madsci.common.types.auth_types.OwnershipInfo`
    :

    `resource_class: str`
    :

    `resource_description: str | None`
    :

    `resource_name: str`
    :

    `resource_name_prefix: str | None`
    :

    ### Static methods

    `discriminate(resource: dict) ‑> madsci.common.types.resource_types.definitions.ResourceDefinition`
    :   Discriminate the resource definition based on its base type.

`ResourceManagerDefinition(**data: Any)`
:   Definition for a Resource Manager's Configuration

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `default_templates: list[madsci.common.types.resource_types.definitions.TemplateDefinition]`
    :

    `manager_type: Literal[<ManagerType.RESOURCE_MANAGER: 'resource_manager'>]`
    :

    `model_config`
    :

    `name: str`
    :

    `resource_manager_id: str`
    :

`ResourceManagerHealth(**data: Any)`
:   Health status for Resource Manager including database connectivity.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerHealth
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `db_connected: bool | None`
    :

    `model_config`
    :

    `total_resources: int | None`
    :

`ResourceManagerSettings(**values: Any)`
:   Settings for the MADSci Resource Manager.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `db_url: str`
    :

    `manager_definition: str | pathlib.Path`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

`RowResourceDefinition(**data: Any)`
:   Definition for a row resource. Rows are 1D collections of resources. They are treated as single collections (i.e. Collection[Resource]).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.definitions.GridResourceDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.row: 'row'>]`
    :

    `columns: int`
    :

    `default_children: dict[str, madsci.common.types.resource_types.definitions.ResourceDefinition] | None`
    :

    `fill: bool`
    :

    `is_one_indexed: bool`
    :

`SlotResourceDefinition(**data: Any)`
:   Definition for a slot resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.slot: 'slot'>]`
    :

    `capacity: Literal[1]`
    :

    `default_child_quantity: int | None`
    :

`StackResourceDefinition(**data: Any)`
:   Definition for a stack resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.stack: 'stack'>]`
    :

    `default_child_quantity: int | None`
    :

`TemplateDefinition(**data: Any)`
:   Definition for a Resource Template to be created on manager startup.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_resource: madsci.common.types.resource_types.definitions.ResourceDefinition | madsci.common.types.resource_types.definitions.AssetResourceDefinition | madsci.common.types.resource_types.definitions.ContainerResourceDefinition | madsci.common.types.resource_types.definitions.CollectionResourceDefinition | madsci.common.types.resource_types.definitions.RowResourceDefinition | madsci.common.types.resource_types.definitions.GridResourceDefinition | madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition | madsci.common.types.resource_types.definitions.StackResourceDefinition | madsci.common.types.resource_types.definitions.QueueResourceDefinition | madsci.common.types.resource_types.definitions.PoolResourceDefinition | madsci.common.types.resource_types.definitions.SlotResourceDefinition | madsci.common.types.resource_types.definitions.ConsumableResourceDefinition | madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition | madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition`
    :

    `description: str | None`
    :

    `model_config`
    :

    `required_overrides: list[str] | None`
    :

    `tags: list[str] | None`
    :

    `template_name: str`
    :

    `version: str`
    :

`VoxelGridResourceDefinition(**data: Any)`
:   Definition for a voxel grid resource. Voxel grids are 3D grids of resources. They are treated as nested collections (i.e. Collection[Collection[Collection[Resource]]]).

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.definitions.GridResourceDefinition
    * madsci.common.types.resource_types.definitions.RowResourceDefinition
    * madsci.common.types.resource_types.definitions.ContainerResourceDefinition
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.voxel_grid: 'voxel_grid'>]`
    :

    `default_children: dict[str, dict[str, dict[str, madsci.common.types.resource_types.definitions.ResourceDefinition]]] | None`
    :

    `layers: int`
    :

    ### Methods

    `get_all_keys(self) ‑> list`
    :   get all keys of this object
