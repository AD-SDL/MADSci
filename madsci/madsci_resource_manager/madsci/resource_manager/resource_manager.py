from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import Response
import pickle
from resource_interface import ResourceInterface
from madsci.common.types.resource_types import ResourceBase
from db_tables import Stack, Queue, Pool, Plate, Asset, Consumable
from madsci.resource_manager.types import (
    ResourceManagerConfig,
    ResourceManagerDefinition,
)

app = FastAPI()

# Resource type map for dynamic reconstruction
RESOURCE_TYPE_MAP = {
    "stack": Stack,
    "asset": Asset,
    "queue": Queue,
    "pool": Pool,
    "plate": Plate,
    "consumable": Consumable,
}

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
async def add_resource(data: UploadFile):
    """
    Add a resource to the database.
    """
    try:
        # Deserialize the uploaded file
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        resource = pickle.loads(payload["resource"])  # Deserialize the resource object

        # Add the resource to the database
        interface = ResourceInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource)

        # Serialize the saved resource for the response
        serialized_resource = pickle.dumps(saved_resource)

        # Return a binary response
        return Response(content=serialized_resource, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    
@app.post("/resource/get")
async def get_resource(data: dict):
    """
    Retrieve a resource from the database using optional parameters.
    """
    try:
        # Extract the payload data
        database_url = data.get("database_url")
        resource_name = data.get("resource_name")
        owner_name = data.get("owner_name")
        resource_id = data.get("resource_id")
        resource_type = data.get("resource_type")

        # Initialize the Resource Interface
        interface = ResourceInterface(database_url=database_url)

        # Retrieve the resource
        resource = interface.get_resource(
            resource_name=resource_name,
            owner_name=owner_name,
            resource_id=resource_id,
            resource_type=resource_type
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Serialize the resource object using pickle and return it
        return Response(content=pickle.dumps(resource), media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/push")
async def push_to_stack(data: UploadFile):
    """
    Push an asset onto a stack.
    """
    try:
        # Deserialize the received data
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        stack = pickle.loads(payload["stack"])  # Deserialize the stack object
        asset = pickle.loads(payload["asset"])  # Deserialize the asset object

        # Interface call to push the asset onto the stack
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_stack(stack, asset)

        # Return a success message
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        # Handle exceptions and return an HTTP error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stack/pop")
async def pop_from_stack(data: UploadFile):
    """
    Pop an asset from a stack.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        stack = pickle.loads(payload["stack"])

        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_stack(stack)
        print(asset)
        return Response(content=pickle.dumps(asset), media_type="application/octet-stream")  # Serialize and send
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/push")
async def push_to_queue(data: UploadFile):
    """
    Push an asset onto a queue.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        queue = pickle.loads(payload["queue"])
        asset = pickle.loads(payload["asset"])

        interface = ResourceInterface(database_url=database_url)
        interface.push_to_queue(queue, asset)

        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/pop")
async def pop_from_queue(data: UploadFile):
    """
    Pop an asset from a queue.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        queue = pickle.loads(payload["queue"])

        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_queue(queue)

        return Response(content=pickle.dumps(asset), media_type="application/octet-stream")  # Serialize and send
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/increase")
async def increase_pool_quantity(data: UploadFile):
    """
    Increase the quantity of a pool resource.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        pool = pickle.loads(payload["pool"])
        amount = payload["amount"]

        interface = ResourceInterface(database_url=database_url)
        interface.increase_pool_quantity(pool, amount)

        return {"message": "Pool quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/decrease")
async def decrease_pool_quantity(data: UploadFile):
    """
    Decrease the quantity of a pool resource.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        pool = pickle.loads(payload["pool"])
        amount = payload["amount"]

        interface = ResourceInterface(database_url=database_url)
        interface.decrease_pool_quantity(pool, amount)

        return {"message": "Pool quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/empty")
async def empty_pool(data: UploadFile):
    """
    Empty a pool resource by setting its quantity to zero.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        pool = pickle.loads(payload["pool"])

        interface = ResourceInterface(database_url=database_url)
        interface.empty_pool(pool)

        return {"message": "Pool emptied successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/fill")
async def fill_pool(data: UploadFile):
    """
    Fill a pool resource to its maximum capacity.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        pool = pickle.loads(payload["pool"])

        interface = ResourceInterface(database_url=database_url)
        interface.fill_pool(pool)

        return {"message": "Pool filled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/increase_well")
async def increase_plate_well(data: UploadFile):
    """
    Increase the quantity in a specific well of a plate.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        plate = pickle.loads(payload["plate"])
        well_id = payload["well_id"]
        quantity = payload["quantity"]

        interface = ResourceInterface(database_url=database_url)
        interface.increase_plate_well(plate, well_id, quantity)

        return {"message": "Well quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/decrease_well")
async def decrease_plate_well(data: UploadFile):
    """
    Decrease the quantity in a specific well of a plate.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        plate = pickle.loads(payload["plate"])
        well_id = payload["well_id"]
        quantity = payload["quantity"]

        interface = ResourceInterface(database_url=database_url)
        interface.decrease_plate_well(plate, well_id, quantity)

        return {"message": "Well quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/update_well")
async def update_plate_well(data: UploadFile):
    """
    Update a specific well in a plate.
    """
    try:
        payload = pickle.loads(await data.read())
        database_url = payload["database_url"]
        plate = pickle.loads(payload["plate"])
        well_id = payload["well_id"]
        child = pickle.loads(payload["child"])

        interface = ResourceInterface(database_url=database_url)
        interface.update_plate_well(plate, well_id, child)

        return {"message": "Well updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.plugin_config.host,
        port=resource_manager_definition.plugin_config.port,
    )
