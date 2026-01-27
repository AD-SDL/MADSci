Module madsci.resource_manager.resource_interface
=================================================
Resources Interface

Classes
-------

`ResourceInterface(url: str | None = None, engine: str | None = None, sessionmaker: <built-in function callable> | None = None, session: sqlmodel.orm.session.Session | None = None, init_timeout: float = 10.0, logger: madsci.client.event_client.EventClient | None = None)`
:   Interface for managing various types of resources.

    Attributes:
        engine (sqlalchemy.engine.Engine): SQLAlchemy engine for database connection.
        session (sqlalchemy.orm.Session): SQLAlchemy session for database operations.

    Initialize the ResourceInterface with a database URL.

    Args:
        database_url (str): Database connection URL.

    ### Methods

    `acquire_lock(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], lock_duration: float = 300.0, client_id: str | None = None, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Acquire a lock on a resource.

        Args:
            resource: Resource object or resource ID
            lock_duration: Lock duration in seconds
            client_id: Identifier for the client acquiring the lock
            parent_session: Optional parent session

        Returns:
            Optional[ResourceDataModels]: if lock was acquired, None if already locked

    `add_child(self, parent_id: str, key: str, child: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], update_existing: bool = True, parent_session: sqlmodel.orm.session.Session | None = None) ‑> None`
    :   Adds a child to a parent resource, or updates an existing child if update_existing is set.

    `add_or_update_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], include_descendants: bool = True, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Add or update a resource in the database.

    `add_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], add_descendants: bool = True, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Add a resource to the database.

        Args:
            resource (ResourceDataModels): The resource to add.

        Returns:
            ResourceDataModels: The saved or existing resource data model.

    `create_resource_from_template(self, template_name: str, resource_name: str, overrides: dict[str, typing.Any] | None = None, add_to_database: bool = True, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a resource from a template and add it to the resource table.

        Args:
            template_name (str): Name of the template to use.
            resource_name (str): Name for the new resource.
            overrides (Optional[dict]): Values to override template defaults.
            add_to_database (bool): Whether to add the resource to the resource table.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            ResourceDataModels: The created resource (stored in resource table).

    `create_template(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], template_name: str, description: str = '', required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Create a template from a resource.

        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            ResourceDataModels: The template resource.

    `delete_template(self, template_name: str, parent_session: sqlmodel.orm.session.Session | None = None) ‑> bool`
    :   Delete a template from the database.

        Args:
            template_name (str): Name of the template to delete.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            bool: True if template was deleted, False if not found.

    `empty(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Empty the contents of a container or consumable resource.

    `fill(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Fill a consumable resource to capacity.

    `get_resource(self, resource_id: str | None = None, resource_name: str | None = None, parent_id: str | None = None, owner: madsci.common.types.auth_types.OwnershipInfo | None = None, resource_class: str | None = None, base_type: madsci.common.types.resource_types.resource_enums.ResourceTypeEnum | None = None, unique: bool = False, multiple: bool = False, **kwargs: Any) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot] | madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get the resource(s) that match the specified properties (unless `unique` is specified,
        in which case an exception is raised if more than one result is found).

        Returns:
            Optional[Union[list[ResourceDataModels], ResourceDataModels]]: The resource(s), if found, otherwise None.

    `get_session(self, session: sqlmodel.orm.session.Session | None = None) ‑> Generator[sqlmodel.orm.session.Session, None, None]`
    :   Fetch a useable session.

    `get_template(self, template_name: str, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Get a template by name, returned as a resource.

        Args:
            template_name (str): Name of the template to retrieve.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.

    `get_template_info(self, template_name: str, parent_session: sqlmodel.orm.session.Session | None = None) ‑> dict[str, typing.Any] | None`
    :   Get detailed template metadata (template-specific fields).

        Args:
            template_name (str): Name of the template.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            Optional[dict]: Template metadata if found, None otherwise.

    `get_templates_by_category(self, parent_session: sqlmodel.orm.session.Session | None = None) ‑> dict[str, list[str]]`
    :   Get templates organized by base_type category.

        Args:
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            dict[str, list[str]]: Dictionary mapping base_type to template names.

    `get_templates_by_tags(self, tags: list[str], parent_session: sqlmodel.orm.session.Session | None = None) ‑> list[str]`
    :   Get template names that have any of the specified tags.

        Args:
            tags (list[str]): Tags to search for.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            list[str]: List of template names that match any of the tags.

    `init_custom_resource(self, input_definition: Annotated[Annotated[madsci.common.types.resource_types.definitions.ResourceDefinition, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.definitions.AssetResourceDefinition, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.definitions.ContainerResourceDefinition, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.definitions.CollectionResourceDefinition, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.definitions.RowResourceDefinition, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.definitions.GridResourceDefinition, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.definitions.StackResourceDefinition, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.definitions.QueueResourceDefinition, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.definitions.PoolResourceDefinition, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.definitions.SlotResourceDefinition, Tag(tag='slot')] | Annotated[madsci.common.types.resource_types.definitions.ConsumableResourceDefinition, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition, Tag(tag='continuous_consumable')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], custom_definition: Annotated[Annotated[madsci.common.types.resource_types.definitions.ResourceDefinition, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.definitions.AssetResourceDefinition, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.definitions.ContainerResourceDefinition, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.definitions.CollectionResourceDefinition, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.definitions.RowResourceDefinition, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.definitions.GridResourceDefinition, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.definitions.VoxelGridResourceDefinition, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.definitions.StackResourceDefinition, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.definitions.QueueResourceDefinition, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.definitions.PoolResourceDefinition, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.definitions.SlotResourceDefinition, Tag(tag='slot')] | Annotated[madsci.common.types.resource_types.definitions.ConsumableResourceDefinition, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.definitions.DiscreteConsumableResourceDefinition, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.definitions.ContinuousConsumableResourceDefinition, Tag(tag='continuous_consumable')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   initialize a custom resource

    `is_locked(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], parent_session: sqlmodel.orm.session.Session | None = None) ‑> tuple[bool, str | None]`
    :   Check if a resource is currently locked.

        Args:
            resource: Resource object or resource ID
            parent_session: Optional parent session

        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)

    `pop(self, parent_id: str) ‑> tuple[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot, madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Slot]`
    :   Pop a resource from a Stack, Queue, or Slot. Returns the popped resource.

        Args:
            parent_id (str): The id of the stack or queue resource to update.

        Returns:
            child (ResourceDataModels): The popped resource.

            updated_parent (Union[Stack, Queue, Slot]): updated parent container

    `push(self, parent_id: str, child: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]) ‑> madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Slot`
    :   Push a resource to a stack, queue, or slot. Automatically adds the child to the database if it's not already there.

        Args:
            parent_id (str): The id of the stack or queue resource to push the resource onto.
            child (Union[ResourceDataModels, str]): The resource to push onto the stack (or an ID, if it already exists).

        Returns:
            updated_parent: The updated stack or queue resource.

    `query_history(self, resource_id: str | None = None, version: int | None = None, change_type: str | None = None, removed: bool | None = None, start_date: datetime.datetime | None = None, end_date: datetime.datetime | None = None, limit: int | None = 100) ‑> list[madsci.resource_manager.resource_tables.ResourceHistoryTable]`
    :   Query the History table with flexible filtering.

        - If only `resource_id` is provided, fetches **all history** for that resource.
        - If additional filters (`event_type`, `removed`, etc.) are given, applies them.

        Args:
            resource_id (str): Required. Fetch history for this resource.
            version (Optional[int]): Fetch a specific version of the resource.
            event_type (Optional[str]): Filter by event type (`created`, `updated`, `deleted`).
            removed (Optional[bool]): Filter by removed status.
            start_date (Optional[datetime]): Start of the date range.
            end_date (Optional[datetime]): End of the date range.
            limit (Optional[int]): Maximum number of records to return (None for all records).

        Returns:
            List[JSON]: A list of deserialized history table entries.

    `query_resource_hierarchy(self, resource_id: str, parent_session: sqlmodel.orm.session.Session | None = None) ‑> dict[str, typing.Any]`
    :   Query the hierarchical relationships of a resource.

        Returns the ancestors (successive parent IDs from closest to furthest)
        and descendants (all children recursively, organized by parent) of the specified resource.

        Args:
            resource_id (str): The ID of the resource to query hierarchy for.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            dict[str, Any]: ResourceHierarchy with:
                - ancestor_ids: List of all direct ancestors (parent, grandparent, etc.)
                - resource_id: The ID of the queried resource
                - descendant_ids: Dict mapping parent IDs to their direct child IDs,
                  recursively including all descendant generations (children, grandchildren, etc.)

    `query_templates(self, base_type: str | None = None, tags: list[str] | None = None, created_by: str | None = None, parent_session: sqlmodel.orm.session.Session | None = None) ‑> list[madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Query templates with optional filtering, returned as resources.

        Args:
            base_type (Optional[str]): Filter by base resource type.
            tags (Optional[list[str]]): Filter by templates that have any of these tags.
            created_by (Optional[str]): Filter by creator.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            list[ResourceDataModels]: List of template resources.

    `release_lock(self, resource: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], client_id: str | None = None, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Release a lock on a resource.

        Args:
            resource: Resource object or resource ID
            client_id: Identifier for the client releasing the lock
            parent_session: Optional parent session

        Returns:
            Optional[ResourceDataModels]: Resource data model if lock was released, None if not locked by this client

    `remove_capacity_limit(self, resource_id: str) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove the capacity limit of a resource.

    `remove_child(self, container_id: str, key: Any) ‑> madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Container`
    :   Remove the child of a container at a particular key/location.

        Args:
            container_id (str): The id of the collection resource to update.
            key (str): The key of the child to remove.

        Returns:
            Union[Container, Collection]: The updated container or collection resource.

    `remove_resource(self, resource_id: str, parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Remove a resource from the database.

    `restore_resource(self, resource_id: str, parent_session: sqlmodel.orm.session.Session = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot | None`
    :   Restore the latest version of a removed resource. This attempts to restore the child resources as well, if any.


        Args:
            resource_id (str): The resource ID.
            restore_children (bool): Whether to restore the child resources as well.

        Returns:
            Optional[ResourceDataModels]: The restored resource, if any

    `set_capacity(self, resource_id: str, capacity: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the capacity of a resource.

    `set_child(self, container_id: str, key: str | tuple, child: str | Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]) ‑> madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Set the child of a container at a particular key/location. Automatically adds the child to the database if it's not already there.
        Only works for Container or Collection resources.

        Args:
            container_id (str): The id of the collection resource to update.
            key (str): The key of the child to update.
            child (Union[Resource, str]): The child resource to update.

        Returns:
            ContainerDataModels: The updated container resource.

    `set_quantity(self, resource_id: str, quantity: int | float) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Change the quantity of a consumable resource.

    `update_resource(self, resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)], update_descendants: bool = True, parent_session: sqlmodel.orm.session.Session | None = None) ‑> None`
    :   Update or refresh a resource in the database, including its children.

        Args:
            resource (Resource): The resource to refresh.

        Returns:
            None

    `update_template(self, template_name: str, updates: dict[str, typing.Any], parent_session: sqlmodel.orm.session.Session | None = None) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Update an existing template.

        Args:
            template_name (str): Name of the template to update.
            updates (dict): Dictionary of fields to update.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            ResourceDataModels: The updated template resource.
