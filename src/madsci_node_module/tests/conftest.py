"""Consolidated fixtures for MADSci node module tests."""

import contextlib
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from madsci.client.event_client import EventClient
from madsci.node_module.abstract_node_module import AbstractNode
from rich.logging import RichHandler

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


@pytest.fixture(autouse=True)
def mock_madsci_context_no_event_server():
    """Ensure no EventClient tries to connect to a real event server during tests.

    This fixture patches get_current_madsci_context to return a context with
    event_server_url=None, preventing any EventClient from attempting to connect
    to a real event server at localhost:8001.
    """
    mock_context = MagicMock()
    mock_context.event_server_url = None

    with patch(
        "madsci.client.event_client.get_current_madsci_context",
        return_value=mock_context,
    ):
        yield


@pytest.fixture(autouse=True, scope="module")
def cleanup_temp_files():
    """Clean up temporary files created during tests to prevent file descriptor leaks.

    Uses module scope to reduce overhead while still preventing "too many open files"
    errors. Temp files are cleaned up after each test module completes rather than
    after every individual test.
    """
    temp_dir = Path(tempfile.gettempdir())

    # Get the set of temp files before the module runs
    before_files = set(temp_dir.glob("tmp*"))

    yield

    # Get temp files after the module and clean up new ones
    after_files = set(temp_dir.glob("tmp*"))
    new_files = after_files - before_files

    for filepath in new_files:
        with contextlib.suppress(Exception):
            if filepath.is_file():
                filepath.unlink()
            elif filepath.is_dir():
                shutil.rmtree(filepath, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Configure logging for tests to suppress event client console output."""
    # Get the original __init__ method before patching
    original_init = EventClient.__init__

    def mock_init(*args, **kwargs):
        """Mock EventClient.__init__ to not add RichHandler."""
        # Call the original __init__ but capture and remove RichHandler
        original_init(*args, **kwargs)
        # Remove only the RichHandler, keep the file handler
        self = args[0]  # First argument is self
        handlers_to_remove = [
            handler
            for handler in self.logger.handlers
            if isinstance(handler, RichHandler)
        ]
        for handler in handlers_to_remove:
            self.logger.removeHandler(handler)

    # Patch the EventClient's __init__ method
    with patch.object(EventClient, "__init__", mock_init):
        yield


@pytest.fixture
def test_node_factory() -> Generator[Callable[..., TestNode], None, None]:
    """Factory for creating test nodes with different configurations.

    This replaces multiple TestNode variants (TestNode, EnhancedTestNode,
    OpenAPISchemaTestNode, etc.) with a single configurable factory.
    """
    # Track all created nodes for cleanup
    created_nodes: list[TestNode] = []

    def _create_node(
        actions: Optional[Dict[str, Callable]] = None,
        config_overrides: Optional[Dict] = None,
        node_name: str = "Test Node",
        module_name: str = "test_node",
        **config_kwargs,
    ) -> TestNode:
        """Create a test node with optional customizations.

        Args:
            actions: Dictionary of additional action methods to add to the node
            config_overrides: Override specific config values
            node_name: Name for the node
            module_name: Module name for the node
            **config_kwargs: Additional config parameters

        Returns:
            Configured TestNode instance
        """
        # Create base config with identity fields
        config_params = {
            "test_required_param": 1,
            "node_name": node_name,
            "module_name": module_name,
            **config_kwargs,
        }
        if config_overrides:
            config_params.update(config_overrides)

        node_config = TestNodeConfig(**config_params)

        # Create the node
        node = TestNode(
            node_config=node_config,
        )
        created_nodes.append(node)

        # Add any additional actions dynamically
        if actions:
            for action_name, action_method in actions.items():
                # Bind the method to the node instance
                bound_method = action_method.__get__(node, TestNode)
                setattr(node, action_name, bound_method)

        return node

    yield _create_node

    # Cleanup: close EventClient on all created nodes
    for node in created_nodes:
        with contextlib.suppress(Exception):
            if hasattr(node, "event_client") and node.event_client:
                node.event_client.close()


@pytest.fixture
def basic_test_node(test_node_factory) -> TestNode:
    """Basic test node for standard tests."""
    return test_node_factory()


@pytest.fixture
def enhanced_test_node(test_node_factory) -> TestNode:
    """Enhanced test node with additional capabilities."""
    return test_node_factory(
        node_name="Enhanced Test Node", module_name="enhanced_test_node"
    )


@pytest.fixture
def openapi_test_node(test_node_factory) -> TestNode:
    """Test node configured for OpenAPI schema testing."""
    return test_node_factory(
        node_name="OpenAPI Schema Test Node", module_name="openapi_schema_test_node"
    )


@pytest.fixture
def argument_test_node(test_node_factory) -> TestNode:
    """Test node configured for argument testing."""
    return test_node_factory(
        node_name="Argument Test Node", module_name="argument_test_node"
    )


@pytest.fixture
def var_args_test_node(test_node_factory) -> TestNode:
    """Test node configured for variable arguments testing."""
    return test_node_factory(
        node_name="Var Args Test Node", module_name="var_args_test_node"
    )


@pytest.fixture
def client_factory(
    test_node_factory,
) -> Generator[Callable[..., TestClient], None, None]:
    """Factory for creating test clients with different configurations.

    This replaces multiple client fixtures (test_client, enhanced_client, etc.)
    with a single configurable factory.
    """
    # Track all created clients for cleanup
    created_clients: list[TestClient] = []

    def _create_client(
        node_config: Optional[Dict] = None,
        testing: bool = True,
        startup_wait: float = 0.1,
        **node_kwargs,
    ) -> TestClient:
        """Create a test client with optional node customizations.

        Args:
            node_config: Configuration overrides for the node
            testing: Whether to start node in testing mode
            startup_wait: Time to wait after startup (seconds)
            **node_kwargs: Additional arguments for test_node_factory

        Returns:
            Configured TestClient instance
        """
        # Override config if provided
        if node_config:
            node_kwargs.setdefault("config_overrides", {}).update(node_config)

        node = test_node_factory(**node_kwargs)

        # Start the node
        if testing:
            node.start_node(testing=True)
        else:
            # Call parent's start_node to trigger startup logic for special cases
            AbstractNode.start_node(node)

        client = TestClient(node.rest_api)
        created_clients.append(client)

        if startup_wait > 0:
            time.sleep(startup_wait)

        return client

    yield _create_client

    # Cleanup: close all created clients to prevent file descriptor leaks
    for client in created_clients:
        with contextlib.suppress(Exception):
            client.close()


@pytest.fixture
def test_client(client_factory) -> TestClient:
    """Standard test client for most tests."""
    # client_factory now yields and handles cleanup
    return client_factory()


@pytest.fixture
def enhanced_client(client_factory) -> TestClient:
    """Enhanced test client."""
    # client_factory now yields and handles cleanup
    return client_factory(
        node_name="Enhanced Test Node", module_name="enhanced_test_node"
    )


@pytest.fixture
def openapi_test_client(client_factory) -> TestClient:
    """Test client for OpenAPI schema testing."""
    # client_factory now yields and handles cleanup
    return client_factory(
        node_name="OpenAPI Schema Test Node", module_name="openapi_schema_test_node"
    )


@pytest.fixture
def argument_test_client(client_factory) -> TestClient:
    """Test client for argument testing."""
    # client_factory now yields and handles cleanup
    return client_factory(
        node_name="Argument Test Node", module_name="argument_test_node"
    )


@pytest.fixture
def var_args_test_client(client_factory) -> TestClient:
    """Test client for variable arguments testing."""
    # client_factory now yields and handles cleanup
    return client_factory(
        node_name="Var Args Test Node",
        module_name="var_args_test_node",
        testing=False,  # Special case for var args tests
    )


# Legacy fixtures for backward compatibility during migration
@pytest.fixture
def test_node(basic_test_node) -> TestNode:
    """Legacy test_node fixture - delegates to basic_test_node."""
    return basic_test_node
