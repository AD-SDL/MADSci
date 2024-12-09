"""A fake liquid handler module for testing."""

from typing import Any

from madsci.common.types.action_types import ActionResult, ActionSucceeded
from madsci.module.abstract_module import action
from madsci.module.rest_module import RestNode


class LiquidHandler:
    """A fake liquid handler for testing."""

    status_code: int = 0

    def __init__(self) -> "LiquidHandler":
        """Initialize the liquid handler."""

    def run_command(self, command: str) -> None:
        """Run a command on the liquid handler."""
        print(f"Running command: {command}")


class LiquidHandlerModule(RestNode):
    """A fake liquid handler module for testing."""

    liquid_handler: LiquidHandler = None

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.liquid_handler = LiquidHandler()

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        print("Shutting down")
        del self.liquid_handler

    def state_handler(self) -> dict[str, Any]:
        """Periodically called to get the current state of the node."""
        if self.liquid_handler is not None:
            self.node_state = {
                "liquid_handler_status_code": self.liquid_handler.status_code,
            }

    @action
    def run_command(self, command: str) -> ActionResult:
        """Run a command on the liquid handler."""
        self.liquid_handler.run_command(command)
        return ActionSucceeded()


if __name__ == "__main__":
    liquid_handler_node = LiquidHandlerModule()
    liquid_handler_node.start_node()
