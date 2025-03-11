"""A Node implementation to use in automated tests."""

from typing import Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionFailed, ActionSucceeded
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.abstract_node_module import action
from madsci.node_module.rest_node_module import RestNode


class TestNodeConfig(RestNodeConfig):
    """Configuration for the test node module."""

    __test__ = False

    test_required_param: int
    """A required parameter."""
    test_optional_param: Optional[int] = None
    """An optional parameter."""
    test_default_param: int = 42
    """A parameter with a default value."""


class TestNodeInterface:
    """A fake test interface for testing."""

    __test__ = False

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

    __test__ = False

    test_interface: TestNodeInterface = None
    config_model = TestNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.logger.log("Node initializing...")
        self.test_interface = TestNodeInterface(logger=self.logger)
        self.startup_has_run = True
        self.logger.log("Test node initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        self.shutdown_has_run = True
        del self.test_interface
        self.test_interface = None
        self.logger.log("Shutdown complete.")

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.test_interface is not None:
            self.node_state = {
                "test_status_code": self.test_interface.status_code,
            }

    @action
    def test_action(self, test_param: int) -> bool:
        """A test action."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}."
        )
        if result:
            return ActionSucceeded()
        return ActionFailed(
            errors=f"`run_command` returned '{result}'. Expected 'True'."
        )

    @action(name="test_fail", description="A test action that fails.")
    def test_action_fail(self, test_param: int) -> bool:
        """A doc string, but not the actual description of the action."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}.", fail=True
        )
        if result:
            return ActionSucceeded()
        return ActionFailed(
            errors=f"`run_command` returned '{result}'. Expected 'True'."
        )

    def pause(self) -> None:
        """Pause the node."""
        self.logger.log("Pausing node...")
        self.node_status.paused = True
        self.logger.log("Node paused.")
        return True

    def resume(self) -> None:
        """Resume the node."""
        self.logger.log("Resuming node...")
        self.node_status.paused = False
        self.logger.log("Node resumed.")
        return True

    def shutdown(self) -> None:
        """Shutdown the node."""
        self.shutdown_handler()
        return True

    def reset(self) -> None:
        """Reset the node."""
        self.logger.log("Resetting node...")
        result = super().reset()
        self.logger.log("Node reset.")
        return result

    def safety_stop(self) -> None:
        """Stop the node."""
        self.logger.log("Stopping node...")
        self.node_status.stopped = True
        self.logger.log("Node stopped.")
        return True

    def cancel(self) -> None:
        """Cancel the node."""
        self.logger.log("Canceling node...")
        self.node_status.cancelled = True
        self.logger.log("Node cancelled.")
        return True


if __name__ == "__main__":
    test_node = TestNode()
    test_node.start_node()
