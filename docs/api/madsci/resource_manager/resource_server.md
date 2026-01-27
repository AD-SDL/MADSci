Module madsci.resource_manager.resource_server
==============================================
Resource Manager server implementation, extending th AbstractBaseManager class.

Classes
-------

`ResourceManager(settings: madsci.common.types.resource_types.definitions.ResourceManagerSettings | None = None, definition: madsci.common.types.resource_types.definitions.ResourceManagerDefinition | None = None, resource_interface: madsci.resource_manager.resource_interface.ResourceInterface | None = None, **kwargs: Any)`
:   Resource Manager REST Server.

    Initialize the Resource Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for a Resource Manager's Configuration

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the MADSci Resource Manager.

    ### Methods

    `acquire_resource_lock(self, resource_id: str, lock_duration: float = 300.0, client_id: str | None = None) ‑> dict[str, typing.Any]`
    :   Acquire a lock on a resource.

        Args:
            resource_id (str): The ID of the resource to lock.
            lock_duration (float): Lock duration in seconds.
            client_id (Optional[str]): Client identifier.

        Returns:
            dict: Lock acquisition result.

    `add_or_update_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] = Body(PydanticUndefined)) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Add a new resource to the Resource Manager.

    `add_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] = Body(PydanticUndefined)) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Add a new resource to the Resource Manager.

    `change_quantity_by(self, resource_id: str, amount: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to change the quantity by.

        Returns:
            ResourceDataModels: The updated resource.

    `check_resource_lock(self, resource_id: str) ‑> dict[str, typing.Any]`
    :   Check if a resource is currently locked.

        Args:
            resource_id (str): The ID of the resource to check.

        Returns:
            dict: Lock status information.

    `create_resource_from_template(self, template_name: str, body: madsci.common.types.resource_types.server_types.CreateResourceFromTemplateBody) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a resource from a template.

        If a matching resource already exists (based on name, class, type, owner, and any overrides),
        it will be returned instead of creating a duplicate.

    `create_server(self) ‑> fastapi.applications.FastAPI`
    :   Create and configure the FastAPI server with middleware.

    `create_template(self, body: madsci.common.types.resource_types.server_types.TemplateCreateBody) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a new resource template from a resource.

    `decrease_quantity(self, resource_id: str, amount: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Decrease the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to decrease the quantity by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.

    `delete_template(self, template_name: str) ‑> dict[str, str]`
    :   Delete a template from the database.

    `empty_resource(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Empty the contents of a container or consumable resource.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.

    `fill_resource(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Fill a consumable resource to capacity.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.

    `get_health(self) ‑> madsci.common.types.resource_types.definitions.ResourceManagerHealth`
    :   Get the health status of the Resource Manager.

    `get_resource(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Retrieve a resource from the database by ID.

    `get_template(self, template_name: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Get a template by name.

    `get_template_info(self, template_name: str) ‑> dict[str, typing.Any]`
    :   Get detailed template metadata.

    `get_templates_by_category(self) ‑> dict[str, list[str]]`
    :   Get templates organized by base_type category.

    `increase_quantity(self, resource_id: str, amount: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Increase the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to increase the quantity by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.

    `init_resource(self, resource_definition: Annotated[Annotated[madsci.common.types.resource_types.definitions.ResourceDefinition, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.definitions.AssetResourceDefinition, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.definitions.ContainerResourceDefinition, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.definitions.CollectionResourceDefinition, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.definitions.RowResourceDefinition, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.definitions.GridResourceDefinition, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.definitions.StackResourceDefinition, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.definitions.QueueResourceDefinition, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.definitions.PoolResourceDefinition, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.definitions.SlotResourceDefinition, Tag(tag='slot')] | Annotated[madsci.common.types.resource_types.definitions.ConsumableResourceDefinition, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition, Tag(tag='continuous_consumable')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] = Body(PydanticUndefined)) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Initialize a resource in the database based on a definition. If a matching resource already exists, it will be returned.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

    `pop(self, resource_id: str) ‑> tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Slot]`
    :   Pop an asset from a stack or queue.

        Args:
            resource_id (str): The ID of the stack or queue to pop the asset from.

        Returns:
            tuple[ResourceDataModels, Union[Stack, Queue, Slot]]: The popped asset and the updated stack or queue.

    `push(self, resource_id: str, body: madsci.common.types.resource_types.server_types.PushResourceBody) ‑> madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Slot`
    :   Push a resource onto a stack or queue.

        Args:
            resource_id (str): The ID of the stack or queue to push the resource onto.
            body (PushResourceBody): The resource to push onto the stack or queue, or the ID of an existing resource.

        Returns:
            Union[Stack, Queue, Slot]: The updated stack or queue.

    `query_all_templates(self) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   List all templates.

    `query_history(self, query: madsci.common.types.resource_types.server_types.ResourceHistoryGetQuery = Body(PydanticUndefined)) ‑> list[madsci.resource_manager.resource_tables.ResourceHistoryTable]`
    :   Retrieve the history of a resource.

        Args:
            query (ResourceHistoryGetQuery): The query parameters.

        Returns:
            list[ResourceHistoryTable]: A list of historical resource entries.

    `query_resource(self, query: madsci.common.types.resource_types.server_types.ResourceGetQuery = Body(PydanticUndefined)) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Retrieve a resource from the database based on the specified parameters.

    `query_resource_hierarchy(self, resource_id: str) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Query the hierarchical relationships of a resource.

        Returns the ancestors (successive parent IDs from closest to furthest)
        and descendants (all children recursively, organized by parent) of the specified resource.

        Args:
            resource_id (str): The ID of the resource to query hierarchy for.

        Returns:
            ResourceHierarchy: Hierarchy information with:
                - ancestor_ids: List of all direct ancestors (parent, grandparent, etc.)
                - resource_id: The ID of the queried resource
                - descendant_ids: Dict mapping parent IDs to their direct child IDs,
                  recursively including all descendant generations (children, grandchildren, etc.)

    `query_templates(self, query: madsci.common.types.resource_types.server_types.TemplateGetQuery) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query templates with optional filtering.

    `release_resource_lock(self, resource_id: str, client_id: str | None = None) ‑> dict[str, typing.Any] | None`
    :   Release a lock on a resource.

        Args:
            resource_id (str): The ID of the resource to unlock.
            client_id (Optional[str]): Client identifier.

        Returns:
            dict: Lock release result.

    `remove_capacity_limit(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove the capacity limit of a resource.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.

    `remove_child(self, resource_id: str, body: madsci.common.types.resource_types.server_types.RemoveChildBody) ‑> madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a child resource from a parent resource. Must be a container type that supports random access.

        Args:
            resource_id (str): The ID of the parent resource.
            body (RemoveChildBody): The body of the request.

        Returns:
            ResourceDataModels: The updated parent resource.

    `remove_resource(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Marks a resource as removed. This will remove the resource from the active resources table,
        but it will still be available in the history table.

    `restore_deleted_resource(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Restore a previously deleted resource from the history table.

        Args:
            resource_id (str): the id of the resource to restore.

        Returns:
            ResourceDataModels: The restored resource.

    `set_capacity(self, resource_id: str, capacity: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the capacity of a resource.

        Args:
            resource_id (str): The ID of the resource.
            capacity (Union[float, int]): The capacity to set.

        Returns:
            ResourceDataModels: The updated resource.

    `set_child(self, resource_id: str, body: madsci.common.types.resource_types.server_types.SetChildBody) ‑> madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set a child resource for a parent resource. Must be a container type that supports random access.

        Args:
            resource_id (str): The ID of the parent resource.
            body (SetChildBody): The body of the request.

        Returns:
            ResourceDataModels: The updated parent resource.

    `set_quantity(self, resource_id: str, quantity: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the quantity of a resource.

        Args:
            resource_id (str): The ID of the resource.
            quantity (Union[float, int]): The quantity to set.

        Returns:
            ResourceDataModels: The updated resource.

    `update_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] = Body(PydanticUndefined)) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update or refresh a resource in the database, including its children.

    `update_template(self, template_name: str, body: madsci.common.types.resource_types.server_types.TemplateUpdateBody) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update an existing template.
