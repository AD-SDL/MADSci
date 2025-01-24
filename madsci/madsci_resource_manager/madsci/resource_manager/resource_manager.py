from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from resource_interface import ResourceInterface
from db_tables import map_resource_type
from serialization_utils import serialize_resource, deserialize_resource

from madsci.resource_manager.types import (
    ResourceManagerConfig,
    ResourceManagerDefinition,
)

app = FastAPI()

resource_manager_definition = ResourceManagerDefinition(
    name="Resource Manager 1",
    manager_type="resource_manager",
    description="The First MADSci Resource Manager.",
    plugin_config=ResourceManagerConfig(),
)
resource_manager_definition.url = f"https://{resource_manager_definition.plugin_config.host}:{resource_manager_definition.plugin_config.port}"

@app.get("/info")
def info() -> ResourceManagerDefinition:
    """Get information about the resource manager."""
    return resource_manager_definition

@app.post("/resource/add")
async def add_resource(data: dict):
    """
    Add a resource to the database.
    """
    try:
        database_url = data["database_url"]
        resource_data = data["resource"]       
        resource = deserialize_resource(resource_data)
        interface = ResourceInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource)
        return JSONResponse(serialize_resource(saved_resource))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/resource/update")
async def update_resource(data: dict):
    """
    Update or refresh a resource in the database, including its children.
    """
    try:
        database_url = data["database_url"]
        resource_data = data["resource"]

        # Deserialize the resource
        resource = deserialize_resource(resource_data)

        # Update the resource in the database
        interface = ResourceInterface(database_url=database_url)
        interface.update_resource(resource)

        # Serialize and return the updated resource
        return JSONResponse(serialize_resource(resource))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/resource/get")
async def get_resource(data: dict):
    """
    Retrieve a resource from the database using optional parameters.
    """
    try:
        database_url = data["database_url"]
        resource_name = data.get("resource_name")
        owner_name = data.get("owner_name")
        resource_id = data.get("resource_id")
        resource_type = data.get("resource_type")
        interface = ResourceInterface(database_url=database_url)
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/push")
async def push_to_stack(data: dict):
    """
    Push an asset onto a stack.
    """
    try:
        database_url = data["database_url"]
        stack_data = data["stack"]
        asset_data = data["asset"]
        stack = deserialize_resource(stack_data)
        asset = deserialize_resource(asset_data)
        interface = ResourceInterface(database_url=database_url)
        updated_stack = interface.push_to_stack(stack, asset)
        return JSONResponse(serialize_resource(updated_stack))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/pop")
async def pop_from_stack(data: dict):
    """
    Pop an asset from a stack.
    """
    try:
        database_url = data["database_url"]
        stack_data = data["stack"]
        stack = deserialize_resource(stack_data)
        interface = ResourceInterface(database_url=database_url)
        popped_asset, updated_stack = interface.pop_from_stack(stack)
        return JSONResponse({
            "asset": serialize_resource(popped_asset),
            "updated_stack": serialize_resource(updated_stack),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/push")
async def push_to_queue(data: dict):
    """
    Push an asset onto a queue.
    """
    try:
        database_url = data["database_url"]
        queue_data = data["queue"]
        asset_data = data["asset"]
        queue = deserialize_resource(queue_data)
        asset = deserialize_resource(asset_data)
        interface = ResourceInterface(database_url=database_url)
        updated_queue = interface.push_to_queue(queue, asset)

        return JSONResponse(serialize_resource(updated_queue))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/pop")
async def pop_from_queue(data: dict):
    """
    Pop an asset from a queue.
    """
    try:
        database_url = data["database_url"]
        queue_data = data["queue"]
        queue = deserialize_resource(queue_data)
        interface = ResourceInterface(database_url=database_url)
        popped_asset, updated_queue = interface.pop_from_queue(queue)
        return JSONResponse({
            "asset": serialize_resource(popped_asset),
            "updated_queue": serialize_resource(updated_queue),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/increase")
async def increase_pool_quantity(data: dict):
    """
    Increase the quantity of a pool resource.
    """
    try:
        database_url = data["database_url"]
        pool_data = data["pool"]
        amount = data["amount"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=database_url)
        updated_pool = interface.increase_pool_quantity(pool, float(amount))
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/decrease")
async def decrease_pool_quantity(data: dict):
    """
    Decrease the quantity of a pool resource.
    """
    try:
        database_url = data["database_url"]
        pool_data = data["pool"]
        amount = data["amount"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=database_url)
        updated_pool = interface.decrease_pool_quantity(pool, float(amount))
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/fill")
async def fill_pool(data: dict):
    """
    Fill a pool resource to its maximum capacity.
    """
    try:
        database_url = data["database_url"]
        pool_data = data["pool"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=database_url)
        updated_pool = interface.fill_pool(pool)
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/empty")
async def empty_pool(data: dict):
    """
    Empty a pool resource by setting its quantity to zero.
    """
    try:
        database_url = data["database_url"]
        pool_data = data["pool"]
        pool = deserialize_resource(pool_data)
        interface = ResourceInterface(database_url=database_url)
        updated_pool = interface.empty_pool(pool)
        return JSONResponse(serialize_resource(updated_pool))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plate/increase_well")
async def increase_plate_well(data: dict):
    """
    Increase the quantity in a specific well of a plate.
    """
    try:
        database_url = data["database_url"]
        plate_data = data["plate"]
        well_id = data["well_id"]
        quantity = data["quantity"]
        plate = deserialize_resource(plate_data)
        interface = ResourceInterface(database_url=database_url)
        updated_plate = interface.increase_plate_well(plate, well_id, quantity)
        updated_plate = interface.get_resource(resource_id = updated_plate.resource_id)
        return JSONResponse(serialize_resource(updated_plate))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plate/decrease_well")
async def decrease_plate_well(data: dict):
    """
    Decrease the quantity in a specific well of a plate.
    """
    try:
        database_url = data["database_url"]
        plate_data = data["plate"]
        well_id = data["well_id"]
        quantity = data["quantity"]
        plate = deserialize_resource(plate_data)
        interface = ResourceInterface(database_url=database_url)
        updated_plate = interface.decrease_plate_well(plate, well_id, quantity)
        updated_plate = interface.get_resource(resource_id = updated_plate.resource_id)
        return JSONResponse(serialize_resource(updated_plate))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collection/update_child")
async def update_collection_child(data: dict):
    """
    Update a specific child in a collection.
    """
    try:
        database_url = data["database_url"]
        collection_data = data["collection"]
        key_id = data["key_id"]
        child_data = data["child"]
        collection = deserialize_resource(collection_data)
        child = deserialize_resource(child_data)
        interface = ResourceInterface(database_url=database_url)
        updated_collection = interface.update_collection_child(collection, key_id, child)
        return JSONResponse(serialize_resource(updated_collection))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.plugin_config.host,
        port=resource_manager_definition.plugin_config.port,
    )
