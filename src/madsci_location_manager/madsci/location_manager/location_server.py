"""MADSci Location Manager using AbstractManagerBase."""

from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator, Optional

from classy_fastapi import delete, get, post
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.ownership import global_ownership_info, ownership_context
from madsci.common.types.location_types import (
    Location,
    LocationManagerDefinition,
    LocationManagerSettings,
)
from madsci.common.types.manager_types import ManagerHealth
from madsci.location_manager.location_state_handler import LocationStateHandler

# Module-level constants for Body() calls to avoid B008 linting errors
LOOKUP_VAL_BODY = Body(...)


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

        # Initialize locations from definition
        self._initialize_locations_from_definition()

    def _initialize_locations_from_definition(self) -> None:
        """Initialize locations from the definition, creating or updating them in the state handler."""
        if not self.definition.locations:
            return

        for location_def in self.definition.locations:
            # Convert LocationDefinition to Location
            location = Location(
                location_id=location_def.location_id,
                name=location_def.location_name,
                description=location_def.description,
                lookup_values=location_def.lookup if location_def.lookup else None,
                # Include resource_definition if needed - this would require integration
                # with resource manager to actually create the resource
            )

            # Check if location already exists to avoid overwriting
            existing_location = self.state_handler.get_location(location.location_id)
            if existing_location is None:
                # Location doesn't exist, create it
                self.state_handler.set_location(location.location_id, location)
            elif location.lookup_values != existing_location.lookup_values:
                # Location exists, update only if definition is newer or has changes
                # For now, we'll update the lookup_values if they're different
                existing_location.lookup_values = location.lookup_values
                self.state_handler.update_location(
                    location.location_id, existing_location
                )

    @get("/health", tags=["Status"])
    def health_endpoint(self) -> ManagerHealth:
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

    @post("/location/{location_id}/add_lookup/{node_name}", tags=["Locations"])
    def add_lookup_values(
        self,
        location_id: str,
        node_name: str,
        lookup_val: Annotated[dict, LOOKUP_VAL_BODY],
    ) -> Location:
        """Add lookup values to a location for a specific node."""
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            location = self.state_handler.get_location(location_id)
            if location is None:
                raise HTTPException(
                    status_code=404, detail=f"Location {location_id} not found"
                )

            # Update the location with new lookup values
            if location.lookup_values is None:
                location.lookup_values = {}
            location.lookup_values[node_name] = lookup_val

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
