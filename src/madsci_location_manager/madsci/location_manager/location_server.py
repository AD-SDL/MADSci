"""MADSci Location Manager using AbstractManagerBase."""

from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator, Optional

from classy_fastapi import delete, get, post
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from madsci.client.resource_client import ResourceClient
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import global_ownership_info, ownership_context
from madsci.common.types.location_types import (
    Location,
    LocationDefinition,
    LocationManagerDefinition,
    LocationManagerHealth,
    LocationManagerSettings,
)
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

        # Initialize ResourceClient for creating/updating resources
        self.resource_client = ResourceClient()

        # Initialize locations from definition
        self._initialize_locations_from_definition()

        # Initialize transfer planner
        self.transfer_planner = TransferPlanner(self.state_handler, self.definition)

    def _initialize_locations_from_definition(self) -> None:
        """Initialize locations from the definition, creating or updating them in the state handler."""
        if not self.definition.locations:
            return

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
                name=location_def.location_name,
                description=location_def.description,
                representations=location_def.representations
                if location_def.representations
                else None,
                resource_id=resource_id,  # Associate the resource with the location
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
            # Generate a unique resource name for this location
            # Use location name as base, with location ID as suffix for uniqueness
            resource_name = (
                f"{location_def.location_name}_{location_def.location_id[:8]}"
            )

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

    @get("/health", tags=["Status"])
    def health_endpoint(self) -> LocationManagerHealth:
        """Get the health status of the Location Manager."""
        return self.get_health()

    @get("/")
    def root_endpoint(self) -> LocationManagerDefinition:
        """Get the Location Manager information."""
        return self.definition

    @get("/definition", tags=["Status"])
    def definition_endpoint(self) -> LocationManagerDefinition:
        """Get the Location Manager information."""
        return self.definition

    @get("/locations", tags=["Locations"])
    def get_locations(self) -> list[Location]:
        """Get all locations."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            return self.state_handler.get_locations()

    @post("/location", tags=["Locations"])
    def add_location(self, location: Location) -> Location:
        """Add a new location."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            result = self.state_handler.set_location(location.location_id, location)
            # Rebuild transfer graph since new location may affect transfer capabilities
            self.transfer_planner.rebuild_transfer_graph()
            return result

    @get("/location", tags=["Locations"])
    def get_location_by_query(
        self, location_id: Optional[str] = None, name: Optional[str] = None
    ) -> Location:
        """Get a specific location by ID or name."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
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
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )
            return location

    @delete("/location/{location_id}", tags=["Locations"])
    def delete_location(self, location_id: str) -> dict[str, str]:
        """Delete a specific location by ID."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
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
        representation_val: Annotated[dict, REPRESENTATION_VAL_BODY],
    ) -> Location:
        """Set representations for a location for a specific node."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
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

    @post("/location/{location_id}/attach_resource", tags=["Locations"])
    def attach_resource(
        self,
        location_id: str,
        resource_id: str,
    ) -> Location:
        """Attach a resource to a location."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            location.resource_id = resource_id

            return self.state_handler.update_location(location_id, location)

    @post("/transfer/plan", tags=["Transfer"])
    def plan_transfer(
        self,
        source_location_id: str,
        destination_location_id: str,
    ) -> WorkflowDefinition:
        """
        Plan a transfer workflow from source to destination.

        Args:
            source_location_id: Source location ID
            destination_location_id: Destination location ID

        Returns:
            Composite workflow definition to execute the transfer

        Raises:
            HTTPException: If no transfer path exists
        """
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            try:
                return self.transfer_planner.plan_transfer(
                    source_location_id, destination_location_id
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=404,
                    detail=str(e),
                ) from e

    @get("/transfer/graph", tags=["Transfer"])
    def get_transfer_graph(self) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs
        """
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            return self.transfer_planner.get_transfer_graph_adjacency_list()

    @get("/location/{location_id}/resources", tags=["Resources"])
    def get_location_resources(self, location_id: str) -> list[str]:
        """
        Get all resource IDs currently at a specific location.

        Args:
            location_id: Location ID to query

        Returns:
            List of resource IDs at the location

        Raises:
            HTTPException: If location not found
        """
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            # For now, return empty list as placeholder
            # TODO: Implement actual resource-location tracking
            # This would involve querying the resource manager for resources
            # that have this location as their parent or are contained within
            # resources at this location
            return []


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
