"""Transfer planning functionality for the Location Manager."""

import heapq
from typing import Optional

from madsci.common.types.location_types import (
    Location,
    LocationManagerDefinition,
    TransferGraphEdge,
    TransferStepTemplate,
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
    ) -> None:
        """Initialize the TransferPlanner.

        Args:
            state_handler: LocationStateHandler instance for accessing location data
            definition: LocationManagerDefinition containing transfer capabilities
        """
        self.state_handler = state_handler
        self.definition = definition
        self._transfer_graph = self._build_transfer_graph()

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

            # Create the step definition
            step = StepDefinition(
                name=step_name,
                key=step_key,
                description=f"Transfer step {i + 1} using {template.node_name}",
                action=template.action,
                node=template.node_name,
                args={},
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
            ValueError: If locations don't exist or no transfer path exists
        """
        # Validate that both locations exist
        self.validate_locations_exist(source_location_id, destination_location_id)

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
