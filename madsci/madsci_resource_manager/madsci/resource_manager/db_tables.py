from typing import List

from sqlalchemy import (
    JSON,
    Column,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.inspection import inspect
from sqlmodel import SQLModel, Field, Session, UniqueConstraint, PrimaryKeyConstraint

from madsci.common.types.resource_types import AssetBase, StackBase, QueueBase, ResourceDefinition


# class AssetBase(SQLModel):
#     """
#     Base class for assets with an ID and a name.

#     Attributes:
#         id (str): Unique identifier for the asset.
#         name (str): Name of the asset.
#         owner_name (str): Module name of the asset.
#     """

#     id: str = SQLField(default_factory=lambda: str(ulid.new()), primary_key=True)
#     name: str = SQLField(default="", nullable=False)
#     owner_name: str = SQLField(default="", nullable=True)
#     unique_resource: bool = SQLField(
#         default=True, nullable=False
#     )  # New flag to determine uniqueness


# class Asset(AssetBase, table=True):
#     """
#     Represents the asset table with relationships to other resources.

#     Attributes:
#         time_created (datetime): Timestamp when the asset is created.
#         time_updated (datetime): Timestamp when the asset is last updated.
#     """

#     time_created: datetime = SQLField(
#         sa_column=Column(DateTime(timezone=True), server_default=func.now())
#     )
#     time_updated: datetime = SQLField(
#         sa_column=Column(
#             DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
#         )
#     )

#     def allocate_to_resource(
#         self, resource_type: str, resource_id: str, index: str, session: Session
#     ):
#         """
#         Allocate this asset to a specific resource.

#         Args:
#             resource_type (str): The type of the resource ('stack', 'queue', etc.).
#             resource_id (str): The ID of the resource.
#             index (int): The index of the asset in the resource (for ordering in lists).
#             session (Session): SQLAlchemy session to use for saving.

#         Raises:
#             ValueError: If the asset is already allocated to a different resource.
#         """
#         # Check if this asset is already allocated
#         existing_allocation = (
#             session.query(AssetAllocation).filter_by(asset_id=self.id).first()
#         )

#         if existing_allocation:
#             # Raise an error if the asset is already allocated to a different resource
#             raise ValueError(
#                 f"Asset {self.name} (ID: {self.id}) is already allocated to resource {existing_allocation.resource_type} "
#                 f"with resource ID {existing_allocation.resource_id}."
#             )

#         # Update the owner_name to match the resource being allocated (optional step)
#         resource = session.get(Asset, resource_id)
#         if resource:
#             self.owner_name = (
#                 resource.owner_name
#             )  # Sync the owner_name with the resource

#         # Create a new allocation for the asset
#         new_allocation = AssetAllocation(
#             asset_id=self.id,
#             resource_type=resource_type,
#             resource_id=resource_id,
#             index=index,
#         )
#         session.add(new_allocation)

#         # Update the asset's timestamp
#         self.time_updated = datetime.now(timezone.utc)

#         # Commit the transaction
#         session.commit()

#     def deallocate(self, session: Session):
#         """
#         Deallocate this asset from its current resource.

#         Args:
#             session (Session): SQLAlchemy session to use for saving.

#         Raises:
#             ValueError: If the asset is not allocated to any resource.
#         """
#         allocation = session.query(AssetAllocation).filter_by(asset_id=self.id).first()

#         if allocation is None:
#             raise ValueError(f"Asset {self.id} is not allocated to any resource.")

#         # Deallocate and set the owner_name to None (indicating the asset is no longer allocated)
#         self.owner_name = None
#         self.time_updated = datetime.now(
#             timezone.utc
#         )  # Set time_updated to current time
#         session.delete(allocation)
#         session.commit()

#     def delete_asset(self, session: Session):
#         """
#         Delete this asset and automatically remove any associated asset allocations.

#         Args:
#             session (Session): The current SQLAlchemy session.
#         """
#         session.delete(self)
#         session.commit()


# class AssetAllocation(SQLModel, table=True):
#     """
#     Table that tracks which asset is allocated to which resource.

#     Attributes:
#         asset_id (str): Foreign key referencing the Asset.
#         resource_type (str): Type of resource (e.g., 'stack', 'queue').
#         resource_id (str): ID of the resource to which the asset is allocated.
#     """

#     asset_id: str = SQLField(foreign_key="asset.id", nullable=False)
#     resource_type: str = SQLField(nullable=False)
#     resource_id: str = SQLField(nullable=False)
#     index: str = SQLField(nullable=False)

#     # Use a composite primary key
#     __table_args__ = (
#         UniqueConstraint(
#             "asset_id",
#             "resource_type",
#             "resource_id",
#             name="uix_asset_resource_allocation",
#         ),
#         PrimaryKeyConstraint("asset_id", "resource_type", "resource_id"),
#     )


# class ResourceContainerBase(AssetBase):
#     """
#     Base class for resource containers with common attributes.

#     Attributes:
#         description (str): Description of the resource container.
#         capacity (Optional[float]): Capacity of the resource container.
#         quantity (float): Current quantity of resources in the container.
#     """

#     description: str = SQLField(default="")
#     capacity: Optional[float] = SQLField(default=None, nullable=True)
#     quantity: float = SQLField(default=0.0)

#     def save(self, session: Session):
#         """
#         Save the resource container to the database.

#         Args:
#             session (Session): SQLAlchemy session to use for saving.
#         """
#         if isinstance(self, Plate):
#             # Handling the Plate as a Collection for database operations
#             collection = (
#                 session.query(Collection)
#                 .filter_by(
#                     name=self.name,
#                     owner_name=self.owner_name,
#                 )
#                 .first()
#             )

#             if not collection:
#                 # Create a new Collection if it doesn't exist
#                 collection = Collection(
#                     id=self.id,
#                     name=self.name,
#                     description=self.description,
#                     capacity=self.capacity,
#                     quantity=self.quantity,
#                     owner_name=self.owner_name,
#                     unique_resource=self.unique_resource,
#                     is_plate=True,
#                 )
#                 session.add(collection)
#             else:
#                 # Update the existing Collection attributes
#                 collection.description = self.description
#                 collection.capacity = self.capacity
#                 collection.quantity = self.quantity
#                 collection.owner_name = self.owner_name

#             session.commit()
#             session.refresh(collection)

#             # Update the corresponding Asset (if it exists)
#             asset = session.get(Asset, collection.id)
#             if asset:
#                 asset.time_updated = datetime.now(timezone.utc)
#                 session.commit()

#             return collection  # Return the updated Collection

#         # Handle normal resources
#         session.add(self)
#         session.commit()

#         # Update the corresponding Asset (if it exists)
#         asset = session.get(Asset, self.id)
#         if asset:
#             asset.time_updated = datetime.now(timezone.utc)
#             session.commit()

#         session.refresh(self)
#         return self  # Return the updated resource

#     def add_resource(self, session: Session) -> "ResourceContainerBase":
#         """
#         Check if a resource with the same name and owner_name exists.
#         If it exists, return the existing resource. Otherwise, create the resource
#         and link it with an Asset.

#         Args:
#             session (Session): SQLAlchemy session to use for database operations.

#         Returns:
#             ResourceContainerBase: The saved or existing resource.
#         """
#         # Handle Plate type as Collection
#         if isinstance(self, Plate):
#             print("Handling Plate as a Collection")

#             # Check if the Plate (treated as Collection) already exists
#             existing_resource = (
#                 session.query(Collection)
#                 .filter_by(name=self.name, owner_name=self.owner_name)
#                 .first()
#             )

#             # If unique_resource is True, check for existing Plate and return or raise an error
#             if self.unique_resource:
#                 if existing_resource:
#                     print(
#                         f"Using existing collection resource: {existing_resource.name}"
#                     )
#                     return self  # Return the Plate object (don't create a duplicate)

#             # If unique_resource is False, allow multiple plates with the same name
#             if not self.unique_resource or not existing_resource:
#                 # Create a new Collection object from the Plate data
#                 collection_resource = Collection(
#                     id=self.id,
#                     name=self.name,
#                     description=self.description,
#                     capacity=self.capacity,
#                     owner_name=self.owner_name,
#                     quantity=self.quantity,
#                     unique_resource=self.unique_resource,
#                     is_plate=True,
#                 )

#                 session.add(collection_resource)
#                 session.commit()
#                 session.refresh(collection_resource)

#                 # Create and link an Asset entry for the resource
#                 asset = Asset(
#                     name=collection_resource.name,
#                     id=collection_resource.id,
#                     owner_name=collection_resource.owner_name,
#                     unique_resource=self.unique_resource,
#                 )
#                 session.add(asset)
#                 session.commit()
#                 session.refresh(asset)

#                 print(f"Added new collection resource: {collection_resource.name}")
#                 return self  # Returning the Plate object itself

#         # Handle normal resources (non-Plate)
#         existing_resource = (
#             session.query(type(self))
#             .filter_by(name=self.name, owner_name=self.owner_name)
#             .first()
#         )

#         # If unique_resource is True, check for existing resource and return or raise an error
#         if self.unique_resource:
#             if existing_resource:
#                 print(f"Using existing resource: {existing_resource.name}")
#                 return existing_resource

#         # If unique_resource is False, allow creating multiple resources with the same name
#         if not self.unique_resource or not existing_resource:
#             # If the resource doesn't exist, create and save a new one
#             session.add(self)
#             session.commit()
#             session.refresh(self)

#             # Automatically create and link an Asset entry for the resource
#             asset = Asset(
#                 name=self.name,
#                 id=self.id,
#                 owner_name=self.owner_name,
#                 unique_resource=self.unique_resource,
#             )
#             session.add(asset)
#             session.commit()
#             session.refresh(asset)

#             print(f"Added new resource: {self.name}")
#             return self
class Asset(AssetBase, table=True):
    """Asset table class"""

    def to_json(self) -> dict:
        """
        Serialize the Asset object into a JSON-compatible dictionary using SQLAlchemy's inspection.

        Returns:
            dict: Serialized dictionary of the Asset object.
        """
        # Use SQLAlchemy's inspection to get the object's field data
        return {column.key: getattr(self, column.key) for column in inspect(self).mapper.column_attrs}
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

        # Remove resource_id from children and flag it as modified
        self.children.pop()
        flag_modified(self, "children")
        # Update the parent of the asset
        last_asset.parent = None
        session.add(last_asset)  # Persist the updated asset

        # Update and save the stack quantity
        self.quantity = len(contents) - 1
        session.add(self)
        session.commit()

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
        flag_modified(self, "children")

        # Update the parent of the asset
        first_asset.parent = None
        session.add(first_asset)  # Persist the updated asset

        # Update and save the queue quantity
        self.quantity = len(contents) - 1
        session.add(self)
        session.commit()

        return first_asset


if __name__ == "__main__":
    # s= Stack(resource_name="",resource_types="",capacity=10,ownership=None)
    # s= StackBase(resource_name="a",resource_type="a",capacity=10,ownership=None)
    s = Stack(resource_name="a", resource_type="a", capacity=10, ownership=None)
