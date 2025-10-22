"""MADSci Location Manager using AbstractManagerBase."""

from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator, Optional

from classy_fastapi import delete, get, post
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from madsci.client.resource_client import ResourceClient
from madsci.common.context import get_current_madsci_context
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import ownership_context
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerHealth,
    LocationManagerSettings,
)
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.location_manager.location_state_handler import LocationStateHandler
from madsci.location_manager.transfer_planner import TransferPlanner

# Module-level constants for Body() calls to avoid B008 linting errors
REPRESENTATION_VAL_BODY = Body(...)


class LocationManager(
    AbstractManagerBase[LocationManagerSettings, LocationManagerDefinition]
):
    """MADSci Location Manager using the new AbstractManagerBase pattern."""

    SETTINGS_CLASS = LocationManagerSettings
    DEFINITION_CLASS = LocationManagerDefinition

    transfer_planner: Optional[TransferPlanner] = None

    def __init__(
        self,
        settings: Optional[LocationManagerSettings] = None,
        definition: Optional[LocationManagerDefinition] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the LocationManager."""
        super().__init__(settings=settings, definition=definition, **kwargs)

    def initialize(self, **_kwargs: Any) -> None:
        """Initialize manager-specific components."""

        self.state_handler = LocationStateHandler(
            self.settings, manager_id=self.definition.manager_id
        )

        # Initialize resource client with resource server URL from context
        context = get_current_madsci_context()
        resource_server_url = context.resource_server_url
        self.resource_client = ResourceClient(resource_server_url=resource_server_url)

        self._initialize_locations_from_definition()
        self.transfer_planner = TransferPlanner(
            self.state_handler, self.definition, self.resource_client
        )

    def _initialize_locations_from_definition(self) -> None:
        """Initialize locations from the definition, creating or updating them in the state handler."""

        for location_def in self.definition.locations:
            # Check if location already exists
            existing_location = self.state_handler.get_location(
                location_def.location_id
            )

            # Handle resource creation/initialization if resource_template_name is provided
            resource_id = None
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
                representations=location_def.representations
                if location_def.representations
                else None,
                resource_id=resource_id,  # Associate the resource with the location
                allow_transfers=location_def.allow_transfers,
            )

            if existing_location is None:
                # Location doesn't exist, create it
                self.state_handler.set_location(location.location_id, location)
            else:
                # Location exists, update if there are changes
                needs_update = False

                if location.representations != existing_location.representations:
                    existing_location.representations = location.representations
                    needs_update = True

                if resource_id != existing_location.resource_id:
                    existing_location.resource_id = resource_id
                    needs_update = True

                if needs_update:
                    self.state_handler.update_location(
                        location.location_id, existing_location
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
                f"Failed to create resource from template '{location_def.resource_template_name}' "
                f"for location '{location_def.location_name}': {e}"
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
                    f"Reusing existing resource '{existing_resource_id}' for location '{location_def.location_name}'"
                )
                return existing_resource_id
            self.logger.info(
                f"Existing resource '{existing_resource_id}' for location '{location_def.location_name}' "
                f"no longer exists. Creating new resource."
            )

        except Exception as e:
            self.logger.info(
                f"Failed to validate existing resource '{existing_resource_id}' for location '{location_def.location_name}': {e}. "
                f"Creating new resource."
            )

        # Existing resource doesn't exist, create a new one
        return self._initialize_location_resource(location_def)

    def get_health(self) -> LocationManagerHealth:
        """Get the health status of the Location Manager."""
        health = LocationManagerHealth()

        try:
            # Test Redis connection if configured
            if (
                hasattr(self.state_handler, "_redis_client")
                and self.state_handler._redis_client
            ):
                self.state_handler._redis_client.ping()
                health.redis_connected = True
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
        with ownership_context():
            return self.state_handler.get_locations()

    @post("/location", tags=["Locations"])
    def add_location(self, location: Location) -> Location:
        """Add a new location."""
        with ownership_context():
            result = self.state_handler.set_location(location.location_id, location)
            # Rebuild transfer graph since new location may affect transfer capabilities
            self.transfer_planner.rebuild_transfer_graph()
            return result

    @get("/location", tags=["Locations"])
    def get_location_by_query(
        self, location_id: Optional[str] = None, name: Optional[str] = None
    ) -> Location:
        """Get a specific location by ID or name."""
        with ownership_context():
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
        with ownership_context():
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )
            return location

    @delete("/location/{location_id}", tags=["Locations"])
    def delete_location(self, location_id: str) -> dict[str, str]:
        """Delete a specific location by ID."""
        with ownership_context():
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
        with ownership_context():
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
        with ownership_context():
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
        with ownership_context():
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            location.resource_id = resource_id

            return self.state_handler.update_location(location_id, location)

    @delete("/location/{location_id}/detach_resource", tags=["Locations"])
    def detach_resource(
        self,
        location_id: str,
    ) -> Location:
        """Detach the resource from a location."""
        with ownership_context():
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
        with ownership_context():
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
        with ownership_context():
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
        with ownership_context():
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            # If no resource is attached to this location, return empty hierarchy
            if not location.resource_id:
                return ResourceHierarchy(
                    ancestor_ids=[], resource_id="", descendant_ids={}
                )

            try:
                # Query the resource hierarchy for the attached resource
                return self.resource_client.query_resource_hierarchy(
                    location.resource_id
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to query resource hierarchy for location {location_id} "
                    f"with resource_id {location.resource_id}: {e}"
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
    definition: Optional[LocationManagerDefinition] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    manager = LocationManager(settings=settings, definition=definition)
    return manager.create_server(
        version="0.1.0",
        lifespan=lifespan,
    )


if __name__ == "__main__":
    manager = LocationManager()
    manager.run_server()
