"""API server for the Resource Manager"""

from typing import Dict, List, Optional, Type

from fastapi import APIRouter, HTTPException
from sqlmodel import SQLModel

from wei.config import Config
from wei.core.state_manager import StateManager
from wei.resources_interface import ResourcesInterface
from wei.types.resource_types import (
    Asset,
    Collection,
    Plate,
    Pool,
    Queue,
    ResourceContainerBase,
    Stack,
)

router = APIRouter()
state_manager = StateManager()
state_manager.resources_interface = ResourcesInterface(database_url=Config.database_url)

# Mapping of resource type names to actual classes
RESOURCE_TYPE_MAP = {
    "Stack": Stack,
    "Queue": Queue,
    "Collection": Collection,
    "Plate": Plate,
    "Pool": Pool,
    "Asset": Asset,
}


# Helper to get the actual SQLModel class from string
def get_resource_class(resource_type_name: str) -> Type[SQLModel]:
    "Returns the resource type"
    resource_class = RESOURCE_TYPE_MAP.get(resource_type_name)
    if not resource_class:
        raise HTTPException(
            status_code=400, detail=f"Invalid resource type: {resource_type_name}"
        )
    return resource_class


@router.post("/resources/add_resource")
def add_resource(resource: ResourceContainerBase):
    """
    Add a new resource to the database.
    """
    try:
        resource_obj = state_manager.resources_interface.add_resource(resource)
        return {"message": "Resource added successfully", "resource": resource_obj}
    except Exception as e:
        return e


@router.get("/resources/get_resource/{resource_name}")
def get_resource(
    resource_name: str, module_name: str, resource_id: Optional[str] = None
):
    """
    Retrieve a resource from the database.
    """
    try:
        resource = state_manager.resources_interface.get_resource(
            resource_name, module_name, resource_id
        )
        if resource:
            return resource
        raise Exception("Resource not found")
    except Exception as e:
        return e


@router.get("/resources/get_type/{resource_id}")
def get_resource_type(resource_id: str):
    """
    Get the type of the resource based on its ID.
    """
    try:
        resource_type = state_manager.resources_interface.get_resource_type(resource_id)
        if resource_type:
            return {"resource_type": resource_type}
        raise Exception("Resource type not found")
    except Exception as e:
        return e


@router.get("/resources/get_all_by_type/{resource_type}")
def get_all_resources(resource_type: str):
    """
    Retrieve all resources of a specific type from the database.
    """
    try:
        # Convert the string to the actual SQLModel class
        resource_type_class = get_resource_class(resource_type)

        # Call the resources_interface with the correct resource type
        resources = state_manager.resource_interface.get_all_resources(
            resource_type_class
        )
        return resources
    except HTTPException as e:
        raise e
    except Exception as e:
        return e


@router.get("/resources/get_assets")
def get_all_assets() -> List[Asset]:
    """
    Get all available assets
    """
    return state_manager.resources_interface.get_all_resources(Asset)


@router.put("/resources/update_resource/{resource_type}/{resource_id}")
def update_resource(resource_type: str, resource_id: str, updates: Dict):
    """
    Update a resource in the database.
    """
    try:
        # Convert the string to the actual SQLModel class
        resource_type_class = get_resource_class(resource_type)

        # Update the resource
        updated_resource = state_manager.resources_interface.update_resource(
            resource_type_class, resource_id, updates
        )
        if updated_resource:
            return {
                "message": "Resource updated successfully",
                "resource": updated_resource,
            }
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        return e


@router.delete("/resources/delete_resource/{resource_type}/{resource_id}")
def delete_resource(resource_type: str, resource_id: str):
    """
    Delete a resource from the database.
    """
    try:
        # Convert the string to the actual SQLModel class
        resource_type_class = get_resource_class(resource_type)

        # Delete the resource
        deleted = state_manager.resources_interface.delete_resource(
            resource_type_class, resource_id
        )
        if deleted:
            return {"message": "Resource deleted successfully"}
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        return e


@router.delete("/resources/delete_tables")
def delete_all_tables():
    """
    Delete all tables from the database.
    """
    try:
        state_manager.resources_interface.delete_all_tables()
        return {"message": "All tables deleted successfully"}
    except Exception as e:
        return e


@router.delete("/resources/clear_all_records")
def clear_all_table_records():
    """
    Clear all records from all tables.
    """
    try:
        state_manager.resources_interface.clear_all_table_records()
        return {"message": "All records cleared successfully"}
    except Exception as e:
        return e


@router.put("/resources/pool/increase")
def increase_pool_quantity(pool: Pool, amount: float):
    """
    Increase the quantity of a pool resource.
    """
    try:
        state_manager.resources_interface.increase_pool_quantity(pool, amount)
        return {"message": "Pool quantity increased successfully"}
    except Exception as e:
        return e


@router.put("/resources/pool/decrease")
def decrease_pool_quantity(pool: Pool, amount: float):
    """
    Decrease the quantity of a pool resource.
    """
    try:
        state_manager.resources_interface.decrease_pool_quantity(pool, amount)
        return {"message": "Pool quantity decreased successfully"}
    except Exception as e:
        return e


@router.put("/resources/pool/fill")
def fill_pool(pool: Pool):
    """
    Fill the pool by setting the quantity to its capacity.
    """
    try:
        state_manager.resources_interface.fill_pool(pool)
        return {"message": "Pool filled successfully"}
    except Exception as e:
        return e


@router.put("/resources/pool/empty")
def empty_pool(pool: Pool):
    """
    Empty the pool by setting the quantity to zero.
    """
    try:
        state_manager.resources_interface.empty_pool(pool)
        return {"message": "Pool emptied successfully"}
    except Exception as e:
        return e


@router.put("/resources/stack/push")
def push_to_stack(stack: Stack, asset: Asset):
    """
    Push an asset to a stack.
    """
    try:
        state_manager.resources_interface.push_to_stack(stack, asset)
        return {"message": "Asset pushed to stack successfully"}
    except Exception as e:
        return e


@router.put("/resources/stack/pop")
def pop_from_stack(stack: Stack):
    """
    Pop an asset from a stack.
    """
    try:
        asset = state_manager.resources_interface.pop_from_stack(stack)
        return {"message": "Asset popped from stack", "asset": asset}
    except Exception as e:
        return e


@router.put("/resources/queue/push")
def push_to_queue(queue: Queue, asset: Asset):
    """
    Push an asset to a queue.
    """
    try:
        state_manager.resources_interface.push_to_queue(queue, asset)
        return {"message": "Asset pushed to queue successfully"}
    except Exception as e:
        return e


@router.put("/resources/queue/pop")
def pop_from_queue(queue: Queue):
    """
    Pop an asset from a queue.
    """
    try:
        asset = state_manager.resources_interface.pop_from_queue(queue)
        return {"message": "Asset popped from queue", "asset": asset}
    except Exception as e:
        return e


@router.put("/resources/collection/insert")
def insert_into_collection(collection: Collection, location: str, asset: Asset):
    """
    Insert an asset into a collection.
    """
    try:
        state_manager.resources_interface.insert_into_collection(
            collection, location, asset
        )
        return {"message": "Asset inserted into collection successfully"}
    except Exception as e:
        return e


@router.get("/resources/collection/retrieve")
def retrieve_from_collection(collection: Collection, location: str):
    """
    Retrieve an asset from a collection.
    """
    try:
        asset = state_manager.resources_interface.retrieve_from_collection(
            collection, location
        )
        if asset:
            return asset
        raise HTTPException(status_code=404, detail="Asset not found")
    except Exception as e:
        return e


@router.put("/resources/plate/well/update")
def update_plate_well(plate: Plate, well_id: str, quantity: float):
    """
    Update the quantity of a well in a plate.
    """
    try:
        state_manager.resources_interface.update_plate_well(plate, well_id, quantity)
        return {"message": "Plate well updated successfully"}
    except Exception as e:
        return e


@router.put("/resources/plate/contents/update")
def update_plate_contents(plate: Plate, new_contents: Dict[str, float]):
    """
    Update the entire contents of a plate.
    """
    try:
        state_manager.resources_interface.update_plate_contents(plate, new_contents)
        return {"message": "Plate contents updated successfully"}
    except Exception as e:
        return e


@router.get("/resources/plate/get_well_quantity/{well_id}")
def get_well_quantity(plate: Plate, well_id: str):
    """
    Get the quantity in a specific well of a plate.
    """
    try:
        quantity = state_manager.resources_interface.get_well_quantity(plate, well_id)
        if quantity is not None:
            return {"quantity": quantity}
        raise HTTPException(status_code=404, detail="Well not found")
    except Exception as e:
        return e


@router.get("/resources/plate/wells")
def get_wells(plate: Plate):
    """
    Retrieve the entire contents (wells) of a plate resource.
    """
    try:
        wells = state_manager.resources_interface.get_wells(plate)
        return {"wells": wells}
    except Exception as e:
        return e
