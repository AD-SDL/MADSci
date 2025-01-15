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
        if not resource_type or resource_type not in RESOURCE_TYPE_MAP:
            raise ValueError(f"Unknown or missing resource_type: {resource_type}")

        # Reconstruct the resource object dynamically
        resource_class = RESOURCE_TYPE_MAP[resource_type]
        resource_obj = resource_class(**resource)

        # Pass the resource object to the interface
        interface = ResourceInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource_obj)

        return {"message": "Resource added successfully", "resource_id": saved_resource.resource_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/resource/get")
def get_resource(
    database_url: str,
    resource_name: str = None,
    owner_name: str = None,
    resource_id: str = None,
    resource_type: str = None
):
    """
    Retrieve a resource from the database.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        resource = interface.get_resource(
            resource_name=resource_name,
            owner_name=owner_name,
            resource_id=resource_id,
            resource_type=resource_type
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        return {"message": "Resource retrieved successfully", "resource": resource.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/push")
def push_to_stack(database_url: str, stack: Stack, asset: Asset):
    """
    Push an asset onto a stack.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_stack(stack, asset)
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/pop")
def pop_from_stack(database_url: str, stack: Stack):
    """
    Pop an asset from a stack.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_stack(stack)
        return {"message": "Asset popped successfully", "asset": asset.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/push")
def push_to_queue(database_url: str, queue: Queue, asset: Asset):
    """
    Push an asset onto a queue.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.push_to_queue(queue, asset)
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/pop")
def pop_from_queue(database_url: str, queue: Queue):
    """
    Pop an asset from a queue.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        asset = interface.pop_from_queue(queue)
        return {"message": "Asset popped successfully", "asset": asset.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/increase")
def increase_pool_quantity(database_url: str, pool: Pool, amount: float):
    """
    Increase the quantity of a pool resource.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.increase_pool_quantity(pool, amount)
        return {"message": "Pool quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/decrease")
def decrease_pool_quantity(database_url: str, pool: Pool, amount: float):
    """
    Decrease the quantity of a pool resource.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_pool_quantity(pool, amount)
        return {"message": "Pool quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/empty")
def empty_pool(database_url: str, pool: Pool):
    """
    Empty a pool resource by setting its quantity to zero.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.empty_pool(pool)
        return {"message": "Pool emptied successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pool/fill")
def fill_pool(database_url: str, pool: Pool):
    """
    Fill a pool resource to its maximum capacity.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.fill_pool(pool)
        return {"message": "Pool filled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plate/well/increase")
def increase_plate_well(database_url: str, plate: Plate, well_id: str, quantity: float):
    """
    Increase the quantity in a specific well of a plate.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.increase_plate_well(plate, well_id, quantity)
        return {"message": "Well quantity increased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plate/well/decrease")
def decrease_plate_well(database_url: str, plate: Plate, well_id: str, quantity: float):
    """
    Decrease the quantity in a specific well of a plate.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.decrease_plate_well(plate, well_id, quantity)
        return {"message": "Well quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plate/well/update")
def update_plate_well(database_url: str, plate: Plate, well_id: str, pool: Pool):
    """
    Update a specific well in a plate.
    """
    try:
        interface = ResourceInterface(database_url=database_url)
        interface.update_plate_well(plate, well_id, pool)
        return {"message": "Well updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print(resource_manager_definition.plugin_config.host)
    print(resource_manager_definition.plugin_config.port)
    uvicorn.run(
        app,
        host=resource_manager_definition.plugin_config.host,
        port=resource_manager_definition.plugin_config.port,
    )
