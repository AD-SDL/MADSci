"""Consolidated fixtures for MADSci node module tests."""

import time
from typing import Callable, Dict, Optional

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.node_types import NodeDefinition
from madsci.node_module.abstract_node_module import AbstractNode

from madsci_node_module.tests.test_node import TestNode, TestNodeConfig


@pytest.fixture
def test_node_factory() -> Callable[..., TestNode]:
    """Factory for creating test nodes with different configurations.

    This replaces multiple TestNode variants (TestNode, EnhancedTestNode,
    OpenAPISchemaTestNode, etc.) with a single configurable factory.
    """

    def _create_node(
        actions: Optional[Dict[str, Callable]] = None,
        config_overrides: Optional[Dict] = None,
        node_name: str = "Test Node",
        module_name: str = "test_node",
        node_definition_overrides: Optional[Dict] = None,
        **config_kwargs,
    ) -> TestNode:
        """Create a test node with optional customizations.

        Args:
            actions: Dictionary of additional action methods to add to the node
            config_overrides: Override specific config values
            node_name: Name for the node
            module_name: Module name for the node
            node_definition_overrides: Override NodeDefinition fields
            **config_kwargs: Additional config parameters

        Returns:
            Configured TestNode instance
        """
        # Create base node definition
        node_def_params = {
            "node_name": node_name,
            "module_name": module_name,
            "description": f"A test node module for automated testing ({node_name}).",
        }
        if node_definition_overrides:
            node_def_params.update(node_definition_overrides)

        node_definition = NodeDefinition(**node_def_params)

        # Create base config
        config_params = {"test_required_param": 1, **config_kwargs}
        if config_overrides:
            config_params.update(config_overrides)

        node_config = TestNodeConfig(**config_params)

        # Create the node
        node = TestNode(
            node_definition=node_definition,
            node_config=node_config,
        )

        # Add any additional actions dynamically
        if actions:
            for action_name, action_method in actions.items():
                # Bind the method to the node instance
                bound_method = action_method.__get__(node, TestNode)
                setattr(node, action_name, bound_method)

        return node

    return _create_node


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
def client_factory(test_node_factory) -> Callable[..., TestClient]:
    """Factory for creating test clients with different configurations.

    This replaces multiple client fixtures (test_client, enhanced_client, etc.)
    with a single configurable factory.
    """

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

        if startup_wait > 0:
            time.sleep(startup_wait)

        return client

    return _create_client


@pytest.fixture
def test_client(client_factory) -> TestClient:
    """Standard test client for most tests."""
    return client_factory()


@pytest.fixture
def enhanced_client(client_factory) -> TestClient:
    """Enhanced test client."""
    return client_factory(
        node_name="Enhanced Test Node", module_name="enhanced_test_node"
    )


@pytest.fixture
def openapi_test_client(client_factory) -> TestClient:
    """Test client for OpenAPI schema testing."""
    return client_factory(
        node_name="OpenAPI Schema Test Node", module_name="openapi_schema_test_node"
    )


@pytest.fixture
def argument_test_client(client_factory) -> TestClient:
    """Test client for argument testing."""
    return client_factory(
        node_name="Argument Test Node", module_name="argument_test_node"
    )


@pytest.fixture
def var_args_test_client(client_factory) -> TestClient:
    """Test client for variable arguments testing."""
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
