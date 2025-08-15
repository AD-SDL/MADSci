"""Simplified Transfer Manager - Core Logic Only."""

import heapq
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from madsci.common.types.step_types import Step
from madsci.common.utils import new_ulid_str
from pydantic import BaseModel


class TransferManagerConfig(BaseModel):
    """Simple configuration for transfer manager."""

    robot_definitions_path: Path
    location_constraints_path: Path


class TransferGraph:
    """Graph representation of possible transfers in the workcell."""

    def __init__(self):
        # Graph structure: location -> [(target_location, robot_name, cost), ...]
        self.edges: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)
        self.locations: Set[str] = set()

    def add_location(self, location: str):
        """Add a location to the graph."""
        self.locations.add(location)

    def add_edge(self, source: str, target: str, robot: str, cost: float = 1.0):
        """Add a transfer edge between two locations."""
        self.edges[source].append((target, robot, cost))
        self.locations.add(source)
        self.locations.add(target)

    def find_shortest_path(self, source: str, target: str) -> Optional[List[Dict]]:
        """Find shortest path using Dijkstra's algorithm."""
        print(f"Debug: Finding path from '{source}' to '{target}'")

        if source not in self.locations or target not in self.locations:
            print(
                f"Debug: Source or target not in locations. Source in: {source in self.locations}, Target in: {target in self.locations}"
            )
            return None

        print(
            f"Debug: Available edges from source '{source}': {self.edges.get(source, [])}"
        )

        # Dijkstra's algorithm
        distances = {loc: float("inf") for loc in self.locations}
        distances[source] = 0
        previous = {}
        robots_used = {}

        # Priority queue: (distance, current_location)
        pq = [(0, source)]
        visited = set()

        while pq:
            current_dist, current = heapq.heappop(pq)

            if current in visited:
                continue

            visited.add(current)

            if current == target:
                print("Debug: Found target! Reconstructing path...")
                # Reconstruct path
                path = []
                node = target

                while node in previous:
                    prev_node = previous[node]
                    robot = robots_used[node]
                    print(f"Debug: Path step: {prev_node} -> {node} via '{robot}'")
                    path.append({"source": prev_node, "target": node, "robot": robot})
                    node = prev_node

                path.reverse()
                print(f"Debug: Complete path: {path}")
                return path

            # Check all neighbors
            print(
                f"Debug: Checking neighbors of '{current}': {len(self.edges[current])} edges"
            )
            for neighbor, robot, edge_cost in self.edges[current]:
                print(
                    f"Debug: Edge: {current} -> {neighbor} via '{robot}' (cost: {edge_cost})"
                )
                distance = current_dist + edge_cost

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    robots_used[neighbor] = robot
                    heapq.heappush(pq, (distance, neighbor))

        print(f"Debug: No path found from '{source}' to '{target}'")
        return None  # No path found

    def find_all_paths(
        self, source: str, target: str, max_length: int = 5
    ) -> List[List[Dict]]:
        """Find all possible paths up to max_length hops."""
        all_paths = []

        def dfs(current: str, path: List[Dict], visited: Set[str], hops: int):
            if hops > max_length:
                return

            if current == target and len(path) > 0:
                all_paths.append(path.copy())
                return

            if current in visited:
                return

            visited.add(current)

            for neighbor, robot, cost in self.edges[current]:
                hop = {
                    "source": current,
                    "target": neighbor,
                    "robot": robot,
                    "cost": cost,
                }
                path.append(hop)
                dfs(neighbor, path, visited.copy(), hops + 1)
                path.pop()

        dfs(source, [], set(), 0)

        # Sort by total cost
        for path in all_paths:
            total_cost = sum(hop["cost"] for hop in path)
            path.append({"total_cost": total_cost})

        all_paths.sort(key=lambda p: p[-1]["total_cost"])

        # Remove cost metadata
        for path in all_paths:
            path.pop()

        return all_paths

    def is_reachable(self, source: str, target: str) -> bool:
        """Check if target is reachable from source."""
        return self.find_shortest_path(source, target) is not None

    def get_neighbors(self, location: str) -> List[str]:
        """Get all locations directly reachable from this location."""
        return [target for target, _, _ in self.edges[location]]


class TransferManager:
    """Core Transfer Manager implementation."""

    def __init__(self, config: TransferManagerConfig):
        self.config = config
        self.robot_definitions: Dict[str, Dict] = {}
        self.location_constraints: Dict[str, Dict] = {}
        self.transfer_graph = TransferGraph()
        self._load_configuration()
        print(f"Debug: Loaded robot definitions: {list(self.robot_definitions.keys())}")
        self._build_transfer_graph()

    def _load_configuration(self):
        """Load robot definitions and location constraints from YAML files."""
        # Load robot definitions
        with open(self.config.robot_definitions_path) as f:
            self.robot_definitions = yaml.safe_load(f)

        # Load location constraints
        with open(self.config.location_constraints_path) as f:
            self.location_constraints = yaml.safe_load(f)

    def _build_transfer_graph(self):
        """Build the transfer graph from configuration."""
        # Add all locations to graph
        for location_name in self.location_constraints:
            self.transfer_graph.add_location(location_name)

        print(f"Debug: Building graph with {len(self.location_constraints)} locations")

        # Build edges based on robot capabilities and location accessibility
        edge_count = 0
        for robot_name, robot_def in self.robot_definitions.items():
            accessible_locations = self._get_robot_accessible_locations(robot_name)
            print(f"Debug: Robot '{robot_name}' can access: {accessible_locations}")

            # Create edges between all pairs of accessible locations for this robot
            for source in accessible_locations:
                for target in accessible_locations:
                    if source != target:
                        # Calculate cost based on various factors
                        cost = self._calculate_transfer_cost(source, target, robot_name)
                        self.transfer_graph.add_edge(source, target, robot_name, cost)
                        edge_count += 1

        print(f"Debug: Created {edge_count} edges in transfer graph")

    def _get_robot_accessible_locations(self, robot_name: str) -> List[str]:
        """Get all locations that a specific robot can access."""
        accessible = []

        for location_name, constraint in self.location_constraints.items():
            accessible_by = constraint.get("accessible_by", [])
            if robot_name in accessible_by:
                accessible.append(location_name)

        return accessible

    def _calculate_transfer_cost(
        self, source: str, target: str, robot_name: str
    ) -> float:
        """Calculate cost for a transfer between two locations using a specific robot."""
        base_cost = 1.0

        # Increase cost based on complexity of location constraints
        source_constraint = self.location_constraints.get(source, {})
        target_constraint = self.location_constraints.get(target, {})

        # More complex locations (more parameters) cost more
        source_complexity = len(source_constraint.get("default_args", {}))
        target_complexity = len(target_constraint.get("default_args", {}))
        complexity_cost = (source_complexity + target_complexity) * 0.1

        # Robot-specific overrides increase cost (more specialized)
        override_cost = 0.0
        if robot_name in source_constraint.get("robot_overrides", {}):
            override_cost += 0.2
        if robot_name in target_constraint.get("robot_overrides", {}):
            override_cost += 0.2

        return base_cost + complexity_cost + override_cost

    def _load_configuration(self):
        """Load robot definitions and location constraints from YAML files."""
        # Load robot definitions
        with open(self.config.robot_definitions_path) as f:
            self.robot_definitions = yaml.safe_load(f)

        # Load location constraints
        with open(self.config.location_constraints_path) as f:
            self.location_constraints = yaml.safe_load(f)

    def expand_transfer_step(self, step: Step) -> List[Step]:
        """
        Main method: Expand a high-level transfer step into concrete workflow steps.
        This is what the workcell manager calls.
        """
        # Only process transfer steps
        if step.action != "transfer":
            return [step]

        # Extract source and target from step
        source = step.locations.get("source", "")
        target = step.locations.get("target", "")

        if not source or not target:
            raise ValueError(f"Transfer step missing source or target: {step.name}")

        # Determine which robot to use (from the step's node field)
        robot_name = step.node

        if robot_name not in self.robot_definitions:
            raise ValueError(f"Robot '{robot_name}' not found in robot definitions")

        # Get robot definition
        robot_def = self.robot_definitions[robot_name]

        # Build the concrete transfer step
        concrete_step = self._build_transfer_step(
            source=source,
            target=target,
            robot_name=robot_name,
            robot_definition=robot_def,
            user_parameters=step.args or {},
        )

        return [concrete_step]

    def _build_transfer_step(
        self,
        source: str,
        target: str,
        robot_name: str,
        robot_definition: Dict,
        user_parameters: Dict,
    ) -> Step:
        """Build a concrete transfer step with all parameters merged."""

        # Start with robot's default template
        step_template = robot_definition["default_step_template"].copy()

        # Replace template variables
        step_template = self._replace_template_variables(
            step_template, robot_name=robot_name, source=source, target=target
        )

        # Merge parameters with proper precedence
        merged_args = self._merge_parameters(
            robot_definition=robot_definition,
            source=source,
            target=target,
            user_parameters=user_parameters,
        )

        # Update step args
        if "args" not in step_template:
            step_template["args"] = {}
        step_template["args"].update(merged_args)

        # Create Step object
        concrete_step = Step(**step_template)
        concrete_step.step_id = new_ulid_str()

        return concrete_step

    def _merge_parameters(
        self, robot_definition: Dict, source: str, target: str, user_parameters: Dict
    ) -> Dict:
        """Merge parameters from different sources with proper precedence."""

        # 1. Start with robot defaults
        merged = robot_definition.get("default_args", {}).copy()

        # 2. Add location-specific defaults
        source_constraint = self.location_constraints.get(source, {})
        target_constraint = self.location_constraints.get(target, {})

        merged.update(source_constraint.get("default_args", {}))
        merged.update(target_constraint.get("default_args", {}))

        # 3. Add robot-specific overrides for these locations
        robot_name = robot_definition["robot_name"]

        source_overrides = source_constraint.get("robot_overrides", {}).get(
            robot_name, {}
        )
        target_overrides = target_constraint.get("robot_overrides", {}).get(
            robot_name, {}
        )

        merged.update(source_overrides)
        merged.update(target_overrides)

        # 4. User parameters have highest precedence
        merged.update(user_parameters)

        return merged

    def _replace_template_variables(self, template: Any, **variables) -> Any:
        """Replace template variables like {robot_name}, {source}, {target}."""

        if isinstance(template, str):
            for var_name, var_value in variables.items():
                template = template.replace(f"{{{var_name}}}", str(var_value))
            return template

        if isinstance(template, dict):
            return {
                k: self._replace_template_variables(v, **variables)
                for k, v in template.items()
            }

        if isinstance(template, list):
            return [
                self._replace_template_variables(item, **variables) for item in template
            ]

        return template

    # Utility methods

    def get_available_robots(self) -> List[str]:
        """Get list of available robots."""
        return list(self.robot_definitions.keys())

    def get_available_locations(self) -> List[str]:
        """Get list of available locations."""
        return list(self.location_constraints.keys())

    def get_robot_info(self, robot_name: str) -> Optional[Dict]:
        """Get information about a specific robot."""
        return self.robot_definitions.get(robot_name)

    def get_location_info(self, location_name: str) -> Optional[Dict]:
        """Get information about a specific location."""
        return self.location_constraints.get(location_name)
