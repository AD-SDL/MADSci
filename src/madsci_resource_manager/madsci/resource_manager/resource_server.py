"""Resource Manager server implementation, extending th AbstractBaseManager class."""

from typing import Any, Callable, Optional, Union

import fastapi
from classy_fastapi import delete, get, post, put
from fastapi import HTTPException
from fastapi.params import Body
from madsci.common.manager_base import AbstractManagerBase
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
    ResourceManagerHealth,
    ResourceManagerSettings,
)
from madsci.common.types.resource_types.server_types import (
    CreateResourceFromTemplateBody,
    PushResourceBody,
    RemoveChildBody,
    ResourceGetQuery,
    ResourceHierarchy,
    ResourceHistoryGetQuery,
    SetChildBody,
    TemplateCreateBody,
    TemplateGetQuery,
    TemplateUpdateBody,
)
from madsci.resource_manager.database_version_checker import (
    DatabaseVersionChecker,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_tables import ResourceHistoryTable
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

# Module-level constants for Body() calls to avoid B008 linting errors
RESOURCE_DEFINITION_BODY_PARAM = Body(...)
RESOURCE_BODY_WITH_DISCRIMINATOR_PARAM = Body(..., discriminator="base_type")
QUERY_BODY_PARAM = Body(...)
HISTORY_QUERY_BODY_PARAM = Body(...)


class ResourceManager(
    AbstractManagerBase[ResourceManagerSettings, ResourceManagerDefinition]
):
    """Resource Manager REST Server."""

    SETTINGS_CLASS = ResourceManagerSettings
    DEFINITION_CLASS = ResourceManagerDefinition

    def __init__(
        self,
        settings: Optional[ResourceManagerSettings] = None,
        definition: Optional[ResourceManagerDefinition] = None,
        resource_interface: Optional[ResourceInterface] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Resource Manager."""
        # Store additional dependencies before calling super().__init__
        self._resource_interface = resource_interface
        self._external_resource_interface = resource_interface is not None

        super().__init__(settings=settings, definition=definition, **kwargs)

        # Initialize the resource interface
        self._setup_resource_interface()

        # Set up ownership middleware
        self._setup_ownership()

        # Initialize default templates after everything is set up
        self._initialize_default_templates()

    def _setup_resource_interface(self) -> None:
        """Setup the resource interface."""
        if not self._resource_interface:
            self._resource_interface = ResourceInterface(
                url=self.settings.db_url, logger=self.logger
            )
            self.logger.info(self._resource_interface)
            self.logger.info(self._resource_interface.session)

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if external resource_interface was provided (e.g., in tests)
        # This is commonly done in tests where a mock or containerized database is used
        if self._external_resource_interface:
            # External interface provided, likely in test context - skip version validation
            self.logger.info(
                "External resource_interface provided, skipping database version validation"
            )
            return

        # DATABASE VERSION VALIDATION AND AUTO-INITIALIZATION
        self.logger.info("Validating database schema version...")

        version_checker = DatabaseVersionChecker(self.settings.db_url, self.logger)
        # Validate database version
        # - Return silently if no version tracking (with helpful log message)
        # - Return silently if version matches
        # - Raise error if version mismatches (with helpful log message)
        try:
            version_checker.validate_or_fail()
            self.logger.info("Database version validation completed successfully")
        except RuntimeError as e:
            self.logger.error(
                "DATABASE VERSION MISMATCH DETECTED! SERVER STARTUP ABORTED!"
            )
            raise e

    def _setup_ownership(self) -> None:
        """Setup ownership information."""
        # Use resource_manager_id as the primary field, but support manager_id for compatibility
        manager_id = getattr(
            self.definition,
            "resource_manager_id",
            getattr(self.definition, "manager_id", None),
        )
        global_ownership_info.manager_id = manager_id

    def _initialize_default_templates(self) -> None:
        """Create or update default templates defined in the manager definition."""
        if not self.definition.default_templates:
            return

        self.logger.info(
            f"Initializing {len(self.definition.default_templates)} default templates"
        )

        for template_def in self.definition.default_templates:
            try:
                # Convert the base resource definition to a Resource instance
                base_resource = Resource.discriminate(template_def.base_resource)

                # Create or update the template
                self._resource_interface.create_template(
                    resource=base_resource,
                    template_name=template_def.template_name,
                    description=template_def.description
                    or f"Template for {template_def.template_name}",
                    required_overrides=template_def.required_overrides,
                    tags=template_def.tags,
                    created_by=f"resource_manager_{self.definition.resource_manager_id}",
                    version=template_def.version,
                )

                self.logger.info(
                    f"Successfully initialized template '{template_def.template_name}'"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize template '{template_def.template_name}': {e}"
                )
                # Continue with other templates even if one fails

    def create_server(self) -> fastapi.FastAPI:
        """Create and configure the FastAPI server with middleware."""
        app = super().create_server()

        @app.middleware("http")
        async def ownership_middleware(
            request: fastapi.Request, call_next: Callable
        ) -> fastapi.Response:
            # Use resource_manager_id as the primary field, but support manager_id for compatibility
            manager_id = getattr(
                self.definition,
                "resource_manager_id",
                getattr(self.definition, "manager_id", None),
            )
            global_ownership_info.manager_id = manager_id
            return await call_next(request)

        return app

    def get_health(self) -> ResourceManagerHealth:
        """Get the health status of the Resource Manager."""
        health = ResourceManagerHealth()

        try:
            # Test database connection and get resource count
            with self._resource_interface.get_session() as session:
                session.execute(text("SELECT 1")).fetchone()
                health.db_connected = True

                try:
                    # Get total resources count (may fail if table doesn't exist)
                    result = session.execute(
                        text("SELECT COUNT(*) FROM resource")
                    ).fetchone()
                    health.total_resources = result[0] if result else 0
                except Exception:
                    # Table might not exist yet - this is OK for health check
                    health.total_resources = 0

            health.healthy = True
            health.description = "Resource Manager is running normally"

        except Exception as e:
            health.healthy = False
            health.db_connected = False
            health.description = f"Database connection failed: {e!s}"

        return health

    @post("/resource/init")
    async def init_resource(
        self, resource_definition: ResourceDefinitions = RESOURCE_DEFINITION_BODY_PARAM
    ) -> ResourceDataModels:
        """
        Initialize a resource in the database based on a definition. If a matching resource already exists, it will be returned.
        """
        try:
            resource = self._resource_interface.get_resource(
                **resource_definition.model_dump(exclude_none=True),
                multiple=False,
                unique=True,
            )
            if not resource:
                resource = self._resource_interface.add_resource(
                    Resource.discriminate(resource_definition)
                )

            return resource
        except Exception as e:
            self.logger.error(e)
            raise e

    @post("/resource/add")
    async def add_resource(
        self, resource: ResourceDataModels = RESOURCE_BODY_WITH_DISCRIMINATOR_PARAM
    ) -> ResourceDataModels:
        """
        Add a new resource to the Resource Manager.
        """
        try:
            return self._resource_interface.add_resource(resource)
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/add_or_update")
    async def add_or_update_resource(
        self, resource: ResourceDataModels = RESOURCE_BODY_WITH_DISCRIMINATOR_PARAM
    ) -> ResourceDataModels:
        """
        Add a new resource to the Resource Manager.
        """
        try:
            return self._resource_interface.add_or_update_resource(resource)
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/update")
    async def update_resource(
        self, resource: ResourceDataModels = RESOURCE_BODY_WITH_DISCRIMINATOR_PARAM
    ) -> ResourceDataModels:
        """
        Update or refresh a resource in the database, including its children.
        """
        try:
            return self._resource_interface.update_resource(resource)
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @delete("/resource/{resource_id}")
    async def remove_resource(self, resource_id: str) -> ResourceDataModels:
        """
        Marks a resource as removed. This will remove the resource from the active resources table,
        but it will still be available in the history table.
        """
        try:
            return self._resource_interface.remove_resource(resource_id)
        except NoResultFound as e:
            self.logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/resource/{resource_id}")
    async def get_resource(self, resource_id: str) -> ResourceDataModels:
        """
        Retrieve a resource from the database by ID.
        """
        try:
            resource = self._resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            return resource
        except Exception as e:
            self.logger.error(e)
            raise

    @post("/resource/query")
    async def query_resource(
        self, query: ResourceGetQuery = QUERY_BODY_PARAM
    ) -> Union[ResourceDataModels, list[ResourceDataModels]]:
        """
        Retrieve a resource from the database based on the specified parameters.
        """
        try:
            resource = self._resource_interface.get_resource(
                **query.model_dump(exclude_none=True),
            )
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")

            return resource
        except Exception as e:
            self.logger.error(e)
            raise e

    @post("/history/query")
    async def query_history(
        self, query: ResourceHistoryGetQuery = HISTORY_QUERY_BODY_PARAM
    ) -> list[ResourceHistoryTable]:
        """
        Retrieve the history of a resource.

        Args:
            query (ResourceHistoryGetQuery): The query parameters.

        Returns:
            list[ResourceHistoryTable]: A list of historical resource entries.
        """
        try:
            return self._resource_interface.query_history(
                **query.model_dump(exclude_none=True)
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/history/{resource_id}/restore")
    async def restore_deleted_resource(self, resource_id: str) -> ResourceDataModels:
        """
        Restore a previously deleted resource from the history table.

        Args:
            resource_id (str): the id of the resource to restore.

        Returns:
            ResourceDataModels: The restored resource.
        """
        try:
            # Fetch the most recent deleted entry
            restored_resource = self._resource_interface.restore_resource(
                resource_id=resource_id
            )
            if not restored_resource:
                raise HTTPException(
                    status_code=404,
                    detail=f"No removed resource with ID '{resource_id}'.",
                )

            return restored_resource
        except Exception as e:
            self.logger.error(e)
            raise e

    @post("/templates")
    async def create_template(self, body: TemplateCreateBody) -> ResourceDataModels:
        """Create a new resource template from a resource."""
        try:
            return self._resource_interface.create_template(
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
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/templates/query")
    async def query_templates(
        self, query: TemplateGetQuery
    ) -> list[ResourceDataModels]:
        """Query templates with optional filtering."""
        try:
            return self._resource_interface.query_templates(
                base_type=query.base_type,
                tags=query.tags,
                created_by=query.created_by,
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/templates")
    async def list_templates(self) -> list[ResourceDataModels]:
        """List all templates."""
        try:
            return self._resource_interface.query_templates()
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/templates/categories")
    async def get_templates_by_category(self) -> dict[str, list[str]]:
        """Get templates organized by base_type category."""
        try:
            self.logger.info("Fetching templates by category")
            return self._resource_interface.get_templates_by_category()
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/template/{template_name}")
    async def get_template(self, template_name: str) -> ResourceDataModels:
        """Get a template by name."""
        try:
            template = self._resource_interface.get_template(template_name)
            if not template:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return template
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/template/{template_name}/info")
    async def get_template_info(self, template_name: str) -> dict[str, Any]:
        """Get detailed template metadata."""
        try:
            template_info = self._resource_interface.get_template_info(template_name)
            if not template_info:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return template_info
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @put("/template/{template_name}")
    async def update_template(
        self, template_name: str, body: TemplateUpdateBody
    ) -> ResourceDataModels:
        """Update an existing template."""
        try:
            updates = body.updates.copy()

            return self._resource_interface.update_template(template_name, updates)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @delete("/template/{template_name}")
    async def delete_template(self, template_name: str) -> dict[str, str]:
        """Delete a template from the database."""
        try:
            deleted = self._resource_interface.delete_template(template_name)
            if not deleted:
                raise HTTPException(
                    status_code=404, detail=f"Template '{template_name}' not found"
                )
            return {"message": f"Template '{template_name}' deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/template/{template_name}/create_resource")
    async def create_resource_from_template(
        self, template_name: str, body: CreateResourceFromTemplateBody
    ) -> ResourceDataModels:
        """
        Create a resource from a template.

        If a matching resource already exists (based on name, class, type, owner, and any overrides),
        it will be returned instead of creating a duplicate.
        """
        try:
            # Get the template to understand what properties to search for
            template = self._resource_interface.get_template(template_name)

            if not template:
                raise ValueError(f"Template '{template_name}' not found")

            # Build search criteria from template defaults and overrides
            search_criteria = {
                "resource_name": body.resource_name,
                "resource_class": template.resource_class,
                "base_type": template.base_type,
            }

            # Add owner to search criteria if present in overrides
            if body.overrides and "owner" in body.overrides:
                search_criteria["owner"] = body.overrides["owner"]

            # Add all override fields to search criteria
            if body.overrides:
                for field, value in body.overrides.items():
                    search_criteria[field] = value

            # Check if matching resources exist
            existing_resources = self._resource_interface.get_resource(
                **search_criteria,
                multiple=True,
            )

            # If exactly one match found, return it
            if existing_resources and len(existing_resources) == 1:
                existing_resource = existing_resources[0]
                self.logger.info(
                    f"Resource '{body.resource_name}' with matching properties already exists (ID: {existing_resource.resource_id}), returning existing resource"
                )
                return existing_resource

            # If multiple matches found, log warning and create new one
            if existing_resources and len(existing_resources) > 1:
                self.logger.warning(
                    f"Found {len(existing_resources)} resources matching '{body.resource_name}' with criteria {search_criteria}. Creating new resource."
                )

            # No existing resource found or multiple found, create new one from template
            return self._resource_interface.create_resource_from_template(
                template_name=template_name,
                resource_name=body.resource_name,
                overrides=body.overrides if body.overrides else {},
                add_to_database=body.add_to_database,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/push")
    async def push(
        self, resource_id: str, body: PushResourceBody
    ) -> Union[Stack, Queue, Slot]:
        """
        Push a resource onto a stack or queue.

        Args:
            resource_id (str): The ID of the stack or queue to push the resource onto.
            body (PushResourceBody): The resource to push onto the stack or queue, or the ID of an existing resource.

        Returns:
            Union[Stack, Queue, Slot]: The updated stack or queue.
        """
        try:
            return self._resource_interface.push(
                parent_id=resource_id, child=body.child if body.child else body.child_id
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/pop")
    async def pop(
        self, resource_id: str
    ) -> tuple[ResourceDataModels, Union[Stack, Queue, Slot]]:
        """
        Pop an asset from a stack or queue.

        Args:
            resource_id (str): The ID of the stack or queue to pop the asset from.

        Returns:
            tuple[ResourceDataModels, Union[Stack, Queue, Slot]]: The popped asset and the updated stack or queue.
        """
        try:
            return self._resource_interface.pop(parent_id=resource_id)
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/child/set")
    async def set_child(
        self, resource_id: str, body: SetChildBody
    ) -> ContainerDataModels:
        """
        Set a child resource for a parent resource. Must be a container type that supports random access.

        Args:
            resource_id (str): The ID of the parent resource.
            body (SetChildBody): The body of the request.

        Returns:
            ResourceDataModels: The updated parent resource.
        """
        try:
            return self._resource_interface.set_child(
                container_id=resource_id, key=body.key, child=body.child
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/child/remove")
    async def remove_child(
        self, resource_id: str, body: RemoveChildBody
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
            return self._resource_interface.remove_child(
                container_id=resource_id, key=body.key
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/quantity")
    async def set_quantity(
        self, resource_id: str, quantity: Union[float, int]
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
            return self._resource_interface.set_quantity(
                resource_id=resource_id, quantity=quantity
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/quantity/change_by")
    async def change_quantity_by(
        self, resource_id: str, amount: Union[float, int]
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
            resource = self._resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return self._resource_interface.set_quantity(
                resource_id=resource_id, quantity=resource.quantity + amount
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/quantity/increase")
    async def increase_quantity(
        self, resource_id: str, amount: Union[float, int]
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
            resource = self._resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return self._resource_interface.set_quantity(
                resource_id=resource_id, quantity=resource.quantity + abs(amount)
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/quantity/decrease")
    async def decrease_quantity(
        self, resource_id: str, amount: Union[float, int]
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
            resource = self._resource_interface.get_resource(resource_id=resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return self._resource_interface.set_quantity(
                resource_id=resource_id,
                quantity=max(resource.quantity - abs(amount), 0),
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/capacity")
    async def set_capacity(
        self, resource_id: str, capacity: Union[float, int]
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
            return self._resource_interface.set_capacity(
                resource_id=resource_id, capacity=capacity
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @delete("/resource/{resource_id}/capacity")
    async def remove_capacity_limit(self, resource_id: str) -> ResourceDataModels:
        """
        Remove the capacity limit of a resource.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return self._resource_interface.remove_capacity_limit(
                resource_id=resource_id
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/empty")
    async def empty_resource(self, resource_id: str) -> ResourceDataModels:
        """
        Empty the contents of a container or consumable resource.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return self._resource_interface.empty(resource_id=resource_id)
        except NoResultFound as e:
            self.logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/fill")
    async def fill_resource(self, resource_id: str) -> ResourceDataModels:
        """
        Fill a consumable resource to capacity.

        Args:
            resource_id (str): The ID of the resource.

        Returns:
            ResourceDataModels: The updated resource.
        """
        try:
            return self._resource_interface.fill(resource_id=resource_id)
        except NoResultFound as e:
            self.logger.info(f"Resource not found: {resource_id}")
            raise HTTPException(status_code=404, detail="Resource not found") from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @post("/resource/{resource_id}/lock")
    async def acquire_resource_lock(
        self,
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
            locked_resource = self._resource_interface.acquire_lock(
                resource=resource_id,
                lock_duration=lock_duration,
                client_id=client_id,
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Handle the response outside the try-except
        if locked_resource:
            return locked_resource.model_dump(mode="json")
        raise HTTPException(
            status_code=409,  # Conflict - resource already locked
            detail=f"Resource {resource_id} is already locked or lock acquisition failed",
        )

    @delete("/resource/{resource_id}/unlock")
    async def release_resource_lock(
        self, resource_id: str, client_id: Optional[str] = None
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
            unlocked_resource = self._resource_interface.release_lock(
                resource=resource_id,
                client_id=client_id,
            )
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

        if unlocked_resource:
            return unlocked_resource.model_dump(mode="json")
        # Return a proper error response instead of None
        raise HTTPException(
            status_code=403,
            detail=f"Cannot release lock on resource {resource_id}: not owned by client {client_id}",
        )

    @get("/resource/{resource_id}/check_lock")
    async def check_resource_lock(self, resource_id: str) -> dict[str, Any]:
        """
        Check if a resource is currently locked.

        Args:
            resource_id (str): The ID of the resource to check.

        Returns:
            dict: Lock status information.
        """
        try:
            is_locked, locked_by = self._resource_interface.is_locked(
                resource=resource_id
            )
            return {
                "resource_id": resource_id,
                "is_locked": is_locked,
                "locked_by": locked_by,
            }
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @get("/resource/{resource_id}/hierarchy")
    async def query_resource_hierarchy(self, resource_id: str) -> ResourceHierarchy:
        """
        Query the hierarchical relationships of a resource.

        Returns the ancestors (successive parent IDs from closest to furthest)
        and descendants (all children recursively, organized by parent) of the specified resource.

        Args:
            resource_id (str): The ID of the resource to query hierarchy for.

        Returns:
            ResourceHierarchy: Hierarchy information with:
                - ancestor_ids: List of all direct ancestors (parent, grandparent, etc.)
                - resource_id: The ID of the queried resource
                - descendant_ids: Dict mapping parent IDs to their direct child IDs,
                  recursively including all descendant generations (children, grandchildren, etc.)
        """
        try:
            hierarchy_data = self._resource_interface.query_resource_hierarchy(
                resource_id=resource_id
            )
            return ResourceHierarchy.model_validate(hierarchy_data)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(status_code=500, detail=str(e)) from e


# Main entry point for running the server
if __name__ == "__main__":
    manager = ResourceManager()
    manager.run_server()
