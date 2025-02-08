from typing import List
from copy import deepcopy
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import SQLModel, Field, Session, UniqueConstraint

from madsci_common.madsci.common.types.resource_types import discriminate_default_resources, AssetBase, StackBase, QueueBase, PoolBase, ConsumableBase, CollectionBase, ResourceBase, GridBase, AllocationBase, HistoryBase

class History(HistoryBase, table=True):
    """
    History table for tracking resource changes.
    """

    @classmethod
    def _convert_datetime(cls, obj):
        """
        Recursively convert datetime objects to JSON-serializable strings.

        Args:
            obj (Any): Any object, including nested dicts/lists.

        Returns:
            JSON-serializable version of the object.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to string
        elif isinstance(obj, dict):
            return {k: cls._convert_datetime(v) for k, v in obj.items()}  # Recursively process dict
        elif isinstance(obj, list):
            return [cls._convert_datetime(v) for v in obj]  # Recursively process list
        return obj  # Return unchanged if it's not a datetime

    @classmethod
    def _log_change(
        cls,
        session: Session,
        resource: SQLModel,
        event_type: str,
        removed: bool = False
    ):
        """
        Log a resource change in the history table.

        Args:
            session (Session): SQLAlchemy session.
            resource (SQLModel): The resource instance being logged.
            event_type (str): Type of change (created, updated, deleted).
            removed (bool): Whether the resource is removed.
        """
        resource_data = resource.dict()
        # Recursively ensure all datetime fields are JSON-serializable
        resource_data = cls._convert_datetime(resource_data)

        history_entry = cls(
            resource_id=resource.resource_id,
            resource_type=resource.resource_type,
            resource_name=resource.resource_name,
            event_type=event_type,
            created_at=resource.created_at,
            data=resource_data, 
            last_modified=resource.last_modified,
            removed=removed
        )

        session.add(history_entry)
        session.commit()
class Asset(AssetBase, table=True):
    """Asset table class"""
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        Archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
        
class Allocation(AllocationBase, table=True):
    """
    Table that tracks which resource is allocated to another resource.

    Attributes:
        index (int): Allocation index for ordering within the parent resource.
    """
    # Composite primary key and unique constraint
    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "parent",
            "resource_type",
            name="uix_resource_allocation",
        ),
    )
    
    @staticmethod
    def _allocate_to_resource(
        resource_id: str,resource_name:str, parent: str, resource_type: str, index: int, session: Session
    ):
        """
        Allocate a resource to a parent.

        Args:
            resource_id (str): ID of the resource being allocated.
            parent (str): ID of the parent resource.
            resource_type (str): Type of the resource.
            index (int): Position in the parent resource.
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the resource is already allocated to another parent.
        """
        # Check if this resource is already allocated
        existing_allocation = (
            session.query(Allocation)
            .filter_by(resource_id=resource_id)
            .first()
        )

        if existing_allocation:
            raise ValueError(
                f"Resource {resource_id} is already allocated to parent {existing_allocation.parent} "
                f"with resource type {existing_allocation.resource_type}."
            )

        # Create a new allocation
        new_allocation = Allocation(
            resource_id=resource_id,
            resource_name=resource_name,
            parent=parent,
            resource_type=resource_type,
            index=index,
        )
        session.add(new_allocation)
        session.commit()

    @staticmethod
    def _deallocate(resource_id: str, session: Session):
        """
        Deallocate a resource from its current parent.

        Args:
            resource_id (str): ID of the resource being deallocated.
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the resource is not allocated to any parent.
        """
        # Fetch the allocation
        allocation = session.query(Allocation).filter_by(resource_id=resource_id).first()
        if not allocation:
            raise ValueError(f"Resource {resource_id} is not allocated to any parent.")

        # Delete the allocation
        session.delete(allocation)
        session.commit()

class Consumable(ConsumableBase, table=True):
    """
    Consumable table class inheriting from ConsumableBase.
    Represents all consumables in the database.
    """
    # Fields from ConsumableBase are mapped.
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
class Stack(StackBase, table=True):
    """
    Base class for stack resources with methods to push and pop assets.
    """
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
        
    def _get_contents(self, session: Session) -> List[Asset]:
        """
        Fetch and return assets in the stack, ordered by their index.

        Args:
            session (Session): SQLAlchemy session.

        Returns:
            List[Asset]: List of assets in the stack, ordered by their index.
        """
        allocations = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.asc())
            .all()
        )
        # Fetch assets from the database using the allocation records
        return [session.get(Asset, alloc.resource_id) for alloc in allocations]


    def _push(self, asset: Asset, session: Session) -> int:
        """
        Push a new asset onto the stack. Assigns the next available index.

        Args:
            asset (Asset): The asset to push onto the stack.
            session (Session): SQLAlchemy session passed from the interface layer.

        Returns:
            int: The new index of the pushed asset.
        """
        contents = self._get_contents(session)

        if self.capacity and len(contents) >= self.capacity:
            raise ValueError(f"Stack {self.resource_name} is full. Capacity: {self.capacity}")
        self._archive(session, event_type="push")

        next_index = len(contents) + 1
        asset.parent = self.resource_id
        session.add(asset)  
        Allocation._allocate_to_resource(
            resource_id=asset.resource_id,
            resource_name=asset.resource_name,
            parent=self.resource_id,
            resource_type="Stack",
            index=next_index,
            session=session,
        )

        self.children.append(asset.resource_id)
        flag_modified(self, "children")
        self.quantity = len(contents) + 1
        session.add(self)
        session.commit()

        return next_index

    def _pop(self, session: Session) -> Asset:
        """
        Pop the last asset from the stack.

        Args:
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            Any: The popped asset.

        Raises:
            ValueError: If the stack is empty or if the asset is not found.
        """
        contents = self._get_contents(session)

        if not contents:
            raise ValueError(f"Stack {self.resource_name} is empty.")
        last_asset = contents[-1]
        self._archive(session, event_type="pop")

        Allocation._deallocate(
            resource_id=last_asset.resource_id,
            session=session,
        )

        self.children.pop()
        flag_modified(self, "children")
        self.quantity = len(contents) - 1
        last_asset.parent = None
        session.add(last_asset)  
        session.add(self)  
        session.commit()
        session.refresh(last_asset)
        session.refresh(self)

        return last_asset
class Queue(QueueBase, table = True): 
    """
    Base class for queue resources with methods to push and pop assets.

    Attributes:
        contents (List[Dict[str, Any]]): List of assets in the queue, stored as JSONB.
    """
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
        
    def _get_contents(self, session: Session) -> List[Asset]:
        """
        Fetch and return assets in the queue, ordered by their index (FIFO).

        Args:
            session (Session): SQLAlchemy session.

        Returns:
            List[Asset]: List of assets in the queue, ordered by their index.
        """
        allocations = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.asc())
            .all()
        )

        # Fetch assets from the database using the allocation records
        return [session.get(Asset, alloc.resource_id) for alloc in allocations]

    def _push(self, asset: Asset, session: Session) -> int:
        """
        Add a new asset to the queue. Assigns the next available index.

        Args:
            asset (Asset): The asset to push.
            session (Session): SQLAlchemy session passed from the interface layer.

        Returns:
            int: The new index of the pushed asset.
        """
        contents = self._get_contents(session)
        if self.capacity and len(contents) >= self.capacity:
            raise ValueError(f"Queue {self.resource_name} is full. Capacity: {self.capacity}")
        self._archive(session, event_type="push")

        max_index = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.desc())
            .first()
        )
        next_index = int(max_index.index) + 1 if max_index else 1
        asset.parent = self.resource_id
        session.add(asset) 
        Allocation._allocate_to_resource(
            resource_id=asset.resource_id,
            resource_name=asset.resource_name,
            parent=self.resource_id,
            resource_type="Queue",
            index=next_index,
            session=session,
        )

        self.children.append(asset.resource_id)
        flag_modified(self, "children")
        self.quantity = len(contents) + 1
        session.add(self)
        session.commit()

        return next_index

    def _pop(self, session: Session) -> Asset:
        """
        Remove and return the first asset from the queue (FIFO).

        Args:
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            Asset: The poped asset.

        Raises:
            ValueError: If the queue is empty or if the asset is not found.
        """
        contents = self._get_contents(session)

        if not contents:
            raise ValueError(f"Queue {self.resource_name} is empty.")
        self._archive(session, event_type="pop")

        first_asset = contents[0]
        Allocation._deallocate(
            resource_id=first_asset.resource_id,
            session=session,
        )
        self.children.pop(0)
        flag_modified(self, "children")
        self.quantity = len(contents) - 1
        first_asset.parent = None
        session.add(first_asset) 
        session.add(self)  
        session.commit()
        session.refresh(first_asset)
        session.refresh(self)

        return first_asset

class Pool(PoolBase, table=True):
    """
    Pool resource class with methods to manage its quantity and capacity.
    """
    def __init__(self, **kwargs):
        """
        Custom initialization for Pool.

        Automatically sets the parent ID for children resources during initialization.
        """
        super().__init__(**kwargs)

        for key, resource in self.children.items():
            if isinstance(resource, ResourceBase):
                resource.parent = self.resource_id
                
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
        
    def _increase_quantity(self, amount: float, session: Session) -> None:
        """
        Increase the quantity in the pool.

        Args:
            amount (float): The amount to increase.
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the pool exceeds its capacity.
        """
        #TODO: Children could be used to increase the amount which should reflect to the quantity of the Pool resource
        if self.capacity and self.quantity + amount > self.capacity:
            raise ValueError(
                f"Pool {self.resource_name} exceeds its capacity. Capacity: {self.capacity}"
            )
        self._archive(session, event_type="increase_quantity")

        self.quantity += amount
        session.add(self)
        session.commit()

    def _decrease_quantity(self, amount: float, session: Session) -> None:
        """
        Decrease the quantity in the pool.

        Args:
            amount (float): The amount to decrease.
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the quantity falls below zero.
        """
        if self.quantity - amount < 0:
            raise ValueError(f"Pool {self.resource_name} cannot have a negative quantity.")
        self._archive(session, event_type="decrease_quantity")

        self.quantity -= amount
        session.add(self)
        session.commit()

    def _fill(self, session: Session) -> None:
        """
        Fill the pool to its maximum capacity.

        Args:
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the capacity is not defined.
        """
        if not self.capacity:
            raise ValueError(f"Pool {self.resource_name} does not have a defined capacity.")
        self._archive(session, event_type="fill")

        self.quantity = self.capacity
        session.add(self)
        session.commit()

    def _empty(self, session: Session) -> None:
        """
        Empty the pool by setting its quantity to zero.

        Args:
            session (Session): SQLAlchemy session for database operations.
        """
        self._archive(session, event_type="empty")
        self.quantity = 0
        session.add(self)
        session.commit()
        
class Collection(CollectionBase, table=True):
    """
    Collection type for managing collections of resources.

    This class represents a Collection resource, which can store resources
    as its children, accessed by unique keys (e.g., "A1", "B1").
    """

    def __init__(self, **kwargs):
        """
        Custom initialization for Collection.

        Automatically sets the parent ID for children resources during initialization.
        """
        super().__init__(**kwargs)

        for key, resource in self.children.items():
            if isinstance(resource, ResourceBase):
                resource.parent = self.resource_id
                
    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()
        
    def _add_child(self, key: str, resource: ResourceBase, session: Session) -> None:
        """
        Add a resource to the Collection.

        Args:
            key (str): The unique key for the resource (e.g., "A1").
            resource: The resource to add.
            session (Session): The database session for persisting changes.
        """
        self._archive(session, event_type="add_child")
        resource = session.merge(resource)
        resource.parent = self.resource_id
        session.add(resource)
        self.children[key] = resource.dict()
        self.quantity=len(self.children)
        flag_modified(self, "children")
        session.add(self)
        session.commit()

    def _remove_child(self, key: str, session: Session):
        """
        Remove a resource from the Collection.

        Args:
            key (str): The unique key of the resource to remove.
            session (Session): The database session for persisting changes.

        Returns:
            resource: The removed  resource.
        """
        if key not in self.children:
            raise KeyError(f"Key '{key}' does not exist in the Collection.")
        self._archive(session, event_type="remove_child")
        resource = self.children.pop(key)
        flag_modified(self, "children")
        self.quantity=len(self.children)
        resource.parent = None
        session.add(resource)
        session.add(self)
        session.commit()

        return resource        
class Grid(GridBase, table=True):
    """
    Grid class that can hold other resource types as children.
    """

    def __init__(self, **data):
        """
        Custom initialization to handle setting parent IDs for children resources.
        """
        children = data.pop("children", {})
        super().__init__(**data)

        for key, resource in children.items():
            resource.parent = self.resource_id
        self.children = children

    def _archive(self, session: Session, event_type: str = "updated"):
        """
        archive or update the Stack resource and log the change.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type=event_type)
        session.add(self)
        session.commit()

    def _delete(self, session: Session):
        """
        Move the resource to the history table instead of actual deletion.

        Args:
            session (Session): SQLAlchemy session.
        """
        self.last_modified = datetime.utcnow()
        History._log_change(session, self, event_type="deleted", removed=True)
        session.delete(self)
        session.commit()

    def _add_child(self, key: str, resource: ResourceBase, session: Session) -> None:
        """
        Add a resource to the Grid's children.

        Args:
            key (str): The key to identify the resource (e.g., "A1").
            resource (ResourceBase): The resource to add as a child.
            session (Session): The database session to persist changes.

        Raises:
            ValueError: If the key already exists in the children.
        """
        if key in self.children:
            raise ValueError(f"Key '{key}' already exists in Grid {self.resource_name}.")
        self._archive(session, event_type="add_child")

        resource.parent = self.resource_id
        session.add(resource)
        self.children[key] = resource
        flag_modified(self, "children")
        session.add(self)
        session.commit()

    def _remove_child(self, key: str, session: Session) -> ResourceBase:
        """
        Remove a resource from the Grid's children.

        Args:
            key (str): The key of the resource to remove.
            session (Session): The database session to persist changes.

        Returns:
            ResourceBase: The removed resource.

        Raises:
            KeyError: If the key does not exist in the children.
        """
        if key not in self.children:
            raise KeyError(f"Key '{key}' not found in Grid {self.resource_name}.")
        self._archive(session, event_type="remove_child")

        resource = self.children.pop(key)
        flag_modified(self, "children")
        resource.parent = None
        session.add(resource)
        session.add(self)
        session.commit()

        return resource

    def _update_child(self, key: str, session: Session, **kwargs) -> None:
        """
        Update attributes of a child resource.

        Args:
            key (str): The key of the child resource to update.
            session (Session): The database session to persist changes.
            kwargs: The attributes to update on the child resource.

        Raises:
            KeyError: If the key does not exist in the children.
        """
        if key not in self.children:
            raise KeyError(f"Key '{key}' not found in Grid {self.resource_name}.")
        self._archive(session, event_type="update_child")

        resource = self.children[key]
        for attr, value in kwargs.items():
            if hasattr(resource, attr):
                setattr(resource, attr, value)

        session.add(resource)
        session.commit()
    
 
# Define a mapping of resource types to DB table classes
DB_RESOURCE_MAP = {
    "stack": Stack,
    "queue": Queue,
    "pool": Pool,
    "collection": Collection,
    "asset": Asset,
    "consumable": Consumable,
}

def map_resource_type(resource_data: dict):
    """
    Map a resource type to its corresponding DB table class using
    `discriminate_default_resources` to infer the resource type.

    Args:
        resource_data (dict): The resource data dictionary.

    Returns:
        type: The corresponding DB table class.
    """
    # Infer the resource type using discriminate_default_resources
    inferred_type = discriminate_default_resources(resource_data)
    # Use RESOURCE_DEFINITION_MAP to validate the resource type
    if inferred_type == "resource":
        raise ValueError(f"Unknown or unsupported resource type: {inferred_type}")
    
    # Map the inferred type to the DB table class
    db_class = DB_RESOURCE_MAP.get(inferred_type)
    if not db_class:
        raise ValueError(f"No DB table class found for resource type: {inferred_type}")
    
    return db_class
