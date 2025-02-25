"""Fast API Server for Resources"""

import logging
from typing import Union

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from madsci.common.types.resource_types import (
    ContainerDataModels,
    Queue,
    ResourceDataModels,
    Stack,
)
from madsci.common.types.resource_types.server_types import (
    PushResourceBody,
    RemoveChildBody,
    ResourceGetQuery,
    ResourceHistoryGetQuery,
    SetChildBody,
)
from madsci.common.types.squid_types import (
    ResourceManagerDefinition,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_tables import ResourceHistoryTable

logger = logging.getLogger(__name__)

app = FastAPI()

resource_manager_definition = ResourceManagerDefinition(
    name="Resource Manager 1",
    manager_type="resource_manager",
    description="The First MADSci Resource Manager.",
)
resource_manager_definition.url = f"https://{resource_manager_definition.manager_config.host}:{resource_manager_definition.manager_config.port}"
DB_URL = resource_manager_definition.manager_config.db_url

interface = ResourceInterface(connection=DB_URL)

@app.get("/info")
def info() -> ResourceManagerDefinition:
    """Get information about the resource manager."""
    return resource_manager_definition


@app.post("/resource/add")
async def add_resource(resource: ResourceDataModels) -> ResourceDataModels:
    """
    Add a new resource to the Resource Manager.
    """
    try:
        return interface.add_resource(resource)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/resource/update")
async def update_resource(resource: ResourceDataModels) -> ResourceDataModels:
    """
    Update or refresh a resource in the database, including its children.
    """
    try:
        return interface.update_resource(resource)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/resource/{resource_id}")
async def remove_resource(resource_id: str) -> ResourceDataModels:
    """
    Marks a resource as removed. This will remove the resource from the active resources table,
    but it will still be available in the history table.
    """
    try:
        return interface.remove_resource(resource_id)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/resource/{resource_id}")
async def get_resource(resource_id: str) -> ResourceDataModels:
    """
    Retrieve a resource from the database by ID.
    """
    try:
        resource = interface.get_resource(resource_id=resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        return resource
    except Exception as e:
        logger.error(e)

@app.post("/resource/query")
async def query_resource(query: ResourceGetQuery) -> ResourceDataModels:
    """
    Retrieve a resource from the database based on the specified parameters.
    """
    try:
        resource = interface.get_resource(
            **query.model_dump(exclude_none=True),
            unique=True
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        return resource
    except Exception as e:
        logger.error(e)


@app.post("/history/query")
async def query_history(query: ResourceHistoryGetQuery) -> list[ResourceHistoryTable]:
    """
    Retrieve the history of a resource.

    Args:
        query (ResourceHistoryGetQuery): The query parameters.

    Returns:
        list[ResourceHistoryTable]: A list of historical resource entries.
    """
    try:
        return interface.query_history(
            **query.model_dump(exclude_none=True)
        )
    except Exception as e:
        logger.error(e)


@app.post("/history/{resource_id}/restore")
async def restore_deleted_resource(resource_id: str) -> ResourceDataModels:
    """
    Restore a previously deleted resource from the history table.

    Args:
        resource_id (str): the id of the resource to restore.

    Returns:
        ResourceDataModels: The restored resource.
    """
    try:
        # Fetch the most recent deleted entry
        restored_resource = interface.restore_resource(
            resource_id=resource_id
        )
        if not restored_resource:
            raise HTTPException(
                status_code=404,
                detail=f"No deleted history found for resource ID '{resource_id}'.",
            )

        return restored_resource
    except Exception as e:
        logger.error(e)


@app.post("/resource/{resource_id}/push")
async def push(resource_id: str, body: PushResourceBody) -> Union[Stack, Queue]:
    """
    Push a resource onto a stack or queue.

    Args:
        resource_id (str): The ID of the stack or queue to push the resource onto.
        body (PushResourceBody): The resource to push onto the stack or queue, or the ID of an existing resource.

    Returns:
        Union[Stack, Queue]: The updated stack or queue.
    """
    try:
        return interface.push(parent_id=resource_id, child=body.child if body.child else body.child_id)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))


@app.post("/resource/{resource_id}/pop")
async def pop(resource_id: str) -> tuple[ResourceDataModels, Union[Stack, Queue]]:
    """
    Pop an asset from a stack or queue.

    Args:
        resource_id (str): The ID of the stack or queue to pop the asset from.

    Returns:
        tuple[ResourceDataModels, Union[Stack, Queue]]: The popped asset and the updated stack or queue.
    """
    try:
        return interface.pop(parent_id=resource_id)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))

@app.post("/resource/{resource_id}/child/set")
async def set_child(resource_id: str, body: SetChildBody) -> ContainerDataModels:
    """
    Set a child resource for a parent resource. Must be a container type that supports random access.

    Args:
        resource_id (str): The ID of the parent resource.
        body (SetChildBody): The body of the request.

    Returns:
        ResourceDataModels: The updated parent resource.
    """
    try:
        return interface.set_child(container_id=resource_id, key=body.key, child=body.child)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))

@app.post("/resource/{resource_id}/child/remove")
async def remove_child(resource_id: str, body: RemoveChildBody) -> ContainerDataModels:
    """
    Remove a child resource from a parent resource. Must be a container type that supports random access.

    Args:
        resource_id (str): The ID of the parent resource.
        body (RemoveChildBody): The body of the request.

    Returns:
        ResourceDataModels: The updated parent resource.
    """
    try:
        return interface.remove_child(container_id=resource_id, key=body.key)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))


@app.post("/resource/{resource_id}/quantity")
async def set_quantity(resource_id: str, quantity: Union[float, int]) -> ResourceDataModels:
    """
    Set the quantity of a resource.

    Args:
        resource_id (str): The ID of the resource.
        quantity (Union[float, int]): The quantity to set.

    Returns:
        ResourceDataModels: The updated resource.
    """
    try:
        return interface.set_quantity(resource_id=resource_id, quantity=quantity)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))

@app.post("/resource/{resource_id}/capacity")
async def set_capacity(resource_id: str, capacity: Union[float, int]) -> ResourceDataModels:
    """
    Set the capacity of a resource.

    Args:
        resource_id (str): The ID of the resource.
        capacity (Union[float, int]): The capacity to set.

    Returns:
        ResourceDataModels: The updated resource.
    """
    try:
        return interface.set_capacity(resource_id=resource_id, capacity=capacity)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))

@app.delete("/resource/{resource_id}/capacity")
async def remove_capacity_limit(resource_id: str) -> ResourceDataModels:
    """
    Remove the capacity limit of a resource.

    Args:
        resource_id (str): The ID of the resource.

    Returns:
        ResourceDataModels: The updated resource.
    """
    try:
        return interface.remove_capacity(resource_id=resource_id)
    except Exception as e:
        logger.error(e)
        return HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
