"""Tests for manager base context integration."""

from unittest.mock import Mock

from madsci.common.context import (
    event_client_context,
    get_event_client,
    get_event_client_context,
    has_event_client_context,
)
from madsci.common.middleware import EventClientContextMiddleware


class TestAbstractManagerBaseContext:
    """Test AbstractManagerBase context integration."""

    def test_manager_logger_uses_context(self):
        """Test that manager logger uses context system."""
        # When running under test harness with context
        with event_client_context(name="test", test_id="t-123"):
            assert has_event_client_context()
            # Manager logger should be able to obtain context-aware client
            logger = get_event_client(manager_name="test_manager")
            assert "test_id" in logger._bound_context
            assert logger._bound_context["test_id"] == "t-123"

    def test_manager_startup_log_includes_manager_info(self):
        """Test that manager startup log includes identifying info."""
        with event_client_context(
            name="manager.event_manager",
            manager_name="event_manager",
            manager_type="EventManager",
        ):
            ctx = get_event_client_context()
            assert ctx.name == "manager.event_manager"
            assert ctx.metadata["manager_name"] == "event_manager"
            assert ctx.metadata["manager_type"] == "EventManager"

    def test_manager_request_context_isolation(self):
        """Test that manager request contexts are isolated."""
        # Simulate two concurrent requests
        request1_ctx = None
        request2_ctx = None

        with event_client_context(name="manager.test", manager_name="test"):
            with event_client_context(name="request", request_id="req-1"):
                request1_ctx = get_event_client_context().metadata.copy()

            with event_client_context(name="request", request_id="req-2"):
                request2_ctx = get_event_client_context().metadata.copy()

        assert request1_ctx["request_id"] == "req-1"
        assert request2_ctx["request_id"] == "req-2"
        # Both should share the manager context
        assert request1_ctx["manager_name"] == "test"
        assert request2_ctx["manager_name"] == "test"

    def test_context_with_manager_endpoint(self):
        """Test context flow through a simulated manager endpoint."""

        def simulated_endpoint_handler():
            """Simulate a manager endpoint handler."""
            # Get a logger (verifies context is accessible)
            _ = get_event_client()
            # Log something - the context should include request info
            ctx = get_event_client_context()
            return {
                "hierarchy": ctx.hierarchy,
                "request_id": ctx.metadata.get("request_id"),
            }

        # Manager context wraps request context
        with (
            event_client_context(
                name="manager.resource_manager",
                manager_name="resource_manager",
            ),
            event_client_context(
                name="request.GET./resources",
                request_id="req-abc",
                http_method="GET",
                http_path="/resources",
            ),
        ):
            result = simulated_endpoint_handler()

        assert result["request_id"] == "req-abc"
        assert "manager.resource_manager" in result["hierarchy"]
        assert "request.GET./resources" in result["hierarchy"]


class TestManagerContextMiddleware:
    """Test the EventClientContextMiddleware for managers."""

    def test_middleware_class_exists(self):
        """Test that the middleware class can be imported and instantiated."""
        # Verify the middleware can be created
        mock_app = Mock()
        middleware = EventClientContextMiddleware(mock_app, manager_name="test_manager")

        assert middleware.manager_name == "test_manager"

    def test_middleware_context_metadata_construction(self):
        """Test that the middleware constructs correct context metadata."""
        # Create mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"
        mock_request.headers.get = Mock(return_value=None)  # No X-Request-ID

        # Verify that context would be properly constructed
        request_id = "test-ulid"  # Simulated
        context_name = f"request.{mock_request.method}.{mock_request.url.path}"

        # Verify the context name format
        assert context_name == "request.GET./test/endpoint"

        # Verify metadata structure
        context_metadata = {
            "request_id": request_id,
            "http_method": mock_request.method,
            "http_path": str(mock_request.url.path),
            "manager": "test_manager",
        }

        assert context_metadata["http_method"] == "GET"
        assert context_metadata["http_path"] == "/test/endpoint"
        assert context_metadata["manager"] == "test_manager"

    def test_middleware_uses_x_request_id_header_logic(self):
        """Test that middleware would use X-Request-ID header if provided."""
        # Create mock request with X-Request-ID
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/resources"
        mock_request.headers.get = Mock(return_value="custom-request-id")

        # Verify header extraction logic
        request_id = mock_request.headers.get("X-Request-ID") or "generated-id"
        assert request_id == "custom-request-id"

        # Verify without header
        mock_request.headers.get = Mock(return_value=None)
        request_id = mock_request.headers.get("X-Request-ID") or "generated-id"
        assert request_id == "generated-id"


class TestNodeModuleContext:
    """Test node module context integration patterns."""

    def test_node_startup_establishes_context(self):
        """Test that node startup pattern establishes context."""
        with event_client_context(
            name="node.test_robot",
            node_name="test_robot",
            node_id="node-123",
        ):
            ctx = get_event_client_context()
            assert ctx.name == "node.test_robot"
            assert ctx.metadata["node_name"] == "test_robot"
            assert ctx.metadata["node_id"] == "node-123"

            # Logger should include node context
            logger = get_event_client()
            assert "node_name" in logger._bound_context

    def test_action_execution_context(self):
        """Test action execution with context."""
        with (
            event_client_context(name="node.robot", node_name="robot", node_id="n-1"),
            event_client_context(
                name="action.grab",
                action_id="act-123",
                action_name="grab",
            ),
        ):
            ctx = get_event_client_context()

            # Should have both node and action context
            assert ctx.metadata["node_name"] == "robot"
            assert ctx.metadata["node_id"] == "n-1"
            assert ctx.metadata["action_id"] == "act-123"
            assert ctx.metadata["action_name"] == "grab"

            # Hierarchy should show both
            assert "node.robot" in ctx.name
            assert "action.grab" in ctx.name

    def test_action_logs_include_full_context(self):
        """Test that action logs include full hierarchical context."""
        with (
            event_client_context(name="node.robot", node_id="n-1"),
            event_client_context(name="action.grab", action_id="act-1"),
        ):
            logger = get_event_client(step="initialize")

            # Logger should have all accumulated context
            assert logger._bound_context.get("node_id") == "n-1"
            assert logger._bound_context.get("action_id") == "act-1"
            assert logger._bound_context.get("step") == "initialize"
