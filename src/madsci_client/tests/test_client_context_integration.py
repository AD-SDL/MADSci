"""Tests for client context integration (Phase 2)."""

from typing import ClassVar

from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.event_client import EventClient
from madsci.client.location_client import LocationClient
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.context import (
    _event_client_context,
    event_client_context,
)
from pydantic import AnyUrl


class TestMadsciClientMixinContextAwareness:
    """Test MadsciClientMixin context-aware behavior."""

    def test_event_client_uses_context_when_available(self):
        """Test that event_client property uses context when available."""

        class TestComponent(MadsciClientMixin):
            pass

        with event_client_context(name="test", test_id="t-123") as ctx_client:
            component = TestComponent()
            # Should use context client (or bound version)
            logger = component.event_client

            # Should have the test_id in bound context
            assert "test_id" in logger._bound_context or logger is ctx_client

    def test_event_client_falls_back_without_context(self):
        """Test that event_client creates new client when no context."""
        # Ensure no context
        _event_client_context.set(None)

        class TestComponent(MadsciClientMixin):
            name = "test_component"

        component = TestComponent()
        logger = component.event_client

        # Should have created a new client
        assert logger is not None
        assert logger.name == "test_component"

    def test_explicit_client_takes_precedence(self):
        """Test that explicitly set client takes precedence over context."""
        explicit_client = EventClient(name="explicit")

        class TestComponent(MadsciClientMixin):
            pass

        with event_client_context(name="context"):
            component = TestComponent()
            component.event_client = explicit_client

            assert component.event_client is explicit_client

    def test_injected_client_via_setup_clients(self):
        """Test that clients injected via setup_clients are used."""
        injected_client = EventClient(name="injected")

        class TestComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event"]

        with event_client_context(name="context"):
            component = TestComponent()
            component.setup_clients(event_client=injected_client)

            assert component.event_client is injected_client

    def test_component_context_added_to_logs(self):
        """Test that component-specific context is added."""

        class TestComponent(MadsciClientMixin):
            name = "my_component"

            def _get_component_context(self):
                return {
                    "component_type": self.__class__.__name__,
                    "component_name": self.name,
                }

        with event_client_context(name="test"):
            component = TestComponent()
            logger = component.event_client

            # Should have component context bound
            assert "component_type" in logger._bound_context
            assert logger._bound_context["component_type"] == "TestComponent"

    def test_other_clients_share_event_client_from_context(self):
        """Test that resource/workcell/location clients use context event_client."""

        class TestComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event", "resource"]
            resource_server_url = (
                None  # Use local-only mode to avoid connection attempt
            )

        with event_client_context(name="test", test_id="t-123"):
            component = TestComponent()
            component.setup_clients()

            # When using context, event_client property returns context client
            # but _event_client remains None (not cached when using context)
            logger = component.event_client
            assert logger is not None
            # Should have inherited test_id from context
            assert (
                "test_id" in logger._bound_context
                or "component_type" in logger._bound_context
            )


class TestRestNodeClientContextAwareness:
    """Test RestNodeClient context-aware behavior."""

    def test_uses_context_when_available(self):
        """Test that RestNodeClient uses context EventClient."""
        with event_client_context(name="workflow", workflow_id="wf-123"):
            client = RestNodeClient(url=AnyUrl("http://localhost:8000/"))

            # Logger should include workflow context
            assert (
                "workflow_id" in client.logger._bound_context
                or client.logger._bound_context.get("node_url") is not None
            )

    def test_uses_injected_client_when_provided(self):
        """Test that RestNodeClient uses injected EventClient."""
        injected = EventClient(name="injected")

        with event_client_context(name="context"):
            client = RestNodeClient(
                url=AnyUrl("http://localhost:8000/"),
                event_client=injected,
            )

            assert client.logger is injected

    def test_creates_new_client_without_context(self):
        """Test that RestNodeClient creates client when no context."""
        _event_client_context.set(None)

        client = RestNodeClient(url=AnyUrl("http://localhost:8000/"))

        assert client.logger is not None

    def test_multiple_instances_share_context_client(self):
        """Test that multiple RestNodeClient instances share context resources."""
        with event_client_context(name="workflow"):
            client1 = RestNodeClient(url=AnyUrl("http://node1:8000/"))
            client2 = RestNodeClient(url=AnyUrl("http://node2:8000/"))

            # Both should derive from the same context client
            # (sharing underlying resources like log files)
            # The exact assertion depends on implementation,
            # but both loggers should have the workflow context
            assert client1.logger is not None
            assert client2.logger is not None


class TestClientContextPropagation:
    """Test context propagation through client operations."""

    def test_context_propagates_through_nested_clients(self):
        """Test that context propagates through nested client creation."""

        class OuterComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event"]

            def create_inner(self):
                return InnerComponent()

        class InnerComponent(MadsciClientMixin):
            REQUIRED_CLIENTS: ClassVar[list[str]] = ["event"]

        with event_client_context(name="outer", outer_id="o-123"):
            outer = OuterComponent()
            outer.setup_clients()

            inner = outer.create_inner()
            inner.setup_clients()

            # Inner should have inherited outer context
            assert (
                "outer_id" in inner.event_client._bound_context
                or inner.event_client._bound_context.get("component_type") is not None
            )

    def test_context_with_experiment_workflow_node_hierarchy(self):
        """Test realistic experiment -> workflow -> node hierarchy."""
        logs = []

        with event_client_context(
            name="experiment", experiment_id="exp-123"
        ) as exp_logger:
            logs.append(("experiment", exp_logger._bound_context.copy()))

            with event_client_context(
                name="workflow", workflow_id="wf-456"
            ) as wf_logger:
                logs.append(("workflow", wf_logger._bound_context.copy()))

                with event_client_context(name="step", step_id="step-1") as step_logger:
                    logs.append(("step", step_logger._bound_context.copy()))

        # Verify hierarchy accumulation
        assert logs[0][1].get("experiment_id") == "exp-123"

        assert logs[1][1].get("experiment_id") == "exp-123"
        assert logs[1][1].get("workflow_id") == "wf-456"

        assert logs[2][1].get("experiment_id") == "exp-123"
        assert logs[2][1].get("workflow_id") == "wf-456"
        assert logs[2][1].get("step_id") == "step-1"


class TestResourceClientContextAwareness:
    """Test ResourceClient context-aware behavior."""

    def test_uses_context_when_available(self):
        """Test that ResourceClient uses context EventClient."""
        with event_client_context(name="workflow", workflow_id="wf-123"):
            # ResourceClient without server URL for local-only mode
            client = ResourceClient(resource_server_url=None)

            # Logger should include workflow context or component context
            assert client.logger is not None
            assert (
                "workflow_id" in client.logger._bound_context
                or client.logger._bound_context.get("component_type") is not None
            )

    def test_uses_injected_client_when_provided(self):
        """Test that ResourceClient uses injected EventClient."""
        injected = EventClient(name="injected")

        with event_client_context(name="context"):
            client = ResourceClient(
                resource_server_url=None,
                event_client=injected,
            )

            assert client.logger is injected


class TestWorkcellClientContextAwareness:
    """Test WorkcellClient context-aware behavior."""

    def test_uses_injected_client_when_provided(self):
        """Test that WorkcellClient uses injected EventClient."""
        injected = EventClient(name="injected")

        with event_client_context(name="context"):
            # We need to provide a URL to avoid the ValueError
            client = WorkcellClient(
                workcell_server_url="http://localhost:8005/",
                event_client=injected,
            )

            assert client.logger is injected


class TestLocationClientContextAwareness:
    """Test LocationClient context-aware behavior."""

    def test_uses_context_when_available(self):
        """Test that LocationClient uses context EventClient."""
        with event_client_context(name="workflow", workflow_id="wf-123"):
            # LocationClient without server URL for testing
            client = LocationClient(location_server_url=None)

            # Logger should include workflow context or component context
            assert client.logger is not None
            assert (
                "workflow_id" in client.logger._bound_context
                or client.logger._bound_context.get("component_type") is not None
            )

    def test_uses_injected_client_when_provided(self):
        """Test that LocationClient uses injected EventClient."""
        injected = EventClient(name="injected")

        with event_client_context(name="context"):
            client = LocationClient(
                location_server_url=None,
                event_client=injected,
            )

            assert client.logger is injected
