"""Resources Interface"""

import time
from typing import Dict, List, Optional, Type

from sqlalchemy import text
from sqlalchemy.exc import MultipleResultsFound
from sqlmodel import Session, SQLModel, create_engine, select

# from wei.types.resource_types import (
#     Asset,
#     Collection,
#     Plate,
#     Pool,
#     Queue,
#     ResourceContainerBase,
#     Stack,
# )
from madsci.common.types.resource_types import StackBase,PoolBase,ResourceBase
from db_tables import Stack, Asset, Queue

class ResourcesInterface:
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
            "queue": Queue,
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
        
    # def get_resource_type(self, resource_id: str) -> Optional[str]:
    #     """
    #     Determine the resource type name based on the provided resource_id.

    #     Args:
    #         resource_id (str): The ID of the resource.

    #     Returns:
    #         str or None: The name of the resource type if found, otherwise None.
    #     """
    #     resource_types = {
    #         "Stack": Stack,
    #         "Pool": Pool,
    #         "Queue": Queue,
    #         "Collection": Collection,
    #         "Plate": Plate,
    #     }

    #     with self.session as session:
    #         for type_name, resource_type in resource_types.items():
    #             statement = select(resource_type).where(resource_type.id == resource_id)
    #             result = session.exec(statement).first()
    #             if result:
    #                 return type_name

    #     return None

    # def get_all_resources(self, resource_type: Type[SQLModel]) -> List[SQLModel]:
    #     """
    #     Retrieve all resources of a specific type from the database.

    #     Args:
    #         resource_type (Type[SQLModel]): The type of the resources.

    #     Returns:
    #         List[SQLModel]: A list of all resources of the specified type.
    #     """
    #     with self.session as session:
    #         # Handle Plate type by filtering Collection where is_plate=True
    #         if resource_type is Plate:
    #             statement = select(Collection).where(Collection.is_plate)
    #             resources = session.exec(statement).all()
    #             return resources

    #         # Handle Collection type by filtering Collection where is_plate=False
    #         elif resource_type is Collection:
    #             statement = select(Collection).where(Collection.is_plate)
    #             resources = session.exec(statement).all()
    #             return resources

    #         # Handle all other resource types normally
    #         else:
    #             statement = select(resource_type)
    #             # Fetch and return resources of the requested type
    #             resources = session.exec(statement).all()
    #             return resources

    # def update_resource(
    #     self, resource_type: Type[SQLModel], resource_id: str, updates: Dict
    # ) -> Optional[SQLModel]:
    #     """
    #     Update a resource in the database.

    #     Args:
    #         resource_type (Type[SQLModel]): The type of the resource.
    #         resource_id (str): The ID of the resource.
    #         updates (Dict): The updates to apply.

    #     Returns:
    #         SQLModel: The updated resource, or None if not found.
    #     """
    #     with self.session as session:
    #         resource = self.get_resource(resource_type, resource_id)
    #         if not resource:
    #             return None

    #         for key, value in updates.items():
    #             setattr(resource, key, value)

    #         session.add(resource)
    #         session.commit()
    #         session.refresh(resource)
    #         return resource

    # def delete_resource(self, resource_type: Type[SQLModel], resource_id: str) -> bool:
    #     """
    #     Delete a resource from the database.

    #     Args:
    #         resource_type (Type[SQLModel]): The type of the resource.
    #         resource_id (str): The ID of the resource.

    #     Returns:
    #         bool: True if the resource was deleted, False if not found.
    #     """
    #     with self.session as session:
    #         resource = self.get_resource(resource_type, resource_id)
    #         if not resource:
    #             return False

    #         session.delete(resource)
    #         session.commit()
    #         return True

    # def delete_all_tables(self):
    #     """
    #     Drop all tables associated with the SQLModel metadata from the database.
    #     """
    #     try:
    #         with self.engine.connect() as connection:
    #             # Drop Asset first, handling foreign key constraints with CASCADE
    #             connection.execute(text("DROP TABLE IF EXISTS assetallocation CASCADE"))
    #             connection.commit()
    #         # Drop the rest of the tables
    #         SQLModel.metadata.drop_all(self.engine)
    #         print("All tables have been deleted.")
    #     except Exception as e:
    #         print(f"An error occurred while deleting tables: {e}")

    # def clear_all_table_records(self):
    #     """
    #     Delete all records from all tables associated with the SQLModel metadata.
    #     """
    #     with self.session as session:
    #         try:
    #             for table in reversed(SQLModel.metadata.sorted_tables):
    #                 session.exec(table.delete())
    #             session.commit()
    #             print("All table records have been cleared.")
    #         except Exception as e:
    #             session.rollback()
    #             print(f"An error occurred while clearing table records: {e}")

    # def increase_pool_quantity(self, pool: Pool, amount: float) -> None:
    #     """
    #     Increase the quantity of a pool resource.

    #     Args:
    #         pool (Pool): The pool resource to update.
    #         amount (float): The amount to increase.
    #     """
    #     with self.session as session:
    #         session.add(pool)
    #         pool.increase(amount, session)
    #         session.refresh(pool)

    # def decrease_pool_quantity(self, pool: Pool, amount: float) -> None:
    #     """
    #     Decrease the quantity of a pool resource.

    #     Args:
    #         pool (Pool): The pool resource to update.
    #         amount (float): The amount to decrease.
    #     """
    #     with self.session as session:
    #         session.add(pool)
    #         pool.decrease(amount, session)
    #         session.refresh(pool)

    # def empty_pool(self, pool: Pool) -> None:
    #     """
    #     Empty the pool by setting the quantity to zero.

    #     Args:
    #         pool (Pool): The pool resource to empty.
    #     """
    #     with self.session as session:
    #         session.add(pool)
    #         pool.empty(session)
    #         session.refresh(pool)

    # def fill_pool(self, pool: Pool) -> None:
    #     """
    #     Fill the pool by setting the quantity to its capacity.

    #     Args:
    #         pool (Pool): The pool resource to fill.
    #     """
    #     with self.session as session:
    #         session.add(pool)
    #         pool.fill(session)
    #         session.refresh(pool)

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
        """
        with self.session as session:
            stack = session.merge(stack)
            asset = stack.pop(session)
            session.commit()
            session.refresh(stack)

            if asset:
                return asset
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
            # Check if the queue exists in the database
            existing_queue = session.query(Queue).filter_by(id=queue.id).first()

            if not existing_queue:
                # If the queue doesn't exist, raise an error
                raise ValueError(
                    f"Queue '{queue.name}' does not exist in the database. Please provide a valid resource."
                )

            queue = existing_queue
            asset = session.merge(asset)
            queue.push(asset, session)
            session.commit()
            session.refresh(queue)

    # def pop_from_queue(self, queue: Queue) -> Asset:
    #     """
    #     Pop an asset from a queue resource.

    #     Args:
    #         queue (Queue): The queue resource to update.

    #     Returns:
    #         Asset: The popped asset.
    #     """
    #     with self.session as session:
    #         session.add(queue)
    #         return queue.pop(session)

    # def insert_into_collection(
    #     self, collection: Collection, location: str, asset: Asset
    # ) -> None:
    #     """
    #     Insert an asset into a collection resource.

    #     Args:
    #         collection (Collection): The collection resource to update.
    #         location (str): The location within the collection to insert the asset.
    #         asset (Asset): The asset to insert.
    #     """
    #     with self.session as session:
    #         collection = session.merge(collection)
    #         asset = session.merge(asset)
    #         collection.insert(location, asset, session)
    #         session.commit()
    #         session.refresh(collection)

    # def retrieve_from_collection(
    #     self, collection: Collection, location: str
    # ) -> Optional[Asset]:
    #     """
    #     Retrieve an asset from a collection resource.

    #     Args:
    #         collection (Collection): The collection resource to update.
    #         location (str): The location within the collection to retrieve the asset from.

    #     Returns:
    #         Asset: The retrieved asset.
    #     """
    #     with self.session as session:
    #         collection = session.merge(collection)
    #         return collection.retrieve(location, session)

    # def update_plate_well(self, plate: Plate, well_id: str, quantity: float) -> None:
    #     """
    #     Update the quantity of a specific well in a plate resource.

    #     Args:
    #         plate (Plate): The plate resource to update.
    #         well_id (str): The well ID to update.
    #         quantity (float): The new quantity for the well.
    #     """
    #     with self.session as session:
    #         # Find the corresponding collection (plate) in the database
    #         collection = session.query(Collection).filter_by(name=plate.name).first()

    #         if not collection:
    #             raise ValueError(f"Collection for plate {plate.name} not found.")

    #         # Use the set_wells function to update the well quantity
    #         plate.set_wells({well_id: quantity}, session)

    #         # Commit the changes and refresh the collection object if needed
    #         session.commit()
    #         session.refresh(collection)

    # def update_plate_contents(
    #     self, plate: Plate, new_contents: Dict[str, float]
    # ) -> None:
    #     """
    #     Update the entire contents of a plate resource.

    #     Args:
    #         plate (Plate): The plate resource to update.
    #         new_contents (Dict[str, float]): A dictionary with well IDs as keys and quantities as values.
    #     """
    #     with self.session as session:
    #         # Retrieve the corresponding Collection from the database
    #         collection = (
    #             session.query(Collection)
    #             .filter_by(
    #                 name=plate.name,
    #                 owner_name=plate.owner_name,
    #             )
    #             .first()
    #         )

    #         if not collection:
    #             raise ValueError(f"Collection for Plate {plate.name} not found.")

    #         # Use the plate object (in memory) to update the wells
    #         plate.set_wells(new_contents, session)  # Use the Plate's set_wells logic

    #         # Make sure to update the Collection's quantity as well
    #         session.commit()

    # def get_well_quantity(self, plate: Plate, well_id: str) -> Optional[float]:
    #     """
    #     Retrieve the quantity in a specific well of a plate resource.

    #     Args:
    #         plate (Plate): The plate resource to query.
    #         well_id (str): The ID of the well to retrieve the quantity for.

    #     Returns:
    #         Optional[float]: The quantity in the well, or None if the well does not exist.
    #     """
    #     with self.session as session:
    #         plate = session.merge(plate)
    #         wells = plate.get_wells(session)
    #         well = wells.get(well_id)

    #         if well is not None:
    #             return well.quantity
    #         else:
    #             print(f"Well {well_id} not found in plate {plate.name}")
    #             return None

    # def increase_well(self, plate: Plate, well_id: str, quantity: float) -> None:
    #     """
    #     Increase the quantity of liquid in a specific well of a plate.

    #     Args:
    #         plate (Plate): The plate resource to update.
    #         well_id (str): The well ID to increase the quantity for.
    #         quantity (float): The amount to increase the well quantity by.
    #     """
    #     with self.session as session:
    #         # Find the corresponding collection (plate)
    #         collection = session.query(Collection).filter_by(name=plate.name).first()

    #         if not collection:
    #             raise ValueError(f"Collection for plate {plate.name} not found.")

    #         plate.increase_well(well_id, quantity, session)
    #         session.commit()
    #         session.refresh(collection)  # Refresh the collection object if needed

    # def decrease_well(self, plate: Plate, well_id: str, quantity: float) -> None:
    #     """
    #     Decrease the quantity of liquid in a specific well of a plate.

    #     Args:
    #         plate (Plate): The plate resource to update.
    #         well_id (str): The well ID to decrease the quantity for.
    #         quantity (float): The amount to decrease the well quantity by.
    #     """
    #     with self.session as session:
    #         # Find the corresponding collection (plate) in the database
    #         collection = session.query(Collection).filter_by(name=plate.name).first()

    #         if not collection:
    #             raise ValueError(f"Collection for plate {plate.name} not found.")

    #         plate.decrease_well(well_id, quantity, session)
    #         session.commit()
    #         session.refresh(collection)

    # def get_wells(self, plate: Plate) -> Dict[str, Pool]:
    #     """
    #     Retrieve the entire contents (wells) of a plate resource.

    #     Args:
    #         plate (Plate): The plate resource to query.

    #     Returns:
    #         Dict[str, Pool]: A dictionary of all wells in the plate, keyed by their well IDs.
    #     """
    #     with self.session as session:
    #         wells = plate.get_wells(session)
    #         return wells


if __name__ == "__main__":
    resources_interface = ResourcesInterface()
    stack = Stack(
        resource_name="stack",
        resource_type="stack1",  # Make sure this matches the expected type in validation
        capacity=10,
        ownership=None
    )
    stack = resources_interface.add_resource(stack) 
    asset = Asset(resource_name="Test plate") 
    asset = resources_interface.add_resource(asset) 
    resources_interface.push_to_stack(stack,asset)
    retrieved_stack = resources_interface.get_resource(resource_id=stack.resource_id,resource_name=stack.resource_name, owner_name=stack.owner)
    print(retrieved_stack)
    # n_asset = resources_interface.pop_from_stack(retrieved_stack)
    
    # resources_interface.clear_all_table_records()
    # pool = Pool(
    #     name="Test Pool",
    #     description="A test pool",
    #     capacity=100.0,
    #     quantity=50.0,
    #     owner_name="test1",
    # )
    # pool = resources_interface.add_resource(pool)
    # all_pools = resources_interface.get_all_resources(Pool)
    # print("\nAll Pools after modification:", all_pools)
    # resources_interface.increase_pool_quantity(pool, 0.0)
    # all_pools = resources_interface.get_all_resources(Pool)
    # print("\nAll Pools after modification:", all_pools)
    # stack = Stack(
    #     name="Test Stack", description="A test stack", capacity=10, owner_name="test2"
    # )
    # resources_interface.add_resource(stack)
    # retrieved_stack = resources_interface.get_resource(
    #     resource_name="Test Stack", owner_name="test2"
    # )
    # print("Retreived_STACK:", retrieved_stack)
    # asset = Asset(name="Test Asset", unique_resource=False)
    # asset3 = Asset(name="Test Asset3", unique_resource=False)
    # resources_interface.push_to_stack(stack, asset)
    # resources_interface.push_to_stack(stack, asset3)
    # all_stacks = resources_interface.get_all_resources(Stack)
    # print("\nAll Stacks after modification:", all_stacks)
    # popped_asset = resources_interface.pop_from_stack(stack)
    # all_stacks = resources_interface.get_all_resources(Stack)
    # print("\nAll Stacks after modification:", all_stacks)
    # queue = Queue(
    #     name="Test Queue", description="A test queue", capacity=10, owner_name="test3"
    # )
    # queue = resources_interface.add_resource(queue)
    # asset2 = Asset(name="Test Asset2")
    # resources_interface.push_to_queue(queue, asset2)
    # # resource_interface.push_to_queue(queue, asset)
    # all_queues = resources_interface.get_all_resources(Queue)
    # print("\nAll Queues after modification:", all_queues)
    # popped_asset_q = resources_interface.pop_from_queue(queue)
    # print("\nPopped Asset from Queue:", popped_asset_q)
    # all_queues = resources_interface.get_all_resources(Queue)
    # print("\nAll Queues after modification:", all_queues)
    # collection = Collection(
    #     name="Test Collection",
    #     description="A test collection",
    #     capacity=10,
    #     owner_name="test4",
    # )
    # collection = resources_interface.add_resource(collection)
    # resources_interface.insert_into_collection(collection, location="1", asset=asset3)
    # retrieved_asset = resources_interface.retrieve_from_collection(
    #     collection, location=1
    # )
    # print("\nRetrieved Asset from Collection:", retrieved_asset)
    # plate = Plate(
    #     name="Test Plate",
    #     description="A test plate",
    #     capacity=96,
    #     well_capacity=100.0,
    #     owner_name="test5",
    #     unique_resource=False,
    # )
    # plate2 = Plate(
    #     name="Test Plate",
    #     description="A test plate",
    #     capacity=96,
    #     well_capacity=100.0,
    #     owner_name="test5",
    #     unique_resource=False,
    # )
    # plate = resources_interface.add_resource(plate)
    # plate2 = resources_interface.add_resource(plate2)
    # wells_to_add = {
    #     "A1": 50.0,
    #     "B1": 66.0,
    # }
    # resources_interface.update_plate_contents(plate, wells_to_add)
    # all_wells = resources_interface.get_wells(plate)
    # print(f"All wells in the plate: {all_wells}")
    # resources_interface.increase_well(plate, well_id="A1", quantity=20.0)
    # resources_interface.decrease_well(plate, well_id="B1", quantity=10.0)
    # new_well_to_add = {
    #     "C1": 70.0,
    # }
    # resources_interface.update_plate_contents(plate, new_well_to_add)
    # updated_wells = resources_interface.get_wells(plate)
    # print(f"Updated wells: {updated_wells}")
    # resources_interface.update_plate_well(plate, well_id="A1", quantity=80.0)
    # all_plates = resources_interface.get_all_resources(Plate)
    # print("\nAll Plates after modification:", all_plates)
    # new_well_to_add2 = {
    #     "D1": 70.0,  # Well C1 with 70.0 quantity
    # }

    # r = resources_interface.get_resource(resource_id=plate2.id)
    # resources_interface.update_plate_contents(r, new_well_to_add2)

    # # all_asset = resource_interface.get_all_resources(Asset)
    # # print("\n Asset Table", all_asset)

    # # print(resource_interface.get_resource_type(stack.id))

    # # print(resource_interface.get_all_assets_with_relations())
