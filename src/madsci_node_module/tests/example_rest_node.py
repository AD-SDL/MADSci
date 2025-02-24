"""A test REST Node for validating the madsci.node_module package."""

from typing import Optional

from madsci.client.event_client import EventClient
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.abstract_node_module import action
from madsci.node_module.rest_node_module import RestNode


class TestNodeConfig(RestNodeConfig):
    """Configuration for the test node module."""

    test_required_param: int
    """A required parameter."""
    test_optional_param: Optional[int] = None
    """An optional parameter."""
    test_default_param: int = 42
    """A parameter with a default value."""


class TestNodeInterface:
    """A fake test interface for testing."""

    status_code: int = 0

    def __init__(self, logger: Optional[EventClient] = None) -> "TestNodeInterface":
        """Initialize the test interface."""
        self.logger = logger if logger else EventClient()

    def run_command(self, command: str, fail: bool = False) -> bool:
        """Run a command on the test interface."""
        self.logger.log(f"Running command {command}.")
        if fail:
            self.logger.log(f"Failed to run command {command}.")
            return False
        return True


class TestNode(RestNode):
    """A test node module for automated testing."""

    test_interface: TestNodeInterface = None
    config_model = TestNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.test_interface = TestNodeInterface(logger=self.logger)
        self.logger.log("Test node initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        del self.test_interface

    def state_handler(self) -> dict[str, int]:
        """Periodically called to get the current state of the node."""
        if self.test_interface is not None:
            self.node_state = {
                "test_status_code": self.test_interface.status_code,
            }
        return self.node_state

    @action
    def test_action(self, test_param: int) -> bool:
        """A test action."""
        return self.test_interface.run_command(f"Test action with param {test_param}.")

    @action
    def test_action_fail(self, test_param: int) -> bool:
        """A test action that fails."""
        return self.test_interface.run_command(
            f"Test action with param {test_param}.", fail=True
        )


if __name__ == "__main__":
    test_node = TestNode()
    test_node.start_node()
