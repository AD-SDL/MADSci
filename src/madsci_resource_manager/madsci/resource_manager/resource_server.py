"""Fast API Server for Resources"""

import logging
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from madsci.common.types.squid_types import (
    ResourceManagerDefinition,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.serialization_utils import (
    deserialize_resource,
    serialize_resource,
)

logger = logging.getLogger(__name__)

app = FastAPI()

resource_manager_definition = ResourceManagerDefinition(
    name="Resource Manager 1",
    manager_type="resource_manager",
    description="The First MADSci Resource Manager.",
)
resource_manager_definition.url = f"https://{resource_manager_definition.manager_config.host}:{resource_manager_definition.manager_config.port}"
DB_URL = resource_manager_definition.manager_config.db_url


@app.get("/info")
def info() -> ResourceManagerDefinition:
    """Get information about the resource manager."""
    return resource_manager_definition


@app.post("/resource/add")
async def add_resource(data: dict) -> JSONResponse:
    """
    Add a resource to the database.
    """
    try:
        resource_data = data["resource"]
        resource = deserialize_resource(resource_data)
        interface = ResourceInterface(database_url=DB_URL)
        saved_resource = interface.add_resource(resource)
        return JSONResponse(serialize_resource(saved_resource))
    except Exception as e:
        traceback.print_exc()
        logger.error(e)


@app.post("/resource/update")
async def update_resource(data: dict) -> JSONResponse:
    """
    Update or refresh a resource in the database, including its children.
    """
    try:
        resource_data = data["resource"]

        # Deserialize the resource
        resource = deserialize_resource(resource_data)

        # Update the resource in the database
        interface = ResourceInterface(database_url=DB_URL)
        interface.update_resource(resource)

        # Serialize and return the updated resource
        return JSONResponse(serialize_resource(resource))
    except Exception as e:
        logger.error(e)


@app.post("/resource/remove")
async def remove_resource(data: dict) -> JSONResponse:
    """
    Remove a resource by moving it to the History table and deleting it from the main table.

    Args:
        data (dict): JSON payload with:
            - `database_url` (str): The database connection string.
            - `resource_id` (str): The ID of the resource to remove.

    Returns:
        JSONResponse: A success message or an error.
    """
    try:
        resource_id = data["resource_id"]

        interface = ResourceInterface(database_url=DB_URL)
        interface.remove_resource(resource_id)

        return JSONResponse(
            {"message": f"Resource {resource_id} successfully removed."}
        )
    except ValueError as e:
        logger.error(e)
    except Exception as e:
        logger.error(e)


@app.post("/resource/get")
async def get_resource(data: dict) -> JSONResponse:
    """
    Retrieve a resource from the database using optional parameters.
    """
    try:
        resource_name = data.get("resource_name")
        owner_name = data.get("owner_name")
        resource_id = data.get("resource_id")
        resource_type = data.get("resource_type")
        interface = ResourceInterface(database_url=DB_URL)
        resource = interface.get_resource(
            resource_name=resource_name,
            owner_name=owner_name,
            resource_id=resource_id,
            resource_type=resource_type,
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        return JSONResponse(serialize_resource(resource))
    except Exception as e:
        logger.error(e)


@app.post("/resource/history")
async def get_history(data: dict) -> JSONResponse:
    """
    Retrieve the history of a resource.

    Args:
        data (dict): JSON payload with:
            - `database_url` (str): The database connection string.
            - `resource_id` (str): The ID of the resource.
            - `event_type` (Optional[str]): Filter by event type (`created`, `updated`, `deleted`).
            - `removed` (Optional[bool]): Filter by removed status.
            - `start_date` (Optional[str]): Start date (ISO format `YYYY-MM-DDTHH:MM:SS`).
            - `end_date` (Optional[str]): End date (ISO format `YYYY-MM-DDTHH:MM:SS`).
            - `limit` (Optional[int]): Maximum number of records to return.

    Returns:
        JSONResponse: A list of historical resource entries.
    """
    try:
        resource_id = data["resource_id"]
        event_type = data.get("event_type")
        removed = data.get("removed")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        limit = data.get("limit", 100)

        interface = ResourceInterface(database_url=DB_URL)

        # Convert date strings to datetime objects
        start_date = datetime.fromisoformat(start_date) if start_date else None
        end_date = datetime.fromisoformat(end_date) if end_date else None

        history_entries = interface.get_history(
            resource_id=resource_id,
            event_type=event_type,
            removed=removed,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return JSONResponse(
            [serialize_resource(entry.data) for entry in history_entries]
        )
    except Exception as e:
        logger.error(e)


@app.post("/resource/restore")
async def restore_deleted_resource(data: dict) -> JSONResponse:
    """
    Restore a previously deleted resource from the history table.

    Args:
        data (dict): JSON payload with:
            - `database_url` (str): The database connection string.
            - `resource_id` (str): The ID of the resource to restore.

    Returns:
        JSONResponse: The restored resource.
    """
    try:
        resource_id = data["resource_id"]

        interface = ResourceInterface(database_url=DB_URL)

        # Fetch the most recent deleted entry
        history_entries = interface.get_history(
            resource_id=resource_id, removed=True, limit=1
        )
        if not history_entries:
            raise HTTPException(
                status_code=404,
                detail=f"No deleted history found for resource ID '{resource_id}'.",
            )

        # Deserialize and restore the resource
        restored_resource = deserialize_resource(history_entries[0].data)
        saved_resource = interface.add_resource(restored_resource)

        return JSONResponse(serialize_resource(saved_resource))
    except Exception as e:
        logger.error(e)


@app.post("/stack/push")
async def push_to_stack(data: dict) -> JSONResponse:
    """
    Push an asset onto a stack.
    """
    try:
        stack_data = data["stack"]
        asset_data = data["asset"]
        stack = deserialize_resource(stack_data)
        asset = deserialize_resource(asset_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_stack = interface.push_to_stack(stack, asset)
        return JSONResponse(serialize_resource(updated_stack))
    except Exception as e:
        logger.error(e)


@app.post("/stack/pop")
async def pop_from_stack(data: dict) -> JSONResponse:
    """
    Pop an asset from a stack.
    """
    try:
        stack_data = data["stack"]
        stack = deserialize_resource(stack_data)
        interface = ResourceInterface(database_url=DB_URL)
        popped_asset, updated_stack = interface.pop_from_stack(stack)
        return JSONResponse(
            {
                "asset": serialize_resource(popped_asset),
                "updated_stack": serialize_resource(updated_stack),
            }
        )
    except Exception as e:
        logger.error(e)


@app.post("/queue/push")
async def push_to_queue(data: dict) -> JSONResponse:
    """
    Push an asset onto a queue.
    """
    try:
        queue_data = data["queue"]
        asset_data = data["asset"]
        queue = deserialize_resource(queue_data)
        asset = deserialize_resource(asset_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_queue = interface.push_to_queue(queue, asset)

        return JSONResponse(serialize_resource(updated_queue))
    except Exception as e:
        logger.error(e)


@app.post("/queue/pop")
async def pop_from_queue(data: dict) -> JSONResponse:
    """
    Pop an asset from a queue.
    """
    try:
        queue_data = data["queue"]
        queue = deserialize_resource(queue_data)
        interface = ResourceInterface(database_url=DB_URL)
        popped_asset, updated_queue = interface.pop_from_queue(queue)
        return JSONResponse(
            {
                "asset": serialize_resource(popped_asset),
                "updated_queue": serialize_resource(updated_queue),
            }
        )
    except Exception as e:
        logger.error(e)


@app.post("/pool/increase")
async def increase_pool_quantity(data: dict) -> JSONResponse:
    """
    Increase the quantity of a pool resource.
    """
    try:
        pool_data = data["pool"]
        amount = data["amount"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_pool = interface.increase_pool_quantity(pool, float(amount))
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        logger.error(e)


@app.post("/pool/decrease")
async def decrease_pool_quantity(data: dict) -> JSONResponse:
    """
    Decrease the quantity of a pool resource.
    """
    try:
        pool_data = data["pool"]
        amount = data["amount"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_pool = interface.decrease_pool_quantity(pool, float(amount))
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        logger.error(e)


@app.post("/pool/fill")
async def fill_pool(data: dict) -> JSONResponse:
    """
    Fill a pool resource to its maximum capacity.
    """
    try:
        pool_data = data["pool"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_pool = interface.fill_pool(pool)
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        logger.error(e)


@app.post("/pool/empty")
async def empty_pool(data: dict) -> JSONResponse:
    """
    Empty a pool resource by setting its quantity to zero.
    """
    try:
        pool_data = data["pool"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_pool = interface.empty_pool(pool)
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        logger.error(e)


@app.post("/plate/increase_well")
async def increase_plate_well(data: dict) -> JSONResponse:
    """
    Increase the quantity in a specific well of a plate.
    """
    try:
        plate_data = data["plate"]
        well_id = data["well_id"]
        quantity = data["quantity"]
        plate = deserialize_resource(plate_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_plate = interface.increase_plate_well(plate, well_id, quantity)
        updated_plate = interface.get_resource(resource_id=updated_plate.resource_id)
        return JSONResponse(serialize_resource(updated_plate))
    except Exception as e:
        logger.error(e)


@app.post("/plate/decrease_well")
async def decrease_plate_well(data: dict) -> JSONResponse:
    """
    Decrease the quantity in a specific well of a plate.
    """
    try:
        plate_data = data["plate"]
        well_id = data["well_id"]
        quantity = data["quantity"]
        plate = deserialize_resource(plate_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_plate = interface.decrease_plate_well(plate, well_id, quantity)
        updated_plate = interface.get_resource(resource_id=updated_plate.resource_id)
        return JSONResponse(serialize_resource(updated_plate))
    except Exception as e:
        logger.error(e)


@app.post("/collection/update_child")
async def update_collection_child(data: dict) -> JSONResponse:
    """
    Update a specific child in a collection.
    """
    try:
        collection_data = data["collection"]
        key_id = data["key_id"]
        child_data = data["child"]
        collection = deserialize_resource(collection_data)
        child = deserialize_resource(child_data)
        interface = ResourceInterface(database_url=DB_URL)
        updated_collection = interface.update_collection_child(
            collection, key_id, child
        )
        return JSONResponse(serialize_resource(updated_collection))
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.manager_config.host,
        port=resource_manager_definition.manager_config.port,
    )
