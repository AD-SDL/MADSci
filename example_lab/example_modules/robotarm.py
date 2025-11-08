"""A fake robot arm module for testing."""

import time
from typing import Annotated, Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionFailed
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import Slot
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from pydantic import Field


class RobotArmConfig(RestNodeConfig):
    """Configuration for the robot arm node module."""

    device_number: int = 0
    """The device number of the robot arm."""
    speed: Optional[float] = Field(default=50.0, ge=1.0, le=100.0)
    """The speed of the robot arm, in mm/s."""
    wait_time: float = 2.0
    """Time to wait while running an action, in seconds."""


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

        gripper_slot = Slot(
            resource_name="robot_arm_gripper",
            resource_class="RobotArmGripper",
            capacity=1,
            attributes={
                "gripper_type": "robotic_gripper",
                "description": "Robot arm gripper slot",
            },
        )

        self.resource_client.init_template(
            resource=gripper_slot,
            template_name="robot_arm_gripper_slot",
            description="Template for robot arm gripper slot. Used to track what the robot arm is currently holding.",
            required_overrides=["resource_name"],
            tags=["robot_arm", "gripper", "slot", "robot"],
            created_by=self.node_definition.node_id,
            version="1.0.0",
        )

        resource_name = "robot_arm_gripper_" + str(self.node_definition.node_name)
        self.gripper = self.resource_client.create_resource_from_template(
            template_name="robot_arm_gripper_slot",
            resource_name=resource_name,
            add_to_database=True,
        )
        self.logger.log(
            f"Initialized gripper resource from template: {self.gripper.resource_id}"
        )

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
            target_resource = self.resource_client.get_resource(target.resource_id)
            if len(target_resource.children) + 1 > target_resource.capacity:
                return ActionFailed(
                    errors=[
                        Error(message=f"Target location {target.resource_id} is full")
                    ]
                )
            try:
                popped_plate, _ = self.resource_client.pop(resource=source.resource_id)
            except Exception as e:
                return ActionFailed(errors=[Error(message=str(e))])
            self.resource_client.push(
                resource=self.gripper.resource_id, child=popped_plate
            )

        time.sleep(100 / speed)  # Simulate time taken to move

        popped_plate, _ = self.resource_client.pop(resource=self.gripper.resource_id)
        self.resource_client.push(resource=target.resource_id, child=popped_plate)
        return None

    def get_location(self) -> AdminCommandResponse:
        """Get location for the robot arm"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    robot_arm_node = RobotArmNode()
    robot_arm_node.start_node()
