"""Resources Interface"""

import time
from typing import Dict, List, Optional, Type
import warnings

# Suppress SAWarnings
warnings.filterwarnings("ignore")

from sqlalchemy import text
from sqlalchemy.exc import MultipleResultsFound
from sqlmodel import Session, SQLModel, create_engine, select

from madsci.common.types.resource_types import ResourceBase
from db_tables import Stack, Asset, Queue, Pool, Consumable, Collection, Grid


class ResourceInterface():
    """
    Interface for managing various types of resources.

    Attributes:
        engine (sqlalchemy.engine.Engine): SQLAlchemy engine for database connection.
        session (sqlalchemy.orm.Session): SQLAlchemy session for database operations.
    """

    def __init__(
        self,
        database_url: str = "postgresql://rpl:rpl@127.0.0.1:5432/resources",
        init_timeout: float = 10,
    ):
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
                print(f"Resources Database started on: {database_url}")
                break
            except Exception:
                print("Database not ready yet. Retrying...")
                time.sleep(5)
                continue

    def add_resource(self, resource:ResourceBase):
        """
        Add a resource to the database using the add_resource method
        in ResourceContainerBase.

        Args:
            resource (ResourceContainerBase): The resource to add.

        Returns:
            ResourceContainerBase: The saved or existing resource.
        """
        with self.session as session:
            try:
                # Ensure children are properly merged
                if hasattr(resource, "children") and isinstance(resource.children, dict):
                    for key, child in resource.children.items():
                        if isinstance(child, ResourceBase):
                            # Merge the child resource
                            child = session.merge(child)
                            resource.children[key] = child

                resource = session.merge(resource)
                session.commit()
                session.refresh(resource)
                if hasattr(resource, "children") and isinstance(resource.children, dict):
                    resource.children = {
                        key: self.get_resource(resource_id=child.resource_id)
                        if isinstance(child, ResourceBase) else child
                        for key, child in resource.children.items()
                    }

                return resource
            except Exception as e:
                print(f"Error adding resource: {e}")
                raise
                    
    def update_resource(self, resource: ResourceBase):
        """
        Update or refresh a resource in the database, including its children.

        Args:
            resource (ResourceBase): The resource to refresh.

        Returns:
            None
        """
        with self.session as session:
            try:
                resource = session.merge(resource)
                if hasattr(resource, "children") and isinstance(resource.children, dict):
                    for key, child in resource.children.items():
                        if isinstance(child, ResourceBase):
                            child.parent = resource.resource_id
                            session.merge(child)

                session.commit()
                session.refresh(resource)
            except Exception as e:
                print(f"Error refreshing resource {resource.resource_id}: {e}")
                raise
                
    def get_resource(
        self,
        resource_name: Optional[str] = None,
        owner_name: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Optional[SQLModel]:
        """
        Retrieve a resource from the database by its name and owner_name across all resource types.

        Args:
            resource_name (str): The name of the resource to retrieve.
            owner_name (str): The module name associated with the resource.
            resource_id (Optional[str]): The optional ID of the resource (if provided, this will take priority).

        Returns:
            Optional[SQLModel]: The resource if found, otherwise None.
        """
        if not resource_id and not (resource_name or owner_name or resource_type):
            raise ValueError(
                "You must provide at least one of the following: resource_id, resource_name, owner_name, or resource_type."
            )

        # Map resource type names to their respective SQLModel classes
        resource_type_map = {
            "stack": Stack,
            "asset": Asset,
            "queue": Queue,
            "pool": Pool,
            "collection": Collection,
            "consumable": Consumable,
        }

        with self.session as session:
            # If resource_id is provided, prioritize searching by ID
            if resource_id:
                resource_types = (
                    [resource_type]
                    if resource_type and resource_type in resource_type_map
                    else resource_type_map.keys()
                )
                for r_type in resource_types:
                    resource_type = resource_type_map[r_type]
                    resource = session.exec(
                        select(resource_type).where(resource_type.resource_id == resource_id)
                    ).first()
                    if resource:
                        print(f"Resource found by ID: {resource.resource_id} in {r_type}")
                        return resource

                print(f"No resource found with ID '{resource_id}'.")
                return None

            query_conditions = []
            if resource_name:
                query_conditions.append(lambda cls: cls.resource_name == resource_name)
            if owner_name:
                query_conditions.append(lambda cls: cls.owner == owner_name)

            resource_types = (
                [resource_type]
                if resource_type and resource_type in resource_type_map
                else resource_type_map.keys()
            )
            for r_type in resource_types:
                resource_type = resource_type_map[r_type]
                statement = select(resource_type)
                for condition in query_conditions:
                    statement = statement.where(condition(resource_type))
                resource = session.exec(statement).first()
                if resource:
                    print(
                        f"Resource found: {resource.resource_name} in {r_type}."
                    )
                    return resource

            print(
                f"No resource found matching name '{resource_name}', owner '{owner_name}', or type '{resource_type}'."
            )
            return None

    def increase_pool_quantity(self, pool: Pool, amount: float) -> None:
        """
        Increase the quantity of a pool resource.

        Args:
            pool (Pool): The pool resource to update.
            amount (float): The amount to increase.
        """
        with self.session as session:
            existing_pool= session.query(Pool).filter_by(resource_id=pool.resource_id).first()
            existing_pool.increase_quantity(amount, session)
            session.refresh(existing_pool)
            return existing_pool

    def decrease_pool_quantity(self, pool: Pool, amount: float) -> None:
        """
        Decrease the quantity of a pool resource.

        Args:
            pool (Pool): The pool resource to update.
            amount (float): The amount to decrease.
        """
        with self.session as session:
            existing_pool= session.query(Pool).filter_by(resource_id=pool.resource_id).first()
            existing_pool.decrease_quantity(amount, session)
            session.refresh(existing_pool)
            return existing_pool

    def empty_pool(self, pool: Pool) -> None:
        """
        Empty the pool by setting the quantity to zero.

        Args:
            pool (Pool): The pool resource to empty.
        """
        with self.session as session:
            existing_pool= session.query(Pool).filter_by(resource_id=pool.resource_id).first()
            existing_pool.empty(session)
            session.refresh(existing_pool)
            return existing_pool

    def fill_pool(self, pool: Pool) -> None:
        """
        Fill the pool by setting the quantity to its capacity.

        Args:
            pool (Pool): The pool resource to fill.
        """
        with self.session as session:
            existing_pool= session.query(Pool).filter_by(resource_id=pool.resource_id).first()
            existing_pool.fill(session)
            session.refresh(existing_pool)
            return existing_pool


    def push_to_stack(self, stack: Stack, asset: Asset) -> None:
        """
        Push an asset to the stack. Automatically adds the asset to the database if it's not already there.

        Args:
            stack (Stack): The stack resource to push the asset onto.
            asset (Asset): The asset to push onto the stack.
        """
        with self.session as session:
            existing_stack = session.query(Stack).filter_by(resource_id=stack.resource_id).first()

            if not existing_stack:
                raise ValueError(
                    f"Stack '{stack.resource_name, stack.resource_id}' does not exist in the database. Please provide a valid resource."
                )
            stack = existing_stack
            asset = session.merge(asset)
            stack.push(asset, session)
            # session.commit()
            session.refresh(stack)
            return stack

    def pop_from_stack(self, stack: Stack) -> Asset:
        """
        Pop an asset from a stack resource.

        Args:
            stack (Stack): The stack resource to update.

        Returns:
            Asset: The popped asset.
            updated_stack: updated stack resource

        """
        with self.session as session:
            stack = session.merge(stack)
            asset = stack.pop(session)

            if asset:
                updated_stack = session.query(Stack).filter_by(resource_id=stack.resource_id).first()
                return asset, updated_stack            
            else:
                raise ValueError("The stack is empty or the asset does not exist.")

    def push_to_queue(self, queue: Queue, asset: Asset) -> None:
        """
        Push an asset to the queue. Automatically adds the asset to the database if it's not already there.

        Args:
            queue (Queue): The queue resource to push the asset onto.
            asset (Asset): The asset to push onto the queue.
        """
        with self.session as session:
            existing_queue = session.query(Queue).filter_by(resource_id=queue.resource_id).first()

            if not existing_queue:
                raise ValueError(
                    f"Queue '{queue.resource_name, queue.resource_id}' does not exist in the database. Please provide a valid resource."
                )
            queue = existing_queue
            asset = session.merge(asset)
            queue.push(asset, session)
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
            asset = queue.pop(session)

            if asset:
                updated_queue = session.query(Queue).filter_by(resource_id=queue.resource_id).first()
                return asset, updated_queue        
            else:
                raise ValueError("The queue is empty or the asset does not exist.")

    def increase_plate_well(self, plate: Collection, well_id: str, quantity: float) -> None:
        """
        Increase the quantity of liquid in a specific well of a plate.

        Args:
            plate (Collection): The plate resource to update.
            well_id (str): The well ID to increase the quantity for.
            quantity (float): The amount to increase the well quantity by.
        """
        with self.session as session:
            existing_plate= session.query(Collection).filter_by(resource_id=plate.resource_id).first()
            pool = existing_plate.children.get(well_id)
            
            if not pool:
                raise ValueError(f"No resource found in well '{well_id}' of plate {existing_plate.resource_name}.")
            
            self.increase_pool_quantity(pool=pool, amount=quantity)
            session.add(existing_plate)
            session.refresh(existing_plate)
            return existing_plate

    def decrease_plate_well(self, plate: Collection, well_id: str, quantity: float) -> None:
        """
        Decrease the quantity of liquid in a specific well of a plate.

        Args:
            plate (Plate): The plate resource to update.
            well_id (str): The well ID to decrease the quantity for.
            quantity (float): The amount to decrease the well quantity by.
        """
        with self.session as session:
            existing_plate= session.query(Collection).filter_by(resource_id=plate.resource_id).first()

            if well_id not in existing_plate.children:
                raise KeyError(f"Well ID '{well_id}' does not exist in existing_plate '{existing_plate.resource_name}'.")

            pool = existing_plate.children[well_id]
            if not isinstance(pool, Pool):
                raise TypeError("Only Pool resources are supported in existing_plate wells.")

            self.decrease_pool_quantity(pool=pool, amount=quantity)
            session.add(existing_plate)
            session.refresh(existing_plate)
            # session.commit()
            return existing_plate
            
    def update_collection_child(self, collection: Collection, key: str, resource: ResourceBase) -> None:
        """
        Update or add a resource in a specific well of a collection using the `add_child` method.

        Args:
            collection (Collection): The collection resource to update.
            collection (str): The well ID to update or add.
            resource (resource): The resource resource to associate with the well.
        """
        with self.session as session:
            collection= session.query(Collection).filter_by(resource_id=collection.resource_id).first()
            resource = self.get_resource(resource_id=resource.resource_id)
            resource = session.merge(resource)
            collection.add_child(key, resource, session)
            session.add(collection)
            # session.commit()
            session.refresh(collection)
            return collection

if __name__ == "__main__":
    resource_interface = ResourceInterface()
    stack = Stack(
        resource_name="stack",
        resource_type="stack1",  # Make sure this matches the expected type in validation
        capacity=10,
        ownership=None
    )
    resource_interface.add_resource(stack) 
    for i in range(5):
        asset = Asset(resource_name="Test plate"+str(i)) 
        asset = resource_interface.add_resource(asset) 
        resource_interface.push_to_stack(stack,asset)
    retrieved_stack = resource_interface.get_resource(resource_id=stack.resource_id,resource_name=stack.resource_name, owner_name=stack.owner)
    for i in range(2):
        n_asset,retrieved_stack = resource_interface.pop_from_stack(retrieved_stack)
        print(f"Popped asset: {n_asset}")
        
    queue = Queue(
        resource_name="queue",
        resource_type="queue",  # Make sure this matches the expected type in validation
        capacity=10,
        ownership=None
    )
    queue = resource_interface.add_resource(queue)
    for i in range(5):
        asset = Asset(resource_name="Test plate"+str(i)) 
        asset = resource_interface.add_resource(asset) 
        resource_interface.push_to_queue(queue,asset)
    retrieved_queue = resource_interface.get_resource(resource_id=queue.resource_id,resource_name=queue.resource_name, owner_name=queue.owner)
    for i in range(2):
        n_asset = resource_interface.pop_from_queue(retrieved_queue)
    resource_interface.push_to_queue(queue,n_asset)

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
        children = {"Water":consumable}
         # Add the ConsumableBase to children
    )
    resource_interface.add_resource(pool)
    print(pool.children)
    print(pool.children["Water"])

    # Example operations on the pool
    print(f"Initial Pool Quantity: {pool.quantity}")
    resource_interface.increase_pool_quantity(pool, 50.0)
    print(f"After Increase: {pool.quantity}")

    resource_interface.decrease_pool_quantity(pool, 20.0)
    print(f"After Decrease: {pool.quantity}")

    resource_interface.fill_pool(pool)
    print(f"After Fill: {pool.quantity}")

    resource_interface.empty_pool(pool)
    print(f"After Empty: {pool.quantity}")
    pool1 = Pool(resource_name="Pool1", resource_type="pool", capacity=100, quantity=50)
    pool1 = resource_interface.add_resource(pool1)
    # Create a Plate resource with initial children
    plate = Collection(
        resource_name="Microplate1",
        resource_type="collection",
        children={"A1": pool},
    )
    resource_interface.add_resource(plate)
    print(plate.children)
    # Increase quantity in a well
    resource_interface.increase_plate_well(plate, "A1", 30)
    print(f"A1 Quantity after increase: {plate.children}")

    # Decrease quantity in a well
    resource_interface.decrease_plate_well(plate, "A1", 20)
    print(f"A1 Quantity after decrease: {plate.children}")
    
    resource_interface.update_plate_well(plate, "A2", pool1)
    print(f"A2 Pool Name: {plate.children}")

