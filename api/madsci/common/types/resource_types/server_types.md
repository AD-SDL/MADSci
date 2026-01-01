Module madsci.common.types.resource_types.server_types
======================================================
Types used by the Resource Manager's Server

Classes
-------

`CreateResourceFromTemplateBody(**data: Any)`
:   A request to create a resource from a template.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `add_to_database: bool | None`
    :   Whether to add the resource to the database.

    `model_config`
    :

    `overrides: dict[str, typing.Any] | None`
    :   Values to override template defaults.

    `resource_name: str`
    :   Name for the new resource.

`PushResourceBody(**data: Any)`
:   A request to push a resource to the database.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `child: madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   The child resource data.

    `child_id: str | None`
    :   The ID of the child resource.

    `model_config`
    :

    ### Static methods

    `validate_push_resource(values: dict) ‑> dict`
    :   Ensure that either a child ID or child resource data is provided.

`RemoveChildBody(**data: Any)`
:   A request to remove a child resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `key: str | tuple[int | str, int | str] | tuple[int | str, int | str, int | str]`
    :   The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index.

    `model_config`
    :

`ResourceGetQuery(**data: Any)`
:   A request to get a resource from the database.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: str | None`
    :   The base type of the resource

    `model_config`
    :

    `multiple: bool | None`
    :   Whether to return multiple resources or just the first.

    `owner: madsci.common.types.auth_types.OwnershipInfo | None`
    :   The owner(s) of the resource

    `parent_id: str | None`
    :   The ID of the parent resource

    `resource_class: str | None`
    :   The class of the resource.

    `resource_description: str | None`
    :   The description of the resource.

    `resource_id: str | None`
    :   The ID of the resource

    `resource_name: str | None`
    :   The name of the resource.

    `unique: bool | None`
    :   Whether to require a unique resource or not.

`ResourceHierarchy(**data: Any)`
:   Represents the hierarchical relationships of a resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `ancestor_ids: list[str]`
    :   List of all direct ancestors from closest to furthest (parent, grandparent, great-grandparent, etc.).

    `descendant_ids: dict[str, list[str]]`
    :   Dictionary mapping parent IDs to their direct child IDs, recursively including all descendant generations (children, grandchildren, great-grandchildren, etc.).

    `model_config`
    :

    `resource_id: str`
    :   The ID of the queried resource.

`ResourceHistoryGetQuery(**data: Any)`
:   A request to get the history of a resource from the database.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `change_type: str | None`
    :   The type of change to the resource.

    `end_date: datetime.datetime | None`
    :   The end of a range from which to get history. If not specified, all history after the start date is returned.

    `limit: int | None`
    :   The maximum number of entries to return.

    `model_config`
    :

    `removed: bool | None`
    :   Whether the resource was removed.

    `resource_id: str | None`
    :   The ID of the resource.

    `start_date: datetime.datetime | None`
    :   The start a range from which to get history. If not specified, all history before the end date is returned.

    `version: int | None`
    :   The version of the resource.

`ResourceRequestBase(**data: Any)`
:   Base class for all resource request models.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Descendants

    * madsci.common.types.resource_types.server_types.CreateResourceFromTemplateBody
    * madsci.common.types.resource_types.server_types.PushResourceBody
    * madsci.common.types.resource_types.server_types.RemoveChildBody
    * madsci.common.types.resource_types.server_types.ResourceGetQuery
    * madsci.common.types.resource_types.server_types.ResourceHistoryGetQuery
    * madsci.common.types.resource_types.server_types.SetChildBody
    * madsci.common.types.resource_types.server_types.TemplateCreateBody
    * madsci.common.types.resource_types.server_types.TemplateGetQuery
    * madsci.common.types.resource_types.server_types.TemplateUpdateBody

    ### Class variables

    `model_config`
    :

`SetChildBody(**data: Any)`
:   A request to set a child resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `child: str | madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   The ID of the child resource or the child resource data.

    `key: str | int | tuple[int | str, int | str] | tuple[int | str, int | str, int | str]`
    :   The key to identify the child resource's location in the parent container. If the parent is a grid/voxel grid, the key should be a 2D or 3D index.

    `model_config`
    :

`TemplateCreateBody(**data: Any)`
:   A request to create a template from a resource.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created_by: str | None`
    :   Creator identifier.

    `description: str | None`
    :   Description of what this template creates.

    `model_config`
    :

    `required_overrides: list[str] | None`
    :   Fields that must be provided when using template.

    `resource: madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   The resource to use as a template.

    `tags: list[str] | None`
    :   Tags for categorization.

    `template_name: str`
    :   Unique name for the template.

    `version: str | None`
    :   Template version.

`TemplateGetQuery(**data: Any)`
:   A request to list/filter templates.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `base_type: str | None`
    :   Filter by base resource type.

    `created_by: str | None`
    :   Filter by creator.

    `model_config`
    :

    `tags: list[str] | None`
    :   Filter by templates that have any of these tags.

`TemplateUpdateBody(**data: Any)`
:   A request to update a template.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.resource_types.server_types.ResourceRequestBase
    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `updates: dict[str, typing.Any]`
    :   Fields to update.
