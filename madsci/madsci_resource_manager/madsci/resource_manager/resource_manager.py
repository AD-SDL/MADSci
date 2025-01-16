from fastapi import FastAPI, HTTPException
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
def add_resource(database_url: str, resource: dict):
    """
    Add a resource to the database.
    """
    try:
        # Determine the resource type
        resource_type = resource.get("resource_type")
        print(type(resource))
        if not resource_type or resource_type not in RESOURCE_TYPE_MAP:
            raise ValueError(f"Unknown or missing resource_type: {resource_type}")

        # Reconstruct the resource object dynamically
        resource_class = RESOURCE_TYPE_MAP[resource_type]
        resource_obj = resource_class(**resource)

        # Pass the resource object to the interface
        interface = ResourceInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource_obj)

        return saved_resource.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/resource/get")
def get_resource(database_url: str, data: dict):
    """
    Retrieve a resource from the database using optional parameters.
    """
    try:
        # Extract optional parameters from the data
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

        # Return the resource as JSON
        return resource.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.post("/stack/push")
def push_to_stack(database_url: str, data: dict):
    """
    Push an asset onto a stack.
    """
    try:
        stack = Stack(**data["stack"])
        asset = Asset(**data["asset"])
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_stack(stack, asset)
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stack/pop")
def pop_from_stack(database_url: str, data: dict):
    """
    Pop an asset from a stack.
    """
    try:
        stack = Stack(**data["stack"])
        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_stack(stack)
        return {"message": "Asset popped successfully", "asset": asset.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/push")
def push_to_queue(database_url: str, data: dict):
    """
    Push an asset onto a queue.
    """
    try:
        queue = Queue(**data["queue"])
        asset = Asset(**data["asset"])
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_queue(queue, asset)
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/pop")
def pop_from_queue(database_url: str, data: dict):
    """
    Pop an asset from a queue.
    """
    try:
        queue = Queue(**data["queue"])
        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_queue(queue)
        return {"message": "Asset popped successfully", "asset": asset.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/increase")
def increase_pool_quantity(database_url: str, data: dict):
    """
    Increase the quantity of a pool resource.
    """
    try:
        pool = Pool(**data["pool"])
        amount = data["amount"]
        interface = ResourceInterface(database_url=database_url)
        interface.increase_pool_quantity(pool, amount)
        return {"message": "Pool quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/decrease")
def decrease_pool_quantity(database_url: str, data: dict):
    """
    Decrease the quantity of a pool resource.
    """
    try:
        pool = Pool(**data["pool"])
        amount = data["amount"]
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_pool_quantity(pool, amount)
        return {"message": "Pool quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/empty")
def empty_pool(database_url: str, data: dict):
    """
    Empty a pool resource by setting its quantity to zero.
    """
    try:
        pool = Pool(**data["pool"])
        interface = ResourceInterface(database_url=database_url)
        interface.empty_pool(pool)
        return {"message": "Pool emptied successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pool/fill")
def fill_pool(database_url: str, data: dict):
    """
    Fill a pool resource to its maximum capacity.
    """
    try:
        pool = Pool(**data["pool"])
        interface = ResourceInterface(database_url=database_url)
        interface.fill_pool(pool)
        return {"message": "Pool filled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/increase_well")
def increase_plate_well(database_url: str, data: dict):
    """
    Increase the quantity in a specific well of a plate.
    """
    try:
        plate = Plate(**data["plate"])
        well_id = data["well_id"]
        quantity = data["quantity"]
        interface = ResourceInterface(database_url=database_url)
        interface.increase_plate_well(plate, well_id, quantity)
        return {"message": "Well quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/decrease_well")
def decrease_plate_well(database_url: str, data: dict):
    """
    Decrease the quantity in a specific well of a plate.
    """
    try:
        plate = Plate(**data["plate"])
        well_id = data["well_id"]
        quantity = data["quantity"]
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_plate_well(plate, well_id, quantity)
        return {"message": "Well quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plate/update_well")
def update_plate_well(database_url: str, data: dict):
    """
    Update a specific well in a plate.
    """
    try:
        plate = Plate(**data["plate"])
        well_id = data["well_id"]
        pool = Pool(**data["child"])
        interface = ResourceInterface(database_url=database_url)
        interface.update_plate_well(plate, well_id, pool)
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
