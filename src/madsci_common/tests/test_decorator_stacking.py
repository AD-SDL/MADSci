"""Tests for decorator stacking and OTEL optional behavior."""

import asyncio

import pytest
from madsci.common.context import (
    _event_client_context,
    event_client_class,
    get_current_madsci_context,
    has_event_client_context,
    madsci_context_class,
    with_event_client,
)
from madsci.common.otel import OtelBootstrapConfig, configure_otel
from madsci.common.otel.tracing import (
    is_span_recording,
    traced_class,
    with_span,
)
from madsci.common.ownership import (
    get_current_ownership_info,
    ownership_class,
    with_ownership,
)
from madsci.common.utils import new_ulid_str


class TestOtelOptionalBehavior:
    """Test that OTEL decorators work safely when OTEL is not configured."""

    def test_with_span_works_without_otel_config(self) -> None:
        """Test @with_span works when OTEL is not configured."""
        # Don't configure OTEL - use default no-op behavior

        @with_span(name="test_function")
        def my_function(x: int) -> int:
            return x * 2

        # Should work without raising
        result = my_function(5)
        assert result == 10

    def test_traced_class_works_without_otel_config(self) -> None:
        """Test @traced_class works when OTEL is not configured."""

        @traced_class(name="TestComponent")
        class TestComponent:
            def process(self, data: str) -> str:
                return data.upper()

        component = TestComponent()
        result = component.process("hello")
        assert result == "HELLO"

    def test_span_operations_safe_when_not_recording(self) -> None:
        """Test that span operations don't raise when span is not recording."""

        @with_span(name="test")
        def function_with_span_ops(span=None):
            # All these should work even with non-recording span
            if span:
                span.set_attribute("key", "value")
                span.add_event("test_event", {"attr": 123})
            return "success"

        result = function_with_span_ops()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_with_span_works_without_otel(self) -> None:
        """Test async @with_span works when OTEL is not configured."""

        @with_span(name="async_test")
        async def async_function() -> str:
            await asyncio.sleep(0.01)
            return "async_result"

        result = await async_function()
        assert result == "async_result"


class TestDecoratorStacking:
    """Test that multiple decorators can be stacked on the same class/function."""

    def test_function_with_all_decorators(self) -> None:
        """Test stacking @with_span, @with_ownership, @with_event_client on a function."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @with_span(name="traced_function")
        @with_ownership(experiment_id=exp_id)
        @with_event_client(name="test_func")
        def multi_decorated_function() -> dict:
            return {
                "has_event_context": has_event_client_context(),
                "experiment_id": get_current_ownership_info().experiment_id,
                "span_recording": is_span_recording(),
            }

        result = multi_decorated_function()
        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id
        # Span may or may not be recording depending on OTEL config
        assert isinstance(result["span_recording"], bool)

    def test_function_decorators_order_independence(self) -> None:
        """Test that decorator order doesn't break functionality."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        # Different order than above
        @with_event_client(name="test_func")
        @with_span(name="traced_function")
        @with_ownership(experiment_id=exp_id)
        def different_order_function() -> dict:
            return {
                "has_event_context": has_event_client_context(),
                "experiment_id": get_current_ownership_info().experiment_id,
            }

        result = different_order_function()
        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id

    def test_class_with_all_decorators(self) -> None:
        """Test stacking @traced_class, @ownership_class, @event_client_class on a class."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @traced_class(name="MultiDecoratedClass")
        @ownership_class(experiment_id=exp_id)
        @event_client_class(name="test_component")
        class MultiDecoratedClass:
            def process(self) -> dict:
                return {
                    "has_event_context": has_event_client_context(),
                    "experiment_id": get_current_ownership_info().experiment_id,
                    "has_current_span": self.current_span is not None,
                    "has_event_client": hasattr(self, "event_client"),
                    "has_ownership_info": hasattr(self, "ownership_info"),
                }

        component = MultiDecoratedClass()
        result = component.process()

        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id
        assert result["has_current_span"] is True
        assert result["has_event_client"] is True
        assert result["has_ownership_info"] is True

    def test_class_decorators_order_independence(self) -> None:
        """Test that class decorator order doesn't break functionality."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        # Different order
        @event_client_class(name="test_component")
        @traced_class(name="DifferentOrderClass")
        @ownership_class(experiment_id=exp_id)
        class DifferentOrderClass:
            def process(self) -> dict:
                return {
                    "has_event_context": has_event_client_context(),
                    "experiment_id": get_current_ownership_info().experiment_id,
                }

        component = DifferentOrderClass()
        result = component.process()

        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id

    def test_class_with_madsci_context_decorator(self) -> None:
        """Test @madsci_context_class stacked with other decorators."""
        _event_client_context.set(None)

        @traced_class(name="ContextAwareClass")
        @madsci_context_class(event_server_url="http://test:8001")
        @event_client_class(name="context_component")
        class ContextAwareClass:
            def get_info(self) -> dict:
                ctx = get_current_madsci_context()
                return {
                    "event_server_url": str(ctx.event_server_url)
                    if ctx.event_server_url
                    else None,
                    "has_event_context": has_event_client_context(),
                }

        component = ContextAwareClass()
        result = component.get_info()

        assert result["event_server_url"] == "http://test:8001/"
        assert result["has_event_context"] is True

    def test_nested_calls_with_stacked_decorators(self) -> None:
        """Test nested function calls with stacked decorators."""
        _event_client_context.set(None)
        outer_exp = new_ulid_str()
        inner_exp = new_ulid_str()

        @with_span(name="outer")
        @with_ownership(experiment_id=outer_exp)
        @with_event_client(name="outer_func")
        def outer_function() -> dict:
            outer_result = {
                "experiment_id": get_current_ownership_info().experiment_id,
            }
            inner_result = inner_function()
            return {"outer": outer_result, "inner": inner_result}

        @with_span(name="inner")
        @with_ownership(workflow_id=inner_exp)  # Different field to test inheritance
        @with_event_client(name="inner_func")
        def inner_function() -> dict:
            info = get_current_ownership_info()
            return {
                "experiment_id": info.experiment_id,  # Should inherit from outer
                "workflow_id": info.workflow_id,  # Should be set by inner
            }

        result = outer_function()

        assert result["outer"]["experiment_id"] == outer_exp
        assert result["inner"]["experiment_id"] == outer_exp  # Inherited
        assert result["inner"]["workflow_id"] == inner_exp  # Set by inner

    @pytest.mark.asyncio
    async def test_async_function_with_stacked_decorators(self) -> None:
        """Test async function with stacked decorators."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @with_span(name="async_traced")
        @with_ownership(experiment_id=exp_id)
        @with_event_client(name="async_func")
        async def async_multi_decorated() -> dict:
            await asyncio.sleep(0.01)
            return {
                "has_event_context": has_event_client_context(),
                "experiment_id": get_current_ownership_info().experiment_id,
            }

        result = await async_multi_decorated()
        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id

    @pytest.mark.asyncio
    async def test_async_class_with_stacked_decorators(self) -> None:
        """Test async methods in class with stacked decorators."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @traced_class(name="AsyncMultiClass")
        @ownership_class(experiment_id=exp_id)
        @event_client_class(name="async_component")
        class AsyncMultiClass:
            async def async_process(self) -> dict:
                await asyncio.sleep(0.01)
                return {
                    "has_event_context": has_event_client_context(),
                    "experiment_id": get_current_ownership_info().experiment_id,
                }

        component = AsyncMultiClass()
        result = await component.async_process()

        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id


class TestDecoratorStackingWithOtel:
    """Test decorator stacking with OTEL properly configured."""

    @pytest.fixture
    def otel_test_runtime(self):
        """Configure OTEL in test mode."""
        return configure_otel(
            OtelBootstrapConfig(
                enabled=True,
                service_name="madsci.stacking.test",
                exporter="none",
                test_mode=True,
            )
        )

    def test_stacked_decorators_with_otel_enabled(self, otel_test_runtime) -> None:
        """Test stacked decorators when OTEL is properly configured."""
        _ = otel_test_runtime
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @with_span(name="otel_traced")
        @with_ownership(experiment_id=exp_id)
        @with_event_client(name="otel_func")
        def otel_enabled_function() -> dict:
            return {
                "has_event_context": has_event_client_context(),
                "experiment_id": get_current_ownership_info().experiment_id,
                "span_recording": is_span_recording(),
            }

        result = otel_enabled_function()
        assert result["has_event_context"] is True
        assert result["experiment_id"] == exp_id
        assert result["span_recording"] is True  # Should be recording with OTEL enabled

    def test_traced_class_with_other_decorators_otel_enabled(
        self, otel_test_runtime
    ) -> None:
        """Test @traced_class with other decorators when OTEL is enabled."""
        _ = otel_test_runtime
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @traced_class(name="OtelEnabledClass")
        @ownership_class(experiment_id=exp_id)
        @event_client_class(name="otel_component")
        class OtelEnabledClass:
            def process(self) -> dict:
                return {
                    "span_recording": self.current_span.is_recording(),
                    "experiment_id": get_current_ownership_info().experiment_id,
                    "has_event_context": has_event_client_context(),
                }

        component = OtelEnabledClass()
        result = component.process()

        assert result["span_recording"] is True
        assert result["experiment_id"] == exp_id
        assert result["has_event_context"] is True


class TestDecoratorStackingEdgeCases:
    """Test edge cases in decorator stacking."""

    def test_class_with_custom_properties_preserved(self) -> None:
        """Test that custom properties are preserved when stacking decorators."""
        _event_client_context.set(None)

        @traced_class(name="CustomPropsClass")
        @ownership_class()
        @event_client_class(name="custom_component")
        class CustomPropsClass:
            def __init__(self, name: str):
                self._name = name

            @property
            def name(self) -> str:
                return self._name

            def get_name(self) -> str:
                return self.name

        component = CustomPropsClass("test_name")
        assert component.name == "test_name"
        assert component.get_name() == "test_name"

    def test_class_with_init_args_preserved(self) -> None:
        """Test that __init__ args work correctly with stacked decorators."""
        _event_client_context.set(None)
        exp_id = new_ulid_str()

        @traced_class(name="InitArgsClass")
        @ownership_class(experiment_id=exp_id)
        @event_client_class(name="init_component")
        class InitArgsClass:
            def __init__(self, value: int, name: str = "default"):
                self.value = value
                self.name = name

            def get_values(self) -> dict:
                return {
                    "value": self.value,
                    "name": self.name,
                    "experiment_id": get_current_ownership_info().experiment_id,
                }

        component = InitArgsClass(42, name="custom")
        assert component.value == 42
        assert component.name == "custom"

        result = component.get_values()
        assert result["value"] == 42
        assert result["name"] == "custom"
        assert result["experiment_id"] == exp_id

    def test_private_methods_not_wrapped_with_stacked_decorators(self) -> None:
        """Test that private methods are not wrapped by any decorator."""
        _event_client_context.set(None)

        @traced_class(name="PrivateMethodsClass")
        @ownership_class()
        @event_client_class(name="private_component")
        class PrivateMethodsClass:
            def public_method(self) -> bool:
                return has_event_client_context()

            def _private_method(self) -> bool:
                return has_event_client_context()

        component = PrivateMethodsClass()

        # Public method should have context
        assert component.public_method() is True

        # Private method should NOT have context (not wrapped)
        assert component._private_method() is False

    def test_get_methods_not_wrapped_to_avoid_recursion(self) -> None:
        """Test that get_* override methods are not wrapped to avoid recursion."""
        _event_client_context.set(None)
        test_node_id = new_ulid_str()

        @traced_class(name="GetMethodsClass")
        @ownership_class()
        @event_client_class(name="get_component")
        class GetMethodsClass:
            def __init__(self, worker_id: str):
                self.worker_id = worker_id
                self._node_id = test_node_id

            def get_event_context(self) -> dict:
                return {"worker_id": self.worker_id}

            def get_ownership_overrides(self) -> dict:
                return {"node_id": self._node_id}

            def get_span_attributes(self) -> dict:
                return {"worker.id": self.worker_id}

            def work(self) -> dict:
                info = get_current_ownership_info()
                return {
                    "node_id": info.node_id,
                    "has_context": has_event_client_context(),
                }

        # Should not raise RecursionError
        component = GetMethodsClass("w-123")
        result = component.work()

        assert result["node_id"] == test_node_id
        assert result["has_context"] is True
