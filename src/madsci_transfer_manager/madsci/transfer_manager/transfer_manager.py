"""Transfer Manager Implementation with Unified Configuration"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

from madsci.client.event_client import EventClient
from pydantic import BaseModel
from madsci.common.types.step_types import Step
from madsci.common.utils import new_ulid_str
from madsci.transfer_manager.transfer_graph import TransferGraph


class TransferManagerConfig(BaseModel):
    """Configuration for Transfer Manager with unified config file."""
    
    config_file_path: Path
    
    def __init__(self, config_file_path: Path = None, **data):
        if config_file_path is None:
            config_file_path = Path("transfer_config.yaml")
        super().__init__(config_file_path=config_file_path, **data)
    
    def load_config(self) -> Dict[str, Any]:
        """Load the unified configuration file."""
        with open(self.config_file_path, 'r') as f:
            return yaml.safe_load(f)


class TransferManager:
    """Main Transfer Manager with graph pathfinding."""
    
    def __init__(
        self, 
        config: TransferManagerConfig, 
        logger: Optional[EventClient] = None,
    )->None:
        """Initialize Transfer Manager with configuration."""
        self.config = config
        self.logger = logger or EventClient()
        self.robot_definitions: Dict[str, Dict] = {}
        self.location_constraints: Dict[str, Dict] = {}
        self.transfer_graph = TransferGraph()
       
        self.logger.info("Loading configuration...")
        self._load_configuration()
        self.logger.info("Building transfer graph...")
        self._build_transfer_graph()
        self.logger.info("Transfer Manager initialized successfully!")
    
    def _load_configuration(self):
        """Load configuration from unified YAML file."""
        # Handle both new unified config and legacy separate configs
        if hasattr(self.config, 'load_config'):
            # New unified config
            config_data = self.config.load_config()
            self.robot_definitions = config_data.get('robots', {})
            self.location_constraints = config_data.get('locations', {})
        else:
            # Legacy separate files (backwards compatibility)
            with open(self.config.robot_definitions_path, 'r') as f:
                self.robot_definitions = yaml.safe_load(f)
            
            with open(self.config.location_constraints_path, 'r') as f:
                self.location_constraints = yaml.safe_load(f)
        
        self.logger.info(f"Loaded {len(self.robot_definitions)} robot definitions: {list(self.robot_definitions.keys())}")
        self.logger.info(f"Loaded {len(self.location_constraints)} location constraints: {list(self.location_constraints.keys())}")
    
    def _build_transfer_graph(self):
        """Build the transfer graph from configuration."""
        # Add all locations
        for location_name in self.location_constraints:
            self.transfer_graph.add_location(location_name)
        
        # Build edges based on robot capabilities
        total_edges = 0
        for robot_name, robot_def in self.robot_definitions.items():
            accessible_locations = self._get_robot_accessible_locations(robot_name)
            self.logger.info(f"Robot '{robot_name}' can access: {accessible_locations}")
            
            # Create edges between all accessible location pairs
            for source in accessible_locations:
                for target in accessible_locations:
                    if source != target:
                        cost = self._calculate_transfer_cost(source, target, robot_name)
                        self.transfer_graph.add_edge(source, target, robot_name, cost)
                        total_edges += 1
        
        self.logger.info(f"Created {total_edges} total edges in transfer graph")
    
    def _get_robot_accessible_locations(self, robot_name: str) -> List[str]:
        """Get locations a robot can access."""
        accessible = []
        for location_name, constraint in self.location_constraints.items():
            accessible_by = constraint.get("accessible_by", [])
            if robot_name in accessible_by:
                accessible.append(location_name)
        return accessible
    
    def _calculate_transfer_cost(self, source: str, target: str, robot_name: str) -> float:
        """Calculate cost for a transfer."""
        base_cost = 1.0
        
        # Add complexity based on constraints
        source_constraint = self.location_constraints.get(source, {})
        target_constraint = self.location_constraints.get(target, {})
        
        complexity = len(source_constraint.get("default_args", {})) + len(target_constraint.get("default_args", {}))
        complexity_cost = complexity * 0.1
        
        # Robot-specific overrides add cost
        override_cost = 0.0
        if robot_name in source_constraint.get("robot_overrides", {}):
            override_cost += 0.2
        if robot_name in target_constraint.get("robot_overrides", {}):
            override_cost += 0.2
        
        return base_cost + complexity_cost + override_cost
    
    def expand_transfer_step(self, step: Step) -> List[Step]:
        """
        Main method: Expand a transfer step into concrete workflow steps.
        This is what the workcell manager calls.
        """
        self.logger.info(f"\n=== EXPAND_TRANSFER_STEP ===")
        self.logger.info(f"Input step: node='{step.node}', action='{step.action}'")
        self.logger.info(f"Locations: {step.locations}")
        
        # Only process transfer steps
        if step.action != "transfer":
            self.logger.warning("Not a transfer step - returning as-is")
            return [step]
        
        # Extract source and target - handle LocationArgument objects
        source_raw = step.locations.get("source", "")
        target_raw = step.locations.get("target", "")
        
        # Convert LocationArgument objects to location names
        source = self._extract_location_name(source_raw)
        target = self._extract_location_name(target_raw)
        
        self.logger.info(f"Source: '{source}', Target: '{target}'")
        
        if not source or not target:
            raise ValueError(f"Transfer step missing source or target: {step.name}")
        
        # Check if specific robot requested and can do direct transfer
        if step.node and step.node.strip() and step.node in self.robot_definitions:
            self.logger.info(f"Checking if robot '{step.node}' can do direct transfer...")
            if self._can_robot_transfer(step.node, source, target):
                self.logger.info(f"Using direct transfer with robot '{step.node}'")
                concrete_step = self._build_transfer_step(
                    source=source,
                    target=target,
                    robot_name=step.node,
                    robot_definition=self.robot_definitions[step.node],
                    user_parameters=step.args or {},
                    original_locations=step.locations  # Pass original LocationArgument objects
                )
                return [concrete_step]
            else:
                self.logger.warning(f"Robot '{step.node}' cannot do direct transfer - using graph")
        else:
            self.logger.warning("No specific robot requested - using graph pathfinding")

        # Use graph pathfinding
        transfer_path = self.transfer_graph.find_shortest_path(source, target)
        
        if not transfer_path:
            raise ValueError(f"No transfer path found from {source} to {target}")
        
        self.logger.info(f"\nFound path with {len(transfer_path)} hops:")
        for i, hop in enumerate(transfer_path):
            self.logger.info(f"  Hop {i+1}: {hop['source']} -> {hop['target']} via '{hop['robot']}'")
        
        # Build concrete steps
        concrete_steps = []
        for i, hop in enumerate(transfer_path):
            robot_name = hop["robot"]
            
            if not robot_name or robot_name not in self.robot_definitions:
                raise ValueError(f"Invalid robot '{robot_name}' in hop {i+1}: {hop}")
            
            concrete_step = self._build_transfer_step(
                source=hop["source"],
                target=hop["target"],
                robot_name=robot_name,
                robot_definition=self.robot_definitions[robot_name],
                user_parameters=step.args or {},
                original_locations=step.locations  # Pass original LocationArgument objects
            )
            concrete_step.name = f"Transfer {i+1}: {hop['source']} -> {hop['target']} via {robot_name}"
            concrete_steps.append(concrete_step)
        
        self.logger.info(f"Generated {len(concrete_steps)} concrete steps")
        return concrete_steps
    
    def _can_robot_transfer(self, robot_name: str, source: str, target: str) -> bool:
        """Check if robot can transfer between two locations."""
        source_constraint = self.location_constraints.get(source, {})
        target_constraint = self.location_constraints.get(target, {})
        
        source_ok = robot_name in source_constraint.get("accessible_by", [])
        target_ok = robot_name in target_constraint.get("accessible_by", [])
        
        return source_ok and target_ok
    
    def _build_transfer_step(
        self,
        source: str,
        target: str,
        robot_name: str,
        robot_definition: Dict,
        user_parameters: Dict,
        original_locations: Dict = None
    ) -> Step:
        """Build a concrete transfer step with merged parameters."""
        self.logger.log_info(f"Building step for {source} -> {target} via {robot_name}")
        
        # Start with robot's template
        step_template = robot_definition["default_step_template"].copy()
        
        # Replace template variables
        step_template = self._replace_template_variables(
            step_template,
            robot_name=robot_name,
            source=source,
            target=target
        )
        
        # Merge parameters
        merged_args = self._merge_parameters(
            robot_definition=robot_definition,
            source=source,
            target=target,
            user_parameters=user_parameters
        )
        
        # Update step args
        if 'args' not in step_template:
            step_template['args'] = {}
        step_template['args'].update(merged_args)
        
        # Handle locations - use original LocationArgument objects and update with robot-specific lookup values
        if original_locations:
            # For multi-hop transfers, we need to map the source/target names back to LocationArgument objects
            step_locations = {}
            
            # Find matching LocationArgument objects and update with robot-specific coordinates
            for key, location_obj in original_locations.items():
                location_name = self._extract_location_name(location_obj)
                if location_name == source:
                    updated_location = self._update_location_with_lookup(location_obj, source, robot_name)
                    step_locations['source'] = updated_location
                elif location_name == target:
                    updated_location = self._update_location_with_lookup(location_obj, target, robot_name)
                    step_locations['target'] = updated_location
            
            # If we couldn't find matching LocationArgument objects, create new ones with lookup values
            if 'source' not in step_locations:
                step_locations['source'] = self._create_location_argument_with_lookup(source, robot_name)
            if 'target' not in step_locations:
                step_locations['target'] = self._create_location_argument_with_lookup(target, robot_name)
                
            step_template['locations'] = step_locations
        
        # Create Step
        concrete_step = Step(**step_template)
        concrete_step.step_id = new_ulid_str()
        
        return concrete_step
    def _update_location_with_lookup(self, location_obj: Any, location_name: str, robot_name: str) -> Any:
        """Update a LocationArgument object with robot-specific lookup coordinates."""
        # Create a copy of the location object to avoid modifying the original
        if hasattr(location_obj, 'model_copy'):
            updated_location = location_obj.model_copy()
        else:
            # Fallback for objects without model_copy
            updated_location = location_obj
        
        # Get lookup coordinates for this robot and location
        lookup_coordinates = self._get_lookup_coordinates(location_name, robot_name)
        
        if lookup_coordinates is not None:
            updated_location.location = lookup_coordinates
            print(f"Updated {location_name} coordinates for {robot_name}: {lookup_coordinates}")
        else:
            print(f"No lookup coordinates found for {location_name} with robot {robot_name}")
        
        return updated_location
    
    def _create_location_argument_with_lookup(self, location_name: str, robot_name: str) -> Dict:
        """Create a new LocationArgument with robot-specific lookup coordinates."""
        lookup_coordinates = self._get_lookup_coordinates(location_name, robot_name)
        
        return {
            "location_name": location_name,
            "location": lookup_coordinates,
            "resource_id": None  # Will be filled by workcell if needed
        }
    
    def _get_lookup_coordinates(self, location_name: str, robot_name: str) -> Any:
        """Get robot-specific coordinates from location lookup table."""
        location_constraint = self.location_constraints.get(location_name, {})
        lookup_table = location_constraint.get("lookup", {})
        
        # Check if this robot has lookup coordinates for this location
        robot_coordinates = lookup_table.get(robot_name)
        
        if robot_coordinates is not None:
            print(f"Found lookup coordinates for {location_name}.{robot_name}: {robot_coordinates}")
            return robot_coordinates
        else:
            print(f"No lookup coordinates found for {location_name}.{robot_name}")
            return None
        
    def _merge_parameters(
        self,
        robot_definition: Dict,
        source: str,
        target: str,
        user_parameters: Dict
    ) -> Dict:
        """Merge parameters with proper precedence."""
        # 1. Robot defaults
        merged = robot_definition.get("default_args", {}).copy()
        
        # 2. Location defaults
        source_constraint = self.location_constraints.get(source, {})
        target_constraint = self.location_constraints.get(target, {})
        
        merged.update(source_constraint.get("default_args", {}))
        merged.update(target_constraint.get("default_args", {}))
        
        # 3. Robot-specific overrides for locations
        robot_name = robot_definition["robot_name"]
        
        source_overrides = source_constraint.get("robot_overrides", {}).get(robot_name, {})
        target_overrides = target_constraint.get("robot_overrides", {}).get(robot_name, {})
        
        merged.update(source_overrides)
        merged.update(target_overrides)
        
        # 4. User parameters (highest precedence)
        merged.update(user_parameters)
        
        return merged
    
    def _extract_location_name(self, location_value) -> str:
        """
        Extract location name from LocationArgument object or string.
        
        Args:
            location_value: Either a LocationArgument object or a string
            
        Returns:
            str: The location name to use for graph lookups
        """
        # If it's a LocationArgument object
        if hasattr(location_value, 'location_name') or hasattr(location_value, 'location'):
            # First try location_name if it's provided and not None
            if hasattr(location_value, 'location_name') and location_value.location_name:
                return location_value.location_name
            
            # If location_name is None/missing, use location field as string
            if hasattr(location_value, 'location') and location_value.location is not None:
                return str(location_value.location)
        
        # If it's already a string, return it
        if isinstance(location_value, str):
            return location_value
        
        # If it has a 'name' attribute (alternative structure)
        if hasattr(location_value, 'name'):
            return location_value.name
            
        # Fallback: convert to string
        return str(location_value)
    
    def _replace_template_variables(self, template: Any, **variables) -> Any:
        """Replace template variables like {robot_name}, {source}, {target}."""
        if isinstance(template, str):
            for var_name, var_value in variables.items():
                template = template.replace(f"{{{var_name}}}", str(var_value))
            return template
        elif isinstance(template, dict):
            return {k: self._replace_template_variables(v, **variables) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._replace_template_variables(item, **variables) for item in template]
        else:
            return template
    
    # Utility methods
    def get_available_robots(self) -> List[str]:
        """Get available robots."""
        return list(self.robot_definitions.keys())
    
    def get_available_locations(self) -> List[str]:
        """Get available locations."""
        return list(self.location_constraints.keys())
    
    def get_transfer_options(self, source: str, target: str, max_options: int = 3) -> List[Dict]:
        """Get multiple transfer path options."""
        # For now, just return the single best path
        path = self.transfer_graph.find_shortest_path(source, target)
        if not path:
            return []
        
        total_cost = sum(1.0 for _ in path)  # Simple cost calculation
        robots_used = [hop["robot"] for hop in path]
        
        return [{
            "option": 1,
            "path": path,
            "total_cost": total_cost,
            "num_hops": len(path),
            "robots_used": robots_used,
            "description": f"{len(path)} hops via {', '.join(set(robots_used))}"
        }]
    
    def validate_transfer_request(self, source: str, target: str) -> Dict[str, Any]:
        """Validate if a transfer is possible."""
        result = {
            "valid": False,
            "reachable": False,
            "source_exists": source in self.location_constraints,
            "target_exists": target in self.location_constraints,
            "errors": [],
            "suggestions": []
        }
        
        if not result["source_exists"]:
            result["errors"].append(f"Source location '{source}' not found")
        
        if not result["target_exists"]:
            result["errors"].append(f"Target location '{target}' not found")
        
        if result["source_exists"] and result["target_exists"]:
            path = self.transfer_graph.find_shortest_path(source, target)
            result["reachable"] = path is not None
            
            if result["reachable"]:
                result["valid"] = True
            else:
                result["errors"].append(f"No path exists from {source} to {target}")
        
        return result