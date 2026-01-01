Module madsci.client.resource_client
====================================
Fast API Client for Resources

Classes
-------

`ResourceClient(resource_server_url: str | pydantic.networks.AnyUrl | None = None, event_client: madsci.client.event_client.EventClient | None = None, config: madsci.common.types.client_types.ResourceClientConfig | None = None)`
:   REST client for interacting with a MADSci Resource Manager.

    Initialize the resource client.

    Args:
        resource_server_url: The URL of the resource server. If not provided, will use the URL from the current MADSci context.
        event_client: Optional EventClient for logging. If not provided, creates a new one.
        config: Client configuration for retry and timeout settings. If not provided, uses default ResourceClientConfig.

    ### Class variables

    `local_resources: dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :

    `local_templates: ClassVar[dict[str, dict]]`
    :

    `resource_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Methods

    `acquire_lock(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, client_id: str | None = None, timeout: float | None = None) ‑> bool`
    :   Acquire a lock on a resource.

        Args:
            resource: Resource object or resource ID
            lock_duration: Lock duration in seconds (default 5 minutes)
            client_id: Client identifier (auto-generated if not provided)
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            bool: True if lock was acquired, False otherwise

    `add_or_update_resource(self, resource: madsci.common.types.resource_types.Resource, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource`
    :   Add a resource to the server.

        Args:
            resource (Resource): The resource to add.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            Resource: The added resource as returned by the server.

    `add_resource(self, resource: madsci.common.types.resource_types.Resource, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource`
    :   Add a resource to the server.

        Args:
            resource (Resource): The resource to add.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            Resource: The added resource as returned by the server.

    `change_quantity_by(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to change by.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `create_resource_from_template(self, template_name: str, resource_name: str, overrides: dict[str, typing.Any] | None = None, add_to_database: bool = True, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a resource from a template.

        Args:
            template_name (str): Name of the template to use.
            resource_name (str): Name for the new resource.
            overrides (Optional[dict[str, Any]]): Values to override template defaults.
            add_to_database (bool): Whether to add the resource to the database.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The created resource.

    `create_template(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], template_name: str, description: str = '', required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a new resource template from a resource.

        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The created template resource.

    `decrease_quantity(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Decrease the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to decrease by. Note that this is a magnitude, so negative and positive values will have the same effect.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `delete_template(self, template_name: str, timeout: float | None = None) ‑> bool`
    :   Delete a template from the database.

        Args:
            template_name (str): Name of the template to delete.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            bool: True if template was deleted, False if not found.

    `empty(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Empty the contents of a container or consumable resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `fill(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Fill a consumable resource to capacity.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `get_resource(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Retrieve a resource from the server.

        Args:
            resource (Optional[Union[str, ResourceDataModels]]): The resource object or ID to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The retrieved resource.

    `get_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a template by name.

        Args:
            template_name (str): Name of the template to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.

    `get_template_info(self, template_name: str, timeout: float | None = None) ‑> dict[str, typing.Any] | None`
    :   Get detailed template metadata.

        Args:
            template_name (str): Name of the template.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            Optional[dict[str, Any]]: Template metadata if found, None otherwise.

    `get_templates_by_category(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get templates organized by base_type category.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            dict[str, list[str]]: Dictionary mapping base_type to template names.

    `increase_quantity(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], amount: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Increase the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to increase by. Note that this is a magnitude, so negative and positive values will have the same effect.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `init_resource(self, resource_definition: Annotated[Annotated[madsci.common.types.resource_types.definitions.ResourceDefinition, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.definitions.AssetResourceDefinition, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.definitions.ContainerResourceDefinition, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.definitions.CollectionResourceDefinition, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.definitions.RowResourceDefinition, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.definitions.GridResourceDefinition, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.definitions.StackResourceDefinition, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.definitions.QueueResourceDefinition, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.definitions.PoolResourceDefinition, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.definitions.SlotResourceDefinition, Tag(tag='slot')] | Annotated[madsci.common.types.resource_types.definitions.ConsumableResourceDefinition, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition, Tag(tag='continuous_consumable')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Initializes a resource with the resource manager based on a definition, either creating a new resource if no matching one exists, or returning an existing match.

        Args:
            resource (Resource): The resource to initialize.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The initialized resource as returned by the server.

    `init_template(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], template_name: str, description: str = '', required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0') ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Initialize a template with the resource manager.

        If a template with the given name already exists, returns the existing template.
        If no matching template exists, creates a new one.

        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.

        Returns:
            ResourceDataModels: The existing or newly created template resource.

    `is_locked(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> tuple[bool, str | None]`
    :   Check if a resource is currently locked.

        Args:
            resource: Resource object or resource ID
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)

    `lock(self, *resources: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, auto_refresh: bool = True, client_id: str | None = None) ‑> Generator[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, ...], None, None]`
    :   Create a context manager for locking multiple resources.

        Args:
            *resources: Resources to lock (can be Resource objects or IDs)
            lock_duration: Lock duration in seconds
            auto_refresh: Whether to refresh resources on entry/exit
            client_id: Client identifier (auto-generated if not provided)

        Returns:
            Context manager that yields locked resources

        Usage:
            with client.lock(stack1, child1) as (stack, child):
                stack.push(child)

    `pop(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Pop an asset from a stack or queue resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            tuple[ResourceDataModels, ResourceDataModels]: The popped asset and updated parent.

    `push(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], child: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Push a child resource onto a parent stack or queue.

        Args:
            resource (Union[ResourceDataModels, str]): The parent resource or its ID.
            child (Union[ResourceDataModels, str]): The child resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated parent resource.

    `query_history(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, version: int | None = None, change_type: str | None = None, removed: bool | None = None, start_date: datetime.datetime | None = None, end_date: datetime.datetime | None = None, limit: int | None = 100, timeout: float | None = None) ‑> list[dict[str, typing.Any]]`
    :   Retrieve the history of a resource with flexible filters.

        Args:
            resource: The resource or resource ID to query history for.
            version: Filter by specific version number.
            change_type: Filter by change type.
            removed: Filter by removed status.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of history entries to return.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `query_resource(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)] | None = None, resource_name: str | None = None, parent_id: str | None = None, resource_class: str | None = None, base_type: str | None = None, unique: bool | None = False, multiple: bool | None = False, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query for one or more resources matching specific properties.

        Args:
            resource (str, Resource): The (ID of) the resource to retrieve.
            resource_name (str): The name of the resource to retrieve.
            parent_id (str): The ID of the parent resource.
            resource_class (str): The class of the resource.
            base_type (str): The base type of the resource.
            unique (bool): Whether to require a unique resource or not.
            multiple (bool): Whether to return multiple resources or just the first.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            Resource: The retrieved resource.

    `query_resource_hierarchy(self, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Query the hierarchical relationships of a resource.

        Returns the ancestors (successive parent IDs from closest to furthest)
        and descendants (direct children organized by parent) of the specified resource.

        Args:
            resource_id (str): The ID of the resource to query hierarchy for.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceHierarchy: Hierarchy information with ancestor_ids, resource_id, and descendant_ids.

        Raises:
            ValueError: If resource not found.
            requests.HTTPError: If server request fails.

    `query_templates(self, base_type: str | None = None, tags: list[str] | None = None, created_by: str | None = None, timeout: float | None = None) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   List templates with optional filtering.

        Args:
            base_type (Optional[str]): Filter by base resource type.
            tags (Optional[list[str]]): Filter by templates that have any of these tags.
            created_by (Optional[str]): Filter by creator.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            list[ResourceDataModels]: List of template resources.

    `release_lock(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], client_id: str | None = None, timeout: float | None = None) ‑> bool`
    :   Release a lock on a resource.

        Args:
            resource: Resource object or resource ID
            client_id: Client identifier
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            bool: True if lock was released, False otherwise

    `remove(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource by moving it to the history table with `removed=True`.

        Args:
            resource: The resource or resource ID to remove.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `remove_capacity_limit(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove the capacity limit of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `remove_child(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], key: str | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]] | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a child resource from a parent container resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated parent container resource.

    `remove_resource(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource by moving it to the history table with `removed=True`.

        Args:
            resource: The resource or resource ID to remove.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `restore_deleted_resource(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Restore a deleted resource from the history table.

        Args:
            resource: The resource or resource ID to restore.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `set_capacity(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], capacity: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the capacity of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            capacity (Union[float, int]): The capacity to set.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `set_child(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], key: str | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]] | tuple[int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)], int | Annotated[str, AfterValidator(func=<function single_letter_or_digit_validator at 0x7ffbac7c7c40>)]], child: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set a child resource in a parent container resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.
            child (Union[str, ResourceDataModels]): The child resource or its ID.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated parent container resource.

    `set_quantity(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], quantity: float | int, timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the quantity of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            quantity (Union[float, int]): The quantity to set.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource.

    `update(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceDataModels): The resource to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource as returned by the server.

    `update_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceDataModels): The resource to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated resource as returned by the server.

    `update_template(self, template_name: str, updates: dict[str, typing.Any], timeout: float | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update an existing template.

        Args:
            template_name (str): Name of the template to update.
            updates (dict[str, Any]): Fields to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns:
            ResourceDataModels: The updated template resource.

`ResourceWrapper(resource: ResourceDataModels, client: ResourceClient)`
:   A wrapper around Resource data models that adds client method convenience.

    This class acts as a transparent proxy to the underlying resource while
    adding client methods.

    - Resource classes stay pure data models (no client dependencies)
    - This wrapper adds client functionality without modifying data classes
    - Wrapper is transparent - behaves like the wrapped resource for data access

    Create a wrapper around a resource.

    Args:
        resource: The pure data model (Stack, Queue, Resource, etc.)
        client: The ResourceClient instance for operations

    ### Instance variables

    `client: ResourceClient`
    :   Get the bound client instance.

    `unwrap: ResourceDataModels`
    :   Get the underlying pure data model.

        Useful when you need to pass the raw resource to functions
        that expect pure data models.
