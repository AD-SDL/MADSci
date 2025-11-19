"""A fake liquid handler module for testing."""

import enum
import time
from pathlib import Path
from typing import Any, Optional
import threading

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import (
    ActionFiles,
    ActionJSON,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Pool, Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class RunCommandJSONData(ActionJSON):
    """JSON data returned from the run_command action"""

    command: str


class RunCommandFileData(ActionFiles):
    """File data returned from the run_command action"""

    log_file: Path


class LiquidHandlerConfig(RestNodeConfig):
    """Configuration for the liquid handler node module."""

    device_number: int = 0
    """The device number of the liquid handler."""


class LiquidHandlerInterface:
    """A fake liquid handler interface for testing."""

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self, device_number: int = 0, logger: Optional[EventClient] = None
    ) -> "LiquidHandlerInterface":
        """Initialize the liquid handler."""
        self.logger = logger or EventClient()
        self.device_number = device_number
        self.sent_cancel = threading.Event()
        self.received_cancel = threading.Event()
    
    def send_cancel(self) -> None:
        self.sent_cancel.set()
    
    def clear_requests(self) -> None:
        self.sent_cancel.clear()
        self.received_cancel.clear()

    def wait_for(self, timeout=10) -> bool:
        return self.received_cancel.wait(timeout)

    def run_command(self, command: str) -> None:
        """Run a command on the liquid handler."""
        self.clear_requests()
        try:
            for _ in range(10):
                if self.sent_cancel.is_set():
                    self.received_cancel.set()
                    return
                time.sleep(0.1)
        finally:
            if self.sent_cancel.is_set() and not self.received_cancel.is_set():
                self.received_cancel.set()


class LiquidHandlerNode(RestNode):
    """A fake liquid handler node module for testing."""

    liquid_handler: LiquidHandlerInterface = None
    config: LiquidHandlerConfig = LiquidHandlerConfig()
    config_model = LiquidHandlerConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.liquid_handler = LiquidHandlerInterface(logger=self.logger)

        # Create deck slot template
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
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        del self.liquid_handler

    def state_handler(self) -> dict[str, Any]:
        """Periodically called to get the current state of the node."""
        if self.liquid_handler is not None:
            self.node_state = {
                "liquid_handler_status_code": self.liquid_handler.status_code,
            }

    @action
    def run_command(self, command: str) -> str:
        """Run a command on the liquid handler. Shows returning both JSON and file data."""
        self.liquid_handler.run_command(command)
        return command

    @action
    def run_protocol(self, protocol: Path) -> Path:
        """Run a protocol on the liquid handler"""
        self.logger.log(protocol)
        self.liquid_handler.run_command("run_protocol")
        return protocol

    @action
    def deck_transfer(
        self, source_location: LocationArgument, target_location: LocationArgument
    ) -> None:
        """Transfer labware between deck locations on the liquid handler."""
        self.logger.log(
            f"Transferring labware from {source_location} to {target_location}"
        )
        self.liquid_handler.run_command(
            f"move_labware {source_location} {target_location}"
        )
        self.resource_client.push(
            target_location.resource_id,
            self.resource_client.pop(source_location.resource_id)[0].resource_id,
        )

    @action
    def arg_type_test(self, x: bool, y: int, z: float, w: str) -> None:
        """Used to test that argument types are correctly passed to the node module."""
        if type(x) is bool and type(y) is int and type(z) is float and type(w) is str:
            self.logger.log(f"Value of x is {x} and type is {type(x)}")
            return
        raise ValueError("Argument types are incorrect")

    def get_location(self) -> AdminCommandResponse:
        """Get location for the liquid handler"""
        return AdminCommandResponse(data=[0, 0, 0, 0])
    
    def cancel(self) -> AdminCommandResponse:
        try:
            self.liquid_handler.send_cancel()
            response = self.liquid_handler.wait_for()
            if not response:
                return AdminCommandResponse(success=False)
            return AdminCommandResponse()
        except Exception as e:
            return AdminCommandResponse(success=False)
        


if __name__ == "__main__":
    liquid_handler_node = LiquidHandlerNode()
    liquid_handler_node.start_node()
