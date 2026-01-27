Module madsci.common.types.resource_types.custom_types
======================================================
Data Models for validating Custom Resource Type Definitions

Classes
-------

`AssetResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Asset Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.asset: 'asset'>]`
    :

    `model_config`
    :

`AssetTypeEnum(*args, **kwds)`
:   Type for a MADSci Asset.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `asset`
    :

    `container`
    :

`CollectionResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Collection Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.collection: 'collection'>]`
    :

    `default_children: list['ResourceDefinition'] | dict[str, 'ResourceDefinition'] | None`
    :

    `keys: list[str] | None`
    :

    `model_config`
    :

    ### Static methods

    `validate_keys(v: int | list[str]) ‑> list[str]`
    :   Convert integer keys count to 1-indexed range.

`ConsumableResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Consumable Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.custom_types.ContinuousConsumableResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.DiscreteConsumableResourceTypeDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.consumable: 'consumable'>]`
    :

    `model_config`
    :

`ConsumableTypeEnum(*args, **kwds)`
:   Type for a MADSci Consumable.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `consumable`
    :

    `continuous_consumable`
    :

    `discrete_consumable`
    :

`ContainerResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Container Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.custom_types.CollectionResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.GridResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.PoolResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.QueueResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.RowResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.SlotTypeDefinition
    * madsci.common.types.resource_types.custom_types.StackResourceTypeDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.container: 'container'>]`
    :

    `default_capacity: float | int | None`
    :

    `default_child_template: list['ResourceDefinition'] | None`
    :

    `default_children: list['ResourceDefinition'] | dict[str, 'ResourceDefinition'] | None`
    :

    `model_config`
    :

    `resizeable: bool`
    :

    `supported_child_types: list[str]`
    :

`ContainerTypeEnum(*args, **kwds)`
:   Type for a MADSci Container.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `collection`
    :

    `container`
    :

    `grid`
    :

    `pool`
    :

    `queue`
    :

    `row`
    :

    `slot`
    :

    `stack`
    :

    `voxel_grid`
    :

`ContinuousConsumableResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Continuous Consumable Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ConsumableResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.continuous_consumable: 'continuous_consumable'>]`
    :

    `model_config`
    :

`CustomResourceAttributeDefinition(**data: Any)`
:   Definition for a MADSci Custom Resource Attribute.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `attribute_description: str | None`
    :

    `attribute_name: str`
    :

    `default_value: Any`
    :

    `model_config`
    :

    `optional: bool`
    :

`DiscreteConsumableResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Discrete Consumable Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ConsumableResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.discrete_consumable: 'discrete_consumable'>]`
    :

    `model_config`
    :

`GridResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Grid Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.custom_types.VoxelGridResourceTypeDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.grid: 'grid'>]`
    :

    `columns: list[str]`
    :

    `model_config`
    :

    `rows: list[str]`
    :

    ### Static methods

    `validate_keys(v: int | list[str]) ‑> list[str]`
    :   Convert integer keys count to 1-indexed range.

`PoolResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Pool Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.pool: 'pool'>]`
    :

    `model_config`
    :

`QueueResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Queue Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.queue: 'queue'>]`
    :

    `default_child_quantity: int | None`
    :

    `model_config`
    :

`ResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.custom_types.AssetResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ConsumableResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.resource: 'resource'>]`
    :

    `custom_attributes: list[madsci.common.types.resource_types.custom_types.CustomResourceAttributeDefinition] | None`
    :

    `model_config`
    :

    `parent_types: list[str]`
    :

    `type_description: str`
    :

    `type_name: str`
    :

    ### Static methods

    `validate_parent_types(v: list[str] | str) ‑> list[str]`
    :   Validate parent types.

`ResourceTypeEnum(*args, **kwds)`
:   Enum for all resource base types.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `asset`
    :

    `collection`
    :

    `consumable`
    :

    `container`
    :   Consumable Resource Base Types

    `continuous_consumable`
    :   Container Resource Base Types

    `discrete_consumable`
    :

    `grid`
    :

    `pool`
    :

    `queue`
    :

    `resource`
    :   Asset Resource Base Types

    `row`
    :

    `slot`
    :

    `stack`
    :

    `voxel_grid`
    :

`RowResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Row Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.row: 'row'>]`
    :

    `model_config`
    :

`SlotTypeDefinition(**data: Any)`
:   Definition for a MADSci Slot Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.slot: 'slot'>]`
    :

    `model_config`
    :

`StackResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Stack Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.stack: 'stack'>]`
    :

    `default_child_quantity: int | None`
    :

    `model_config`
    :

`VoxelGridResourceTypeDefinition(**data: Any)`
:   Definition for a MADSci Voxel Grid Resource Type.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.custom_types.GridResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ContainerResourceTypeDefinition
    * madsci.common.types.resource_types.custom_types.ResourceTypeDefinition
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: Literal[<ResourceTypeEnum.voxel_grid: 'voxel_grid'>]`
    :

    `capacity: int | None`
    :

    `model_config`
    :

    `planes: list[str]`
    :
