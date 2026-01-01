Module madsci.resource_manager.resource_tables
==============================================
Resource table objects

Functions
---------

`add_automated_history(session: sqlmodel.orm.session.Session) ‑> None`
:   Add automated history to the session.

    Args:
        session (Session): SQLAlchemy session.

`create_session(*args: Any, **kwargs: Any) ‑> sqlmodel.orm.session.Session`
:   Create a new SQLModel session.

`delete_descendants(session: sqlmodel.orm.session.Session, resource_entry: ResourceTable) ‑> list[str]`
:   Recursively delete all children of a resource entry.
    Args:
        session (Session): SQLAlchemy session.
        resource_entry (ResourceTable): The resource entry.

`prevent_recursive_parent_relationships(session: sqlmodel.orm.session.Session, _flush_context: Any, _instances: Any) ‑> None`
:   Event listener to prevent recursive parent relationships in ResourceTable before flush.
    Raises ValueError if a cycle is detected.

Classes
-------

`ResourceHistoryTable(**data)`
:   The table for storing information about historical Resources.

    ### Ancestors (in MRO)

    * madsci.resource_manager.resource_tables.ResourceTableBase
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Instance variables

    `attributes: dict`
    :

    `base_type: str`
    :

    `capacity: decimal.Decimal | None`
    :

    `change_type: str`
    :

    `changed_at: datetime.datetime | None`
    :

    `child_ids: list[str] | None`
    :

    `columns: int | None`
    :

    `created_at: datetime.datetime | None`
    :

    `custom_attributes: list[madsci.common.types.resource_types.definitions.CustomResourceAttributeDefinition] | None`
    :

    `key: str | None`
    :

    `layers: int | None`
    :

    `locked_by: str | None`
    :

    `locked_until: datetime.datetime | None`
    :

    `owner: dict[str, str]`
    :

    `parent_id: str | None`
    :

    `quantity: decimal.Decimal | None`
    :

    `removed: bool`
    :

    `resource_class: str`
    :

    `resource_description: str | None`
    :

    `resource_id: str`
    :

    `resource_name: str`
    :

    `resource_name_prefix: str | None`
    :

    `resource_url: str | None`
    :

    `rows: int | None`
    :

    `template_name: str | None`
    :

    `updated_at: datetime.datetime | None`
    :

    `version: int | None`
    :

`ResourceTable(**data)`
:   The table for storing information about active Resources, with various utility methods.

    ### Ancestors (in MRO)

    * madsci.resource_manager.resource_tables.ResourceTableBase
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Instance variables

    `attributes: dict`
    :

    `base_type: str`
    :

    `capacity: decimal.Decimal | None`
    :

    `children: dict[str, 'ResourceTable']`
    :   Get the children resources as a dictionary.

        Returns:
            dict: Dictionary of children resources.

    `children_list: sqlalchemy.orm.base.Mapped[list[madsci.resource_manager.resource_tables.ResourceTable]]`
    :

    `columns: int | None`
    :

    `created_at: datetime.datetime | None`
    :

    `custom_attributes: list[madsci.common.types.resource_types.definitions.CustomResourceAttributeDefinition] | None`
    :

    `key: str | None`
    :

    `layers: int | None`
    :

    `locked_by: str | None`
    :

    `locked_until: datetime.datetime | None`
    :

    `owner: dict[str, str]`
    :

    `parent: sqlalchemy.orm.base.Mapped[madsci.resource_manager.resource_tables.ResourceTable | None]`
    :

    `parent_id: str | None`
    :

    `quantity: decimal.Decimal | None`
    :

    `removed: bool`
    :

    `resource_class: str`
    :

    `resource_description: str | None`
    :

    `resource_id: str`
    :

    `resource_name: str`
    :

    `resource_name_prefix: str | None`
    :

    `resource_url: str | None`
    :

    `rows: int | None`
    :

    `template_name: str | None`
    :

    `updated_at: datetime.datetime | None`
    :

    ### Methods

    `check_no_recursive_parent(self) ‑> None`
    :   Check for recursive parent relationships (cycles) in the parent chain.
        Raises ValueError if a cycle is detected.

`ResourceTableBase(**data: Any)`
:   Base class for all resource-based tables.

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

    * madsci.resource_manager.resource_tables.ResourceHistoryTable
    * madsci.resource_manager.resource_tables.ResourceTable
    * madsci.resource_manager.resource_tables.ResourceTemplateTable

    ### Class variables

    `base_type: str`
    :

    `capacity: decimal.Decimal | None`
    :

    `columns: int | None`
    :

    `created_at: datetime.datetime | None`
    :

    `key: str | None`
    :

    `layers: int | None`
    :

    `locked_by: str | None`
    :

    `locked_until: datetime.datetime | None`
    :

    `owner: dict[str, str]`
    :

    `parent_id: str | None`
    :

    `quantity: decimal.Decimal | None`
    :

    `rows: int | None`
    :

    `template_name: str | None`
    :

    ### Static methods

    `from_data_model(resource: Annotated[Annotated[madsci.common.types.resource_types.Resource, Tag(tag='resource')] | Annotated[madsci.common.types.resource_types.Asset, Tag(tag='asset')] | Annotated[madsci.common.types.resource_types.Consumable, Tag(tag='consumable')] | Annotated[madsci.common.types.resource_types.DiscreteConsumable, Tag(tag='discrete_consumable')] | Annotated[madsci.common.types.resource_types.ContinuousConsumable, Tag(tag='continuous_consumable')] | Annotated[madsci.common.types.resource_types.Container, Tag(tag='container')] | Annotated[madsci.common.types.resource_types.Collection, Tag(tag='collection')] | Annotated[madsci.common.types.resource_types.Row, Tag(tag='row')] | Annotated[madsci.common.types.resource_types.Grid, Tag(tag='grid')] | Annotated[madsci.common.types.resource_types.VoxelGrid, Tag(tag='voxel_grid')] | Annotated[madsci.common.types.resource_types.Stack, Tag(tag='stack')] | Annotated[madsci.common.types.resource_types.Queue, Tag(tag='queue')] | Annotated[madsci.common.types.resource_types.Pool, Tag(tag='pool')] | Annotated[madsci.common.types.resource_types.Slot, Tag(tag='slot')], Discriminator(discriminator='base_type', custom_error_type=None, custom_error_message=None, custom_error_context=None)]) ‑> Self`
    :   Create a new Resource Table entry from a resource data model.

    ### Methods

    `to_data_model(self, include_children: bool = True) ‑> madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot`
    :   Convert the table entry to a data model.

        Returns:
            ResourceDataModels: The resource data model.

`ResourceTemplateTable(**data)`
:   The table for storing Resource Template definitions.

    ### Ancestors (in MRO)

    * madsci.resource_manager.resource_tables.ResourceTableBase
    * madsci.common.types.resource_types.Resource
    * madsci.common.types.resource_types.definitions.ResourceDefinition
    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Instance variables

    `attributes: dict`
    :

    `base_type: str`
    :

    `capacity: decimal.Decimal | None`
    :

    `columns: int | None`
    :

    `created_at: datetime.datetime | None`
    :

    `created_by: str | None`
    :

    `custom_attributes: list[madsci.common.types.resource_types.definitions.CustomResourceAttributeDefinition] | None`
    :

    `default_values: dict[str, typing.Any]`
    :

    `description: str`
    :

    `key: str | None`
    :

    `layers: int | None`
    :

    `locked_by: str | None`
    :

    `locked_until: datetime.datetime | None`
    :

    `owner: dict[str, str]`
    :

    `parent_id: str | None`
    :

    `quantity: decimal.Decimal | None`
    :

    `removed: bool`
    :

    `required_overrides: list[str]`
    :

    `resource_class: str`
    :

    `resource_description: str | None`
    :

    `resource_id: str`
    :

    `resource_name: str`
    :

    `resource_name_prefix: str | None`
    :

    `resource_url: str | None`
    :

    `rows: int | None`
    :

    `tags: list[str]`
    :

    `template_name: str`
    :

    `updated_at: datetime.datetime | None`
    :

    `version: str`
    :

`SchemaVersionTable(**data)`
:   Table to track the current schema version of the MADSci database.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciSQLModel
    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Instance variables

    `applied_at: datetime.datetime | None`
    :

    `migration_notes: str | None`
    :

    `version: str`
    :
