from sqlalchemy import (
    JSON,
    Column,
)
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Field, Session

from madsci.common.types.resource_types import AssetBase, StackBase, QueueBase


class Asset(AssetBase, table=True):
    """Asset table class"""

    attributes: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title="Attributes",
        description="Custom attributes for the asset.",
    )


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


class Stack(StackBase, table=True):
    """
    Base class for stack resources with methods to push and pop assets.
    """

    attributes: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title="Attributes",
        description="Custom attributes for the stack.",
    )

    def get_contents(self, session: Session):
        """
        Fetch and return assets in the stack, ordered by their index.

        The assets are returned as a list, ordered by their index in ascending order.
        Args:
            session (Session): The database session passed from the interface layer.

        Returns:
            List[Asset]: A list of assets sorted by their index.
        """

        # Return the assets as a list based on the sorted allocations
        if not self.children:
            return []

        return [Asset(**child) for child in self.children]

    def push(self, asset: Asset, session: Session) -> int:
        """
        Push a new asset onto the stack. Assigns the next available index.

        Args:
            asset (Asset): The asset to push onto the stack.
            session (Session): SQLAlchemy session passed from the interface layer.

        Returns:
            int: The new index of the pushed asset.
        """
        # Ensure the children attribute exists
        if not hasattr(self, 'children') or self.children is None:
            self.children = []
            
        if len(self.children) >= self.capacity:
            raise ValueError(f"Stack {self.resource_name} is full. Capacity: {self.capacity}")

        # Update parent and owner for the asset
        asset.parent = self.resource_name

        # Save the asset to the database with updated parent and owner
        session.merge(asset)  # Use merge to insert or update
        session.commit()

        # Serialize the Asset object to a dictionary before storing it
        serialized_asset = asset.dict()

        # Append the serialized asset to the children list
        self.children.append(serialized_asset)

        # Flag the children field as modified and commit the changes
        flag_modified(self, "children")
        session.add(self)
        session.commit()

        return len(self.children)

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
        if not self.children or len(self.children) == 0:
            raise ValueError(f"Stack {self.resource_name} is empty.")

        # Retrieve and remove the last serialized asset from the list
        serialized_asset = self.children.pop()

        # Flag the children field as modified
        flag_modified(self, "children")

        # Commit the updated stack to the database
        session.add(self)
        session.commit()

        # Deserialize the asset back into an Asset object
        if isinstance(serialized_asset, dict):
            asset = Asset(**serialized_asset)
        else:
            raise TypeError(
                f"Unexpected type in children: {type(serialized_asset)}. Expected dict."
            )

        # Only modify the parent 
        asset.parent = None
        # Update the asset in the database
        session.commit()

        return asset

class Queue(QueueBase, table = False): 
    """
    Base class for queue resources with methods to push and pop assets.

    Attributes:
        contents (List[Dict[str, Any]]): List of assets in the queue, stored as JSONB.
    """

    attributes: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title="Attributes",
        description="Custom attributes for the stack.",
    )
    def get_contents(self, session: Session):
        """
        Fetch and return assets in the queue, ordered by their index (FIFO).

        The assets are returned as a list, ordered by their index in ascending order.
        Args:
            session (Session): The database session passed from the interface layer.

        Returns:
            List[Asset]: A list of assets sorted by their index.
        """

        # Return the assets based on the sorted allocations
        # return [session.get(Asset, alloc.asset_id) for alloc in allocations]
        pass

    def push(self, asset: Asset, session: Session) -> int:
        """
        Push a new asset onto the queue.

        Args:
            asset (Any): The asset to push onto the queue.
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            int: The index of the pushed asset.

        Raises:
            ValueError: If the queue is full.
        """
        # Fetch the current contents (sorted by index)
        contents = self.get_contents(session)
        # Check if the capacity is exceeded
        if self.capacity and len(contents) >= self.capacity:
            raise ValueError(f"Queue {self.name} is full. Capacity: {self.capacity}")




        # Update the quantity based on the number of assets in the queue
        self.quantity = len(contents) + 1  # Increase quantity by 1
        self.save(session)


    def pop(self, session: Session) :
        """
        Pop the first asset from the queue (FIFO).

        Args:
            session (Session): SQLAlchemy session to use for saving.

        Returns:
            Any: The popped asset.

        Raises:
            ValueError: If the queue is empty or if the asset is not found.
        """
        # Fetch the current contents (sorted by index)
        contents = self.get_contents(session)  # Get the current queue contents

        if not contents:
            raise ValueError(f"Resource {self.name} is empty.")  # Error raised here

        # Pop the first asset (FIFO)
        first_asset = contents[0]

        # Deallocate the asset from this queue
        first_asset.deallocate(session)

        # Update the quantity after removing the asset
        self.quantity = len(contents) - 1  # Decrease quantity
        self.save(session)

        return {
            "id": first_asset.id,
            "name": first_asset.name,
            "owner_name": first_asset.owner_name,
        }



if __name__ == "__main__":
    # s= Stack(resource_name="",resource_types="",capacity=10,ownership=None)
    # s= StackBase(resource_name="a",resource_type="a",capacity=10,ownership=None)
    s = Stack(resource_name="a", resource_type="a", capacity=10, ownership=None)
