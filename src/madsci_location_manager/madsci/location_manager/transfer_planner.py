"""Transfer planning functionality for the Location Manager."""

import heapq
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.location_types import (
    Location,
    LocationManagerDefinition,
    TransferGraphEdge,
    TransferStepTemplate,
    TransferTemplateOverrides,
)
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.workflow_types import (
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowParameters,
)
from madsci.location_manager.location_state_handler import LocationStateHandler


class TransferPlanner:
    """Handles transfer planning and graph operations for the Location Manager."""

    def __init__(
        self,
        state_handler: LocationStateHandler,
        definition: LocationManagerDefinition,
        resource_client: Optional[ResourceClient] = None,
    ) -> None:
        """Initialize the TransferPlanner.

        Args:
            state_handler: LocationStateHandler instance for accessing location data
            definition: LocationManagerDefinition containing transfer capabilities
            resource_client: ResourceClient for capacity-aware transfer planning (optional)
        """
        self.state_handler = state_handler
        self.definition = definition
        self.resource_client = resource_client
        self._transfer_graph = self._build_transfer_graph()

    def _build_transfer_graph(self) -> dict[tuple[str, str], TransferGraphEdge]:
        """
        Build transfer graph based on location representations and transfer templates.

        When multiple templates are available for a location pair, chooses the one with lowest cost.

        Returns:
            Dict mapping (source_id, dest_id) tuples to TransferGraphEdge objects
        """
        transfer_graph = {}

        if not self.definition.transfer_capabilities:
            return transfer_graph

        locations = self.state_handler.get_locations()

        # Process all location pairs
        for source_location in locations:
            for dest_location in locations:
                if source_location.location_id == dest_location.location_id:
                    continue  # Skip self-transfers

                # Skip locations that don't allow transfers
                if (
                    not source_location.allow_transfers
                    or not dest_location.allow_transfers
                ):
                    continue

                # Get applicable templates for this location pair
                applicable_templates = self._get_applicable_templates(
                    source_location, dest_location
                )

                # Find the best (lowest cost) template for this location pair
                best_edge = None
                for template in applicable_templates:
                    if self._can_transfer_between_locations(
                        source_location, dest_location, template
                    ):
                        base_cost = template.cost_weight or 1.0

                        # Apply capacity-based cost adjustments if enabled
                        adjusted_cost = self._apply_capacity_cost_adjustment(
                            base_cost, dest_location
                        )

                        edge = TransferGraphEdge(
                            source_location_id=source_location.location_id,
                            destination_location_id=dest_location.location_id,
                            transfer_template=template,
                            cost=adjusted_cost,
                        )

                        # Keep the edge with the lowest cost
                        if best_edge is None or edge.cost < best_edge.cost:
                            best_edge = edge

                # Add the best edge to the graph
                if best_edge is not None:
                    transfer_graph[
                        (source_location.location_id, dest_location.location_id)
                    ] = best_edge

        return transfer_graph

    def _get_applicable_templates(
        self, source_location: Location, dest_location: Location
    ) -> list[TransferStepTemplate]:
        """
        Get applicable transfer templates for a specific location pair.

        Precedence order:
        1. Pair-specific overrides (highest priority)
        2. Source-specific overrides
        3. Destination-specific overrides
        4. Default templates (lowest priority)

        Args:
            source_location: Source location
            dest_location: Destination location

        Returns:
            List of applicable transfer templates in priority order
        """
        templates = []

        # Check if override templates are configured
        overrides = (
            self.definition.transfer_capabilities.override_transfer_templates
            if self.definition.transfer_capabilities
            else None
        )

        if overrides:
            # 1. Check for pair-specific overrides (highest priority)
            pair_templates = self._get_pair_override_templates(
                source_location, dest_location, overrides
            )
            if pair_templates:
                return pair_templates

            # 2. Check for source-specific overrides
            source_templates = self._get_source_override_templates(
                source_location, overrides
            )
            if source_templates:
                return source_templates

            # 3. Check for destination-specific overrides
            dest_templates = self._get_destination_override_templates(
                dest_location, overrides
            )
            if dest_templates:
                return dest_templates

        # 4. If no overrides found, use default templates
        if not templates and self.definition.transfer_capabilities:
            templates = self.definition.transfer_capabilities.transfer_templates

        return templates

    def _get_pair_override_templates(
        self,
        source_location: Location,
        dest_location: Location,
        overrides: TransferTemplateOverrides,
    ) -> Optional[list[TransferStepTemplate]]:
        """Get override templates for a specific (source, destination) pair."""
        if not overrides.pair_overrides:
            return None

        # Check both location_id and location_name for source
        for source_key in [source_location.location_id, source_location.location_name]:
            if source_key in overrides.pair_overrides:
                dest_overrides = overrides.pair_overrides[source_key]
                # Check both location_id and location_name for destination
                for dest_key in [
                    dest_location.location_id,
                    dest_location.location_name,
                ]:
                    if dest_key in dest_overrides:
                        return dest_overrides[dest_key]
        return None

    def _get_source_override_templates(
        self, source_location: Location, overrides: TransferTemplateOverrides
    ) -> Optional[list[TransferStepTemplate]]:
        """Get override templates for a specific source location."""
        if not overrides.source_overrides:
            return None

        # Check both location_id and location_name
        for key in [source_location.location_id, source_location.location_name]:
            if key in overrides.source_overrides:
                return overrides.source_overrides[key]
        return None

    def _get_destination_override_templates(
        self, dest_location: Location, overrides: TransferTemplateOverrides
    ) -> Optional[list[TransferStepTemplate]]:
        """Get override templates for a specific destination location."""
        if not overrides.destination_overrides:
            return None

        # Check both location_id and location_name
        for key in [dest_location.location_id, dest_location.location_name]:
            if key in overrides.destination_overrides:
                return overrides.destination_overrides[key]
        return None

    def _apply_capacity_cost_adjustment(
        self, base_cost: float, destination_location: Location
    ) -> float:
        """
        Apply capacity-based cost adjustments to the base transfer cost.

        Args:
            base_cost: Base cost of the transfer
            destination_location: Destination location to check for capacity

        Returns:
            Adjusted cost based on destination resource capacity utilization
        """
        # Check if capacity cost adjustments are not enabled, resource client is unavailable, or destination has no resource
        if (
            not self.definition.transfer_capabilities
            or not self.definition.transfer_capabilities.capacity_cost_config
            or not self.definition.transfer_capabilities.capacity_cost_config.enabled
            or not self.resource_client
            or not destination_location.resource_id
        ):
            return base_cost

        try:
            # Get the destination resource
            resource = self.resource_client.get_resource(
                destination_location.resource_id
            )

            # Check if resource has capacity and quantity fields (consumable resources)
            if (
                not hasattr(resource, "capacity")
                or not hasattr(resource, "quantity")
                or resource.capacity is None
                or resource.capacity <= 0
            ):
                return base_cost

            # Calculate utilization ratio
            utilization_ratio = float(resource.quantity) / float(resource.capacity)

            # Get capacity configuration
            config = self.definition.transfer_capabilities.capacity_cost_config

            # Apply multipliers based on utilization thresholds
            if utilization_ratio >= config.full_capacity_threshold:
                return base_cost * config.full_capacity_multiplier
            if utilization_ratio >= config.high_capacity_threshold:
                return base_cost * config.high_capacity_multiplier
            return base_cost

        except Exception:
            # Log warning but don't fail - just return base cost
            EventClient().warning(
                f"Failure during capacity check for resource {destination_location.resource_id}. Using base transfer cost."
            )
            return base_cost

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

    def find_shortest_transfer_path(
        self, source_id: str, dest_id: str
    ) -> Optional[list[TransferGraphEdge]]:
        """
        Find shortest path using Dijkstra's algorithm with edge weights.

        Args:
            source_id: Source location ID
            dest_id: Destination location ID

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

    def create_composite_transfer_workflow(
        self, path: list[TransferGraphEdge]
    ) -> WorkflowDefinition:
        """
        Create a single composite workflow from multiple transfer steps.

        Each step in the path becomes a step in the workflow with proper
        source/target location parameters.

        Args:
            path: List of transfer edges representing the path

        Returns:
            WorkflowDefinition for executing the transfer
        """

        # Create workflow with steps for each transfer edge
        workflow_steps = []
        workflow_parameters = WorkflowParameters()

        for i, edge in enumerate(path):
            # Construct step dynamically from transfer template
            template = edge.transfer_template

            # Generate unique step name and key
            step_name = f"transfer_step_{i + 1}"
            step_key = f"transfer_step_{i + 1}"

            # Create step definition with locations mapped to template argument names
            step_locations = {
                template.source_argument_name: self.state_handler.get_location(
                    edge.source_location_id
                ).name,
                template.target_argument_name: self.state_handler.get_location(
                    edge.destination_location_id
                ).name,
            }

            # Add additional location arguments from template
            for arg_name, location_name in template.additional_location_args.items():
                step_locations[arg_name] = location_name

            # Start with additional standard arguments from template
            step_args = template.additional_args.copy()

            # Create the step definition
            step = StepDefinition(
                name=step_name,
                key=step_key,
                description=f"Transfer step {i + 1} using {template.node_name}",
                action=template.action,
                node=template.node_name,
                args=step_args,
                files={},
                locations=step_locations,
                conditions=[],
                data_labels={},
            )

            workflow_steps.append(step)

        # Create the composite workflow
        if path:
            # Get source and destination locations for names and IDs
            source_location = self.state_handler.get_location(
                path[0].source_location_id
            )
            dest_location = self.state_handler.get_location(
                path[-1].destination_location_id
            )

            # Use location names in workflow name
            workflow_name = (
                f"Transfer: '{source_location.name}' -> '{dest_location.name}'"
            )

            # Create description with both names and IDs
            description = f"Transfer from {source_location.name} ({path[0].source_location_id}) to {dest_location.name} ({path[-1].destination_location_id})"
        else:
            workflow_name = "Transfer: Same location"
            description = "Transfer within the same location"

        return WorkflowDefinition(
            name=workflow_name,
            parameters=workflow_parameters,
            steps=workflow_steps,
            definition_metadata=WorkflowMetadata(description=description),
        )

    def get_transfer_graph_adjacency_list(self) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs
        """
        adjacency_list = {}

        for source_id, dest_id in self._transfer_graph:
            if source_id not in adjacency_list:
                adjacency_list[source_id] = []
            adjacency_list[source_id].append(dest_id)

        return adjacency_list

    def rebuild_transfer_graph(self) -> None:
        """Rebuild the transfer graph, typically called when locations or transfer capabilities change."""
        self._transfer_graph = self._build_transfer_graph()

    def validate_locations_exist(
        self, source_id: str, dest_id: str
    ) -> tuple[Location, Location]:
        """
        Validate that both source and destination locations exist.

        Args:
            source_id: Source location ID
            dest_id: Destination location ID

        Returns:
            Tuple of (source_location, dest_location)

        Raises:
            ValueError: If either location is not found
        """
        source_location = self.state_handler.get_location(source_id)
        if source_location is None:
            raise ValueError(f"Source location {source_id} not found")

        dest_location = self.state_handler.get_location(dest_id)
        if dest_location is None:
            raise ValueError(f"Destination location {dest_id} not found")

        return source_location, dest_location

    def plan_transfer(
        self, source_location_id: str, destination_location_id: str
    ) -> WorkflowDefinition:
        """
        Plan a transfer workflow from source to destination.

        Args:
            source_location_id: Source location ID
            destination_location_id: Destination location ID

        Returns:
            Composite workflow definition to execute the transfer

        Raises:
            ValueError: If locations don't exist, don't allow transfers, or no transfer path exists
        """
        # Validate that both locations exist
        source_location, dest_location = self.validate_locations_exist(
            source_location_id, destination_location_id
        )

        # Check if transfers are allowed for both locations
        if not source_location.allow_transfers:
            raise ValueError(
                f"Source location '{source_location.name}' ({source_location_id}) does not allow transfers"
            )
        if not dest_location.allow_transfers:
            raise ValueError(
                f"Destination location '{dest_location.name}' ({destination_location_id}) does not allow transfers"
            )

        # Find shortest transfer path
        transfer_path = self.find_shortest_transfer_path(
            source_location_id, destination_location_id
        )
        if transfer_path is None:
            raise ValueError(
                f"No transfer path exists between {source_location_id} and {destination_location_id}"
            )

        # Create composite workflow
        return self.create_composite_transfer_workflow(transfer_path)
