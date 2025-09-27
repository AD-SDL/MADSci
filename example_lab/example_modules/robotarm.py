"""A fake robot arm module for testing."""

import time
from typing import Annotated, Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from pydantic import Field


class RobotArmConfig(RestNodeConfig):
    """Configuration for the robot arm node module."""

    device_number: int = 0
    """The device number of the robot arm."""
    speed: Optional[float] = Field(default=50.0, ge=1.0, le=100.0)
    """The speed of the robot arm, in mm/s."""


class RobotArmInterface:
    """A fake robot arm interface for testing."""

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self, device_number: int = 0, logger: Optional[EventClient] = None
    ) -> "RobotArmInterface":
        """Initialize the robot arm."""
        self.logger = logger or EventClient()
        self.device_number = device_number

    def run_command(self, command: str) -> None:
        """Run a command on the robot arm."""
        self.logger.log(
            f"Running command {command} on device number {self.device_number}."
        )
        time.sleep(2)  # Simulate command execution


class RobotArmNode(RestNode):
    """A fake robot arm node module for testing."""

    robot_arm: RobotArmInterface = None
    config: RobotArmConfig = RobotArmConfig()
    config_model = RobotArmConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.robot_arm = RobotArmInterface(logger=self.logger)
        resource_name = "robot_arm_gripper_" + str(self.node_definition.node_name)
        slot_def = SlotResourceDefinition(resource_name=resource_name)
        self.gripper = self.resource_client.init_resource(slot_def)
        self.logger.log("Robot arm initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        del self.robot_arm

    def state_handler(self) -> dict[str, Any]:
        """Periodically called to get the current state of the node."""
        if self.robot_arm is not None:
            self.node_state = {
                "robot_arm_status_code": self.robot_arm.status_code,
            }

    @action
    def transfer(
        self,
        source: Annotated[LocationArgument, "The source location"],
        target: Annotated[LocationArgument, "the target location"],
        speed: Annotated[
            Optional[float], "The speed of the transfer, in 1-100 mm/s"
        ] = None,
    ) -> None:
        """Transfer a plate from one location to another, at the specified speed."""
        if not speed:
            speed = self.config.speed
        speed = max(1.0, min(100.0, speed))  # Clamp speed to 1-100 mm/s
        if self.resource_client:
            try:
                popped_plate, _ = self.resource_client.pop(resource=source.resource_id)
            except Exception:
                raise ValueError("No plate in source!") from None
            self.resource_client.push(
                resource=self.gripper.resource_id, child=popped_plate
            )

            time.sleep(100 / speed)  # Simulate time taken to move

            popped_plate, _ = self.resource_client.pop(
                resource=self.gripper.resource_id
            )
            self.resource_client.push(resource=target.resource_id, child=popped_plate)

    def get_location(self) -> AdminCommandResponse:
        """Get location for the robot arm"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    robot_arm_node = RobotArmNode()
    robot_arm_node.start_node()
