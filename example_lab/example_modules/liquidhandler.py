"""
Example Virtual Liquid Handler Node Module for MADSci

This module demonstrates how to implement a virtual laboratory instrument node in MADSci.
It simulates a liquid handling robot with deck positions and pipettes, showing:

1. Node configuration with custom settings
2. Resource template creation and management
3. Action method implementation with proper decorators
4. Resource tracking and location management
5. Event logging and error handling

Key Concepts Demonstrated:
- RestNode inheritance for HTTP API nodes
- @action decorator for exposing callable methods
- Resource templates for reusable lab components
- ULID-based resource identification
- Location-based resource transfers

This serves as a template for creating real instrument drivers.
"""

import time
from pathlib import Path
from typing import Any, Optional
import threading
import functools

from madsci.client.event_client import EventClient
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Pool, Slot
from madsci.common.types.action_types import ActionCancelled
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

# ***
class CancelledError(Exception):
    pass

def cancellable(action_fn):
    @functools.wraps(action_fn)
    def wrapper(self, *args, **kwargs):
        self._cancel_event.clear()
        result_container = {"value": None}
        def run():
            try:
                result_container["value"] = action_fn(self, *args, **kwargs)
            except CancelledError:
                result_container["value"] = self._cancel_result()
            except Exception as e:
                result_container["value"] = e
        t = threading.Thread(target=run)
        t.start()
        while t.is_alive():
            if self._cancel_event.is_set():
                return self._cancel_result()
            time.sleep(0.05)
        return result_container["value"]
    return wrapper

class LiquidHandlerConfig(RestNodeConfig):
    """
    Configuration for the liquid handler node module.

    Extends RestNodeConfig to add liquid handler-specific settings.
    These settings can be overridden via environment variables with
    the node name prefix (e.g., LIQUIDHANDLER_1_DEVICE_NUMBER=1).

    Attributes:
        device_number: Identifier for the physical/virtual liquid handler device
        wait_time: Simulation delay for action execution (seconds)
    """

    device_number: int = 0
    """The device number of the liquid handler (for multi-device setups)."""

    wait_time: float = 20.0
    """Time to wait while running an action, in seconds (simulates real hardware timing)."""


class LiquidHandlerInterface:
    """
    Simulated liquid handler hardware interface.

    This class represents the low-level hardware communication layer that
    would typically interface with real liquid handler firmware/drivers.
    In a real implementation, this would contain actual device communication
    protocols (e.g., serial, TCP/IP, vendor SDK calls).

    Attributes:
        status_code: Current device status (0=OK, >0=error conditions)
        device_number: Hardware device identifier
        logger: Event client for logging device operations
    """

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self, device_number: int = 0, logger: Optional[EventClient] = None
    ) -> "LiquidHandlerInterface":
        """
        Initialize the liquid handler hardware interface.

        Args:
            device_number: Unique identifier for this liquid handler device
            logger: Event client for logging (creates default if None)
        """
        self.logger = logger or EventClient()
        self.device_number = device_number

    def run_command(self, command: str) -> None:
        """Run a command on the liquid handler."""
        self.logger.log(f"Executing hardware command: {command}")
        time.sleep(0.1)


class LiquidHandlerNode(RestNode):
    """
    Virtual Liquid Handler Node for MADSci Laboratory Automation.

    This node simulates a multi-deck liquid handling robot with the following capabilities:
    - Two deck positions (deck1, deck2) for placing labware
    - Multi-channel pipette system for liquid transfers
    - Protocol execution from file-based procedures
    - Resource tracking for plates and consumables
    - Location-based transfers between deck positions

    Node Architecture:
    - Inherits from RestNode for HTTP API exposure
    - Uses @action decorator to expose callable methods
    - Manages resources through ResourceClient integration
    - Logs all operations through EventClient

    Resource Management:
    - Creates and manages deck slot templates (Slot resources)
    - Creates and manages pipette pool templates (Pool resources)
    - Initializes specific deck1, deck2, and pipette instances
    - Tracks resource movements and state changes

    Example Usage:
        # Direct API calls (from curl or other HTTP clients)
        POST /actions/run_command {"command": "aspirate 100 ul"}
        POST /actions/deck_transfer {"source_location": "deck1", "target_location": "deck2"}

        # Via MADSci WorkcellClient
        client.execute_action(node_id, "run_command", {"command": "aspirate 100 ul"})
    """

    # Hardware interface instance (initialized in startup_handler)
    liquid_handler: LiquidHandlerInterface = None

    # Configuration instance with node-specific settings
    config: LiquidHandlerConfig = LiquidHandlerConfig()

    # Pydantic model class for configuration validation
    config_model = LiquidHandlerConfig

    def __init__(self):
        super().__init__()
        self._cancel_event = threading.Event()
    
    def _cancel_result(self):
        action_response = ActionCancelled()
        return action_response

    def startup_handler(self) -> None:
        """
        Initialize the liquid handler node and create resource templates.

        This method is called when the node starts up or restarts. It performs:
        1. Hardware interface initialization
        2. Resource template creation for deck slots and pipettes
        3. Instantiation of specific resources (deck1, deck2, pipette)
        4. Registration of resources with the resource manager

        Resource Template Pattern:
        Templates define reusable resource types that can be instantiated multiple
        times with different names/IDs. This allows labs to easily add new instances
        of similar equipment (e.g., additional deck positions) without code changes.
        """
        # Initialize the hardware interface with event logging
        self.liquid_handler = LiquidHandlerInterface(logger=self.logger)

        # Create deck slot template - represents positions where labware can be placed
        deck_slot = Slot(
            resource_name="liquid_handler_deck",
            resource_class="LiquidHandlerDeck",
            capacity=1,
            attributes={
                "slot_type": "deck_position",
                "accessible": True,
                "description": "Liquid handler deck slot for placing plates or labware",
            },
        )

        self.resource_client.init_template(
            resource=deck_slot,
            template_name="liquid_handler_deck_slot",
            description="Template for liquid handler deck slot. Represents deck positions where plates or labware can be placed.",
            required_overrides=["resource_name"],
            tags=["liquid_handler", "deck", "slot"],
            created_by=self.node_definition.node_id,
            version="1.0.0",
        )

        # Create pipette template (Pool type for holding tips/liquid)
        pipette_pool = Pool(
            resource_name="liquid_handler_pipette",
            resource_class="LiquidHandlerPipette",
            capacity=1000.0,
            attributes={
                "pipette_type": "8-channel",
                "min_volume": 0.5,
                "max_volume": 1000.0,
                "channels": 8,
                "description": "Liquid handler pipette pool for tracking tips and aspirated liquid",
            },
        )

        self.resource_client.init_template(
            resource=pipette_pool,
            template_name="liquid_handler_pipette_pool",
            description="Template for liquid handler pipette pool. Tracks pipette tips and aspirated liquids.",
            required_overrides=["resource_name"],
            tags=["liquid_handler", "pipette", "pool", "consumable"],
            created_by=self.node_definition.node_id,
            version="1.0.0",
        )

        # Initialize deck 1
        deck1_resource_name = f"liquid_handler_deck1_{self.node_definition.node_name}"
        self.deck1 = self.resource_client.create_resource_from_template(
            template_name="liquid_handler_deck_slot",
            resource_name=deck1_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized deck1 resource from template: {self.deck1.resource_id}"
        )

        # Initialize deck 2
        deck2_resource_name = f"liquid_handler_deck2_{self.node_definition.node_name}"
        self.deck2 = self.resource_client.create_resource_from_template(
            template_name="liquid_handler_deck_slot",
            resource_name=deck2_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized deck2 resource from template: {self.deck2.resource_id}"
        )

        # Initialize pipette
        pipette_resource_name = (
            f"liquid_handler_pipette_{self.node_definition.node_name}"
        )
        self.pipette = self.resource_client.create_resource_from_template(
            template_name="liquid_handler_pipette_pool",
            resource_name=pipette_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized pipette resource from template: {self.pipette.resource_id}"
        )

        self.logger.log("Liquid handler initialized!")

    def shutdown_handler(self) -> None:
        """
        Clean shutdown of the liquid handler node.

        This method is called when the node is being shut down or restarted.
        It should clean up any resources, close device connections, and
        ensure the hardware is in a safe state.

        For real hardware, this might include:
        - Parking pipettes in safe positions
        - Closing serial/network connections
        - Saving calibration data
        - Releasing any locked resources
        """
        self.logger.log("Shutting down liquid handler node")
        del self.liquid_handler

    def state_handler(self) -> dict[str, Any]:
        """
        Report current node state for monitoring and debugging.

        This method is called periodically by the MADSci framework to collect
        node status information. The returned data is used for:
        - Dashboard status displays
        - Health monitoring and alerting
        - Debugging and troubleshooting
        - Resource scheduling decisions

        Returns:
            dict: Current node state including hardware status and resource info
        """
        if self.liquid_handler is not None:
            self.node_state = {
                "liquid_handler_status_code": self.liquid_handler.status_code,
            }

    @action
    @cancellable
    def run_command(self, command: str) -> str:
        """
        Execute a direct hardware command on the liquid handler.

        This action demonstrates basic command execution with string parameters
        and simple return values. Useful for debugging and low-level control.

        Args:
            command: Hardware-specific command string (e.g., "aspirate 100 ul", "dispense 50 ul")

        Returns:
            str: Echo of the executed command for confirmation

        Example:
            POST /actions/run_command {"command": "aspirate 100 ul"}
            Response: "aspirate 100 ul"
        """
        self.liquid_handler.run_command(command)
        time.sleep(self.config.wait_time)
        return command

    @action
    def run_protocol(self, protocol: Path) -> dict:
        """
        Execute a protocol file on the liquid handler.

        This action demonstrates file path handling and structured return data.
        In a real implementation, this would parse and execute protocol steps
        from the provided file.

        Args:
            protocol: Path to the protocol file to execute

        Returns:
            dict: Protocol execution results with metadata

        Example:
            POST /actions/run_protocol {"protocol": "/protocols/pcr_setup.json"}
            Response: {"protocol_name": "pcr_setup.json"}
        """
        self.logger.log(f"Executing protocol: {protocol}")
        time.sleep(self.config.wait_time)
        return {"protocol_name": str(protocol.name)}

    @action
    def deck_transfer(
        self, source_location: LocationArgument, target_location: LocationArgument
    ) -> None:
        """
        Transfer labware between deck locations on the liquid handler.

        This action demonstrates:
        - Location-based resource management
        - Resource tracking with pop/push operations
        - Integration between hardware actions and resource state

        The resource system automatically tracks which items are at which
        locations, enabling the workcell manager to coordinate transfers
        between different instruments.

        Args:
            source_location: Location to transfer from (must contain a resource)
            target_location: Destination location (must have available capacity)

        Raises:
            ResourceError: If source location is empty or target is full

        Example:
            POST /actions/deck_transfer {
                "source_location": {"resource_id": "deck1_id"},
                "target_location": {"resource_id": "deck2_id"}
            }
        """
        self.logger.log(
            f"Transferring labware from {source_location} to {target_location}"
        )

        # Execute the physical hardware movement
        self.liquid_handler.run_command(
            f"move_labware {source_location} {target_location}"
        )
        time.sleep(self.config.wait_time)

        # Update resource tracking: remove from source, add to target
        transferred_resource = self.resource_client.pop(source_location.resource_id)[0]
        self.resource_client.push(
            target_location.resource_id, transferred_resource.resource_id
        )

    def get_location(self) -> AdminCommandResponse:
        """
        Get the physical location coordinates of the liquid handler.

        This administrative command returns the position of the liquid handler
        in the laboratory coordinate system. Used for resource tracking and
        automated scheduling decisions.

        Returns:
            AdminCommandResponse: Location data [x, y, z, rotation] in lab coordinates
        """
        return AdminCommandResponse(data=[0, 0, 0, 0])
    
    def cancel(self) -> AdminCommandResponse:
        self._cancel_event.set()
        return AdminCommandResponse()
        


if __name__ == "__main__":
    """
    Direct execution entry point for the liquid handler node.

    When run directly, this starts the liquid handler as a standalone REST API server.
    The node will:
    1. Load configuration from environment variables and YAML files
    2. Initialize hardware connections and resource templates
    3. Start the HTTP server on the configured port
    4. Register with the lab manager and begin accepting requests

    Environment Variables:
        NODE_DEFINITION: Path to node definition YAML file
        NODE_URL: URL for this node's HTTP server
        LIQUIDHANDLER_X_*: Node-specific configuration overrides

    Usage:
        python liquidhandler.py

        # Or via Docker Compose (recommended)
        docker compose up liquidhandler_1
    """
    liquid_handler_node = LiquidHandlerNode()
    liquid_handler_node.start_node()
