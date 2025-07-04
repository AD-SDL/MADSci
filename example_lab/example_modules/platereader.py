"""A fake plate reader module for testing."""

from typing import Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionResult, ActionSucceeded
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import RestNodeConfig
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


class PlateReaderNode(RestNode):
    """A fake plate reader node module for testing."""

    plate_reader: PlateReaderInterface = None
    config_model = PlateReaderConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.plate_reader = PlateReaderInterface(logger=self.logger)
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

        return ActionSucceeded(data={"example_data": {"example": "data"}})

    def get_location(self) -> AdminCommandResponse:
        """Get location for the plate reader"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    plate_reader_node = PlateReaderNode()
    plate_reader_node.start_node()
