"""Resources Interface"""

# Suppress SAWarnings
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from madsci.common.types.resource_types import (
    ContainerTypeEnum,
    Pool,
    Resource,
    ResourceBase,
    ResourceBaseTypeEnum,
    ResourceDataModels,
    ResourceTypes,
    Stack,
)
from madsci.resource_manager.resource_tables import (
    HistoryTable,
    ResourceLinkTable,
    ResourceTable,
)
from madsci.resource_manager.serialization_utils import deserialize_resource
from sqlalchemy import true
from sqlalchemy.exc import MultipleResultsFound
from sqlmodel import Session, SQLModel, create_engine, select

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
        database_url: str,
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
                self.engine = create_engine(database_url)
                self.session = Session(self.engine)
                SQLModel.metadata.create_all(self.engine)
                logger.info(f"Resources Database started on: {database_url}")
                break
            except Exception:
                logger.error(
                    f"Error while creating database: \n{traceback.print_exc()}"
                )
                time.sleep(5)
                continue
        else:
            logger.error(f"Failed to connect to database after {init_timeout} seconds.")
            raise ConnectionError(
                f"Failed to connect to database after {init_timeout} seconds."
            )

    def add_resource(
        self, resource: ResourceTypes, commit: bool = True
    ) -> ResourceDataModels:
        """
        Add a resource to the database.

        Args:
            resource (ResourceTypes): The resource to add.

        Returns:
            ResourceDataModels: The saved or existing resource data model.
        """
        with self.session as session:
            try:
                resource_row = ResourceTable.from_resource(resource)
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

                resource_row = session.merge(resource_row)
                if hasattr(resource, "children"):
                    children = resource.extract_children()
                    for key, child in children.items():
                        child_result = self.add_resource(resource=child, commit=False)
                        ResourceLinkTable.link_resource(
                            resource_row.resource_id, child_result.resource_id, key
                        )

                if commit:
                    session.commit()
                    session.refresh(resource)

                return resource.to_data_model()
            except Exception as e:
                logger.error(f"Error adding resource: \n{traceback.format_exc()}")
                raise e

    def update_resource(self, resource: ResourceTypes) -> None:
        """
        Update or refresh a resource in the database, including its children.

        Args:
            resource (ResourceBase): The resource to refresh.

        Returns:
            None
        """
        with self.session as session:
            try:
                resource_row = ResourceTable.from_resource(resource)
                resource_row = session.merge(resource_row)
                if hasattr(resource, "children"):
                    children = resource.extract_children()
                    for key, child in children.items():
                        child_result = self.update_resource(
                            resource=child, commit=False
                        )
                        link = ResourceLinkTable(
                            parent=resource_row.resource_id,
                            child=child_result.resource_id,
                            key=key,
                        )
                        session.merge(link)

                session.commit()
                session.refresh(resource)
            except Exception as e:
                logger.error(f"Error updating resource {resource.resource_id}: {e}")
                raise

    def get_resource(
        self,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        owner_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_base_type: Optional[ResourceBaseTypeEnum] = None,
        exact_match: bool = False,
    ) -> Optional[ResourceDataModels]:
        """
        Lookup a resource by field values.

        Returns:
            Optional[ResourceDataModels]: The resource if found, otherwise None.
        """

        with self.session as session:
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
            statement = (
                statement.where(ResourceTable.owner == owner_name)
                if owner_name
                else statement
            )
            statement = (
                statement.where(ResourceTable.resource_type == resource_type)
                if resource_type
                else statement
            )
            statement = (
                statement.where(ResourceTable.resource_base_type == resource_base_type)
                if resource_base_type
                else statement
            )

            if exact_match:
                try:
                    result = session.exec(statement).one_or_none()
                except MultipleResultsFound as e:
                    logger.error(
                        f"Found multiple matching resources, narrow down the search criteria: {e}"
                    )
                    raise e
                if result is None:
                    logger.error("No resource found matching the provided criteria.")
                    raise ValueError(
                        "No resource found matching the provided criteria."
                    )
            else:
                result = session.exec(statement).first()
            if result:
                return result.to_data_model()
            return result

    def get_history(
        self,
        resource_id: str,
        event_type: Optional[str] = None,
        removed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> list[HistoryTable]:
        """
        TODO
        Query the History table with flexible filtering.

        - If only `resource_id` is provided, fetches **all history** for that resource.
        - If additional filters (`event_type`, `removed`, etc.) are given, applies them.

        Args:
            resource_id (str): Required. Fetch history for this resource.
            event_type (Optional[str]): Filter by event type (`created`, `updated`, `deleted`).
            removed (Optional[bool]): Filter by removed status.
            start_date (Optional[datetime]): Start of the date range.
            end_date (Optional[datetime]): End of the date range.
            limit (Optional[int]): Maximum number of records to return (None for all records).

        Returns:
            List[History]: A list of deserialized historical resource objects.
        """
        with self.session as session:
            query = select(HistoryTable).where(HistoryTable.resource_id == resource_id)

            # Apply additional filters if provided
            if event_type:
                query = query.where(HistoryTable.event_type == event_type)
            if removed is not None:
                query = query.where(HistoryTable.removed == removed)
            if start_date:
                query = query.where(HistoryTable.updated_at >= start_date)
            if end_date:
                query = query.where(HistoryTable.updated_at <= end_date)

            query = query.order_by(
                HistoryTable.updated_at.desc()
            )  # Sorting by updated_at

            if limit:
                query = query.limit(limit)

            history_entries = session.exec(query).all()

            # Deserialize the `data` field into ResourceBase objects
            for entry in history_entries:
                entry.data = deserialize_resource(entry.data)

            return history_entries

    def restore_removed_resource(
        self, resource_id: str
    ) -> Optional[ResourceDataModels]:
        """
        TODO
        Restore the latest version of a removed resource.

        Args:
            resource_id (str): The resource ID.

        Returns:
            ResourceDataModels: The restored resource
        """
        with self.session as session:
            resource_history = session.exec(
                select(HistoryTable)
                .where(HistoryTable.resource_id == resource_id)
                .where(HistoryTable.removed == true())
                .order_by(HistoryTable.history_created_at.desc())
            ).first()
            # TODO: Links?

    def remove_resource(self, resource_id: str) -> None:
        """
        TODO
        Remove a resource by moving it to the History table and deleting it from the main table.

        This function:
        - Fetches the resource by `resource_id`
        - Calls `delete()` on the resource to move it to the History table
        - Deletes the resource from the original table

        Args:
            resource_id (str): ID of the resource to remove.

        Raises:
            ValueError: If the resource does not exist.
        """
        with self.session as session:
            # Retrieve the resource
            session.exec(
                select(ResourceTable).where(ResourceTable.resource_id == resource_id)
            ).one()._remove(session)

    def change_pool_quantity(self, pool_id: str, amount: float) -> Pool:
        """
        Increase or decrease the quantity of a pool resource by an amount.

        Args:
            pool_id: The id of the pool resource to update.
            amount (float): The amount to increase (positive) or decrease (negative) the current quantity.
        """
        with self.session as session:
            pool = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=pool_id, base_type=ContainerTypeEnum.pool
                )
            ).one()
            if pool.capacity and pool.quantity + amount > pool.capacity:
                raise ValueError(
                    f"Cannot increase the quantity of pool '{pool.resource_name}' beyond its capacity {pool.capacity}."
                )
            if pool.quantity + amount < 0:
                raise ValueError(
                    f"Cannot decrease the quantity of pool '{pool.resource_name}' below zero."
                )
            pool._archive(session, event_type="change_quantity")
            pool.quantity += amount
            session.merge(pool)
            session.refresh(pool)
            return pool.to_data_model()

    def empty_pool(self, pool_id: str) -> Pool:
        """
        Empty the pool by setting the quantity to zero.

        Args:
            pool (str): The id of the pool resource to empty.
        """
        with self.session as session:
            pool = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=pool_id, base_type=ContainerTypeEnum.pool
                )
            ).one()
            pool._archive(session, event_type="empty")
            pool.quantity = 0
            session.merge(pool)
            session.refresh(pool)
            return pool.to_data_model()

    def fill_pool(self, pool_id: str) -> Pool:
        """
        Fill the pool by setting the quantity to its capacity.

        Args:
            pool (Pool): The id of the pool resource to fill.
        """
        with self.session as session:
            pool = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=pool_id, base_type=ContainerTypeEnum.pool
                )
            ).one()
            pool._archive(session, event_type="empty")
            if pool.capacity is None:
                raise ValueError(
                    f"Cannot fill pool '{pool.resource_name}' without a capacity."
                )
            pool.quantity = pool.capacity
            session.merge(pool)
            session.refresh(pool)
            return pool.to_data_model()

    def push_to_stack(
        self, stack_id: str, child: Union[Resource, ResourceBase, str]
    ) -> Stack:
        """
        Push an asset to the stack. Automatically adds the asset to the database if it's not already there.

        Args:
            stack_id (str): The id of the stack resource to push the resource onto.
            child (Union[Resource, ResourceBase, str]): The resource to push onto the stack (or an ID, if it already exists).
        """
        with self.session as session:
            stack_row = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=stack_id, base_type=ContainerTypeEnum.stack
                )
            ).one()
            stack = stack_row.to_data_model()
            child_id = child if isinstance(child, str) else child.resource_id
            child_row = session.exec(
                select(ResourceTable).filter_by(resource_id=child_id)
            ).one_or_none()
            if not child_row and not isinstance(child, str):
                child = self.add_resource(child, commit=False)
                child_row = ResourceTable.from_data_model(child)
                child_row.refresh()
            else:
                raise ValueError(
                    f"The child resource {child_id} does not exist in the database and couldn't be added."
                )

            if stack_row.capacity and len(stack.children) >= stack_row.capacity:
                raise ValueError(
                    f"Cannot push asset '{child_row.resource_name}' to stack '{stack_row.resource_name}' because it is full."
                )
            ResourceLinkTable.link_resource(
                parent=stack_row,
                child=child_row,
                key=len(stack.children) + 1,
                commit=False,
            )
            session.commit()
            session.refresh(stack)
            return stack.to_data_model()

    def pop_from_stack(self, stack_id: str) -> tuple[ResourceDataModels, Stack]:
        """
        Pop a resource from a stack resource. Returns the popped resource.

        Args:
            stack_id (str): The id of the stack resource to update.

        Returns:
            resource (ResourceDataModels): The popped resource.
            updated_stack (Stack): updated stack resource

        """
        with self.session as session:
            stack_row = session.exec(
                select(ResourceTable).filter_by(
                    resource_id=stack_id, base_type=ContainerTypeEnum.stack
                )
            ).one()
            stack = stack_row.to_data_model()
            if not stack.children:
                raise ValueError(f"Stack '{stack.resource_name}' is empty.")
            child = stack.children[-1]
            child_row = session.exec(
                select(ResourceTable).filter_by(resource_id=child.resource_id)
            ).one()

            ResourceLinkTable.unlink_resource(child=child_row, commit=False)

            session.commit()
            session.refresh()
            return child_row.to_data_model(), stack.to_data_model()

    # TODO: VVVVVVVV

    def push_to_queue(self, queue: Queue, asset: Asset) -> None:
        """
        Push an asset to the queue. Automatically adds the asset to the database if it's not already there.

        Args:
            queue (Queue): The queue resource to push the asset onto.
            asset (Asset): The asset to push onto the queue.
        """
        with self.session as session:
            existing_queue = session.exec(
                select(Queue).filter_by(resource_id=queue.resource_id)
            ).first()

            if not existing_queue:
                raise ValueError(
                    f"Queue '{queue.resource_name, queue.resource_id}' does not exist in the database. Please provide a valid resource."
                )
            queue = existing_queue
            asset = session.merge(asset)
            queue._push(asset, session)
            session.refresh(queue)
            return queue

    def pop_from_queue(self, queue: Queue) -> tuple:
        """
        Pop an asset from a queue resource.

        Args:
            queue (Queue): The queue resource to update.

        Returns:
            Asset: The popped asset.
            updated_queue: updated queue resource
        """
        with self.session as session:
            queue = session.merge(queue)
            asset = queue._pop(session)

            if asset:
                updated_queue = session.exec(
                    select(Queue).filter_by(resource_id=queue.resource_id)
                ).first()
                return asset, updated_queue
            raise ValueError("The queue is empty or the asset does not exist.")

    def increase_plate_well(
        self, plate: Collection, well_id: str, quantity: float
    ) -> None:
        """
        Increase the quantity of liquid in a specific well of a plate.

        Args:
            plate (Collection): The plate resource to update.
            well_id (str): The well ID to increase the quantity for.
            quantity (float): The amount to increase the well quantity by.
        """
        with self.session as session:
            existing_plate = session.exec(
                select(Collection).filter_by(resource_id=plate.resource_id)
            ).first()
            pool = existing_plate.children.get(well_id)

            if not pool:
                raise ValueError(
                    f"No resource found in well '{well_id}' of plate {existing_plate.resource_name}."
                )

            self.change_pool_quantity(pool=pool, amount=quantity)
            session.add(existing_plate)
            session.refresh(existing_plate)
            return existing_plate

    def decrease_plate_well(
        self, plate: Collection, well_id: str, quantity: float
    ) -> None:
        """
        Decrease the quantity of liquid in a specific well of a plate.

        Args:
            plate (Plate): The plate resource to update.
            well_id (str): The well ID to decrease the quantity for.
            quantity (float): The amount to decrease the well quantity by.
        """
        with self.session as session:
            existing_plate = session.exec(
                select(Collection).filter_by(resource_id=plate.resource_id)
            ).first()

            if well_id not in existing_plate.children:
                raise KeyError(
                    f"Well ID '{well_id}' does not exist in existing_plate '{existing_plate.resource_name}'."
                )

            pool = existing_plate.children[well_id]
            if not isinstance(pool, Pool):
                raise TypeError(
                    "Only Pool resources are supported in existing_plate wells."
                )

            self.decrease_pool_quantity(pool=pool, amount=quantity)
            session.add(existing_plate)
            session.refresh(existing_plate)
            return existing_plate

    def update_collection_child(
        self, collection: Collection, key: str, resource: ResourceBase
    ) -> None:
        """
        Update or add a resource in a specific well of a collection using the `add_child` method.

        Args:
            collection (Collection): The collection resource to update.
            collection (str): The well ID to update or add.
            resource (resource): The resource resource to associate with the well.
        """
        with self.session as session:
            collection = session.exec(
                select(Collection).filter_by(resource_id=collection.resource_id)
            ).first()
            resource = self.get_resource(resource_id=resource.resource_id)
            collection._add_child(key=key, resource=resource, session=session)
            session.add(collection)
            session.refresh(collection)
            return collection


if __name__ == "__main__":
    resource_interface = ResourceInterface(
        database_url="postgresql://rpl:rpl@localhost:5432/resources"
    )
    stack = Stack(
        resource_name="stack",
        resource_type="stack",
        capacity=10,
        ownership=None,
    )
    resource_interface.add_resource(stack)
    for _i in range(5):
        asset = Asset(resource_name="Test plate" + str(_i))
        asset = resource_interface.add_resource(asset)
        resource_interface.push_to_stack(stack, asset)
    retrieved_stack = resource_interface.get_resource(
        resource_id=stack.resource_id,
        resource_name=stack.resource_name,
        owner_name=stack.owner,
    )
    for _i in range(2):
        n_asset, retrieved_stack = resource_interface.pop_from_stack(retrieved_stack)

    queue = Queue(
        resource_name="queue",
        resource_type="queue",
        capacity=10,
        ownership=None,
    )
    queue = resource_interface.add_resource(queue)
    for _i in range(5):
        asset = Asset(resource_name="Test plate" + str(_i))
        asset = resource_interface.add_resource(asset)
        resource_interface.push_to_queue(queue, asset)
    retrieved_queue = resource_interface.get_resource(
        resource_id=queue.resource_id,
        resource_name=queue.resource_name,
        owner_name=queue.owner,
    )
    for _i in range(2):
        n_asset, retrieved_queue = resource_interface.pop_from_queue(retrieved_queue)
    resource_interface.push_to_queue(queue, n_asset)

    consumable = Consumable(
        resource_name="Water",
        resource_type="consumable",
        quantity=50.0,
        ownership=None,
        capacity=100,
    )
    # Add the ConsumableBase to the database
    resource_interface.add_resource(consumable)

    # # Create a Pool resource
    pool = Pool(
        resource_name="Vial_1",
        resource_type="pool",
        capacity=500.0,
        children={"Water": consumable},
        # Add the ConsumableBase to children
    )
    pool = resource_interface.add_resource(pool)

    # Example operations on the pool
    pool = resource_interface.change_pool_quantity(pool, 50.0)

    pool = resource_interface.decrease_pool_quantity(pool, 20.0)

    pool = resource_interface.fill_pool(pool)

    pool = resource_interface.empty_pool(pool)
    pool1 = Pool(resource_name="Pool1", resource_type="pool", capacity=100, quantity=50)
    pool1 = resource_interface.add_resource(pool1)
    # Create a Plate resource with initial children
    plate = Collection(
        resource_name="Microplate1",
        resource_type="collection",
        children={"A1": pool},
    )
    resource_interface.add_resource(plate)
    # Increase quantity in a well
    resource_interface.increase_plate_well(plate, "A1", 30)

    # Decrease quantity in a well
    resource_interface.decrease_plate_well(plate, "A1", 20)

    resource_interface.update_collection_child(plate, "A2", pool1)

    start_date = datetime.now(timezone.utc) - timedelta(seconds=6)
    end_date = datetime.now(timezone.utc)

    resource_interface.remove_resource(resource_id=stack.resource_id)
    history_entries = resource_interface.get_history(
        resource_id=stack.resource_id,
    )
    for _entry in history_entries:
        pass
