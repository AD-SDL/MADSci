"""Resources Interface"""

# Suppress SAWarnings
import logging
import time
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional, Union

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.resource_types import (
    Collection,
    ConsumableTypeEnum,
    Container,
    ContainerDataModels,
    ContainerTypeEnum,
    Queue,
    ResourceDataModels,
    ResourceTypeEnum,
    Slot,
    Stack,
)
from madsci.resource_manager.resource_tables import (
    ResourceHistoryTable,
    ResourceTable,
    create_session,
)
from sqlalchemy import true
from sqlalchemy.exc import MultipleResultsFound
from sqlmodel import Session, SQLModel, create_engine, func, select

logger = logging.getLogger(__name__)


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
                logger.info("Initialized Resource Interface.")
                break
            except Exception:
                logger.error(
                    f"Error while creating/connecting to database: \n{traceback.print_exc()}"
                )
                time.sleep(5)
                continue
        else:
            logger.error(f"Failed to connect to database after {init_timeout} seconds.")
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
            logger.error(session)
            session.bind = self.engine
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
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
                    logger.info(
                        f"Resource with ID '{resource_row.resource_id}' already exists in the database. No action taken."
                    )
                    return existing_resource.to_data_model()

                session.add(resource_row)
                if add_descendants and getattr(resource, "children", None):
                    children = resource.extract_children()
                    for key, child in children.items():
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
            logger.error(f"Error adding resource: \n{traceback.format_exc()}")
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
            logger.error(f"Error updating resource: \n{traceback.format_exc()}")
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
        resource_type: Optional[str] = None,
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
                statement.where(ResourceTable.resource_type == resource_type)
                if resource_type
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
                    logger.error(
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
                logger.error(
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
            if container_row.base_type in ContainerTypeEnum:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} is not a container."
                )
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
                if isinstance(key, str):
                    key = container.expand_key(key)
                if not container.check_key_bounds(key):
                    raise KeyError(key)
                key = container.flatten_key(key)
            elif (
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

    def remove_child(self, container_id: str, key: str) -> Union[Collection, Container]:
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
            if container_row.base_type in ContainerTypeEnum:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} is not a container."
                )
            if container_row.base_type in [
                ContainerTypeEnum.stack,
                ContainerTypeEnum.queue,
                ContainerTypeEnum.slot,
            ]:
                raise ValueError(
                    f"Resource '{container_row.resource_name}' with type {container_row.base_type} does not support random access, use `.pop` instead."
                )
            container = container_row.to_data_model()
            if container.base_type in [
                ContainerTypeEnum.row,
                ContainerTypeEnum.grid,
                ContainerTypeEnum.voxel_grid,
            ]:
                key = container.flatten_key(key)
            child = container.children[key]
            child_row = session.exec(
                select(ResourceTable).filter_by(resource_id=child.resource_id)
            ).one()
            child_row.parent_id = None
            child_row.key = None
            session.merge(child_row)
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
            if not hasattr(resource, "capacity"):
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no capacity attribute."
                )
            if capacity < resource.quantity:
                raise ValueError(
                    f"Cannot set capacity of resource '{resource.resource_name}' to {capacity} because it currently contains {resource.quantity}."
                )
            if resource.capacity == capacity:
                logger.info(
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
            if not hasattr(resource, "capacity"):
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no capacity attribute."
                )
            if resource.capacity is None:
                logger.info(
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
            if not hasattr(resource, "quantity"):
                raise ValueError(
                    f"Resource '{resource.resource_name}' with type {resource.base_type} has no quantity attribute."
                )
            if resource.capacity and quantity > resource.capacity:
                raise ValueError(
                    f"Cannot set quantity of consumable '{resource.resource_name}' to {quantity} because it exceeds the capacity of {resource.capacity}."
                )
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
