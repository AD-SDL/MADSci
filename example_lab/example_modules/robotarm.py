"""A fake robot arm module for testing."""

import time
from typing import Annotated, Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import Error
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class RobotArmConfig(RestNodeConfig):
    """Configuration for the robot arm node module."""

    device_number: int = 0
    """The device number of the robot arm."""


class RobotArmInterface:
    """A fake robot arm interface for testing."""

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self, device_number: int = 0, logger: Optional[EventClient] = None
    ) -> "RobotArmInterface":
        """Initialize the robot arm."""
        self.logger = logger if logger else EventClient()
        self.device_number = device_number

    def run_command(self, command: str) -> None:
        """Run a command on the robot arm."""
        self.logger.log(
            f"Running command {command} on device number {self.device_number}."
        )


class RobotArmNode(RestNode):
    """A fake robot arm node module for testing."""

    robot_arm: RobotArmInterface = None
    config_model = RobotArmConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.robot_arm = RobotArmInterface(logger=self.logger)
        ownership_info = OwnershipInfo(node_id=self.node_definition.node_id)
        resource_name = "robot_arm_gripper_" + str(self.node_definition.node_name)
        slot_def = SlotResourceDefinition(
            resource_name=resource_name, owner=ownership_info
        )
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
    ) -> ActionResult:
        """Run a command on the robot arm."""

        if self.resource_client:
            try:
                popped_plate, _ = self.resource_client.pop(resource=source.resource_id)
            except Exception:
                return ActionFailed(errors=[Error(message="No plate in source!")])
            self.resource_client.push(
                resource=self.gripper.resource_id, child=popped_plate
            )

            time.sleep(1)

            popped_plate, _ = self.resource_client.pop(
                resource=self.gripper.resource_id
            )
            self.resource_client.push(resource=target.resource_id, child=popped_plate)

        return ActionSucceeded()

    def get_location(self) -> AdminCommandResponse:
        """Get location for the robot arm"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    robot_arm_node = RobotArmNode()
    robot_arm_node.start_node()
