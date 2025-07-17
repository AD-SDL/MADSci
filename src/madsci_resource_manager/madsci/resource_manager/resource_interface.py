"""Resources Interface"""

# Suppress SAWarnings
import time
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from madsci.client.event_client import EventClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.resource_types import (
    RESOURCE_TYPE_MAP,
    Collection,
    ConsumableTypeEnum,
    Container,
    ContainerDataModels,
    ContainerTypeEnum,
    Queue,
    Resource,
    ResourceDataModels,
    ResourceTypeEnum,
    Slot,
    Stack,
)
from madsci.common.types.resource_types.definitions import (
    ResourceDefinitions,
)
from madsci.common.utils import new_ulid_str
from madsci.resource_manager.resource_tables import (
    ResourceHistoryTable,
    ResourceTable,
    ResourceTemplateTable,
    create_session,
)
from sqlalchemy import and_, true
from sqlalchemy.exc import MultipleResultsFound
from sqlmodel import Session, SQLModel, create_engine, func, select


class ResourceInterface:
    """
    Interface for managing various types of resources.

    Attributes:
        engine (sqlalchemy.engine.Engine): SQLAlchemy engine for database connection.
        session (sqlalchemy.orm.Session): SQLAlchemy session for database operations.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        engine: Optional[str] = None,
        sessionmaker: Optional[callable] = None,
        session: Optional[Session] = None,
        init_timeout: float = 10.0,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the ResourceInterface with a database URL.

        Args:
            database_url (str): Database connection URL.
        """
        start_time = time.time()
        while time.time() - start_time < init_timeout:
            try:
                self.url = url
                self.engine = engine
                self.sessionmaker = sessionmaker
                self.session = session
                self.logger = logger or EventClient()

                if not (self.url or self.engine or self.sessionmaker or self.session):
                    raise ValueError(
                        "At least one of url, engine, sessionmaker, or session must be provided."
                    )
                if self.url and not self.engine:
                    self.engine = create_engine(self.url)
                if not self.engine and self.session:
                    self.engine = self.session.bind
                self.sessionmaker = self.sessionmaker or create_session
                if self.engine:
                    SQLModel.metadata.create_all(self.engine)
                self.logger.info("Initialized Resource Interface.")
                break
            except Exception:
                self.logger.error(
                    f"Error while creating/connecting to database: \n{traceback.print_exc()}"
                )
                time.sleep(5)
                continue
        else:
            self.logger.error(
                f"Failed to connect to database after {init_timeout} seconds."
            )
            raise ConnectionError(
                f"Failed to connect to database after {init_timeout} seconds."
            )

    @contextmanager
    def get_session(
        self, session: Optional[Session] = None
    ) -> Generator[Session, None, None]:
        """Fetch a useable session."""
        if session:
            yield session
        elif self.session:
            yield self.session
        else:
            session = self.sessionmaker()
            session.bind = self.engine
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                self.logger.error(
                    f"Error while committing session: \n{traceback.format_exc()}"
                )
                raise
            finally:
                session.close()

    def add_resource(
        self,
        resource: ResourceDataModels,
        add_descendants: bool = True,
        parent_session: Optional[Session] = None,
    ) -> ResourceDataModels:
        """
        Add a resource to the database.

        Args:
            resource (ResourceDataModels): The resource to add.

        Returns:
            ResourceDataModels: The saved or existing resource data model.
        """
        try:
            with self.get_session(parent_session) as session:
                resource_row = ResourceTable.from_data_model(resource)
                # * Check if the resource already exists in the database
                existing_resource = session.exec(
                    select(ResourceTable).where(
                        ResourceTable.resource_id == resource_row.resource_id
                    )
                ).first()
                if existing_resource:
                    self.logger.info(
                        f"Resource with ID '{resource_row.resource_id}' already exists in the database. No action taken."
                    )
                    return existing_resource.to_data_model()

                session.add(resource_row)
                if add_descendants and getattr(resource, "children", None):
                    children = resource.extract_children()
                    for key, child in children.items():
                        if child is not None:
                            child.parent_id = resource_row.resource_id
                            child.key = key
                            self.add_or_update_resource(
                                resource=child,
                                include_descendants=add_descendants,
                                parent_session=session,
                            )
                session.commit()
                session.refresh(resource_row)
                return resource_row.to_data_model()
        except Exception as e:
            self.logger.error(f"Error adding resource: \n{traceback.format_exc()}")
            raise e

    def update_resource(
        self,
        resource: ResourceDataModels,
        update_descendants: bool = True,
        parent_session: Optional[Session] = None,
    ) -> None:
        """
        Update or refresh a resource in the database, including its children.

        Args:
            resource (Resource): The resource to refresh.

        Returns:
            None
        """
        try:
            with self.get_session(parent_session) as session:
                existing_row = session.exec(
                    select(ResourceTable).where(
                        ResourceTable.resource_id == resource.resource_id
                    )
                ).one()
                resource_row = session.merge(
                    existing_row.model_copy(
                        update=resource.model_dump(
                            exclude={"children", "created_at", "updated_at"}
                        ),
                        deep=True,
                    )
                )
                if update_descendants and hasattr(resource, "children"):
                    resource_row.children_list = []
                    children = resource.extract_children()
                    for key, child in children.items():
                        if child is None:
                            continue
                        child.parent_id = resource_row.resource_id
                        child.key = key
                        self.add_or_update_resource(
                            resource=child,
                            include_descendants=update_descendants,
                            parent_session=session,
                        )
                session.commit()
                session.refresh(resource_row)
                return resource_row.to_data_model()
        except Exception as e:
            self.logger.error(f"Error updating resource: \n{traceback.format_exc()}")
            raise e

    def add_or_update_resource(
        self,
        resource: ResourceDataModels,
        include_descendants: bool = True,
        parent_session: Optional[Session] = None,
    ) -> ResourceDataModels:
        """Add or update a resource in the database."""
        with self.get_session(parent_session) as session:
            existing_resource = session.exec(
                select(ResourceTable).where(
                    ResourceTable.resource_id == resource.resource_id
                )
            ).first()
            if existing_resource:
                return self.update_resource(
                    resource,
                    update_descendants=include_descendants,
                    parent_session=session,
                )
            return self.add_resource(
                resource, add_descendants=include_descendants, parent_session=session
            )

    def get_resource(
        self,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        owner: Optional[OwnershipInfo] = None,
        resource_class: Optional[str] = None,
        base_type: Optional[ResourceTypeEnum] = None,
        unique: bool = False,
        multiple: bool = False,
        **kwargs: Any,  #  noqa ARG002:Consumes any additional keyword arguments to make model dumps easier
    ) -> Optional[Union[list[ResourceDataModels], ResourceDataModels]]:
        """
        Get the resource(s) that match the specified properties (unless `unique` is specified,
        in which case an exception is raised if more than one result is found).

        Returns:
            Optional[Union[list[ResourceDataModels], ResourceDataModels]]: The resource(s), if found, otherwise None.
        """
        with self.get_session() as session:
            # * Build the query statement
            statement = select(ResourceTable)
            statement = (
                statement.where(ResourceTable.resource_id == resource_id)
                if resource_id
                else statement
            )
            statement = (
                statement.where(ResourceTable.resource_name == resource_name)
                if resource_name
                else statement
            )
            statement = (
                statement.where(ResourceTable.parent_id == parent_id)
                if parent_id
                else statement
            )
            if owner is not None:
                owner = OwnershipInfo.model_validate(owner)
                for key, value in owner.model_dump(exclude_none=True).items():
                    statement = statement.filter(
                        ResourceTable.owner[key].as_string() == value
                    )
            statement = (
                statement.where(ResourceTable.resource_class == resource_class)
                if resource_class
                else statement
            )
            statement = (
                statement.where(ResourceTable.base_type == base_type)
                if base_type
                else statement
            )

            if unique:
                try:
                    result = session.exec(statement).one_or_none()
                except MultipleResultsFound as e:
                    self.logger.error(
                        f"Result is not unique, narrow down the search criteria: {e}"
                    )
                    raise e
            elif multiple:
                return [
                    result.to_data_model() for result in session.exec(statement).all()
                ]
            else:
                result = session.exec(statement).first()
            if result:
                return result.to_data_model()
            return None

    def remove_resource(
        self, resource_id: str, parent_session: Optional[Session] = None
    ) -> ResourceDataModels:
        """Remove a resource from the database."""
        with self.get_session(parent_session) as session:
            resource = session.exec(
                select(ResourceTable).where(ResourceTable.resource_id == resource_id)
            ).one()
            resource.removed = True
            session.delete(resource)
            return resource.to_data_model()

    def query_history(
        self,
        resource_id: Optional[str] = None,
        version: Optional[int] = None,
        change_type: Optional[str] = None,
        removed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> list[ResourceHistoryTable]:
        """
        Query the History table with flexible filtering.

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
        """
        with self.get_session() as session:
            query = select(ResourceHistoryTable)

            # Apply additional filters if provided
            if resource_id:
                query = query.where(ResourceHistoryTable.resource_id == resource_id)
            if change_type:
                query = query.where(ResourceHistoryTable.change_type == change_type)
            if version:
                query = query.where(ResourceHistoryTable.version == version)
            if removed is not None:
                query = query.where(ResourceHistoryTable.removed == removed)
            if start_date:
                query = query.where(ResourceHistoryTable.changed_at >= start_date)
            if end_date:
                query = query.where(ResourceHistoryTable.changed_at <= end_date)

            query = query.order_by(ResourceHistoryTable.version.desc())

            if limit:
                query = query.limit(limit)

            history_entries = session.exec(query).all()
            return [history_entry.model_dump() for history_entry in history_entries]

    def restore_resource(
        self, resource_id: str, parent_session: Session = None
    ) -> Optional[ResourceDataModels]:
        """
        Restore the latest version of a removed resource. This attempts to restore the child resources as well, if any.


        Args:
            resource_id (str): The resource ID.
            restore_children (bool): Whether to restore the child resources as well.

        Returns:
            Optional[ResourceDataModels]: The restored resource, if any
        """
        with self.get_session(parent_session) as session:
            resource_history = session.exec(
                select(ResourceHistoryTable)
                .where(ResourceHistoryTable.resource_id == resource_id)
                .where(ResourceHistoryTable.removed == true())
                .order_by(ResourceHistoryTable.version.desc())
            ).first()
            if resource_history is None:
                self.logger.error(
                    f"No removed resource found for ID '{resource_id}' in the History table."
                )
                return None
            resource_history.removed = False
            restored_row = ResourceTable.from_data_model(
                resource_history.to_data_model()
            )
            for child_id in resource_history.child_ids:
                child_history = session.exec(
                    select(ResourceHistoryTable)
                    .where(ResourceHistoryTable.resource_id == child_id)
                    .where(ResourceHistoryTable.removed == true())
                    .order_by(
                        func.abs(
                            func.extract(
                                "epoch",
                                ResourceHistoryTable.changed_at
                                - resource_history.changed_at,
                            )
                        )
                    )
                ).first()
                if child_history:
                    self.restore_resource(
                        child_history.resource_id, parent_session=session
                    )
            session.add(restored_row)
            return resource_history.to_data_model()

    def add_child(
        self,
        parent_id: str,
        key: str,
        child: Union[ResourceDataModels, str],
        update_existing: bool = True,
        parent_session: Optional[Session] = None,
    ) -> None:
        """Adds a child to a parent resource, or updates an existing child if update_existing is set."""
        with self.get_session(parent_session) as session:
            child_id = child if isinstance(child, str) else child.resource_id
            child_row = session.exec(
                select(ResourceTable).filter_by(resource_id=child_id)
            ).one_or_none()
            existing_child = session.exec(
                select(ResourceTable).filter_by(parent_id=parent_id, key=str(key))
            ).one_or_none()
            if existing_child:
                if not update_existing:
                    raise ValueError(
                        f"Child with key '{key}' already exists for parent '{parent_id}'. Set update_existing=True to update the existing child."
                    )
                if existing_child.resource_id == child_id:
                    child.parent_id = parent_id
                    child.key = str(key)
                    self.update_resource(
                        child, update_descendants=True, parent_session=session
                    )
                else:
                    existing_child.parent_id = None
                    existing_child.key = None
                    session.merge(existing_child)
            if child_row:
                child_row.parent_id = parent_id
                child_row.key = str(key)
                session.merge(child_row)
            elif not isinstance(child, str):
                child.parent_id = parent_id
                child.key = str(key)
                child = self.add_resource(child, parent_session=session)
                child_row = ResourceTable.from_data_model(child)
            else:
                raise ValueError(
                    f"The child resource {child_id} does not exist in the database and must be added. Alternatively, provide a ResourceDataModels object instead of the ID, to have the object added automatically."
                )
            parent_row = session.exec(
                select(ResourceTable).filter_by(resource_id=parent_id)
            ).one()

        # Refresh to get updated children_list
        session.refresh(parent_row)

        # Update quantity based on actual children count
        parent_row.quantity = len(parent_row.children_list)
        session.merge(parent_row)

    def push(
        self, parent_id: str, child: Union[ResourceDataModels, str]
    ) -> Union[Stack, Queue, Slot]:
        """
        Push a resource to a stack, queue, or slot. Automatically adds the child to the database if it's not already there.

        Args:
            parent_id (str): The id of the stack or queue resource to push the resource onto.
            child (Union[ResourceDataModels, str]): The resource to push onto the stack (or an ID, if it already exists).

        Returns:
            updated_parent: The updated stack or queue resource.
        """
        with self.get_session() as session:
            parent_row = session.exec(
                select(ResourceTable).filter_by(resource_id=parent_id)
            ).one()
            if parent_row.base_type not in [
                ContainerTypeEnum.stack,
                ContainerTypeEnum.queue,
                ContainerTypeEnum.slot,
            ]:
                raise ValueError(
                    f"Resource '{parent_row.resource_name}' with type {parent_row.base_type} is not a stack, slot, or queue resource."
                )
            parent = parent_row.to_data_model()
            if parent.capacity and len(parent.children) >= parent_row.capacity:
                raise ValueError(
                    f"Cannot push resource '{child.resource_name} ({child.resource_id})' to container '{parent_row.resource_name} ({parent_row.resource_id})' because it is full."
                )
            self.add_child(
                parent_id=parent_id,
                key=str(len(parent.children)),
                child=child,
                update_existing=False,
                parent_session=session,
            )
            session.commit()
            session.refresh(parent_row)

            return parent_row.to_data_model()

    def pop(
        self, parent_id: str
    ) -> tuple[ResourceDataModels, Union[Stack, Queue, Slot]]:
        """
        Pop a resource from a Stack, Queue, or Slot. Returns the popped resource.

        Args:
            parent_id (str): The id of the stack or queue resource to update.

        Returns:
            child (ResourceDataModels): The popped resource.

            updated_parent (Union[Stack, Queue, Slot]): updated parent container

        """
        with self.get_session() as session:
            parent_row = session.exec(
                select(ResourceTable).filter_by(resource_id=parent_id)
            ).one()
            if parent_row.base_type not in [
                ContainerTypeEnum.stack,
                ContainerTypeEnum.queue,
                ContainerTypeEnum.slot,
            ]:
                raise ValueError(
                    f"Resource '{parent_row.resource_name}' with type {parent_row.base_type} is not a stack, slot, or queue resource."
                )
            parent = parent_row.to_data_model()
            if not parent.children:
                raise ValueError(f"Container '{parent.resource_name}' is empty.")
            if parent.base_type == ContainerTypeEnum.stack:
                child = parent.children[-1]
            elif parent.base_type in [ContainerTypeEnum.queue, ContainerTypeEnum.slot]:
                child = parent.children[0]
            else:
                raise ValueError(
                    f"Resource '{parent.resource_name}' with type {parent.base_type} is not a stack, slot, or queue resource."
                )
            child_row = session.exec(
                select(ResourceTable).filter_by(resource_id=child.resource_id)
            ).one()
            child_row.parent_id = None
            child_row.key = None
            session.merge(child_row)
            session.commit()
            session.refresh(parent_row)
            session.refresh(child_row)
            parent_row.quantity = len(parent_row.children_list)
            session.merge(parent_row)
            session.commit()
            session.refresh(parent_row)

            return child_row.to_data_model(), parent_row.to_data_model()

    def set_child(
        self,
        container_id: str,
        key: Union[str, tuple],
        child: Union[ResourceDataModels, str],
    ) -> ContainerDataModels:
        """
        Set the child of a container at a particular key/location. Automatically adds the child to the database if it's not already there.
        Only works for Container or Collection resources.

        Args:
            container_id (str): The id of the collection resource to update.
            key (str): The key of the child to update.
            child (Union[Resource, str]): The child resource to update.

        Returns:
            ContainerDataModels: The updated container resource.
        """
        with self.get_session() as session:
            container_row = session.exec(
                select(ResourceTable).filter_by(resource_id=container_id)
            ).one()
            try:
                ContainerTypeEnum(container_row.base_type)
            except ValueError as e:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} is not a container."
                ) from e
            if container_row.base_type in [
                ContainerTypeEnum.stack,
                ContainerTypeEnum.queue,
                ContainerTypeEnum.slot,
            ]:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} does not support random access, use `.push` instead."
                )
            container = container_row.to_data_model()
            if container.base_type in [
                ContainerTypeEnum.row,
                ContainerTypeEnum.grid,
                ContainerTypeEnum.voxel_grid,
            ]:
                container[key] = child
                self.update_resource(
                    container, update_descendants=True, parent_session=session
                )
                session.commit()
                session.refresh(container_row)
                return container_row.to_data_model()
            if (
                container.capacity
                and container.quantity >= container.capacity
                and key not in container.children
            ):
                raise ValueError(
                    f"Cannot add child '{child.resource_name}' to container '{container.resource_name}' because it is full."
                )
            self.add_child(
                parent_id=container_id, key=key, child=child, parent_session=session
            )
            session.commit()
            session.refresh(container_row)
            return container_row.to_data_model()

    def remove_child(self, container_id: str, key: Any) -> Union[Collection, Container]:
        """Remove the child of a container at a particular key/location.

        Args:
            container_id (str): The id of the collection resource to update.
            key (str): The key of the child to remove.

        Returns:
            Union[Container, Collection]: The updated container or collection resource.
        """
        with self.get_session() as session:
            container_row = session.exec(
                select(ResourceTable).filter_by(resource_id=container_id)
            ).one()
            try:
                ContainerTypeEnum(container_row.base_type)
            except ValueError as e:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} is not a container."
                ) from e
            if container_row.base_type in [
                ContainerTypeEnum.stack,
                ContainerTypeEnum.queue,
                ContainerTypeEnum.slot,
            ]:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} does not support random access, use `.pop` instead."
                )
            container = container_row.to_data_model()
            child = container.get_child(key)
            if child is None:
                raise (KeyError("Key not found in children"))
            child_row = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=getattr(child, "resource_id", None)
                )
            ).one()
            child_row.parent_id = None
            child_row.key = None
            session.merge(child_row)
            session.commit()
            session.refresh(container_row)

            container_row.quantity = len(container_row.children_list)
            session.merge(container_row)
            session.commit()
            session.refresh(container_row)
            return container_row.to_data_model()

    def set_capacity(
        self, resource_id: str, capacity: Union[int, float]
    ) -> ResourceDataModels:
        """Change the capacity of a resource."""
        with self.get_session() as session:
            resource_row = session.exec(
                select(ResourceTable).filter_by(resource_id=resource_id)
            ).one()
            resource = resource_row.to_data_model()
            if resource.base_type in [
                ResourceTypeEnum.resource,
                ResourceTypeEnum.asset,
            ]:
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no capacity attribute."
                )
            if capacity < resource.quantity:
                raise ValueError(
                    f"Cannot set capacity of resource '{resource.resource_name}' to {capacity} because it currently contains {resource.quantity}."
                )
            if resource.capacity == capacity:
                self.logger.info(
                    f"Capacity of container '{resource.resource_name}' is already set to {capacity}. No action taken."
                )
                return resource_row.to_data_model()
            resource_row.capacity = capacity
            session.merge(resource_row)
            session.commit()
            return resource_row.to_data_model()

    def remove_capacity_limit(self, resource_id: str) -> ResourceDataModels:
        """Remove the capacity limit of a resource."""
        with self.get_session() as session:
            resource_row = session.exec(
                select(ResourceTable).filter_by(resource_id=resource_id)
            ).one()
            resource = resource_row.to_data_model()
            if resource.base_type in [
                ResourceTypeEnum.resource,
                ResourceTypeEnum.asset,
            ]:
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no capacity attribute."
                )
            if resource.capacity is None:
                self.logger.info(
                    f"Container '{resource.resource_name}' has no capacity limit set. No action taken."
                )
                return resource_row.to_data_model()
            resource_row.capacity = None
            session.merge(resource_row)
            session.commit()
            return resource_row.to_data_model()

    def set_quantity(
        self, resource_id: str, quantity: Union[int, float]
    ) -> ResourceDataModels:
        """Change the quantity of a consumable resource."""
        with self.get_session() as session:
            resource_row = session.exec(
                select(ResourceTable).filter_by(resource_id=resource_id)
            ).one()
            resource = resource_row.to_data_model()
            if resource.base_type in [
                ResourceTypeEnum.resource,
                ResourceTypeEnum.asset,
            ]:
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no quantity attribute."
                )
            if resource.capacity and quantity > resource.capacity:
                raise ValueError(
                    f"Cannot set quantity of consumable '{resource.resource_name}' to {quantity} because it exceeds the capacity of {resource.capacity}."
                )
            try:
                # Try to get the property descriptor
                quantity_descriptor = getattr(type(resource), "quantity", None)
                if (
                    quantity_descriptor
                    and isinstance(quantity_descriptor, property)
                    and quantity_descriptor.fset is None
                ):
                    raise ValueError(
                        f"Resource '{resource.resource_name}' with type {resource.base_type} has a read-only quantity attribute."
                    )
            except AttributeError:
                pass

            try:
                resource.quantity = quantity  # * Check that the quantity attribute is not read-only (this is important, because ResourceTable doesn't validate this, whereas the ResourceDataModels do)
                resource_row.quantity = quantity
            except AttributeError as e:
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has a read-only quantity attribute."
                ) from e
            session.merge(resource_row)
            session.commit()
            return resource_row.to_data_model()

    def empty(self, resource_id: str) -> ResourceDataModels:
        """Empty the contents of a container or consumable resource."""
        with self.get_session() as session:
            resource_row = session.exec(
                select(ResourceTable).filter_by(resource_id=resource_id)
            ).one()
            resource = resource_row.to_data_model()
            if resource.base_type in ContainerTypeEnum:
                for child in resource.children.values():
                    self.remove_resource(child.resource_id, parent_session=session)
            elif resource.base_type in ConsumableTypeEnum:
                resource_row.quantity = 0
            session.commit()
            session.refresh(resource_row)
            return resource_row.to_data_model()

    def fill(self, resource_id: str) -> ResourceDataModels:
        """Fill a consumable resource to capacity."""
        with self.get_session() as session:
            resource_row = session.exec(
                select(ResourceTable).filter_by(resource_id=resource_id)
            ).one()
            resource = resource_row.to_data_model()
            if resource.base_type not in ConsumableTypeEnum:
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} is not a consumable."
                )
            if not resource.capacity:
                raise ValueError(
                    f"Resource '{resource.resource_name}' has no capacity limit set, please set a capacity or use set_quantity."
                )
            resource_row.quantity = resource.capacity
            session.merge(resource_row)
            session.commit()
            return resource_row.to_data_model()

    def init_custom_resource(
        self,
        input_definition: ResourceDefinitions,
        custom_definition: ResourceDefinitions,
    ) -> ResourceDataModels:
        """initialize a custom resource"""
        self.logger.warning(
            "THIS METHOD IS DEPRECATED AND WILL BE REMOVED IN A FUTURE VERSION! Use Template methods instead."
        )
        input_dict = input_definition.model_dump(mode="json", exclude_unset=True)
        custom_dict = custom_definition.model_dump(mode="json")
        custom_dict.update(**input_dict)
        custom_dict["base_type"] = custom_definition.base_type
        resource = Resource.discriminate(custom_dict)
        for attribute in custom_definition.custom_attributes:
            if attribute.default_value:
                resource.attributes[attribute.attribute_name] = attribute.default_value
            if (
                input_definition.model_extra
                and attribute.attribute_name in input_definition.model_extra
            ):
                resource.attributes[attribute.attribute_name] = getattr(
                    input_definition, attribute.attribute_name
                )
            elif not attribute.optional:
                raise (
                    ValueError(
                        f"Missing necessary custom attribute: {attribute.attribute_name}"
                    )
                )
        if custom_definition.fill:
            keys = resource.get_all_keys()
            for key in keys:
                child_resource = Resource.discriminate(
                    custom_definition.default_child_template.model_dump(mode="json")
                )
                if custom_definition.default_child_template.resource_name_prefix:
                    child_resource.resource_name = (
                        custom_definition.default_child_template.resource_name_prefix
                        + str(key)
                    )
                resource.set_child(key, child_resource)
        if custom_definition.default_children:
            for key in custom_definition.default_children:
                resource.set_child(
                    key,
                    Resource.discriminate(
                        custom_definition.default_children[key].model_dump(mode="json")
                    ),
                )
        resource = self.add_resource(resource)
        return self.get_resource(resource.resource_id)

    def create_template(
        self,
        resource: ResourceDataModels,
        template_name: str,
        description: str = "",
        required_overrides: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        version: str = "1.0.0",
        parent_session: Optional[Session] = None,
    ) -> ResourceDataModels:
        """
        Create a template from a resource.

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
        """
        try:
            with self.get_session(parent_session) as session:
                # Check if template already exists
                existing_template = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name
                    )
                ).first()

                if existing_template:
                    session.delete(existing_template)
                    session.flush()

                resource_data = resource.model_dump(
                    exclude={"resource_id", "created_at", "updated_at"}
                )
                template_data = {
                    **resource_data,
                    "template_name": template_name,
                    "description": description,
                    "required_overrides": required_overrides or [],
                    "tags": tags or [],
                    "created_by": created_by,
                    "version": version,
                    "default_values": resource_data,
                }

                # Create new template
                template_row = ResourceTemplateTable(**template_data)
                session.add(template_row)

                action = "Replaced" if existing_template else "Created"
                self.logger.info(f"{action} template '{template_name}'")

                session.commit()
                session.refresh(template_row)

                return template_row.to_data_model()

        except Exception as e:
            self.logger.error(
                f"Error creating/updating template: \n{traceback.format_exc()}"
            )
            raise e

    def get_template(
        self,
        template_name: str,
        parent_session: Optional[Session] = None,
    ) -> Optional[ResourceDataModels]:
        """
        Get a template by name, returned as a resource.

        Args:
            template_name (str): Name of the template to retrieve.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.
        """
        try:
            with self.get_session(parent_session) as session:
                template_row = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name.lower()
                    )
                ).first()

                if template_row:
                    return template_row.to_data_model()
                return None

        except Exception as e:
            self.logger.error(f"Error getting template: \n{traceback.format_exc()}")
            raise e

    def update_template(
        self,
        template_name: str,
        updates: dict[str, Any],
        parent_session: Optional[Session] = None,
    ) -> ResourceDataModels:
        """
        Update an existing template.

        Args:
            template_name (str): Name of the template to update.
            updates (dict): Dictionary of fields to update.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            ResourceDataModels: The updated template resource.
        """
        try:
            with self.get_session(parent_session) as session:
                template_row = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name.lower()
                    )
                ).one()

                # Update the template row with new values
                for key, value in updates.items():
                    if hasattr(template_row, key):
                        setattr(template_row, key, value)
                    else:
                        self.logger.warning(f"Unknown field '{key}' in template update")

                # If any resource fields were updated, update default_values too
                resource_fields = {
                    "resource_name",
                    "base_type",
                    "resource_class",
                    "capacity",
                    "rows",
                    "columns",
                    "layers",
                    "quantity",
                    "attributes",
                }
                updated_resource_fields = {
                    k: v for k, v in updates.items() if k in resource_fields
                }
                if updated_resource_fields:
                    current_defaults = template_row.default_values.copy()
                    current_defaults.update(updated_resource_fields)
                    template_row.default_values = current_defaults

                session.commit()
                session.refresh(template_row)

                self.logger.info(f"Updated template '{template_name}'")
                return template_row.to_data_model()

        except Exception as e:
            self.logger.error(f"Error updating template: \n{traceback.format_exc()}")
            raise e

    def delete_template(
        self,
        template_name: str,
        parent_session: Optional[Session] = None,
    ) -> bool:
        """
        Delete a template from the database.

        Args:
            template_name (str): Name of the template to delete.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            bool: True if template was deleted, False if not found.
        """
        try:
            with self.get_session(parent_session) as session:
                template_row = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name.lower()
                    )
                ).first()

                if not template_row:
                    self.logger.warning(
                        f"Template '{template_name}' not found for deletion"
                    )
                    return False

                session.delete(template_row)
                session.commit()

                self.logger.info(f"Deleted template '{template_name}'")
                return True

        except Exception as e:
            self.logger.error(f"Error deleting template: \n{traceback.format_exc()}")
            raise e

    def list_templates(
        self,
        base_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        parent_session: Optional[Session] = None,
    ) -> list[ResourceDataModels]:
        """
        List templates with optional filtering, returned as resources.

        Args:
            base_type (Optional[str]): Filter by base resource type.
            tags (Optional[list[str]]): Filter by templates that have any of these tags.
            created_by (Optional[str]): Filter by creator.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            list[ResourceDataModels]: List of template resources.
        """
        try:
            with self.get_session(parent_session) as session:
                statement = select(ResourceTemplateTable)

                # Apply simple filters first
                if base_type:
                    statement = statement.where(
                        ResourceTemplateTable.base_type == base_type
                    )
                if created_by:
                    statement = statement.where(
                        ResourceTemplateTable.created_by == created_by
                    )

                # Get all matching templates first
                template_rows = session.exec(statement).all()

                if tags:
                    filtered_rows = []
                    for row in template_rows:
                        row_tags = row.tags or []
                        # Check if any of the requested tags are in the template's tags
                        if any(tag in row_tags for tag in tags):
                            filtered_rows.append(row)
                    template_rows = filtered_rows

                return [row.to_data_model() for row in template_rows]

        except Exception as e:
            self.logger.error(f"Error listing templates: \n{traceback.format_exc()}")
            raise e

    def _check_template_nested_field(self, data: dict, field_path: str) -> bool:
        """Check if a nested field exists in the data using dot notation."""
        try:
            parts = field_path.split(".")
            current = data
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]
            return True
        except (KeyError, TypeError, AttributeError):
            return False

    def _validate_template_required_fields(
        self, template_row: ResourceTemplateTable, resource_data: dict
    ) -> None:
        """Validate that all required fields are present in the resource data."""
        missing_required = []
        for field in template_row.required_overrides:
            if not self._check_template_nested_field(resource_data, field):
                missing_required.append(field)

        if missing_required:
            raise ValueError(f"Missing required fields: {missing_required}")

    def create_resource_from_template(
        self,
        template_name: str,
        resource_name: str,
        overrides: Optional[dict[str, Any]] = None,
        add_to_database: bool = True,
        parent_session: Optional[Session] = None,
    ) -> ResourceDataModels:
        """
        Create a resource from a template and add it to the resource table.

        Args:
            template_name (str): Name of the template to use.
            resource_name (str): Name for the new resource.
            overrides (Optional[dict]): Values to override template defaults.
            add_to_database (bool): Whether to add the resource to the resource table.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            ResourceDataModels: The created resource (stored in resource table).
        """
        try:
            with self.get_session(parent_session) as session:
                # Get the template from the template table
                template_row = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name.lower()
                    )
                ).first()

                if not template_row:
                    available_templates = [
                        row.template_name
                        for row in session.exec(select(ResourceTemplateTable)).all()
                    ]
                    raise ValueError(
                        f"Template '{template_name}' not found. Available: {available_templates}"
                    )

                # Prepare resource data
                overrides = overrides or {}
                resource_data = template_row.default_values.copy()
                resource_data.update(overrides)
                resource_data["resource_name"] = resource_name
                resource_data["template_name"] = template_row.template_name.lower()
                # Clean up template-specific fields
                resource_data.pop("resource_id", None)
                resource_data.pop("created_at", None)
                resource_data.pop("updated_at", None)

                # Validate required fields
                self._validate_template_required_fields(template_row, resource_data)

                # Create the resource
                if template_row.base_type not in RESOURCE_TYPE_MAP:
                    raise ValueError(f"Unknown base type: {template_row.base_type}")

                resource_model_class = RESOURCE_TYPE_MAP[template_row.base_type][
                    "model"
                ]
                resource = resource_model_class.model_validate(resource_data)

                # Add to database if requested
                if add_to_database:
                    self.logger.info(
                        f"Adding resource '{resource_name}' to resource table..."
                    )
                    resource = self.add_resource(resource, parent_session=session)
                    self.logger.info(
                        f"Resource '{resource_name}' stored in resource table with ID: {resource.resource_id}"
                    )
                else:
                    self.logger.info(
                        f"Created resource '{resource_name}' from template (not added to database)"
                    )

                self.logger.info(
                    f"Created resource '{resource_name}' from template '{template_name}'"
                )
                return resource

        except Exception as e:
            self.logger.error(
                f"Error creating resource from template: \n{traceback.format_exc()}"
            )
            raise e

    def get_template_info(
        self,
        template_name: str,
        parent_session: Optional[Session] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get detailed template metadata (template-specific fields).

        Args:
            template_name (str): Name of the template.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            Optional[dict]: Template metadata if found, None otherwise.
        """
        try:
            with self.get_session(parent_session) as session:
                template_row = session.exec(
                    select(ResourceTemplateTable).where(
                        ResourceTemplateTable.template_name == template_name.lower()
                    )
                ).first()

                if not template_row:
                    return None

                return {
                    "template_name": template_row.template_name,
                    "description": template_row.description,
                    "required_overrides": template_row.required_overrides,
                    "tags": template_row.tags,
                    "created_by": template_row.created_by,
                    "version": template_row.version,
                    "default_values": template_row.default_values,
                    "created_at": template_row.created_at,
                    "updated_at": template_row.updated_at,
                }

        except Exception as e:
            self.logger.error(
                f"Error getting template info: \n{traceback.format_exc()}"
            )
            raise e

    def get_templates_by_category(
        self,
        parent_session: Optional[Session] = None,
    ) -> dict[str, list[str]]:
        """
        Get templates organized by base_type category.

        Args:
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            dict[str, list[str]]: Dictionary mapping base_type to template names.
        """
        templates = self.list_templates(parent_session=parent_session)
        categories = {}

        for template in templates:
            category = template.base_type.value
            if category not in categories:
                categories[category] = []
            categories[category].append(template.resource_name)

        return categories

    def get_templates_by_tags(
        self,
        tags: list[str],
        parent_session: Optional[Session] = None,
    ) -> list[str]:
        """
        Get template names that have any of the specified tags.

        Args:
            tags (list[str]): Tags to search for.
            parent_session (Optional[Session]): Optional parent session.

        Returns:
            list[str]: List of template names that match any of the tags.
        """
        try:
            with self.get_session(parent_session) as session:
                # Get all templates
                template_rows = session.exec(select(ResourceTemplateTable)).all()

                matching_templates = []
                for row in template_rows:
                    row_tags = row.tags or []
                    # Check if any of the requested tags are in the template's tags
                    if any(tag in row_tags for tag in tags):
                        matching_templates.append(row.template_name)

                return matching_templates

        except Exception as e:
            self.logger.error(
                f"Error getting templates by tags: \n{traceback.format_exc()}"
            )
            raise e

    def _cleanup_expired_locks(self, session: Session) -> None:
        """Clean up expired locks."""
        try:
            expired_resources = session.exec(
                select(ResourceTable).where(
                    and_(
                        ResourceTable.locked_until.is_not(None),
                        ResourceTable.locked_until <= datetime.now(timezone.utc),
                    )
                )
            ).all()

            for resource in expired_resources:
                resource.locked_until = None
                resource.locked_by = None
                session.merge(resource)

            if expired_resources:
                session.commit()
                self.logger.info(f"Cleaned up {len(expired_resources)} expired locks")

        except Exception as e:
            self.logger.error(f"Error cleaning up expired locks: {e}")

    def _check_resource_lock(
        self,
        resource_id: str,
        client_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> None:
        """
        Check if a resource is locked before modification.
        Raises ValueError if locked by another client.
        """
        is_locked, locked_by = self.is_locked(resource_id, session)
        if is_locked and (not client_id or locked_by != client_id):
            return {"resource_id": resource_id, "locked_by": locked_by}
        if is_locked and client_id == locked_by:
            return {"resource_id": resource_id, "locked_by": client_id}
        if not is_locked:
            return {"resource_id": resource_id, "locked_by": None}
        return None

    def acquire_lock(
        self,
        resource: Union[str, ResourceDataModels],
        lock_duration: float = 300.0,  # 5 minutes default
        client_id: Optional[str] = None,
        parent_session: Optional[Session] = None,
    ) -> Optional[ResourceDataModels]:
        """
        Acquire a lock on a resource.

        Args:
            resource: Resource object or resource ID
            lock_duration: Lock duration in seconds
            client_id: Identifier for the client acquiring the lock
            parent_session: Optional parent session

        Returns:
            Optional[ResourceDataModels]: if lock was acquired, None if already locked
        """

        resource_id = resource if isinstance(resource, str) else resource.resource_id
        client_id = client_id or new_ulid_str()

        try:
            with self.get_session(parent_session) as session:
                # First, clean up expired locks
                self._cleanup_expired_locks(session)

                # Try to acquire the lock
                resource_row = session.exec(
                    select(ResourceTable).where(
                        ResourceTable.resource_id == resource_id
                    )
                ).one()

                # Check if already locked by someone else
                if (
                    resource_row.locked_until
                    and resource_row.locked_until > datetime.now(timezone.utc)
                    and resource_row.locked_by != client_id
                ):
                    return None

                # Acquire or renew the lock
                resource_row.locked_until = datetime.now(timezone.utc) + timedelta(
                    seconds=lock_duration
                )
                resource_row.locked_by = client_id
                session.merge(resource_row)
                session.commit()
                session.refresh(resource_row)

                self.logger.info(
                    f"Lock acquired on resource {resource_id} by {client_id}"
                )
                return resource_row.to_data_model()

        except Exception as e:
            self.logger.error(f"Error acquiring lock: {e}")
            return None

    def release_lock(
        self,
        resource: Union[str, ResourceDataModels],
        client_id: Optional[str] = None,
        parent_session: Optional[Session] = None,
    ) -> Optional[ResourceDataModels]:
        """
        Release a lock on a resource.

        Args:
            resource: Resource object or resource ID
            client_id: Identifier for the client releasing the lock
            parent_session: Optional parent session

        Returns:
            Optional[ResourceDataModels]: Resource data model if lock was released, None if not locked by this client
        """
        resource_id = resource if isinstance(resource, str) else resource.resource_id

        try:
            with self.get_session(parent_session) as session:
                resource_row = session.exec(
                    select(ResourceTable).where(
                        ResourceTable.resource_id == resource_id
                    )
                ).one()

                # Check if locked by this client or lock expired
                if (
                    resource_row.locked_by  # If there's a lock
                    and client_id
                    != resource_row.locked_by  # And client doesn't match (including None case)
                ):
                    self.logger.warning(
                        f"Cannot release lock on {resource_id}: not owned by {client_id}"
                    )
                    return None

                # Release the lock
                resource_row.locked_until = None
                resource_row.locked_by = None
                session.merge(resource_row)
                session.commit()
                session.refresh(resource_row)
                self.logger.info(f"Lock released on resource {resource_id}")
                return resource_row.to_data_model()

        except Exception as e:
            self.logger.error(f"Error releasing lock: {e}")
            return None

    def is_locked(
        self,
        resource: Union[str, ResourceDataModels],
        parent_session: Optional[Session] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a resource is currently locked.

        Args:
            resource: Resource object or resource ID
            parent_session: Optional parent session

        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)
        """
        resource_id = resource if isinstance(resource, str) else resource.resource_id

        try:
            with self.get_session(parent_session) as session:
                resource_row = session.exec(
                    select(ResourceTable).where(
                        ResourceTable.resource_id == resource_id
                    )
                ).one()

                self._cleanup_expired_locks(session)

                session.refresh(resource_row)

                if (
                    resource_row.locked_until
                    and resource_row.locked_until > datetime.now(timezone.utc)
                ):
                    return True, resource_row.locked_by
                return False, None

        except Exception as e:
            self.logger.error(f"Error checking lock status: {e}")
            return False, None
