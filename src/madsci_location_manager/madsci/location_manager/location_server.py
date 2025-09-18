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
from madsci.common.types.resource_types import Resource, ResourceDataModels
from madsci.common.types.resource_types.definitions import ResourceDefinitions
from madsci.location_manager.location_state_handler import LocationStateHandler

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
        self.state_handler = LocationStateHandler(self.settings)

        # Initialize ResourceClient for creating/updating resources
        self.resource_client = ResourceClient()

        # Initialize locations from definition
        self._initialize_locations_from_definition()

    def _initialize_locations_from_definition(self) -> None:
        """Initialize locations from the definition, creating or updating them in the state handler."""
        if not self.definition.locations:
            return

        for location_def in self.definition.locations:
            # Handle resource creation/initialization if resource_definition is provided
            resource_id = None
            if location_def.resource_definition:
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

            # Check if location already exists to avoid overwriting
            existing_location = self.state_handler.get_location(location.location_id)
            if existing_location is None:
                # Location doesn't exist, create it
                self.state_handler.set_location(location.location_id, location)
            else:
                # Location exists, update if there are changes
                needs_update = False

                if location.representations != existing_location.representations:
                    existing_location.representations = location.representations
                    needs_update = True

                if resource_id and resource_id != existing_location.resource_id:
                    existing_location.resource_id = resource_id
                    needs_update = True

                if needs_update:
                    self.state_handler.update_location(
                        location.location_id, existing_location
                    )

    def _initialize_location_resource(
        self, location_def: LocationDefinition
    ) -> Optional[str]:
        """Initialize a resource for a location based on its resource_definition.

        Args:
            location_def: LocationDefinition containing the resource_definition

        Returns:
            Optional[str]: The resource_id of the created/updated resource, or None if no resource created
        """
        if not location_def.resource_definition:
            return None

        try:
            # First, check if a resource with matching characteristics already exists
            existing_resources = self.resource_client.query_resource(
                resource_name=location_def.resource_definition.resource_name,
                resource_class=location_def.resource_definition.resource_class,
                base_type=location_def.resource_definition.base_type.value,
                multiple=True,
            )

            # If we found existing resources, check if any exactly match our definition
            if existing_resources:
                for existing_resource in existing_resources:
                    if self._resource_matches_definition(
                        existing_resource, location_def.resource_definition
                    ):
                        # Found a matching resource, reuse it
                        return existing_resource.resource_id

            # No matching resource found, create a new one
            resource_data = location_def.resource_definition.model_dump()

            # Convert the resource definition to a Resource instance
            resource = Resource.discriminate(resource_data)

            # Create the resource
            created_resource = self.resource_client.add_or_update_resource(resource)

            if created_resource:
                return created_resource.resource_id

        except Exception:
            # If resource initialization fails, continue without the resource
            # Locations can still function without associated resources
            return None

        return None

    def _resource_matches_definition(
        self, resource: ResourceDataModels, resource_definition: ResourceDefinitions
    ) -> bool:
        """Check if an existing resource matches the given resource definition.

        Args:
            resource: Existing resource from the resource manager
            resource_definition: ResourceDefinition to compare against

        Returns:
            bool: True if the resource matches the definition
        """
        try:
            # Compare key characteristics that should match
            if resource.resource_name != resource_definition.resource_name:
                return False

            if resource.resource_class != resource_definition.resource_class:
                return False

            if resource.base_type.value != resource_definition.base_type.value:
                return False

            # For container types, also check capacity if defined
            return not (
                hasattr(resource_definition, "capacity")
                and hasattr(resource, "capacity")
                and resource_definition.capacity is not None
                and resource.capacity != resource_definition.capacity
            )

        except Exception:
            # If comparison fails, assume they don't match
            return False

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
            return self.state_handler.set_location(location.location_id, location)

    @get("/location/{location_id}", tags=["Locations"])
    def get_location(self, location_id: str) -> Location:
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

            return self.state_handler.update_location(location_id, location)

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
