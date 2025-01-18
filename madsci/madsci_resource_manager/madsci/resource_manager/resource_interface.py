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
from db_tables import Stack, Asset, Queue, Pool, Consumable, Plate, Grid


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
        
            # existing_resource = (
            #     session.query(type(resource))
            #     .filter_by(resource_name=resource.resource_name, owner=resource.owner)
            #     .first()
            # )

            # # If unique_resource is True, check for existing resource and return or raise an error
            # if resource.unique_resource:
            # if existing_resource:
            #     print(f"Using existing resource: {existing_resource.resource_name}")
            #     return existing_resource

            # # If unique_resource is False, allow creating multiple resources with the same name
            # if not resource.unique_resource or not existing_resource:
            #     # If the resource doesn't exist, create and save a new one
            #     session.add(resource)
            #     session.commit()
            #     session.refresh(resource)
            
            session.add(resource)
            session.commit()
            session.refresh(resource)
            return resource


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
            "plate": Plate,
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

            # Build query conditions for name and owner
            query_conditions = []
            if resource_name:
                query_conditions.append(lambda cls: cls.resource_name == resource_name)
            if owner_name:
                query_conditions.append(lambda cls: cls.owner == owner_name)

            # Search specific resource type if provided, otherwise search all types
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
            pool.increase_quantity(amount, session)
            session.refresh(pool)

    def decrease_pool_quantity(self, pool: Pool, amount: float) -> None:
        """
        Decrease the quantity of a pool resource.

        Args:
            pool (Pool): The pool resource to update.
            amount (float): The amount to decrease.
        """
        with self.session as session:
            pool.decrease_quantity(amount, session)
            session.refresh(pool)

    def empty_pool(self, pool: Pool) -> None:
        """
        Empty the pool by setting the quantity to zero.

        Args:
            pool (Pool): The pool resource to empty.
        """
        with self.session as session:
            pool.empty(session)
            session.refresh(pool)

    def fill_pool(self, pool: Pool) -> None:
        """
        Fill the pool by setting the quantity to its capacity.

        Args:
            pool (Pool): The pool resource to fill.
        """
        with self.session as session:
            pool.fill(session)
            session.refresh(pool)


    def push_to_stack(self, stack: Stack, asset: Asset) -> None:
        """
        Push an asset to the stack. Automatically adds the asset to the database if it's not already there.

        Args:
            stack (Stack): The stack resource to push the asset onto.
            asset (Asset): The asset to push onto the stack.
        """
        with self.session as session:
            # Check if the stack exists in the database
            existing_stack = session.query(Stack).filter_by(resource_id=stack.resource_id).first()

            if not existing_stack:
                # If the stack doesn't exist, raise an error
                raise ValueError(
                    f"Stack '{stack.resource_name, stack.resource_id}' does not exist in the database. Please provide a valid resource."
                )
            stack = existing_stack
            asset = session.merge(asset)
            stack.push(asset, session)
            session.commit()
            session.refresh(stack)

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
            # session.commit()
            # session.refresh(stack)

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
                # If the queue doesn't exist, raise an error
                raise ValueError(
                    f"Queue '{queue.resource_name, queue.resource_id}' does not exist in the database. Please provide a valid resource."
                )
            queue = existing_queue
            asset = session.merge(asset)
            queue.push(asset, session)
            session.refresh(queue)

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
            session.commit()
            session.refresh(queue)

            if asset:
                updated_queue = session.query(Queue).filter_by(resource_id=queue.resource_id).first()
                return asset, updated_queue        
            else:
                raise ValueError("The queue is empty or the asset does not exist.")

    def increase_plate_well(self, plate: Plate, well_id: str, quantity: float) -> None:
        """
        Increase the quantity of liquid in a specific well of a plate.

        Args:
            plate (Plate): The plate resource to update.
            well_id (str): The well ID to increase the quantity for.
            quantity (float): The amount to increase the well quantity by.
        """
        with self.session as session:
            # Re-attach the plate to the session if it is detached
            plate = session.merge(plate)

            # Access the child Pool resource in the specified well
            pool = plate.children.get(well_id)
            if not pool:
                raise ValueError(f"No resource found in well '{well_id}' of plate {plate.resource_name}.")

            # Increase the Pool resource's quantity
            self.increase_pool_quantity(pool=pool, amount=quantity)

            # Update the Plate's quantity to reflect the number of wells
            # plate.quantity = len(plate.children)

            # Save changes to the session
            session.add(plate)
            session.commit()


    def decrease_plate_well(self, plate: Plate, well_id: str, quantity: float) -> None:
        """
        Decrease the quantity of liquid in a specific well of a plate.

        Args:
            plate (Plate): The plate resource to update.
            well_id (str): The well ID to decrease the quantity for.
            quantity (float): The amount to decrease the well quantity by.
        """
        with self.session as session:
            # Ensure the plate instance is bound to the session
            plate = session.merge(plate)

            # Check if the well exists
            if well_id not in plate.children:
                raise KeyError(f"Well ID '{well_id}' does not exist in plate '{plate.resource_name}'.")

            # Get the pool resource from the well
            pool = plate.children[well_id]
            if not isinstance(pool, Pool):
                raise TypeError("Only Pool resources are supported in plate wells.")

            # Use the `decrease_pool_quantity` method to decrease the pool's quantity
            self.decrease_pool_quantity(pool=pool, amount=quantity)

            # Update the plate's quantity based on the number of wells
            # plate.quantity = len(plate.children)
            session.add(plate)
            session.commit()
            
    def update_plate_well(self, plate: Plate, well_id: str, pool: Pool) -> None:
        """
        Update or add a resource in a specific well of a plate using the `add_child` method.

        Args:
            plate (Plate): The plate resource to update.
            well_id (str): The well ID to update or add.
            pool (Pool): The Pool resource to associate with the well.
        """
        if not isinstance(pool, Pool):
            raise TypeError("Only Pool resources can be assigned to plate wells.")

        with self.session as session:
            # Use the add_child method to handle adding/updating the well
            plate = session.merge(plate)
            pool = session.merge(pool)
            plate.add_child(well_id, pool, session)

            # Commit the changes
            session.add(plate)
            # session.refresh()
        session.commit()

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
        
    # queue = Queue(
    #     resource_name="queue",
    #     resource_type="queue",  # Make sure this matches the expected type in validation
    #     capacity=10,
    #     ownership=None
    # )
    # queue = resource_interface.add_resource(queue)
    # for i in range(5):
    #     asset = Asset(resource_name="Test plate"+str(i)) 
    #     asset = resource_interface.add_resource(asset) 
    #     resource_interface.push_to_queue(queue,asset)
    # retrieved_queue = resource_interface.get_resource(resource_id=queue.resource_id,resource_name=queue.resource_name, owner_name=queue.owner)
    # for i in range(2):
    #     n_asset = resource_interface.pop_from_queue(retrieved_queue)
    # resource_interface.push_to_queue(queue,n_asset)

    # consumable = Consumable(
    #     resource_name="Water",
    #     resource_type="consumable",
    #     quantity=50.0,
    #     ownership=None,
    #     capacity=100,
    # )
    # # Add the ConsumableBase to the database
    # resource_interface.add_resource(consumable)

    # # Create a Pool resource
    # pool = Pool(
    #     resource_name="Vial_1",
    #     resource_type="pool",
    #     capacity=500.0,
    #     children = {"Water":consumable}
    #      # Add the ConsumableBase to children
    # )
    # pool = resource_interface.add_resource(pool)
    # # print(pool.children["Water"])

    # # Example operations on the pool
    # print(f"Initial Pool Quantity: {pool.quantity}")
    # resource_interface.increase_pool_quantity(pool, 50.0)
    # print(f"After Increase: {pool.quantity}")

    # resource_interface.decrease_pool_quantity(pool, 20.0)
    # print(f"After Decrease: {pool.quantity}")

    # # resource_interface.fill_pool(pool)
    # # print(f"After Fill: {pool.quantity}")

    # # resource_interface.empty_pool(pool)
    # # print(f"After Empty: {pool.quantity}")
    # pool1 = Pool(resource_name="Pool1", resource_type="pool", capacity=100, quantity=50)
    # pool1 = resource_interface.add_resource(pool1)
    # # Create a Plate resource with initial children
    # plate = Plate(
    #     resource_name="Microplate1",
    #     resource_type="plate",
    #     children={"A1": pool},
    # )
    # plate = resource_interface.add_resource(plate)
    # print(plate.children)
    # # Increase quantity in a well
    # resource_interface.increase_plate_well(plate, "A1", 30)
    # print(f"A1 Quantity after increase: {plate.children}")

    # # Decrease quantity in a well
    # resource_interface.decrease_plate_well(plate, "A1", 20)
    # print(f"A1 Quantity after decrease: {plate.children}")
    
    # resource_interface.update_plate_well(plate, "A2", pool1)
    # print(f"A2 Pool Name: {plate.children}")

