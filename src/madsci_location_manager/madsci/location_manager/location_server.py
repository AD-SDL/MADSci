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
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the application lifespan."""
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
