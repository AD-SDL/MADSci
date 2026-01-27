Module madsci.location_manager.transfer_planner
===============================================
Transfer planning functionality for the Location Manager.

Classes
-------

`TransferPlanner(state_handler: madsci.location_manager.location_state_handler.LocationStateHandler, definition: madsci.common.types.location_types.LocationManagerDefinition, resource_client: madsci.client.resource_client.ResourceClient | None = None)`
:   Handles transfer planning and graph operations for the Location Manager.

    Initialize the TransferPlanner.

    Args:
        state_handler: LocationStateHandler instance for accessing location data
        definition: LocationManagerDefinition containing transfer capabilities
        resource_client: ResourceClient for capacity-aware transfer planning (optional)

    ### Methods

    `create_composite_transfer_workflow(self, path: list[madsci.common.types.location_types.TransferGraphEdge]) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Create a single composite workflow from multiple transfer steps.

        Each step in the path becomes a step in the workflow with proper
        source/target location parameters.

        Args:
            path: List of transfer edges representing the path

        Returns:
            WorkflowDefinition for executing the transfer

    `find_shortest_transfer_path(self, source_id: str, dest_id: str) ‑> list[madsci.common.types.location_types.TransferGraphEdge] | None`
    :   Find shortest path using Dijkstra's algorithm with edge weights.

        Args:
            source_id: Source location ID
            dest_id: Destination location ID

        Returns:
            List of edges representing the transfer path, or None if no path exists

    `get_transfer_graph_adjacency_list(self) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs

    `plan_transfer(self, source_location_id: str, target_location_id: str) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Plan a transfer workflow from source to target.

        Args:
            source_location_id: Source location ID
            target_location_id: Target location ID

        Returns:
            Composite workflow definition to execute the transfer

        Raises:
            ValueError: If locations don't exist, don't allow transfers, or no transfer path exists

    `rebuild_transfer_graph(self) ‑> None`
    :   Rebuild the transfer graph, typically called when locations or transfer capabilities change.

    `validate_locations_exist(self, source_id: str, dest_id: str) ‑> tuple[madsci.common.types.location_types.Location, madsci.common.types.location_types.Location]`
    :   Validate that both source and target locations exist.

        Args:
            source_id: Source location ID
            dest_id: Target location ID

        Returns:
            Tuple of (source_location, dest_location)

        Raises:
            ValueError: If either location is not found
