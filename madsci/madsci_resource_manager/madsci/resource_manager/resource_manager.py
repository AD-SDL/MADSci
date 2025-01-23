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
        print("Raw resource data:", resource_data)
        
        # Deserialize resource
        resource = deserialize_resource(resource_data)
        print("Deserialized resource:", resource)
        print("Deserialized children:", resource.children)
        # Add resource to the database
        interface = ResourceInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource)
        print("HERE",type(saved_resource))

        # Serialize the saved resource
        return JSONResponse(serialize_resource(saved_resource))
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

        # Retrieve the resource
        interface = ResourceInterface(database_url=database_url)
        resource = interface.get_resource(
            resource_name=resource_name,
            owner_name=owner_name,
            resource_id=resource_id,
            resource_type=resource_type,
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Serialize the resource
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

        # Deserialize stack and asset
        stack = deserialize_resource(stack_data)
        asset = deserialize_resource(asset_data)

        # Push the asset onto the stack
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_stack(stack, asset)

        return JSONResponse({"message": "Asset pushed successfully"})
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

        # Deserialize stack
        stack = deserialize_resource(stack_data)

        # Pop the asset from the stack
        interface = ResourceInterface(database_url=database_url)
        popped_asset, updated_stack = interface.pop_from_stack(stack)

        # Serialize and return the response
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

        # Deserialize queue and asset
        queue = deserialize_resource(queue_data)
        asset = deserialize_resource(asset_data)

        # Push the asset onto the queue
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_queue(queue, asset)

        return JSONResponse({"message": "Asset pushed successfully"})
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

        # Deserialize queue
        queue = deserialize_resource(queue_data)

        # Pop the asset from the queue
        interface = ResourceInterface(database_url=database_url)
        popped_asset, updated_queue = interface.pop_from_queue(queue)

        # Serialize and return the response
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

        # Deserialize pool
        pool = deserialize_resource(pool_data)

        # Increase the pool quantity
        interface = ResourceInterface(database_url=database_url)
        interface.increase_pool_quantity(pool, float(amount))
        return JSONResponse({"message": "Pool quantity increased successfully"})
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

        # Deserialize pool
        pool = deserialize_resource(pool_data)

        # Decrease the pool quantity
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_pool_quantity(pool, float(amount))

        return JSONResponse({"message": "Pool quantity decreased successfully"})
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

        # Deserialize pool
        pool = deserialize_resource(pool_data)

        # Fill the pool
        interface = ResourceInterface(database_url=database_url)
        interface.fill_pool(pool)

        return JSONResponse({"message": "Pool filled successfully"})
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

        # Deserialize pool
        pool = deserialize_resource(pool_data)

        # Empty the pool
        interface = ResourceInterface(database_url=database_url)
        interface.empty_pool(pool)

        return JSONResponse({"message": "Pool emptied successfully"})
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

        # Deserialize plate
        plate = deserialize_resource(plate_data)

        # Increase the well quantity
        interface = ResourceInterface(database_url=database_url)
        interface.increase_plate_well(plate, well_id, quantity)

        return JSONResponse({"message": "Well quantity increased successfully"})
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

        # Deserialize plate
        plate = deserialize_resource(plate_data)

        # Decrease the well quantity
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_plate_well(plate, well_id, quantity)

        return JSONResponse({"message": "Well quantity decreased successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/update_well")
async def update_plate_well(data: dict):
    """
    Update a specific well in a plate.
    """
    try:
        database_url = data["database_url"]
        plate_data = data["plate"]
        well_id = data["well_id"]
        child_data = data["child"]

        # Deserialize plate and child
        plate = deserialize_resource(plate_data)
        child = deserialize_resource(child_data)

        # Update the well
        interface = ResourceInterface(database_url=database_url)
        interface.update_plate_well(plate, well_id, child)

        # Serialize and return the response
        return JSONResponse({"message": "Well updated successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.plugin_config.host,
        port=resource_manager_definition.plugin_config.port,
    )
