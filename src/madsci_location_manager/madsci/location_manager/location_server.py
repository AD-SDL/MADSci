"""MADSci Location Manager using AbstractManagerBase."""

from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator, Optional

from classy_fastapi import delete, get, post
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from madsci.client.resource_client import ResourceClient
from madsci.common.context import get_current_madsci_context
from madsci.common.db_handlers import RedisHandler
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import ownership_class
from madsci.common.types.event_types import EventType
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerHealth,
    LocationManagerSettings,
)
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.location_manager.location_state_handler import LocationStateHandler
from madsci.location_manager.transfer_planner import TransferPlanner

# Module-level constants for Body() calls to avoid B008 linting errors
REPRESENTATION_VAL_BODY = Body(...)


@ownership_class()
class LocationManager(AbstractManagerBase[LocationManagerSettings]):
    """MADSci Location Manager using the new AbstractManagerBase pattern.

    This class is decorated with @ownership_class() which automatically
    establishes ownership context for all public methods, eliminating the
    need for manual `with ownership_context():` blocks in each endpoint.
    """

    SETTINGS_CLASS = LocationManagerSettings

    transfer_planner: Optional[TransferPlanner] = None

    def __init__(
        self,
        settings: Optional[LocationManagerSettings] = None,
        redis_connection: Optional[Any] = None,
        redis_handler: Optional[RedisHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the LocationManager."""
        self.redis_connection = redis_connection
        self.redis_handler = redis_handler
        super().__init__(settings=settings, **kwargs)

    def initialize(self, **_kwargs: Any) -> None:
        """Initialize manager-specific components."""

        self.state_handler = LocationStateHandler(
            settings=self.settings,
            manager_id=self.settings.manager_id,
            redis_connection=self.redis_connection,
            redis_handler=self.redis_handler,
        )

        # Initialize resource client with resource server URL from context
        context = get_current_madsci_context()
        resource_server_url = context.resource_server_url
        self.resource_client = ResourceClient(resource_server_url=resource_server_url)

        self._initialize_locations()
        self.transfer_planner = TransferPlanner(
            state_handler=self.state_handler,
            transfer_capabilities=self.settings.transfer_capabilities,
            resource_client=self.resource_client,
        )

    def _initialize_locations(self) -> None:
        """Initialize locations from settings, creating or updating them in the state handler."""
        locations = self.settings.locations or []

        if not locations:
            self.logger.warning(
                "No locations configured in settings. "
                "Ensure 'location_locations' is defined in settings.yaml "
                "or location.settings.yaml, and that these files are "
                "accessible from the current working directory or via "
                "MADSCI_SETTINGS_DIR.",
                event_type=EventType.LOCATION_UPDATE,
            )

        for location_def in locations:
            # Check if location already exists
            existing_location = self.state_handler.get_location(
                location_def.location_id
            )

            # Handle resource creation/initialization if resource_template_name is provided
            resource_id = existing_location.resource_id if existing_location else None
            if location_def.resource_template_name:
                if existing_location and existing_location.resource_id:
                    # Location exists and has a resource, validate it still exists and matches template
                    resource_id = self._validate_or_recreate_location_resource(
                        location_def, existing_location.resource_id
                    )
                else:
                    # Location doesn't exist or has no resource, create new one
                    resource_id = self._initialize_location_resource(location_def)

            # Convert LocationDefinition to Location
            location = Location(
                location_id=location_def.location_id,
                location_name=location_def.location_name,
                description=location_def.description,
                representations=location_def.representations or None,
                resource_id=resource_id,  # Associate the resource with the location
                allow_transfers=location_def.allow_transfers,
            )

            self.state_handler.set_location(location.location_id, location)

        if locations:
            self.logger.info(
                "Initialized locations from settings",
                event_type=EventType.LOCATION_UPDATE,
                num_locations=len(locations),
            )

    def _initialize_location_resource(
        self, location_def: LocationDefinition
    ) -> Optional[str]:
        """Initialize a resource for a location based on its resource_template_name.

        Args:
            location_def: LocationDefinition containing the resource_template_name and optional overrides

        Returns:
            Optional[str]: The resource_id of the created resource, or None if no resource created
        """
        if not location_def.resource_template_name:
            return None

        try:
            resource_name = location_def.location_name

            # Create resource from template
            created_resource = self.resource_client.create_resource_from_template(
                template_name=location_def.resource_template_name,
                resource_name=resource_name,
                overrides=location_def.resource_template_overrides or {},
                add_to_database=True,
            )

            if created_resource:
                return created_resource.resource_id

        except Exception as e:
            # Log the error but continue - locations can still function without associated resources
            self.logger.warning(
                "Failed to create resource from template",
                event_type=EventType.RESOURCE_CREATE,
                template_name=location_def.resource_template_name,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
                error=str(e),
                exc_info=True,
            )
            return None

        return None

    def _validate_or_recreate_location_resource(
        self, location_def: LocationDefinition, existing_resource_id: str
    ) -> Optional[str]:
        """Check if existing resource still exists. If so, reuse it. If not, create a new one.

        Args:
            location_def: LocationDefinition containing the resource_template_name and overrides
            existing_resource_id: The existing resource ID to validate

        Returns:
            Optional[str]: The resource_id (existing or newly created), or None if failed
        """
        if not location_def.resource_template_name:
            return None

        try:
            # Simply check if the existing resource still exists in the resource manager
            existing_resource = self.resource_client.get_resource(existing_resource_id)

            if existing_resource:
                # Resource exists, reuse it
                self.logger.debug(
                    "Reusing existing resource for location",
                    existing_resource_id=existing_resource_id,
                    location_id=location_def.location_id,
                    location_name=location_def.location_name,
                )
                return existing_resource_id
            self.logger.info(
                "Existing resource missing; recreating for location",
                event_type=EventType.RESOURCE_CREATE,
                existing_resource_id=existing_resource_id,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
            )

        except Exception as e:
            self.logger.info(
                "Failed to validate existing location resource; recreating",
                event_type=EventType.RESOURCE_CREATE,
                existing_resource_id=existing_resource_id,
                location_id=location_def.location_id,
                location_name=location_def.location_name,
                error=str(e),
                exc_info=True,
            )

        # Existing resource doesn't exist, create a new one
        return self._initialize_location_resource(location_def)

    def get_health(self) -> LocationManagerHealth:
        """Get the health status of the Location Manager."""
        health = LocationManagerHealth()

        try:
            # Test Redis connection if configured
            if hasattr(self.state_handler, "_redis_handler"):
                health.redis_connected = self.state_handler._redis_handler.ping()
            else:
                health.redis_connected = None

            # Count managed locations
            locations = self.state_handler.get_locations()
            health.num_locations = len(locations)

            health.healthy = True
            health.description = "Location Manager is running normally"

        except Exception as e:
            health.healthy = False
            if "redis" in str(e).lower():
                health.redis_connected = False
            health.description = f"Health check failed: {e!s}"

        return health

    @get("/locations", tags=["Locations"])
    def get_locations(self) -> list[Location]:
        """Get all locations."""
        return self.state_handler.get_locations()

    @post("/location", tags=["Locations"])
    def add_location(self, location: Location) -> Location:
        """Add a new location."""
        with self.span(
            "location.create",
            attributes={"location.id": location.location_id},
        ):
            result = self.state_handler.set_location(location.location_id, location)
            # Rebuild transfer graph since new location may affect transfer capabilities
            self.transfer_planner.rebuild_transfer_graph()

            return result

    @get("/location", tags=["Locations"])
    def get_location_by_query(
        self, location_id: Optional[str] = None, name: Optional[str] = None
    ) -> Location:
        """Get a specific location by ID or name."""
        # Exactly one of location_id or name must be provided
        if (location_id is None) == (name is None):
            raise HTTPException(
                status_code=400,
                detail="Exactly one of 'location_id' or 'name' query parameter must be provided",
            )

        if location_id is not None:
            # Search by ID
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Location with ID '{location_id}' not found",
                )
            return location
        # Search by name
        locations = self.state_handler.get_locations()
        for location in locations:
            if location.name == name:
                return location
        raise HTTPException(
            status_code=404, detail=f"Location with name '{name}' not found"
        )

    @get("/location/{location_id}", tags=["Locations"])
    def get_location_by_id(self, location_id: str) -> Location:
        """Get a specific location by ID."""
        location = self.state_handler.get_location(location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )
        return location

    @delete("/location/{location_id}", tags=["Locations"])
    def delete_location(self, location_id: str) -> dict[str, str]:
        """Delete a specific location by ID."""
        success = self.state_handler.delete_location(location_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )
        # Rebuild transfer graph since deleted location affects transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return {"message": f"Location {location_id} deleted successfully"}

    @post("/location/{location_id}/set_representation/{node_name}", tags=["Locations"])
    def set_representations(
        self,
        location_id: str,
        node_name: str,
        representation_val: Annotated[Any, REPRESENTATION_VAL_BODY],
    ) -> Location:
        """Set representations for a location for a specific node."""
        location = self.state_handler.get_location(location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )

        # Update the location with new representations
        if location.representations is None:
            location.representations = {}
        location.representations[node_name] = representation_val

        result = self.state_handler.update_location(location_id, location)
        # Rebuild transfer graph since representations affect transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return result

    @delete(
        "/location/{location_id}/remove_representation/{node_name}", tags=["Locations"]
    )
    def remove_representation(
        self,
        location_id: str,
        node_name: str,
    ) -> Location:
        """Remove representations for a location for a specific node."""
        location = self.state_handler.get_location(location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )

        # Check if representations exist and if the node_name exists
        if (
            location.representations is None
            or node_name not in location.representations
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Representation for node '{node_name}' not found in location {location_id}",
            )

        # Remove the representation for the specified node
        del location.representations[node_name]

        # If no representations remain, set to empty dict (consistent with existing behavior)
        if not location.representations:
            location.representations = {}

        result = self.state_handler.update_location(location_id, location)
        # Rebuild transfer graph since representations affect transfer capabilities
        self.transfer_planner.rebuild_transfer_graph()
        return result

    @post("/location/{location_id}/attach_resource", tags=["Locations"])
    def attach_resource(
        self,
        location_id: str,
        resource_id: str,
    ) -> Location:
        """Attach a resource to a location."""
        with self.span(
            "attachment.create",
            attributes={
                "location.id": location_id,
                "resource.id": resource_id,
            },
        ):
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            location.resource_id = resource_id

            # Note: We don't sync resource_id changes to definition as resource_id is runtime-only
            # The definition uses resource_template_name for resource initialization
            return self.state_handler.update_location(location_id, location)

    @delete("/location/{location_id}/detach_resource", tags=["Locations"])
    def detach_resource(
        self,
        location_id: str,
    ) -> Location:
        """Detach the resource from a location."""
        location = self.state_handler.get_location(location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )

        # Check if location has a resource attached
        if location.resource_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"No resource attached to location {location_id}",
            )

        # Detach the resource
        location.resource_id = None

        # Note: We don't sync resource_id changes to definition as resource_id is runtime-only
        # The definition uses resource_template_name for resource initialization
        return self.state_handler.update_location(location_id, location)

    @post("/transfer/plan", tags=["Transfer"])
    def plan_transfer(
        self,
        source_location_id: str,
        target_location_id: str,
    ) -> WorkflowDefinition:
        """
        Plan a transfer workflow from source to target.

        Args:
            source_location_id: Source location ID
            target_location_id: Target location ID

        Returns:
            Composite workflow definition to execute the transfer

        Raises:
            HTTPException: If no transfer path exists
        """
        with self.span(
            "transfer.plan",
            attributes={
                "transfer.source_location_id": source_location_id,
                "transfer.target_location_id": target_location_id,
            },
        ):
            try:
                return self.transfer_planner.plan_transfer(
                    source_location_id, target_location_id
                )
            except ValueError as e:
                error_message = str(e)
                # Check if this is a "does not allow transfers" error
                if "does not allow transfers" in error_message:
                    raise HTTPException(
                        status_code=400,
                        detail=error_message,
                    ) from e
                # Check if this is a "not found" or "no transfer path" error
                if (
                    "not found" in error_message
                    or "No transfer path exists" in error_message
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=error_message,
                    ) from e
                # Default to 400 for other ValueError cases
                raise HTTPException(
                    status_code=400,
                    detail=error_message,
                ) from e

    @get("/transfer/graph", tags=["Transfer"])
    def get_transfer_graph(self) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs
        """
        return self.transfer_planner.get_transfer_graph_adjacency_list()

    @get("/location/{location_id}/resources", tags=["Resources"])
    def get_location_resources(self, location_id: str) -> ResourceHierarchy:
        """
        Get the resource hierarchy for resources currently at a specific location.

        Args:
            location_id: Location ID to query

        Returns:
            ResourceHierarchy: Hierarchy of resources at the location, or empty hierarchy if no attached resource

        Raises:
            HTTPException: If location not found
        """
        location = self.state_handler.get_location(location_id)
        if location is None:
            raise HTTPException(
                status_code=404, detail=f"Location {location_id} not found"
            )

        # If no resource is attached to this location, return empty hierarchy
        if not location.resource_id:
            return ResourceHierarchy(ancestor_ids=[], resource_id="", descendant_ids={})

        try:
            # Query the resource hierarchy for the attached resource
            return self.resource_client.query_resource_hierarchy(location.resource_id)
        except Exception as e:
            self.logger.warning(
                "Failed to query resource hierarchy for location",
                event_type=EventType.DATA_QUERY,
                location_id=location_id,
                resource_id=location.resource_id,
                error=str(e),
                exc_info=True,
            )
            # Return empty hierarchy if query fails
            return ResourceHierarchy(
                ancestor_ids=[],
                resource_id=location.resource_id or "",
                descendant_ids={},
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the application lifespan."""
    # Future: Add startup/shutdown logic here if needed
    _ = app  # Explicitly acknowledge app parameter
    yield


def create_app(
    settings: Optional[LocationManagerSettings] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    manager = LocationManager(settings=settings)
    return manager.create_server(
        version="0.1.0",
        lifespan=lifespan,
    )


if __name__ == "__main__":
    manager = LocationManager()
    manager.run_server()
