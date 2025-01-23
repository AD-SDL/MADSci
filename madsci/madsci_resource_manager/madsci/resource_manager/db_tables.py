from typing import List
from copy import deepcopy

from sqlalchemy import (
    JSON,
    Column,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.inspection import inspect
from sqlmodel import SQLModel, Field, Session, UniqueConstraint, PrimaryKeyConstraint

from madsci.common.types.resource_types import discriminate_default_resources, AssetBase, StackBase, QueueBase, PoolBase, ConsumableBase, CollectionBase, ResourceBase, GridBase

class Asset(AssetBase, table=True):
    """Asset table class"""
    pass
class Allocation(SQLModel, table=True):
    """
    Table that tracks which resource is allocated to another resource.

    Attributes:
        index (int): Allocation index for ordering within the parent resource.
    """
    resource_id: str = Field(
        title="Resource ID",
        description="The ID of the resource being allocated.",
        nullable=False,
        primary_key=True,
    )
    resource_name: str = Field(
        title="Resource Name",
        description="The name of the resource being allocated.",
        nullable=True,
    )
    resource_type: str = Field(
        title="Resource Type",
        description="The type of the resource (e.g., 'stack', 'queue').",
        nullable=False,
    )
    parent: str = Field(
        title="Parent Resource",
        description="The ID of the resource under which this resource is allocated.",
        nullable=False,
    )
    index: int = Field(
        title="Allocation Index",
        description="The index position of the resource in the parent resource.",
        nullable=False,
    )
    index: int = Field(
        title="Allocation Index",
        description="The index position of the resource in the parent resource.",
        nullable=False
    )
    

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
    def allocate_to_resource(
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
    def deallocate(resource_id: str, session: Session):
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
    pass

class Stack(StackBase, table=True):
    """
    Base class for stack resources with methods to push and pop assets.
    """

    def get_contents(self, session: Session) -> List[Asset]:
        """
        Fetch and return assets in the stack, ordered by their index.

        Args:
            session (Session): SQLAlchemy session.

        Returns:
            List[Asset]: List of assets in the stack, ordered by their index.
        """
        # Query allocations for this stack and sort by index
        allocations = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.asc())
            .all()
        )

        # Fetch assets from the database using the allocation records
        return [session.get(Asset, alloc.resource_id) for alloc in allocations]


    def push(self, asset: Asset, session: Session) -> int:
        """
        Push a new asset onto the stack. Assigns the next available index.

        Args:
            asset (Asset): The asset to push onto the stack.
            session (Session): SQLAlchemy session passed from the interface layer.

        Returns:
            int: The new index of the pushed asset.
        """
        # Fetch the current contents
        contents = self.get_contents(session)

        # Check capacity
        if self.capacity and len(contents) >= self.capacity:
            raise ValueError(f"Stack {self.resource_name} is full. Capacity: {self.capacity}")

        # Determine the next index
        next_index = len(contents) + 1
        # Update the parent of the asset
        asset.parent = self.resource_id
        session.add(asset)  # Persist the updated asset

        # Allocate the asset to this stack
        Allocation.allocate_to_resource(
            resource_id=asset.resource_id,
            resource_name=asset.resource_name,
            parent=self.resource_id,
            resource_type="Stack",
            index=next_index,
            session=session,
        )

        # Add resource_id to children and flag it as modified
        self.children.append(asset.resource_id)
        flag_modified(self, "children")

        # Update and save the stack quantity
        self.quantity = len(contents) + 1
        session.add(self)
        session.commit()

        return next_index

    def pop(self, session: Session) -> Asset:
        """
        Pop the last asset from the stack.

        Args:
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            Any: The popped asset.

        Raises:
            ValueError: If the stack is empty or if the asset is not found.
        """
        # Fetch the current contents
        contents = self.get_contents(session)

        if not contents:
            raise ValueError(f"Stack {self.resource_name} is empty.")

        # Get the last asset (LIFO)
        last_asset = contents[-1]

        # Deallocate the asset from this stack
        Allocation.deallocate(
            resource_id=last_asset.resource_id,
            session=session,
        )

        # Remove resource_id from children
        self.children.pop()

        # Notify SQLAlchemy that the children field has been modified
        flag_modified(self, "children")

        # Update the stack quantity
        self.quantity = len(contents) - 1

        # Update the parent of the asset
        last_asset.parent = None
        session.add(last_asset)  # Persist the updated asset
        session.add(self)  # Update the stack

        # Commit the transaction
        session.commit()

        # Refresh the queried asset and stack to reload their states
        session.refresh(last_asset)
        session.refresh(self)

        return last_asset
class Queue(QueueBase, table = True): 
    """
    Base class for queue resources with methods to push and pop assets.

    Attributes:
        contents (List[Dict[str, Any]]): List of assets in the queue, stored as JSONB.
    """

    def get_contents(self, session: Session) -> List[Asset]:
        """
        Fetch and return assets in the queue, ordered by their index (FIFO).

        Args:
            session (Session): SQLAlchemy session.

        Returns:
            List[Asset]: List of assets in the queue, ordered by their index.
        """
        # Query allocations for this queue and sort by index
        allocations = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.asc())
            .all()
        )

        # Fetch assets from the database using the allocation records
        return [session.get(Asset, alloc.resource_id) for alloc in allocations]

    def push(self, asset: Asset, session: Session) -> int:
        """
        Add a new asset to the queue. Assigns the next available index.

        Args:
            asset (Asset): The asset to push.
            session (Session): SQLAlchemy session passed from the interface layer.

        Returns:
            int: The new index of the pushed asset.
        """
        # Fetch the current contents
        contents = self.get_contents(session)

        # Check capacity
        if self.capacity and len(contents) >= self.capacity:
            raise ValueError(f"Queue {self.resource_name} is full. Capacity: {self.capacity}")

        # Determine the next available index dynamically
        max_index = (
            session.query(Allocation)
            .filter_by(parent=self.resource_id)
            .order_by(Allocation.index.desc())
            .first()
        )
        next_index = int(max_index.index) + 1 if max_index else 1

        # Update the parent of the asset
        asset.parent = self.resource_id
        session.add(asset)  # Persist the updated asset

        # Allocate the asset to this queue
        Allocation.allocate_to_resource(
            resource_id=asset.resource_id,
            resource_name=asset.resource_name,
            parent=self.resource_id,
            resource_type="Queue",
            index=next_index,
            session=session,
        )

        # Add resource_id to children and flag it as modified
        self.children.append(asset.resource_id)
        flag_modified(self, "children")

        # Update and save the queue quantity
        self.quantity = len(contents) + 1
        session.add(self)
        session.commit()

        return next_index

    def pop(self, session: Session) -> Asset:
        """
        Remove and return the first asset from the queue (FIFO).

        Args:
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            Asset: The poped asset.

        Raises:
            ValueError: If the queue is empty or if the asset is not found.
        """
        # Fetch the current contents
        contents = self.get_contents(session)

        if not contents:
            raise ValueError(f"Queue {self.resource_name} is empty.")

        # Get the first asset (FIFO)
        first_asset = contents[0]

        # Deallocate the asset from this queue
        Allocation.deallocate(
            resource_id=first_asset.resource_id,
            session=session,
        )

        # Remove resource_id from children and flag it as modified
        self.children.pop(0)

        # Notify SQLAlchemy that the children field has been modified
        flag_modified(self, "children")

        self.quantity = len(contents) - 1

        # Update the parent of the asset
        first_asset.parent = None
        session.add(first_asset)  # Persist the updated asset
        session.add(self)  

        # Commit the transaction
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

        # Ensure children have the Pool's resource_id as their parent
        for key, resource in self.children.items():
            if isinstance(resource, ResourceBase):
                resource.parent = self.resource_id

    def increase_quantity(self, amount: float, session: Session) -> None:
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

        self.quantity += amount
        session.add(self)
        session.commit()

    def decrease_quantity(self, amount: float, session: Session) -> None:
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

        self.quantity -= amount
        session.add(self)
        session.commit()

    def fill(self, session: Session) -> None:
        """
        Fill the pool to its maximum capacity.

        Args:
            session (Session): SQLAlchemy session for database operations.

        Raises:
            ValueError: If the capacity is not defined.
        """
        if not self.capacity:
            raise ValueError(f"Pool {self.resource_name} does not have a defined capacity.")

        self.quantity = self.capacity
        session.add(self)
        session.commit()

    def empty(self, session: Session) -> None:
        """
        Empty the pool by setting its quantity to zero.

        Args:
            session (Session): SQLAlchemy session for database operations.
        """
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

        # Ensure children have the Pool's resource_id as their parent
        for key, resource in self.children.items():
            if isinstance(resource, ResourceBase):
                resource.parent = self.resource_id

    def add_child(self, key: str, resource: ResourceBase, session: Session) -> None:
        """
        Add a resource to the Collection.

        Args:
            key (str): The unique key for the resource (e.g., "A1").
            resource: The resource to add.
            session (Session): The database session for persisting changes.
        """
        resource = session.merge(resource)
        # Set the parent of the resource
        resource.parent = self.resource_id
        print(resource)
        session.add(resource)

        # Add the resource to the children dictionary
        self.children[key] = resource.dict()
        self.quantity=len(self.children)
        flag_modified(self, "children")

        # Persist the changes to the Collection
        session.add(self)
        session.commit()

    def remove_child(self, key: str, session: Session):
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

        # Remove the child resource
        resource = self.children.pop(key)
        flag_modified(self, "children")
        self.quantity=len(self.children)

        # Update the parent of the resource to None
        resource.parent = None
        session.add(resource)

        # Persist the changes
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

            # Set parent for each child
            for key, resource in children.items():
                resource.parent = self.resource_id
            self.children = children

        def add_child(self, key: str, resource: ResourceBase, session: Session) -> None:
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

            # Set the parent of the child resource
            resource.parent = self.resource_id
            session.add(resource)

            # Add the child resource to the children dictionary
            self.children[key] = resource
            flag_modified(self, "children")

            # Save changes
            session.add(self)
            session.commit()

        def remove_child(self, key: str, session: Session) -> ResourceBase:
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

            # Get and remove the resource
            resource = self.children.pop(key)
            flag_modified(self, "children")

            # Update the parent of the removed resource
            resource.parent = None
            session.add(resource)

            # Save changes
            session.add(self)
            session.commit()

            return resource

        def update_child(self, key: str, session: Session, **kwargs) -> None:
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

            # Get the child resource
            resource = self.children[key]

            # Update resource attributes
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
              
if __name__ == "__main__":
    # s= Stack(resource_name="",resource_types="",capacity=10,ownership=None)
    # s= StackBase(resource_name="a",resource_type="a",capacity=10,ownership=None)
    s = Stack(resource_name="a", resource_type="pool", capacity=10, ownership=None)
    resource_class = map_resource_type(s)
    print(resource_class)
    
    
