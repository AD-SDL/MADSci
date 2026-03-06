"""Tests for EventClient context propagation."""

import asyncio
from typing import Any
from unittest.mock import Mock

import pytest
from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.event_client import EventClient
from madsci.common.context import (
    _event_client_context,
    event_client_class,
    event_client_context,
    get_event_client,
    get_event_client_context,
    has_event_client_context,
    with_event_client,
)
from madsci.common.types.event_types import EventClientContext


class TestEventClientContext:
    """Test EventClientContext dataclass."""

    def test_context_stores_client(self):
        """Test that EventClientContext stores an EventClient."""
        client = EventClient(name="test", event_server_url=None)
        ctx = EventClientContext(client=client)

        assert ctx.client is client
        assert ctx.hierarchy == []
        assert ctx.metadata == {}

    def test_context_name_from_hierarchy(self):
        """Test that context name is built from hierarchy."""
        client = Mock()
        ctx = EventClientContext(
            client=client,
            hierarchy=["experiment", "workflow", "step"],
        )

        assert ctx.name == "experiment.workflow.step"

    def test_context_name_empty_hierarchy(self):
        """Test that empty hierarchy returns default name."""
        client = Mock()
        ctx = EventClientContext(client=client)

        assert ctx.name == "madsci"

    def test_child_context_extends_hierarchy(self):
        """Test that child() extends the hierarchy."""
        parent_client = Mock()
        parent_client.bind.return_value = Mock()

        parent_ctx = EventClientContext(
            client=parent_client,
            hierarchy=["experiment"],
            metadata={"experiment_id": "exp-123"},
        )

        child_ctx = parent_ctx.child("workflow", workflow_id="wf-456")

        assert child_ctx.hierarchy == ["experiment", "workflow"]
        assert child_ctx.metadata == {
            "experiment_id": "exp-123",
            "workflow_id": "wf-456",
        }
        parent_client.bind.assert_called_once_with(workflow_id="wf-456")

    def test_child_context_with_explicit_client(self):
        """Test that child() can use an explicit client."""
        parent_client = Mock()
        child_client = Mock()

        parent_ctx = EventClientContext(client=parent_client, hierarchy=["parent"])
        child_ctx = parent_ctx.child("child", client=child_client)

        assert child_ctx.client is child_client
        assert child_ctx.hierarchy == ["parent", "child"]


class TestGetEventClient:
    """Test get_event_client() function."""

    def test_get_event_client_no_context_creates_new(self):
        """Test that get_event_client creates a new client when no context exists."""
        # Ensure no context
        _event_client_context.set(None)

        client = get_event_client()

        assert client is not None
        # Should have a name derived from caller
        assert client.name is not None

    def test_get_event_client_with_context_returns_context_client(self):
        """Test that get_event_client returns context client when available."""
        with event_client_context(name="test") as ctx_client:
            client = get_event_client()
            # Should be the same client (or bound version)
            assert client is ctx_client

    def test_get_event_client_with_additional_context_binds(self):
        """Test that get_event_client with kwargs binds additional context."""
        with event_client_context(name="test") as ctx_client:
            client = get_event_client(step_id="step-1")
            # Should be a bound version, not the original
            assert client is not ctx_client
            assert "step_id" in client._bound_context

    def test_get_event_client_with_name_uses_name(self):
        """Test that explicit name is used."""
        _event_client_context.set(None)

        client = get_event_client(name="custom_name")

        assert client.name == "custom_name"

    def test_get_event_client_always_works(self):
        """Test that get_event_client never raises due to missing context."""
        # Clear any existing context
        _event_client_context.set(None)

        # Should not raise
        client = get_event_client()
        assert client is not None

        # Should be able to log
        client.info("Test message")  # Should not raise


class TestEventClientContextManager:
    """Test event_client_context() context manager."""

    def test_context_manager_establishes_context(self):
        """Test that context manager establishes context."""
        assert not has_event_client_context()

        with event_client_context(name="test"):
            assert has_event_client_context()

        assert not has_event_client_context()

    def test_context_manager_yields_client(self):
        """Test that context manager yields the EventClient."""
        with event_client_context(name="test") as client:
            assert isinstance(client, EventClient)

    def test_nested_context_inherits_parent(self):
        """Test that nested context inherits parent context."""
        with event_client_context(name="parent", parent_id="p-123"):
            parent_ctx = get_event_client_context()
            assert parent_ctx is not None
            assert parent_ctx.hierarchy == ["parent"]
            assert parent_ctx.metadata == {"parent_id": "p-123"}

            with event_client_context(name="child", child_id="c-456"):
                child_ctx = get_event_client_context()
                assert child_ctx is not None
                assert child_ctx.hierarchy == ["parent", "child"]
                assert child_ctx.metadata == {"parent_id": "p-123", "child_id": "c-456"}

            # After child exits, should be back to parent
            restored_ctx = get_event_client_context()
            assert restored_ctx is not None
            assert restored_ctx.hierarchy == ["parent"]

    def test_context_with_explicit_client(self):
        """Test that explicit client is used when provided."""
        explicit_client = EventClient(name="explicit", event_server_url=None)

        with event_client_context(client=explicit_client) as client:
            assert client is explicit_client

    def test_context_inherit_false_creates_fresh(self):
        """Test that inherit=False creates fresh context."""
        with event_client_context(name="parent", parent_id="p-123"):  # noqa: SIM117
            # Nested context with inherit=False - intentionally nested to test isolation
            with event_client_context(
                name="isolated", inherit=False, isolated_id="i-789"
            ):
                ctx = get_event_client_context()
                # Should NOT have parent's metadata
                assert "parent_id" not in ctx.metadata
                assert ctx.metadata == {"isolated_id": "i-789"}
                assert ctx.hierarchy == ["isolated"]

    def test_context_binds_metadata_to_logs(self):
        """Test that context metadata is included in log messages."""
        with event_client_context(name="test", experiment_id="exp-123") as client:
            # The bound context should include experiment_id
            assert "experiment_id" in client._bound_context
            assert client._bound_context["experiment_id"] == "exp-123"


class TestHasEventClientContext:
    """Test has_event_client_context() function."""

    def test_returns_false_when_no_context(self):
        """Test returns False when no context exists."""
        _event_client_context.set(None)

        assert has_event_client_context() is False

    def test_returns_true_when_context_exists(self):
        """Test returns True when context exists."""
        with event_client_context(name="test"):
            assert has_event_client_context() is True


class TestContextAsyncPropagation:
    """Test that context propagates correctly in async code."""

    @pytest.mark.asyncio
    async def test_context_propagates_across_await(self):
        """Test that context propagates across await boundaries."""

        async def inner_async():
            await asyncio.sleep(0.01)
            assert has_event_client_context()
            client = get_event_client()
            assert "async_id" in client._bound_context
            return client._bound_context["async_id"]

        with event_client_context(name="async_test", async_id="a-123"):
            result = await inner_async()
            assert result == "a-123"

    @pytest.mark.asyncio
    async def test_concurrent_contexts_isolated(self):
        """Test that concurrent async operations have isolated contexts."""

        async def task_with_context(task_id: str):
            with event_client_context(name=f"task_{task_id}", task_id=task_id):
                await asyncio.sleep(0.01)  # Yield to allow interleaving
                client = get_event_client()
                return client._bound_context.get("task_id")

        # Run multiple tasks concurrently
        results = await asyncio.gather(
            task_with_context("1"),
            task_with_context("2"),
            task_with_context("3"),
        )

        # Each task should have seen its own context
        assert results == ["1", "2", "3"]


class TestContextStackInspection:
    """Test stack inspection fallback for naming."""

    def test_infers_name_from_caller_module(self):
        """Test that name is inferred from calling module when no context."""
        _event_client_context.set(None)

        client = get_event_client()

        # Should have inferred name from this test module
        # (exact name depends on test runner, but should not be empty)
        assert client.name is not None
        assert len(client.name) > 0


class TestCreateIfMissing:
    """Test the create_if_missing parameter."""

    def test_create_if_missing_false_raises_when_no_context(self):
        """Test that create_if_missing=False raises RuntimeError when no context."""
        _event_client_context.set(None)

        with pytest.raises(RuntimeError, match="No EventClient context available"):
            get_event_client(create_if_missing=False)

    def test_create_if_missing_false_works_with_context(self):
        """Test that create_if_missing=False works when context exists."""
        with event_client_context(name="test"):
            # Should not raise
            client = get_event_client(create_if_missing=False)
            assert client is not None


class TestWithEventClientDecorator:
    """Test with_event_client() decorator."""

    def test_decorator_establishes_context(self):
        """Test that decorator establishes context within the function."""
        _event_client_context.set(None)

        @with_event_client
        def my_function():
            assert has_event_client_context()
            return get_event_client()

        # Before calling, no context
        assert not has_event_client_context()

        client = my_function()
        assert client is not None

        # After calling, context is cleaned up
        assert not has_event_client_context()

    def test_decorator_with_name(self):
        """Test that decorator uses custom name."""
        _event_client_context.set(None)

        @with_event_client(name="custom_name")
        def my_function():
            ctx = get_event_client_context()
            return ctx.hierarchy if ctx else []

        hierarchy = my_function()
        assert hierarchy == ["custom_name"]

    def test_decorator_with_metadata(self):
        """Test that decorator binds metadata to context."""
        _event_client_context.set(None)

        @with_event_client(name="test", experiment_id="exp-123")
        def my_function():
            client = get_event_client()
            return client._bound_context.get("experiment_id")

        result = my_function()
        assert result == "exp-123"

    def test_decorator_injects_event_client_parameter(self):
        """Test that decorator injects event_client if parameter exists."""
        _event_client_context.set(None)

        @with_event_client(name="test")
        def my_function(event_client: EventClient = None):
            return event_client

        client = my_function()
        assert client is not None
        assert isinstance(client, EventClient)

    def test_decorator_does_not_override_explicit_event_client(self):
        """Test that explicit event_client parameter is not overridden."""
        _event_client_context.set(None)
        explicit_client = EventClient(name="explicit", event_server_url=None)

        @with_event_client(name="test")
        def my_function(event_client: EventClient = None):
            return event_client

        result = my_function(event_client=explicit_client)
        assert result is explicit_client

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""

        @with_event_client
        def my_function_with_docs():
            """This is a docstring."""

        assert my_function_with_docs.__name__ == "my_function_with_docs"
        assert my_function_with_docs.__doc__ == "This is a docstring."

    def test_decorator_with_function_arguments(self):
        """Test that decorator works with functions that have arguments."""
        _event_client_context.set(None)

        @with_event_client(name="test")
        def add_numbers(a: int, b: int, event_client: EventClient = None) -> int:
            assert event_client is not None
            return a + b

        result = add_numbers(2, 3)
        assert result == 5

    def test_decorator_nesting(self):
        """Test that decorators nest correctly."""
        _event_client_context.set(None)

        @with_event_client(name="outer", outer_id="o-123")
        def outer_function():
            ctx = get_event_client_context()
            assert ctx is not None
            assert ctx.hierarchy == ["outer"]
            return inner_function()

        @with_event_client(name="inner", inner_id="i-456")
        def inner_function():
            ctx = get_event_client_context()
            assert ctx is not None
            # Inner inherits from outer
            assert ctx.hierarchy == ["outer", "inner"]
            assert ctx.metadata.get("outer_id") == "o-123"
            assert ctx.metadata.get("inner_id") == "i-456"
            return "success"

        result = outer_function()
        assert result == "success"

    def test_decorator_inherit_false(self):
        """Test that inherit=False creates fresh context."""
        _event_client_context.set(None)

        @with_event_client(name="outer", outer_id="o-123")
        def outer_function():
            return inner_function()

        @with_event_client(name="inner", inherit=False, inner_id="i-456")
        def inner_function():
            ctx = get_event_client_context()
            assert ctx is not None
            # Should NOT have outer's metadata
            assert "outer_id" not in ctx.metadata
            assert ctx.metadata.get("inner_id") == "i-456"
            assert ctx.hierarchy == ["inner"]
            return "success"

        result = outer_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_with_async_function(self):
        """Test that decorator works with async functions."""
        _event_client_context.set(None)

        @with_event_client(name="async_test", async_id="a-123")
        async def async_function():
            await asyncio.sleep(0.01)
            assert has_event_client_context()
            client = get_event_client()
            return client._bound_context.get("async_id")

        result = await async_function()
        assert result == "a-123"

    @pytest.mark.asyncio
    async def test_decorator_async_with_event_client_injection(self):
        """Test that decorator injects event_client in async functions."""
        _event_client_context.set(None)

        @with_event_client(name="async_test")
        async def async_function(event_client: EventClient = None):
            await asyncio.sleep(0.01)
            return event_client

        client = await async_function()
        assert client is not None
        assert isinstance(client, EventClient)


class TestEventClientClassDecorator:
    """Test event_client_class() decorator."""

    def test_class_decorator_adds_event_client_property(self):
        """Test that class decorator adds event_client property."""
        _event_client_context.set(None)

        @event_client_class()
        class MyComponent:
            def do_work(self):
                return self.event_client

        component = MyComponent()
        with event_client_context(name="test"):
            client = component.do_work()
            assert client is not None
            assert isinstance(client, EventClient)

    def test_class_decorator_wraps_public_methods(self):
        """Test that public methods are wrapped with context."""
        _event_client_context.set(None)

        @event_client_class(name="MyComponent")
        class MyComponent:
            def process(self):
                assert has_event_client_context()
                ctx = get_event_client_context()
                return ctx.hierarchy if ctx else []

        component = MyComponent()
        hierarchy = component.process()
        assert hierarchy == ["MyComponent.process"]

    def test_class_decorator_skips_private_methods(self):
        """Test that private methods are not wrapped."""
        _event_client_context.set(None)

        @event_client_class(name="MyComponent")
        class MyComponent:
            def _private_method(self):
                return has_event_client_context()

        component = MyComponent()
        # Private method should NOT have context
        assert component._private_method() is False

    def test_class_decorator_with_metadata(self):
        """Test that class decorator binds metadata to methods."""
        _event_client_context.set(None)

        @event_client_class(component_type="processor")
        class DataProcessor:
            def process(self):
                client = get_event_client()
                return client._bound_context.get("component_type")

        processor = DataProcessor()
        result = processor.process()
        assert result == "processor"

    def test_class_decorator_with_get_event_context_method(self):
        """Test that get_event_context method adds instance-specific context."""
        _event_client_context.set(None)

        @event_client_class(name="Worker")
        class Worker:
            def __init__(self, worker_id: str):
                self.worker_id = worker_id

            def get_event_context(self) -> dict:
                return {"worker_id": self.worker_id}

            def work(self):
                client = get_event_client()
                return client._bound_context.get("worker_id")

        worker = Worker("w-123")
        result = worker.work()
        assert result == "w-123"

    def test_class_decorator_preserves_existing_event_client_property(self):
        """Test that existing event_client property is not overwritten."""
        _event_client_context.set(None)
        custom_client = EventClient(name="custom", event_server_url=None)

        @event_client_class()
        class MyComponent:
            @property
            def event_client(self):
                return custom_client

            def do_work(self):
                return self.event_client

        component = MyComponent()
        with event_client_context(name="test"):
            client = component.do_work()
            assert client is custom_client

    def test_class_decorator_nested_method_calls(self):
        """Test that nested method calls have correct context."""
        _event_client_context.set(None)

        @event_client_class(name="MyComponent")
        class MyComponent:
            def outer_method(self):
                ctx = get_event_client_context()
                outer_hierarchy = ctx.hierarchy if ctx else []
                inner_hierarchy = self.inner_method()
                return outer_hierarchy, inner_hierarchy

            def inner_method(self):
                ctx = get_event_client_context()
                return ctx.hierarchy if ctx else []

        component = MyComponent()
        outer_h, inner_h = component.outer_method()
        assert outer_h == ["MyComponent.outer_method"]
        # Inner method creates a nested context
        assert inner_h == ["MyComponent.outer_method", "MyComponent.inner_method"]

    @pytest.mark.asyncio
    async def test_class_decorator_with_async_methods(self):
        """Test that class decorator works with async methods."""
        _event_client_context.set(None)

        @event_client_class(name="AsyncComponent")
        class AsyncComponent:
            async def async_process(self):
                await asyncio.sleep(0.01)
                assert has_event_client_context()
                ctx = get_event_client_context()
                return ctx.hierarchy if ctx else []

        component = AsyncComponent()
        hierarchy = await component.async_process()
        assert hierarchy == ["AsyncComponent.async_process"]


class TestDecoratorInteractions:
    """Test how decorators interact with each other and MadsciClientMixin."""

    def test_class_decorator_with_method_decorator_override(self):
        """Test using @with_event_client on a method within @event_client_class."""
        _event_client_context.set(None)

        @event_client_class(name="MyComponent", component_type="processor")
        class MyComponent:
            def regular_method(self):
                """This method gets auto-wrapped by class decorator."""
                ctx = get_event_client_context()
                return ctx.hierarchy if ctx else []

            @with_event_client(name="custom_method_name", custom_id="c-123")
            def custom_method(self):
                """This method has explicit decorator - gets double-wrapped."""
                ctx = get_event_client_context()
                client = get_event_client()
                return {
                    "hierarchy": ctx.hierarchy if ctx else [],
                    "has_custom_id": "custom_id" in client._bound_context,
                }

        component = MyComponent()

        # Regular method should have class-level context
        regular_result = component.regular_method()
        assert regular_result == ["MyComponent.regular_method"]

        # Custom method gets double-wrapped: class decorator wraps the with_event_client wrapper
        custom_result = component.custom_method()
        # The hierarchy shows both wrappings
        assert "custom_method_name" in custom_result["hierarchy"]
        assert custom_result["has_custom_id"]

    def test_nested_decorated_functions(self):
        """Test calling decorated function from within decorated function."""
        _event_client_context.set(None)

        @with_event_client(name="outer", outer_key="outer_value")
        def outer_function():
            ctx = get_event_client_context()
            outer_hierarchy = ctx.hierarchy if ctx else []
            inner_result = inner_function()
            return {"outer": outer_hierarchy, "inner": inner_result}

        @with_event_client(name="inner", inner_key="inner_value")
        def inner_function():
            ctx = get_event_client_context()
            client = get_event_client()
            return {
                "hierarchy": ctx.hierarchy if ctx else [],
                "has_outer_key": "outer_key" in client._bound_context,
                "has_inner_key": "inner_key" in client._bound_context,
            }

        result = outer_function()
        assert result["outer"] == ["outer"]
        assert result["inner"]["hierarchy"] == ["outer", "inner"]
        assert result["inner"]["has_outer_key"]  # Inner inherits outer context
        assert result["inner"]["has_inner_key"]

    def test_decorated_class_instantiated_in_one_context_used_in_another(self):
        """Test class instantiated in context A, method called in context B."""
        _event_client_context.set(None)

        @event_client_class(name="Worker")
        class Worker:
            def __init__(self, worker_id: str):
                self.worker_id = worker_id
                # Capture context at instantiation time
                self.instantiation_ctx = get_event_client_context()

            def get_event_context(self) -> dict:
                return {"worker_id": self.worker_id}

            def work(self):
                ctx = get_event_client_context()
                client = get_event_client()
                return {
                    "hierarchy": ctx.hierarchy if ctx else [],
                    "has_experiment_id": "experiment_id" in client._bound_context,
                    "has_job_id": "job_id" in client._bound_context,
                    "worker_id": client._bound_context.get("worker_id"),
                }

        # Instantiate worker in experiment context
        with event_client_context(name="experiment", experiment_id="exp-123"):
            worker = Worker("w-001")
            assert worker.instantiation_ctx is not None
            assert worker.instantiation_ctx.hierarchy == ["experiment"]

        # Call worker.work() in a different context (job context)
        with event_client_context(name="job", job_id="job-456"):
            result = worker.work()
            # The method runs in the CURRENT context (job), not instantiation context
            assert "Worker.work" in result["hierarchy"]
            assert result["has_job_id"]  # Has the current context's metadata
            assert not result["has_experiment_id"]  # Does NOT have old context
            assert result["worker_id"] == "w-001"  # Has instance metadata

    def test_decorated_class_method_called_without_context(self):
        """Test calling decorated class method when no external context exists."""
        _event_client_context.set(None)

        @event_client_class(name="Processor")
        class Processor:
            def process(self):
                assert has_event_client_context()  # Method creates its own context
                ctx = get_event_client_context()
                return ctx.hierarchy if ctx else []

        processor = Processor()
        # No external context, but method still works
        result = processor.process()
        assert result == ["Processor.process"]

        # After method returns, no context should remain
        assert not has_event_client_context()

    def test_function_decorator_called_within_class_method(self):
        """Test @with_event_client function called from @event_client_class method."""
        _event_client_context.set(None)

        @with_event_client(name="helper_func", helper_key="helper_value")
        def helper_function():
            ctx = get_event_client_context()
            client = get_event_client()
            return {
                "hierarchy": ctx.hierarchy if ctx else [],
                "has_component_key": "component_key" in client._bound_context,
                "has_helper_key": "helper_key" in client._bound_context,
            }

        @event_client_class(name="Component", component_key="component_value")
        class Component:
            def do_work(self):
                return helper_function()

        component = Component()
        result = component.do_work()

        # Helper inherits from Component.do_work context
        assert result["hierarchy"] == ["Component.do_work", "helper_func"]
        assert result["has_component_key"]  # Inherited from class
        assert result["has_helper_key"]  # Added by helper decorator

    def test_inherit_false_breaks_context_chain(self):
        """Test that inherit=False creates isolated context."""
        _event_client_context.set(None)

        @with_event_client(
            name="isolated", inherit=False, isolated_key="isolated_value"
        )
        def isolated_function():
            ctx = get_event_client_context()
            client = get_event_client()
            return {
                "hierarchy": ctx.hierarchy if ctx else [],
                "has_outer_key": "outer_key" in client._bound_context,
                "has_isolated_key": "isolated_key" in client._bound_context,
            }

        @with_event_client(name="outer", outer_key="outer_value")
        def outer_function():
            return isolated_function()

        result = outer_function()
        assert result["hierarchy"] == ["isolated"]  # No "outer" in hierarchy
        assert not result["has_outer_key"]  # Outer context not inherited
        assert result["has_isolated_key"]

    @pytest.mark.asyncio
    async def test_async_decorated_functions_nesting(self):
        """Test nested async decorated functions."""
        _event_client_context.set(None)

        @with_event_client(name="async_outer", outer_async_key="o-123")
        async def async_outer():
            await asyncio.sleep(0.01)
            return await async_inner()

        @with_event_client(name="async_inner", inner_async_key="i-456")
        async def async_inner():
            await asyncio.sleep(0.01)
            ctx = get_event_client_context()
            client = get_event_client()
            return {
                "hierarchy": ctx.hierarchy if ctx else [],
                "has_outer": "outer_async_key" in client._bound_context,
                "has_inner": "inner_async_key" in client._bound_context,
            }

        result = await async_outer()
        assert result["hierarchy"] == ["async_outer", "async_inner"]
        assert result["has_outer"]
        assert result["has_inner"]

    @pytest.mark.asyncio
    async def test_concurrent_decorated_functions_isolation(self):
        """Test that concurrent decorated functions have isolated contexts."""
        _event_client_context.set(None)

        @with_event_client(name="task")
        async def task_with_id(task_id: str):
            # Bind task_id to context
            client = get_event_client(task_id=task_id)
            await asyncio.sleep(0.02)  # Allow interleaving
            # Verify we still have our own task_id
            return client._bound_context.get("task_id")

        # Run multiple tasks concurrently
        results = await asyncio.gather(
            task_with_id("task-1"),
            task_with_id("task-2"),
            task_with_id("task-3"),
        )

        # Each task should have its own context
        assert results == ["task-1", "task-2", "task-3"]


class TestMadsciClientMixinWithDecorators:
    """Test how decorators interact with MadsciClientMixin."""

    def test_mixin_uses_decorator_context(self):
        """Test that MadsciClientMixin uses context from decorator."""
        _event_client_context.set(None)

        class MyComponent(MadsciClientMixin):
            name = "my_component"

        @with_event_client(name="workflow", workflow_id="wf-123")
        def run_workflow():
            component = MyComponent()
            client = component.event_client
            return {
                "has_workflow_id": "workflow_id" in client._bound_context,
                "component_name": client._bound_context.get("component_name"),
            }

        result = run_workflow()
        assert result["has_workflow_id"]  # Mixin gets context from decorator
        assert result["component_name"] == "my_component"  # Mixin adds its own context

    def test_mixin_in_decorated_class(self):
        """Test MadsciClientMixin combined with @event_client_class."""
        _event_client_context.set(None)

        # Note: Using both MadsciClientMixin and @event_client_class is redundant
        # because both add event_client. MadsciClientMixin's takes precedence
        # since it's in the MRO before the decorator's property.
        @event_client_class(name="DecoratedMixin")
        class DecoratedMixin(MadsciClientMixin):
            name = "decorated_mixin"

            def do_work(self):
                # Inside the method, context is established by decorator
                client = self.event_client
                return {
                    "has_context": has_event_client_context(),
                    "component_name": client._bound_context.get("component_name"),
                }

        component = DecoratedMixin()
        result = component.do_work()
        assert result["has_context"]
        assert result["component_name"] == "decorated_mixin"

    def test_mixin_instantiated_in_one_decorator_used_in_another(self):
        """Test MadsciClientMixin behavior across different decorator contexts."""
        _event_client_context.set(None)

        class Worker(MadsciClientMixin):
            name = "worker"

            def _get_component_context(self) -> dict[str, Any]:
                return {"worker_name": self.name}

        @with_event_client(name="setup", setup_id="s-123")
        def setup_phase():
            return Worker()

        @with_event_client(name="execution", execution_id="e-456")
        def execution_phase(worker: Worker):
            client = worker.event_client
            return {
                "has_execution_id": "execution_id" in client._bound_context,
                "has_setup_id": "setup_id" in client._bound_context,
                "worker_name": client._bound_context.get("worker_name"),
            }

        # Create worker in setup context
        worker = setup_phase()

        # Use worker in execution context
        result = execution_phase(worker)

        # Worker should use CURRENT context (execution), not setup context
        assert result["has_execution_id"]
        assert not result["has_setup_id"]  # Setup context is gone
        assert result["worker_name"] == "worker"  # Worker's own context is added

    def test_mixin_outside_decorator_context(self):
        """Test MadsciClientMixin works outside any decorator context."""
        _event_client_context.set(None)

        class MyComponent(MadsciClientMixin):
            name = "standalone_component"

        component = MyComponent()
        # No decorator context, mixin falls back to creating its own client
        client = component.event_client
        assert client is not None
        assert isinstance(client, EventClient)
        # Component context should still be bound
        assert client._bound_context.get("component_name") == "standalone_component"

    def test_decorated_function_with_mixin_parameter(self):
        """Test passing MadsciClientMixin instance to decorated function."""
        _event_client_context.set(None)

        class Processor(MadsciClientMixin):
            name = "processor"

        @with_event_client(name="batch_job", batch_id="b-123")
        def process_batch(processor: Processor, data: list):
            # Processor should inherit batch context
            client = processor.event_client
            return {
                "has_batch_id": "batch_id" in client._bound_context,
                "processor_name": client._bound_context.get("component_name"),
                "data_len": len(data),
            }

        processor = Processor()
        result = process_batch(processor, [1, 2, 3])

        assert result["has_batch_id"]
        assert result["processor_name"] == "processor"
        assert result["data_len"] == 3
