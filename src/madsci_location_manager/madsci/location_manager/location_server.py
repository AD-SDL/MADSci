"""MADSci Location Manager using AbstractManagerBase."""

import heapq
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
    TransferGraphEdge,
    TransferStepTemplate,
)
from madsci.common.types.parameter_types import ParameterInputJson
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.workflow_types import WorkflowDefinition, WorkflowParameters
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
        self.state_handler = LocationStateHandler(
            self.settings, manager_id=self.definition.manager_id
        )

        # Initialize ResourceClient for creating/updating resources
        self.resource_client = ResourceClient()

        # Initialize locations from definition
        self._initialize_locations_from_definition()

        # Initialize transfer graph
        self._transfer_graph = self._build_transfer_graph()

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

    def _build_transfer_graph(self) -> dict[tuple[str, str], TransferGraphEdge]:
        """
        Build transfer graph based on location representations and transfer templates.

        Returns:
            Dict mapping (source_id, dest_id) tuples to TransferGraphEdge objects
        """
        transfer_graph = {}

        if not self.definition.transfer_capabilities:
            return transfer_graph

        locations = self.state_handler.get_locations()

        for template in self.definition.transfer_capabilities.transfer_templates:
            # Find all location pairs that can use this transfer template
            for source_location in locations:
                for dest_location in locations:
                    if source_location.location_id == dest_location.location_id:
                        continue  # Skip self-transfers

                    if self._can_transfer_between_locations(
                        source_location, dest_location, template
                    ):
                        edge = TransferGraphEdge(
                            source_location_id=source_location.location_id,
                            destination_location_id=dest_location.location_id,
                            transfer_template=template,
                            cost=template.cost_weight or 1.0,
                        )
                        transfer_graph[
                            (source_location.location_id, dest_location.location_id)
                        ] = edge

        return transfer_graph

    def _can_transfer_between_locations(
        self, source: Location, dest: Location, template: TransferStepTemplate
    ) -> bool:
        """
        Check if transfer is possible between two locations using a template.

        Based on simple representation key matching: if both locations have
        representations for the template's node_name, transfer is possible.
        """
        if not source.representations or not dest.representations:
            return False

        return (
            template.node_name in source.representations
            and template.node_name in dest.representations
        )

    def _find_shortest_transfer_path(
        self, source_id: str, dest_id: str
    ) -> Optional[list[TransferGraphEdge]]:
        """
        Find shortest path using Dijkstra's algorithm with edge weights.

        Returns:
            List of edges representing the transfer path, or None if no path exists
        """
        if source_id == dest_id:
            return []  # No transfer needed

        # Dijkstra's algorithm
        distances = {source_id: 0}
        previous = {}
        unvisited = [(0, source_id)]
        visited = set()

        while unvisited:
            current_distance, current_location = heapq.heappop(unvisited)

            if current_location in visited:
                continue

            visited.add(current_location)

            if current_location == dest_id:
                # Reconstruct path
                path = []
                current = dest_id
                while current != source_id:
                    prev = previous[current]
                    edge = self._transfer_graph[(prev, current)]
                    path.insert(0, edge)
                    current = prev
                return path

            # Check all neighbors
            for (src, dst), edge in self._transfer_graph.items():
                if src == current_location and dst not in visited:
                    distance = current_distance + edge.cost

                    if dst not in distances or distance < distances[dst]:
                        distances[dst] = distance
                        previous[dst] = current_location
                        heapq.heappush(unvisited, (distance, dst))

        return None  # No path found

    def _composite_transfer_workflow(
        self, path: list[TransferGraphEdge]
    ) -> WorkflowDefinition:
        """
        Create a single composite workflow from multiple transfer steps.

        Each step in the path becomes a step in the workflow with proper
        source/target location parameters.
        """

        # Create workflow with steps for each transfer edge
        workflow_steps = []
        workflow_parameters = WorkflowParameters()

        for i, edge in enumerate(path):
            # Create step from template
            step_template = edge.transfer_template.step_template
            step_dict = step_template.model_dump()

            # Generate unique step name
            step_dict["name"] = f"transfer_step_{i + 1}"
            step_dict["key"] = f"transfer_step_{i + 1}"

            # Add source and target location parameters to the step
            if not step_dict.get("locations"):
                step_dict["locations"] = {}

            # Use parameter keys for source and target locations
            source_param_key = f"source_location_{i + 1}"
            target_param_key = f"target_location_{i + 1}"

            step_dict["locations"]["source"] = source_param_key
            step_dict["locations"]["target"] = target_param_key

            # Add parameters to workflow for this step's locations
            source_location = self.state_handler.get_location(edge.source_location_id)
            target_location = self.state_handler.get_location(
                edge.destination_location_id
            )

            if source_location:
                source_repr = (source_location.representations or {}).get(
                    edge.transfer_template.node_name, {}
                )
                source_param = ParameterInputJson(
                    key=source_param_key,
                    description=f"Source location for transfer step {i + 1}",
                    default=source_repr,
                )
                workflow_parameters.json_inputs.append(source_param)

            if target_location:
                target_repr = (target_location.representations or {}).get(
                    edge.transfer_template.node_name, {}
                )
                target_param = ParameterInputJson(
                    key=target_param_key,
                    description=f"Target location for transfer step {i + 1}",
                    default=target_repr,
                )
                workflow_parameters.json_inputs.append(target_param)

            workflow_steps.append(StepDefinition.model_validate(step_dict))

        # Create the composite workflow
        if path:
            workflow_name = f"transfer_{path[0].source_location_id}_to_{path[-1].destination_location_id}"
        else:
            workflow_name = "transfer_same_location"

        return WorkflowDefinition(
            name=workflow_name, parameters=workflow_parameters, steps=workflow_steps
        )

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
            # Validate that both locations exist
            source_location = self.state_handler.get_location(source_location_id)
            if source_location is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source location {source_location_id} not found",
                )

            dest_location = self.state_handler.get_location(destination_location_id)
            if dest_location is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Destination location {destination_location_id} not found",
                )

            # Find shortest transfer path
            transfer_path = self._find_shortest_transfer_path(
                source_location_id, destination_location_id
            )
            if transfer_path is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No transfer path exists between {source_location_id} and {destination_location_id}",
                )

            # Create composite workflow
            return self._composite_transfer_workflow(transfer_path)

    @get("/transfer/graph", tags=["Transfer"])
    def get_transfer_graph(self) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs
        """
        with ownership_context(**global_ownership_info.model_dump(exclude_none=True)):
            adjacency_list = {}

            for source_id, dest_id in self._transfer_graph:
                if source_id not in adjacency_list:
                    adjacency_list[source_id] = []
                adjacency_list[source_id].append(dest_id)

            return adjacency_list

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
