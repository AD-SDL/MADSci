"""Automated pytest unit tests for the RestNode class."""

import time
import unittest
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from madsci.client.event_client import EventClient
from madsci.common.types.node_types import NodeDefinition, RestNodeConfig
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
        self.logger.log("Shutdown complete.")

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


@pytest.fixture
def test_node() -> TestNode:
    """Return a RestNode instance for testing."""
    node_definition = NodeDefinition(
        node_name="Test Node 1",
        module_name="test_node",
        description="A test node module for automated testing.",
    )

    with unittest.mock.patch(
        "sys.argv", ["program_name", "--test_required_param", "1"]
    ):
        return TestNode(node_definition=node_definition)


@pytest.fixture
def test_client(test_node: TestNode) -> TestClient:
    """Return a TestClient instance for testing."""

    test_node.start_node(testing=True)

    return TestClient(test_node.rest_api)


def test_lifecycle_handlers(test_node: TestNode) -> None:
    """Test the startup_handler and shutdown_handler methods."""

    assert not hasattr(test_node, "startup_has_run")
    assert not hasattr(test_node, "shutdown_has_run")
    assert test_node.test_interface is None

    test_node.start_node(testing=True)

    with TestClient(test_node.rest_api) as client:
        assert test_node.startup_has_run
        assert not hasattr(test_node, "shutdown_has_run")
        assert test_node.test_interface is not None

        response = client.get("/status")
        assert response.status_code == 200

    time.sleep(1)

    assert test_node.startup_has_run
    assert test_node.shutdown_has_run
    assert test_node.test_interface is None
