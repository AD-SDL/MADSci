"""Fast API Server for Resources"""

from pathlib import Path
from typing import Any, Callable, Optional, Union

import fastapi
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Body
from madsci.client.event_client import EventClient
from madsci.common.ownership import global_ownership_info
from madsci.common.types.resource_types import (
    ContainerDataModels,
    Queue,
    Resource,
    ResourceDataModels,
    Slot,
    Stack,
)
from madsci.common.types.resource_types.definitions import (
    ResourceDefinitions,
    ResourceManagerDefinition,
    ResourceManagerSettings,
)
from madsci.common.types.resource_types.server_types import (
    CreateResourceFromTemplateBody,
    PushResourceBody,
    RemoveChildBody,
    ResourceGetQuery,
    ResourceHistoryGetQuery,
    SetChildBody,
    TemplateCreateBody,
    TemplateGetQuery,
    TemplateUpdateBody,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_tables import ResourceHistoryTable
from sqlalchemy.exc import NoResultFound


def create_resource_server(  # noqa: C901, PLR0915
    resource_manager_definition: Optional[ResourceManagerDefinition] = None,
    resource_server_settings: Optional[ResourceManagerSettings] = None,
    resource_interface: Optional[ResourceInterface] = None,
) -> FastAPI:
    """Creates a Resource Manager's REST server."""
    logger = EventClient()
    resource_server_settings = resource_server_settings or ResourceManagerSettings()
    logger.log_info(resource_server_settings)

    if not resource_manager_definition:
        def_path = Path(
            resource_server_settings.resource_manager_definition
        ).expanduser()
        if def_path.exists():
            resource_manager_definition = ResourceManagerDefinition.from_yaml(
                def_path,
            )
        else:
            resource_manager_definition = ResourceManagerDefinition()
        logger.log_info(f"Writing to resource manager definition file: {def_path}")
        resource_manager_definition.to_yaml(def_path)

    global_ownership_info.manager_id = resource_manager_definition.resource_manager_id
    logger = EventClient(name=f"resource_manager.{resource_manager_definition.name}")
    logger.log_info(resource_manager_definition)

    if not resource_interface:
        resource_interface = ResourceInterface(
            url=resource_server_settings.db_url, logger=logger
        )
        logger.info(resource_interface)
        logger.info(resource_interface.session)

    app = FastAPI()

    @app.middleware("http")
    async def ownership_middleware(
        request: fastapi.Request, call_next: Callable
    ) -> fastapi.Response:
        global_ownership_info.manager_id = (
            resource_manager_definition.resource_manager_id
        )
        return await call_next(request)

    @app.get("/")
    @app.get("/info")
    @app.get("/definition")
    def info() -> ResourceManagerDefinition:
        """Get information about the resource manager."""
        return resource_manager_definition

    @app.post("/resource/init")
    async def init_resource(
        resource_definition: ResourceDefinitions = Body(...),  # noqa: B008
    ) -> ResourceDataModels:
        """
        Initialize a resource in the database based on a definition. If a matching resource already exists, it will be returned.
        """
        try:
            resource = resource_interface.get_resource(
                **resource_definition.model_dump(exclude_none=True),
                multiple=False,
                unique=True,
            )
            if not resource:
                if (
                    resource_definition.resource_class
                    and resource_definition.resource_class
                    in resource_manager_definition.custom_types
                ):
                    custom_definition = resource_manager_definition.custom_types[
                        resource_definition.resource_class
                    ]
                    resource = resource_interface.init_custom_resource(
                        resource_definition, custom_definition
                    )
                else:
                    resource = resource_interface.add_resource(
                        Resource.discriminate(resource_definition)
                    )

            return resource
        except Exception as e:
            logger.error(e)
            raise e

    @app.post("/resource/add")
    async def add_resource(
        resource: ResourceDataModels = Body(..., discriminator="base_type"),  # noqa: B008
    ) -> ResourceDataModels:
        """
        Add a new resource to the Resource Manager.
        """
        try:
            return resource_interface.add_resource(resource)
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/add_or_update")
    async def add_or_update_resource(
        resource: ResourceDataModels = Body(..., discriminator="base_type"),  # noqa: B008
    ) -> ResourceDataModels:
        """
        Add a new resource to the Resource Manager.
        """
        try:
            return resource_interface.add_or_update_resource(resource)
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/update")
    async def update_resource(
        resource: ResourceDataModels = Body(..., discriminator="base_type"),  # noqa: B008
    ) -> ResourceDataModels:
        """
        Update or refresh a resource in the database, including its children.
        """
        try:
            return resource_interface.update_resource(resource)
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
            return resource_interface.remove_resource(resource_id)
        except NoResultFound as e:
            logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/resource/{resource_id}")
    async def get_resource(resource_id: str) -> ResourceDataModels:
        """
        Retrieve a resource from the database by ID.
        """
        try:
            resource = resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            return resource
        except Exception as e:
            logger.error(e)
            raise

    @app.post("/resource/query")
    async def query_resource(
        query: ResourceGetQuery = Body(...),  # noqa: B008
    ) -> Union[ResourceDataModels, list[ResourceDataModels]]:
        """
        Retrieve a resource from the database based on the specified parameters.
        """
        try:
            resource = resource_interface.get_resource(
                **query.model_dump(exclude_none=True),
            )
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            return resource
        except Exception as e:
            logger.error(e)
            raise e

    @app.post("/history/query")
    async def query_history(
        query: ResourceHistoryGetQuery = Body(...),  # noqa: B008
    ) -> list[ResourceHistoryTable]:
        """
        Retrieve the history of a resource.

        Args:
            query (ResourceHistoryGetQuery): The query parameters.

        Returns:
            list[ResourceHistoryTable]: A list of historical resource entries.
        """
        try:
            return resource_interface.query_history(
                **query.model_dump(exclude_none=True)
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

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
            restored_resource = resource_interface.restore_resource(
                resource_id=resource_id
            )
            if not restored_resource:
                raise HTTPException(
                    status_code=404,
                    detail=f"No removed resource with ID '{resource_id}'.",
                )

            return restored_resource
        except Exception as e:
            logger.error(e)
            raise e

    @app.post("/templates")
    async def create_template(body: TemplateCreateBody) -> ResourceDataModels:
        """Create a new resource template from a resource."""
        try:
            return resource_interface.create_template(
                resource=body.resource,
                template_name=body.template_name,
                description=body.description,
                required_overrides=body.required_overrides,
                tags=body.tags,
                created_by=body.created_by,
                version=body.version,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/templates/query")
    async def list_templates(query: TemplateGetQuery) -> list[ResourceDataModels]:
        """List templates with optional filtering."""
        try:
            return resource_interface.list_templates(
                base_type=query.base_type,
                tags=query.tags,
                created_by=query.created_by,
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/templates")
    async def list_templates_simple() -> list[ResourceDataModels]:
        """List all templates (simple endpoint without filtering)."""
        try:
            return resource_interface.list_templates()
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/templates/categories")
    async def get_templates_by_category() -> dict[str, list[str]]:
        """Get templates organized by base_type category."""
        try:
            logger.info("Fetching templates by category")
            return resource_interface.get_templates_by_category()
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/templates/{template_name}")
    async def get_template(template_name: str) -> ResourceDataModels:
        """Get a template by name."""
        try:
            template = resource_interface.get_template(template_name)
            if not template:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return template
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/templates/{template_name}/info")
    async def get_template_info(template_name: str) -> dict[str, Any]:
        """Get detailed template metadata."""
        try:
            template_info = resource_interface.get_template_info(template_name)
            if not template_info:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return template_info
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.put("/templates/{template_name}")
    async def update_template(
        template_name: str, body: TemplateUpdateBody
    ) -> ResourceDataModels:
        """Update an existing template."""
        try:
            updates = body.updates.copy()

            return resource_interface.update_template(template_name, updates)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.delete("/templates/{template_name}")
    async def delete_template(template_name: str) -> dict[str, str]:
        """Delete a template from the database."""
        try:
            deleted = resource_interface.delete_template(template_name)
            if not deleted:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return {"message": f"Template '{template_name}' deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/templates/{template_name}/create_resource")
    async def create_resource_from_template(
        template_name: str, body: CreateResourceFromTemplateBody
    ) -> ResourceDataModels:
        """Create a resource from a template."""
        try:
            return resource_interface.create_resource_from_template(
                template_name=template_name,
                resource_name=body.resource_name,
                overrides=body.overrides,
                add_to_database=body.add_to_database,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/push")
    async def push(
        resource_id: str, body: PushResourceBody
    ) -> Union[Stack, Queue, Slot]:
        """
        Push a resource onto a stack or queue.

        Args:
            resource_id (str): The ID of the stNetworkErrorack or queue to push the resource onto.
            body (PushResourceBody): The resource to push onto the stack or queue, or the ID of an existing resource.

        Returns:
            Union[Stack, Queue, Slot]: The updated stack or queue.
        """
        try:
            return resource_interface.push(
                parent_id=resource_id, child=body.child if body.child else body.child_id
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/pop")
    async def pop(
        resource_id: str,
    ) -> tuple[ResourceDataModels, Union[Stack, Queue, Slot]]:
        """
        Pop an asset from a stack or queue.

        Args:
            resource_id (str): The ID of the stack or queue to pop the asset from.

        Returns:
            tuple[ResourceDataModels, Union[Stack, Queue, Slot]]: The popped asset and the updated stack or queue.
        """
        try:
            return resource_interface.pop(parent_id=resource_id)
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

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
            return resource_interface.set_child(
                container_id=resource_id, key=body.key, child=body.child
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/child/remove")
    async def remove_child(
        resource_id: str, body: RemoveChildBody
    ) -> ContainerDataModels:
        """
        Remove a child resource from a parent resource. Must be a container type that supports random access.

        Args:
            resource_id (str): The ID of the parent resource.
            body (RemoveChildBody): The body of the request.

        Returns:
            ResourceDataModels: The updated parent resource.
        """
        try:
            return resource_interface.remove_child(
                container_id=resource_id, key=body.key
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/quantity")
    async def set_quantity(
        resource_id: str, quantity: Union[float, int]
    ) -> ResourceDataModels:
        """
        Set the quantity of a resource.

        Args:
            resource_id (str): The ID of the resource.
            quantity (Union[float, int]): The quantity to set.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return resource_interface.set_quantity(
                resource_id=resource_id, quantity=quantity
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/quantity/change_by")
    async def change_quantity_by(
        resource_id: str, amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Change the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to change the quantity by.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            resource = resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return resource_interface.set_quantity(
                resource_id=resource_id, quantity=resource.quantity + amount
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/quantity/increase")
    async def increase_quantity(
        resource_id: str, amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Increase the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to increase the quantity by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            resource = resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return resource_interface.set_quantity(
                resource_id=resource_id, quantity=resource.quantity + abs(amount)
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/quantity/decrease")
    async def decrease_quantity(
        resource_id: str, amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Decrease the quantity of a resource by a given amount.

        Args:
            resource_id (str): The ID of the resource.
            amount (Union[float, int]): The amount to decrease the quantity by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            resource = resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return resource_interface.set_quantity(
                resource_id=resource_id,
                quantity=max(resource.quantity - abs(amount), 0),
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/capacity")
    async def set_capacity(
        resource_id: str, capacity: Union[float, int]
    ) -> ResourceDataModels:
        """
        Set the capacity of a resource.

        Args:
            resource_id (str): The ID of the resource.
            capacity (Union[float, int]): The capacity to set.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return resource_interface.set_capacity(
                resource_id=resource_id, capacity=capacity
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

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
            return resource_interface.remove_capacity_limit(resource_id=resource_id)
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/empty")
    async def empty_resource(resource_id: str) -> ResourceDataModels:
        """
        Empty the contents of a container or consumable resource.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return resource_interface.empty(resource_id=resource_id)
        except NoResultFound as e:
            logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/fill")
    async def fill_resource(resource_id: str) -> ResourceDataModels:
        """
        Fill a consumable resource to capacity.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return resource_interface.fill(resource_id=resource_id)
        except NoResultFound as e:
            logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/resource/{resource_id}/lock")
    async def acquire_resource_lock(
        resource_id: str,
        lock_duration: float = 300.0,
        client_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Acquire a lock on a resource.

        Args:
            resource_id (str): The ID of the resource to lock.
            lock_duration (float): Lock duration in seconds.
            client_id (Optional[str]): Client identifier.

        Returns:
            dict: Lock acquisition result.
        """
        try:
            locked_resource = resource_interface.acquire_lock(
                resource=resource_id,
                lock_duration=lock_duration,
                client_id=client_id,
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Handle the response outside the try-except
        if locked_resource:
            return locked_resource.model_dump(mode="json")
        raise HTTPException(
            status_code=409,  # Conflict - resource already locked
            detail=f"Resource {resource_id} is already locked or lock acquisition failed",
        )

    @app.delete("/resource/{resource_id}/unlock")
    async def release_resource_lock(
        resource_id: str, client_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Release a lock on a resource.

        Args:
            resource_id (str): The ID of the resource to unlock.
            client_id (Optional[str]): Client identifier.

        Returns:
            dict: Lock release result.
        """
        try:
            unlocked_resource = resource_interface.release_lock(
                resource=resource_id,
                client_id=client_id,
            )
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

        if unlocked_resource:
            return unlocked_resource.model_dump(mode="json")
        # Return a proper error response instead of None
        raise HTTPException(
            status_code=403,
            detail=f"Cannot release lock on resource {resource_id}: not owned by client {client_id}",
        )

    @app.get("/resource/{resource_id}/check_lock")
    async def check_resource_lock(resource_id: str) -> dict[str, Any]:
        """
        Check if a resource is currently locked.

        Args:
            resource_id (str): The ID of the resource to check.

        Returns:
            dict: Lock status information.
        """
        try:
            is_locked, locked_by = resource_interface.is_locked(resource=resource_id)
            return {
                "resource_id": resource_id,
                "is_locked": is_locked,
                "locked_by": locked_by,
            }
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


if __name__ == "__main__":
    import uvicorn

    resource_server_settings = ResourceManagerSettings()
    app = create_resource_server(
        resource_server_settings=resource_server_settings,
    )
    uvicorn.run(
        app,
        host=resource_server_settings.resource_server_url.host,
        port=resource_server_settings.resource_server_url.port,
    )
