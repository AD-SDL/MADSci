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

import functools
import threading
import time
from pathlib import Path
from typing import Any, ClassVar, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionCancelled, ActionPaused
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import (
    NodeIntrinsicLocationDefinition,
    NodeRepresentationTemplateDefinition,
    NodeResourceTemplateDefinition,
    RestNodeConfig,
)
from madsci.common.types.resource_types import Pool, Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


# ***
class CancelledError(Exception):
    """Raised when an action is cancelled via the cancel admin command."""


class PausedError(Exception):
    """Raised when an action is paused via the pause admin command."""


def interruptable(action_fn: Any) -> Any:
    """Decorator that makes an action interruptable by cancel/pause events."""

    @functools.wraps(action_fn)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        self._cancel_event.clear()
        self._pause_event.clear()
        self.logger.debug("Cancel and pause events cleared in interruptable wrapper")
        result_container: dict[str, Any] = {"value": None, "error": None}

        def run() -> None:
            try:
                self.logger.debug("Running action in interruptable wrapper")
                result_container["value"] = action_fn(self, *args, **kwargs)
            except CancelledError:
                self.logger.debug("CancelledError raised in interruptable wrapper")
                result_container["value"] = self._cancel_result()
            except PausedError:
                self.logger.debug("PausedError raised in interruptable wrapper")
                result_container["value"] = self._pause_result()
            except Exception as e:
                result_container["error"] = e

        t = threading.Thread(target=run, daemon=True)
        t.start()
        while t.is_alive():
            if self._cancel_event.is_set() or self._pause_event.is_set():
                self.logger.debug("Cancel or pause event set, returning from wrapper")
                t.join(timeout=2.0)
                if t.is_alive():
                    self.logger.warning("Action thread still running after interrupt")
                return (
                    self._cancel_result()
                    if self._cancel_event.is_set()
                    else self._pause_result()
                )
            time.sleep(0.05)

        if result_container["error"] is not None:
            raise result_container["error"]
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

    wait_time: float = 2.0
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

    # Declarative template definitions — registered automatically by template_handler()
    resource_templates: ClassVar[list[NodeResourceTemplateDefinition]] = [
        NodeResourceTemplateDefinition(
            resource=Slot(
                resource_name="liquid_handler_deck",
                resource_class="LiquidHandlerDeck",
                capacity=1,
                attributes={
                    "slot_type": "deck_position",
                    "accessible": True,
                    "description": "Liquid handler deck slot for placing plates or labware",
                },
            ),
            template_name="liquid_handler_deck_slot",
            description="Template for liquid handler deck slot. Represents deck positions where plates or labware can be placed.",
            required_overrides=["resource_name"],
            tags=["liquid_handler", "deck", "slot"],
            version="1.0.0",
        ),
        NodeResourceTemplateDefinition(
            resource=Pool(
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
            ),
            template_name="liquid_handler_pipette_pool",
            description="Template for liquid handler pipette pool. Tracks pipette tips and aspirated liquids.",
            required_overrides=["resource_name"],
            tags=["liquid_handler", "pipette", "pool", "consumable"],
            version="1.0.0",
        ),
    ]

    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="lh_deck_repr",
            default_values={"deck_type": "standard", "max_plates": 1},
            schema_def={
                "type": "object",
                "properties": {
                    "deck_position": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Deck slot number on the liquid handler",
                    },
                    "deck_type": {
                        "type": "string",
                        "enum": ["standard", "deep_well", "pcr"],
                        "description": "Type of deck slot",
                    },
                    "max_plates": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Maximum number of plates this slot can hold",
                    },
                    "accessible": {
                        "type": "boolean",
                        "description": "Whether this deck position is currently accessible",
                    },
                },
                "required": ["deck_position"],
            },
            required_overrides=["deck_position"],
            tags=["liquid_handler", "deck"],
            version="1.1.0",
            description="Liquid handler deck slot representation with position and type",
        ),
    ]

    # Intrinsic locations — auto-created on startup with '{node_name}.' prefix
    intrinsic_locations: ClassVar[list[NodeIntrinsicLocationDefinition]] = [
        NodeIntrinsicLocationDefinition(
            location_name=f"deck_{i}",
            description=f"Deck slot {i}",
            representation_template_name="lh_deck_repr",
            representation_overrides={"deck_position": i},
            resource_template_name="liquid_handler_deck_slot",
            allow_transfers=True,
        )
        for i in range(1, 5)
    ]

    def __init__(self) -> None:
        """Initialize the liquid handler node with cancel/pause event support."""
        super().__init__()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()

    def _cancel_result(self) -> ActionCancelled:
        self.logger.debug("Returning cancelled action response")
        return ActionCancelled()

    def _pause_result(self) -> ActionPaused:
        self.logger.debug("Returning paused action response")
        return ActionPaused()

    def _checkpoint(self) -> None:
        if self._cancel_event.is_set():
            self.logger.debug("Cancel event set, raising CancelledError")
            raise CancelledError()
        if self._pause_event.is_set():
            self.logger.debug("Pause event set, raising PausedError")
            raise PausedError()

    def _wait(self, seconds: float, tick: float = 0.1) -> None:
        end = time.monotonic() + seconds
        while True:
            self._checkpoint()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            sleep_time = min(tick, remaining)
            # Wait on cancel; if it doesn't fire, also check pause
            if self._cancel_event.wait(timeout=sleep_time / 2):
                self._checkpoint()
            if self._pause_event.wait(timeout=sleep_time / 2):
                self._checkpoint()

    def startup_handler(self) -> None:
        """
        Initialize the liquid handler node and create resource instances.

        This method is called when the node starts up or restarts. It performs:
        1. Hardware interface initialization
        2. Instantiation of specific resources (deck1, deck2, pipette)
        3. Registration of resources with the resource manager

        Resource templates and representation templates are registered
        automatically by template_handler() before this method is called.
        """
        # Initialize the hardware interface with event logging
        self.liquid_handler = LiquidHandlerInterface(logger=self.logger)

        # Initialize deck 1
        deck1_resource_name = f"liquid_handler_deck1_{self.node_info.node_name}"
        self.deck1 = self.resource_client.create_resource_from_template(
            template_name="liquid_handler_deck_slot",
            resource_name=deck1_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized deck1 resource from template: {self.deck1.resource_id}"
        )

        # Initialize deck 2
        deck2_resource_name = f"liquid_handler_deck2_{self.node_info.node_name}"
        self.deck2 = self.resource_client.create_resource_from_template(
            template_name="liquid_handler_deck_slot",
            resource_name=deck2_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized deck2 resource from template: {self.deck2.resource_id}"
        )

        # Initialize pipette
        pipette_resource_name = f"liquid_handler_pipette_{self.node_info.node_name}"
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
    @interruptable
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
        self.logger.debug("Running run_command action", command=command)
        self.liquid_handler.run_command(command)
        self._wait(seconds=self.config.wait_time)
        return command

    @action
    @interruptable
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
        self._wait(self.config.wait_time)
        return {"protocol_name": str(protocol.name)}

    @action
    @interruptable
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
        self._wait(self.config.wait_time)

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
        """Cancel the currently running action."""
        self.logger.debug("Setting cancel event")
        self._cancel_event.set()
        return AdminCommandResponse()

    def pause(self) -> AdminCommandResponse:
        """Pause the currently running action."""
        self.logger.debug("Setting pause event and paused status")
        self.node_status.paused = True
        self._pause_event.set()
        return AdminCommandResponse()

    def resume(self) -> AdminCommandResponse:
        """Resume a paused action."""
        self.logger.debug("Resuming, setting paused status to False")
        self.node_status.paused = False
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
        NODE_NAME: Name of this node instance
        NODE_URL: URL for this node's HTTP server
        LIQUIDHANDLER_X_*: Node-specific configuration overrides

    Usage:
        python liquidhandler.py

        # Or via Docker Compose (recommended)
        docker compose up liquidhandler_1
    """
    liquid_handler_node = LiquidHandlerNode()
    liquid_handler_node.start_node()
