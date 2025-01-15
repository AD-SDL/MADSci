from fastapi import FastAPI, HTTPException
from resource_interface import ResourceInterface
from madsci.common.types.resource_types import ResourceBase
from db_tables import Stack, Queue, Pool, Plate, Asset
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

@app.post("/resources/add")
def add_resource(database_url: str, resource: ResourceBase):
    """
    Add a resource to the database.
    """
    try:
        interface = ResourcesInterface(database_url=database_url)
        saved_resource = interface.add_resource(resource)
        return {"message": "Resource added successfully", "resource_id": saved_resource.resource_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/push")
def push_to_stack(database_url: str, stack: Stack, asset: Asset):
    """
    Push an asset onto a stack.
    """
    try:
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
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
        interface = ResourcesInterface(database_url=database_url)
        interface.update_plate_well(plate, well_id, pool)
        return {"message": "Well updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources/get")
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
        interface = ResourcesInterface(database_url=database_url)
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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.plugin_config.host,
        port=resource_manager_definition.plugin_config.port,
    )
