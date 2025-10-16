"""A fake plate reader module for testing."""

import time
from pathlib import Path
from typing import Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionResult, ActionSucceeded
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class PlateReaderConfig(RestNodeConfig):
    """Configuration for the plate reader node module."""

    device_number: int = 0
    """The device number of the plate reader."""


class PlateReaderInterface:
    """A fake plate reader interface for testing."""

    status_code: int = 0
    device_number: int = 0
    config: PlateReaderConfig = PlateReaderConfig()
    config_model = PlateReaderConfig

    def __init__(
        self, device_number: int = 0, logger: Optional[EventClient] = None
    ) -> "PlateReaderInterface":
        """Initialize the plate reader."""
        self.logger = logger or EventClient()
        self.device_number = device_number

    def run_command(self, command: str) -> None:
        """Run a command on the plate reader."""
        self.logger.log(
            f"Running command {command} on device number {self.device_number}."
        )
        time.sleep(2)  # Simulate command execution


class PlateReaderNode(RestNode):
    """A fake plate reader node module for testing."""

    plate_reader: PlateReaderInterface = None
    config_model = PlateReaderConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.plate_reader = PlateReaderInterface(logger=self.logger)

        # Create plate deck slot template
        plate_deck_slot = Slot(
            resource_name="plate_reader_deck",
            resource_class="PlateReaderDeck",
            capacity=1,
            attributes={
                "slot_type": "plate_deck",
                "can_read": True,
                "description": "Plate reader deck slot where plates are placed for reading",
            },
        )

        self.resource_client.init_template(
            resource=plate_deck_slot,
            template_name="plate_reader_deck_slot",
            description="Template for plate reader deck slot. Represents the deck position where plates are placed for reading.",
            required_overrides=["resource_name"],
            tags=["plate_reader", "deck", "slot", "measurement"],
            created_by=self.node_definition.node_id,
            version="1.0.0",
        )

        # Initialize plate deck resource
        deck_resource_name = "plate_reader_deck_" + str(self.node_definition.node_name)
        self.plate_deck = self.resource_client.create_resource_from_template(
            template_name="plate_reader_deck_slot",
            resource_name=deck_resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized plate deck resource from template: {self.plate_deck.resource_id}"
        )

        self.logger.log("Plate reader initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        del self.plate_reader

    def state_handler(self) -> dict[str, Any]:
        """Periodically called to get the current state of the node."""
        if self.plate_reader is not None:
            self.node_state = {
                "plate_reader_status_code": self.plate_reader.status_code,
            }

    @action
    def read_plate(
        self,
    ) -> ActionResult:
        """Run a command on the plate reader."""
        time.sleep(5)
        return ActionSucceeded(data={"example_data": {"example": "data"}})

    @action
    def create_plate_file(
        self,
    ) -> ActionResult:
        """Run a command on the plate reader."""

        with (Path.home() / "test.txt").open("w") as f:
            self.logger.info(f.write("test"))
        path = str(Path.home() / "test.txt")

        return ActionSucceeded(files={"example_file": path})

    def get_location(self) -> AdminCommandResponse:
        """Get location for the plate reader"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    plate_reader_node = PlateReaderNode()
    plate_reader_node.start_node()
