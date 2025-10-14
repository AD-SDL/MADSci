"""A fake liquid handler module for testing."""

import time
from pathlib import Path
from typing import Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class LiquidHandlerConfig(RestNodeConfig):
    """Configuration for the liquid handler node module."""

    device_number: int = 0
    """The device number of the liquid handler."""
    wait_time: float = 2.0
    """Time to wait while running an action, in seconds."""


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

    def run_command(self, command: str) -> None:
        """Run a command on the liquid handler."""
        self.logger.log(
            f"Running command {command} on device number {self.device_number}."
        )
        time.sleep(2)  # Simulate command execution


class LiquidHandlerNode(RestNode):
    """A fake liquid handler node module for testing."""

    liquid_handler: LiquidHandlerInterface = None
    config: LiquidHandlerConfig = LiquidHandlerConfig()
    config_model = LiquidHandlerConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.liquid_handler = LiquidHandlerInterface(
            logger=self.logger, device_number=self.config.device_number
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
        time.sleep(self.config.wait_time)
        return command

    @action
    def run_protocol(self, protocol: Path) -> dict:
        """Run a protocol on the liquid handler"""
        self.logger.log(protocol)
        time.sleep(self.config.wait_time)
        return {"protocol_name": str(protocol.name)}

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
        time.sleep(self.config.wait_time)
        self.resource_client.push(
            target_location.resource_id,
            self.resource_client.pop(source_location.resource_id)[0].resource_id,
        )

    def get_location(self) -> AdminCommandResponse:
        """Get location for the liquid handler"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    liquid_handler_node = LiquidHandlerNode()
    liquid_handler_node.start_node()
