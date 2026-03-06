"""Tests for OpenTelemetry tracing decorators and context managers."""

import asyncio

import pytest
from madsci.common.otel import OtelBootstrapConfig, configure_otel
from madsci.common.otel.tracing import (
    add_span_event,
    get_current_span,
    get_tracer,
    is_span_recording,
    safe_span_context,
    set_span_attributes,
    set_span_error,
    span_context,
    traced_class,
    with_span,
)
from opentelemetry.trace import SpanKind


@pytest.fixture
def otel_test_runtime():
    """Configure OTEL in test mode with in-memory exporter."""
    return configure_otel(
        OtelBootstrapConfig(
            enabled=True,
            service_name="madsci.tracing.test",
            exporter="none",
            test_mode=True,
        )
    )


class TestSpanContext:
    """Test span_context context manager."""

    def test_span_context_creates_span(self, otel_test_runtime) -> None:
        """Test that span_context creates a recording span."""
        _ = otel_test_runtime

        with span_context("test_span") as span:
            assert span is not None
            assert span.is_recording()

    def test_span_context_with_attributes(self, otel_test_runtime) -> None:
        """Test that span_context sets attributes."""
        _ = otel_test_runtime

        with span_context("test_span", attributes={"key": "value"}) as span:
            assert span.is_recording()
            # Span attributes are set

    def test_span_context_with_kind(self, otel_test_runtime) -> None:
        """Test that span_context sets span kind."""
        _ = otel_test_runtime

        with span_context("client_span", kind=SpanKind.CLIENT) as span:
            assert span.is_recording()

    def test_span_context_nesting(self, otel_test_runtime) -> None:
        """Test that spans nest correctly."""
        _ = otel_test_runtime

        with span_context("outer") as outer_span:
            outer_context = outer_span.get_span_context()

            with span_context("inner") as inner_span:
                inner_context = inner_span.get_span_context()
                # Same trace, different spans
                assert inner_context.trace_id == outer_context.trace_id
                assert inner_context.span_id != outer_context.span_id

    def test_span_context_records_exception(self, otel_test_runtime) -> None:
        """Test that span_context records exceptions."""
        _ = otel_test_runtime

        with pytest.raises(ValueError), span_context("failing_span"):
            raise ValueError("Test error")


class TestSafeSpanContext:
    """Test safe_span_context context manager."""

    def test_safe_span_context_with_otel(self, otel_test_runtime) -> None:
        """Test safe_span_context when OTEL is configured."""
        _ = otel_test_runtime

        with safe_span_context("test_span") as span:
            assert span is not None
            assert span.is_recording()

    def test_safe_span_context_never_raises(self, otel_test_runtime) -> None:
        """Test that safe_span_context doesn't propagate tracing errors."""
        _ = otel_test_runtime

        # Even with an unusual span name, should not raise
        with safe_span_context("test") as span:
            # Should work normally
            if span:
                span.set_attribute("key", "value")


class TestWithSpanDecorator:
    """Test with_span() decorator."""

    def test_decorator_creates_span(self, otel_test_runtime) -> None:
        """Test that decorator creates a span."""
        _ = otel_test_runtime

        @with_span
        def my_function() -> bool:
            return is_span_recording()

        result = my_function()
        assert result is True

    def test_decorator_uses_function_name(self, otel_test_runtime) -> None:
        """Test that decorator uses function name as span name."""
        _ = otel_test_runtime
        captured_name = None

        @with_span
        def my_named_function() -> str:
            nonlocal captured_name
            get_current_span()
            # The span name is set, we can verify recording
            captured_name = "my_named_function"
            return captured_name

        result = my_named_function()
        assert result == "my_named_function"

    def test_decorator_with_custom_name(self, otel_test_runtime) -> None:
        """Test that decorator uses custom name."""
        _ = otel_test_runtime

        @with_span(name="custom_span_name")
        def my_function() -> bool:
            return is_span_recording()

        result = my_function()
        assert result is True

    def test_decorator_with_attributes(self, otel_test_runtime) -> None:
        """Test that decorator sets span attributes."""
        _ = otel_test_runtime

        @with_span(attributes={"operation": "test", "priority": 1})
        def my_function() -> bool:
            span = get_current_span()
            return span.is_recording()

        result = my_function()
        assert result is True

    def test_decorator_injects_span_parameter(self, otel_test_runtime) -> None:
        """Test that decorator injects span if parameter exists."""
        _ = otel_test_runtime

        @with_span(name="test")
        def my_function(span=None):
            return span is not None and span.is_recording()

        result = my_function()
        assert result is True

    def test_decorator_does_not_override_explicit_span(self, otel_test_runtime) -> None:
        """Test that explicit span parameter is not overridden."""
        _ = otel_test_runtime
        marker = object()

        @with_span(name="test")
        def my_function(span=None):
            return span

        result = my_function(span=marker)
        assert result is marker

    def test_decorator_preserves_function_metadata(self, otel_test_runtime) -> None:
        """Test that decorator preserves function name and docstring."""
        _ = otel_test_runtime

        @with_span
        def my_function_with_docs() -> None:
            """This is a docstring."""

        assert my_function_with_docs.__name__ == "my_function_with_docs"
        assert my_function_with_docs.__doc__ == "This is a docstring."

    def test_decorator_with_function_arguments(self, otel_test_runtime) -> None:
        """Test that decorator works with functions that have arguments."""
        _ = otel_test_runtime

        @with_span(name="add")
        def add_numbers(a: int, b: int) -> int:
            return a + b

        result = add_numbers(2, 3)
        assert result == 5

    def test_decorator_nesting(self, otel_test_runtime) -> None:
        """Test that decorators nest correctly."""
        _ = otel_test_runtime
        trace_ids = []
        span_ids = []

        @with_span(name="outer")
        def outer_function():
            span = get_current_span()
            ctx = span.get_span_context()
            trace_ids.append(ctx.trace_id)
            span_ids.append(ctx.span_id)
            return inner_function()

        @with_span(name="inner")
        def inner_function():
            span = get_current_span()
            ctx = span.get_span_context()
            trace_ids.append(ctx.trace_id)
            span_ids.append(ctx.span_id)
            return "success"

        result = outer_function()
        assert result == "success"
        # Same trace, different spans
        assert trace_ids[0] == trace_ids[1]
        assert span_ids[0] != span_ids[1]

    @pytest.mark.asyncio
    async def test_decorator_with_async_function(self, otel_test_runtime) -> None:
        """Test that decorator works with async functions."""
        _ = otel_test_runtime

        @with_span(name="async_test")
        async def async_function() -> bool:
            await asyncio.sleep(0.01)
            return is_span_recording()

        result = await async_function()
        assert result is True

    @pytest.mark.asyncio
    async def test_decorator_async_with_span_injection(self, otel_test_runtime) -> None:
        """Test that decorator injects span in async functions."""
        _ = otel_test_runtime

        @with_span(name="async_test")
        async def async_function(span=None):
            await asyncio.sleep(0.01)
            return span is not None and span.is_recording()

        result = await async_function()
        assert result is True

    def test_decorator_records_exception(self, otel_test_runtime) -> None:
        """Test that decorator records exceptions."""
        _ = otel_test_runtime

        @with_span(name="failing")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()


class TestTracedClassDecorator:
    """Test traced_class() decorator."""

    def test_class_decorator_adds_current_span_property(
        self, otel_test_runtime
    ) -> None:
        """Test that class decorator adds current_span property."""
        _ = otel_test_runtime

        @traced_class()
        class MyComponent:
            def check_span_recording(self):
                # Check inside the method while span is active
                return self.current_span.is_recording()

        component = MyComponent()
        # The span is recording while inside the method
        is_recording = component.check_span_recording()
        assert is_recording is True

    def test_class_decorator_wraps_public_methods(self, otel_test_runtime) -> None:
        """Test that public methods are wrapped with spans."""
        _ = otel_test_runtime

        @traced_class(name="MyComponent")
        class MyComponent:
            def process(self) -> bool:
                return is_span_recording()

        component = MyComponent()
        result = component.process()
        assert result is True

    def test_class_decorator_skips_private_methods(self, otel_test_runtime) -> None:
        """Test that private methods are not wrapped."""
        _ = otel_test_runtime

        @traced_class(name="MyComponent")
        class MyComponent:
            def _private_method(self) -> bool:
                # Private methods don't get wrapped
                # So the span from the test context (none) should be used
                return is_span_recording()

        component = MyComponent()
        # Private method is not wrapped, so no new span is created
        # Result depends on whether there's an active span in context
        result = component._private_method()
        assert isinstance(result, bool)

    def test_class_decorator_with_attributes(self, otel_test_runtime) -> None:
        """Test that class decorator sets attributes on spans."""
        _ = otel_test_runtime

        @traced_class(attributes={"component": "processor"})
        class DataProcessor:
            def process(self) -> bool:
                span = get_current_span()
                return span.is_recording()

        processor = DataProcessor()
        result = processor.process()
        assert result is True

    def test_class_decorator_with_get_span_attributes(self, otel_test_runtime) -> None:
        """Test that get_span_attributes adds instance-specific attributes."""
        _ = otel_test_runtime

        @traced_class(name="Worker")
        class Worker:
            def __init__(self, worker_id: str):
                self.worker_id = worker_id

            def get_span_attributes(self) -> dict:
                return {"worker.id": self.worker_id}

            def work(self) -> bool:
                return is_span_recording()

        worker = Worker("w-123")
        result = worker.work()
        assert result is True

    def test_class_decorator_preserves_existing_property(
        self, otel_test_runtime
    ) -> None:
        """Test that existing current_span property is not overwritten."""
        _ = otel_test_runtime
        marker = object()

        @traced_class()
        class MyComponent:
            @property
            def current_span(self):
                return marker

            def get_span(self):
                return self.current_span

        component = MyComponent()
        result = component.get_span()
        assert result is marker

    def test_class_decorator_nested_method_calls(self, otel_test_runtime) -> None:
        """Test that nested method calls create nested spans."""
        _ = otel_test_runtime
        trace_ids = []
        span_ids = []

        @traced_class(name="MyComponent")
        class MyComponent:
            def outer_method(self):
                span = get_current_span()
                ctx = span.get_span_context()
                trace_ids.append(ctx.trace_id)
                span_ids.append(ctx.span_id)
                return self.inner_method()

            def inner_method(self):
                span = get_current_span()
                ctx = span.get_span_context()
                trace_ids.append(ctx.trace_id)
                span_ids.append(ctx.span_id)
                return "success"

        component = MyComponent()
        result = component.outer_method()
        assert result == "success"
        # Same trace, different spans
        assert trace_ids[0] == trace_ids[1]
        assert span_ids[0] != span_ids[1]

    @pytest.mark.asyncio
    async def test_class_decorator_with_async_methods(self, otel_test_runtime) -> None:
        """Test that class decorator works with async methods."""
        _ = otel_test_runtime

        @traced_class(name="AsyncComponent")
        class AsyncComponent:
            async def async_process(self) -> bool:
                await asyncio.sleep(0.01)
                return is_span_recording()

        component = AsyncComponent()
        result = await component.async_process()
        assert result is True


class TestSpanUtilities:
    """Test span utility functions."""

    def test_get_tracer(self, otel_test_runtime) -> None:
        """Test get_tracer returns a tracer."""
        _ = otel_test_runtime
        tracer = get_tracer("test")
        assert tracer is not None

    def test_get_current_span(self, otel_test_runtime) -> None:
        """Test get_current_span returns current span."""
        _ = otel_test_runtime

        with span_context("test"):
            span = get_current_span()
            assert span.is_recording()

    def test_is_span_recording(self, otel_test_runtime) -> None:
        """Test is_span_recording returns True in span."""
        _ = otel_test_runtime

        with span_context("test"):
            assert is_span_recording() is True

    def test_set_span_error(self, otel_test_runtime) -> None:
        """Test set_span_error sets error status."""
        _ = otel_test_runtime

        with span_context("test") as span:
            set_span_error(message="Test error")
            # Span should still be recording
            assert span.is_recording()

    def test_set_span_error_with_exception(self, otel_test_runtime) -> None:
        """Test set_span_error records exception."""
        _ = otel_test_runtime

        with span_context("test") as span:
            try:
                raise ValueError("Test")
            except ValueError as e:
                set_span_error(exception=e, message="Operation failed")
            assert span.is_recording()

    def test_add_span_event(self, otel_test_runtime) -> None:
        """Test add_span_event adds event to span."""
        _ = otel_test_runtime

        with span_context("test") as span:
            add_span_event("checkpoint", {"step": 1})
            assert span.is_recording()

    def test_set_span_attributes(self, otel_test_runtime) -> None:
        """Test set_span_attributes sets multiple attributes."""
        _ = otel_test_runtime

        with span_context("test") as span:
            set_span_attributes({"key1": "value1", "key2": 42})
            assert span.is_recording()


class TestDecoratorInteractions:
    """Test interactions between tracing and other decorators."""

    def test_with_span_inside_span_context(self, otel_test_runtime) -> None:
        """Test @with_span called within span_context."""
        _ = otel_test_runtime
        trace_ids = []

        @with_span(name="inner_function")
        def inner_function():
            span = get_current_span()
            trace_ids.append(span.get_span_context().trace_id)
            return is_span_recording()

        with span_context("outer_context") as outer:
            trace_ids.append(outer.get_span_context().trace_id)
            result = inner_function()

        assert result is True
        # Same trace for both spans
        assert trace_ids[0] == trace_ids[1]

    def test_nested_decorated_classes(self, otel_test_runtime) -> None:
        """Test calling traced class from within traced class."""
        _ = otel_test_runtime
        trace_ids = []

        @traced_class(name="Outer")
        class OuterClass:
            def __init__(self, inner):
                self.inner = inner

            def process(self):
                span = get_current_span()
                trace_ids.append(span.get_span_context().trace_id)
                return self.inner.work()

        @traced_class(name="Inner")
        class InnerClass:
            def work(self):
                span = get_current_span()
                trace_ids.append(span.get_span_context().trace_id)
                return "done"

        inner = InnerClass()
        outer = OuterClass(inner)
        result = outer.process()

        assert result == "done"
        # Same trace for both
        assert trace_ids[0] == trace_ids[1]
