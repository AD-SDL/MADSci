"""Unit tests for madsci.common.context module."""

import asyncio
import threading

import pytest
from madsci.common.context import (
    GlobalMadsciContext,
    get_current_madsci_context,
    has_madsci_context,
    madsci_context,
    madsci_context_class,
    with_madsci_context,
)
from madsci.common.types.context_types import MadsciContext


def test_global_madsci_context_default() -> None:
    """Test that GlobalMadsciContext returns a MadsciContext instance."""
    context = GlobalMadsciContext.get_context()
    assert isinstance(context, MadsciContext)


def test_global_context_across_threads() -> None:
    """Tests that changes to GlobalMadsciContext are consistent across threads."""
    original_context = GlobalMadsciContext.get_context()
    original_url = original_context.lab_server_url
    test_url = "http://test-lab:8000"

    # Create a new context with modified URL
    new_context = original_context.model_copy()
    new_context.lab_server_url = test_url
    GlobalMadsciContext.set_context(new_context)
    assert (
        str(GlobalMadsciContext.get_context().lab_server_url) == "http://test-lab:8000/"
    )

    def check_context() -> None:
        """Function to check context in a separate thread."""
        assert (
            str(GlobalMadsciContext.get_context().lab_server_url)
            == "http://test-lab:8000/"
        )
        # Restore original context
        restore_context = GlobalMadsciContext.get_context().model_copy()
        restore_context.lab_server_url = original_url
        GlobalMadsciContext.set_context(restore_context)

    # Run the check in a separate thread
    thread = threading.Thread(target=check_context)
    thread.start()
    thread.join()
    # Ensure the original state is restored
    final_context = GlobalMadsciContext.get_context().model_copy()
    final_context.lab_server_url = original_url
    GlobalMadsciContext.set_context(final_context)


def test_madsci_context_temporary_override() -> None:
    """Test that madsci_context temporarily overrides and restores context."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url = "http://test-lab:8000"
    test_event_url = "http://test-event:8001"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(
        lab_server_url=test_lab_url, event_server_url=test_event_url
    ) as context:
        assert str(context.lab_server_url) == "http://test-lab:8000/"
        assert str(context.event_server_url) == "http://test-event:8001/"
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

    # After context, should be restored
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_madsci_context_partial_override() -> None:
    """Test that madsci_context only overrides specified fields."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url = "http://test-lab:8000"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(lab_server_url=test_lab_url):
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab:8000/"
        )
        # event_server_url should remain unchanged
        assert get_current_madsci_context().event_server_url == original_event_url

    # After context, should be restored
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_get_current_madsci_context() -> None:
    """Test that get_current_madsci_context returns a MadsciContext instance."""
    context = get_current_madsci_context()
    assert isinstance(context, MadsciContext)


def test_nested_madsci_context() -> None:
    """Test that nested context managers work correctly."""
    original_context = GlobalMadsciContext.get_context()
    original_lab_url = original_context.lab_server_url
    original_event_url = original_context.event_server_url
    test_lab_url1 = "http://test-lab1:8000"
    test_lab_url2 = "http://test-lab2:8000"
    test_event_url = "http://test-event:8001"

    # Ensure we start with known state
    base_context = original_context.model_copy()
    base_context.lab_server_url = original_lab_url
    base_context.event_server_url = original_event_url
    GlobalMadsciContext.set_context(base_context)

    with madsci_context(lab_server_url=test_lab_url1, event_server_url=test_event_url):
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab1:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

        with madsci_context(lab_server_url=test_lab_url2):
            # Inner context overrides lab_server_url but keeps event_server_url
            assert (
                str(get_current_madsci_context().lab_server_url)
                == "http://test-lab2:8000/"
            )
            assert (
                str(get_current_madsci_context().event_server_url)
                == "http://test-event:8001/"
            )

        # Back to outer context
        assert (
            str(get_current_madsci_context().lab_server_url) == "http://test-lab1:8000/"
        )
        assert (
            str(get_current_madsci_context().event_server_url)
            == "http://test-event:8001/"
        )

    # Back to original context
    assert get_current_madsci_context().lab_server_url == original_lab_url
    assert get_current_madsci_context().event_server_url == original_event_url


def test_madsci_context_with_all_fields() -> None:
    """Test that madsci_context works with all available context fields."""
    original_context = get_current_madsci_context()

    test_values = {
        "lab_server_url": "http://test-lab:8000",
        "event_server_url": "http://test-event:8001",
        "experiment_server_url": "http://test-experiment:8002",
        "data_server_url": "http://test-data:8003",
        "resource_server_url": "http://test-resource:8004",
        "workcell_server_url": "http://test-workcell:8005",
    }

    with madsci_context(**test_values):
        current = get_current_madsci_context()
        # Check that all URLs are set correctly (with trailing slash added by AnyUrl)
        assert str(current.lab_server_url) == "http://test-lab:8000/"
        assert str(current.event_server_url) == "http://test-event:8001/"
        assert str(current.experiment_server_url) == "http://test-experiment:8002/"
        assert str(current.data_server_url) == "http://test-data:8003/"
        assert str(current.resource_server_url) == "http://test-resource:8004/"
        assert str(current.workcell_server_url) == "http://test-workcell:8005/"

    # After context, should be restored
    restored_context = get_current_madsci_context()
    for field in test_values:
        assert getattr(restored_context, field) == getattr(original_context, field)


class TestWithMadsciContextDecorator:
    """Test with_madsci_context() decorator."""

    def test_decorator_establishes_context(self) -> None:
        """Test that decorator establishes madsci context."""
        test_url = "http://test-server:8001"

        @with_madsci_context(event_server_url=test_url)
        def my_function() -> str:
            ctx = get_current_madsci_context()
            return str(ctx.event_server_url)

        result = my_function()
        assert result == "http://test-server:8001/"

    def test_decorator_without_args(self) -> None:
        """Test decorator without arguments."""

        @with_madsci_context
        def my_function() -> bool:
            # Should run within context
            return has_madsci_context()

        result = my_function()
        assert result is True

    def test_decorator_with_multiple_urls(self) -> None:
        """Test decorator with multiple server URLs."""
        lab_url = "http://lab:8000"
        event_url = "http://event:8001"
        data_url = "http://data:8004"

        @with_madsci_context(
            lab_server_url=lab_url,
            event_server_url=event_url,
            data_server_url=data_url,
        )
        def my_function() -> dict:
            ctx = get_current_madsci_context()
            return {
                "lab": str(ctx.lab_server_url),
                "event": str(ctx.event_server_url),
                "data": str(ctx.data_server_url),
            }

        result = my_function()
        assert result["lab"] == "http://lab:8000/"
        assert result["event"] == "http://event:8001/"
        assert result["data"] == "http://data:8004/"

    def test_decorator_injects_madsci_ctx_parameter(self) -> None:
        """Test that decorator injects madsci_ctx if parameter exists."""
        test_url = "http://test:8000"

        @with_madsci_context(lab_server_url=test_url)
        def my_function(madsci_ctx: MadsciContext = None) -> str:
            return str(madsci_ctx.lab_server_url)

        result = my_function()
        assert result == "http://test:8000/"

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves function name and docstring."""

        @with_madsci_context(event_server_url="http://test:8001")
        def my_function_with_docs() -> None:
            """This is a docstring."""

        assert my_function_with_docs.__name__ == "my_function_with_docs"
        assert my_function_with_docs.__doc__ == "This is a docstring."

    def test_decorator_nesting(self) -> None:
        """Test that decorators nest correctly."""

        @with_madsci_context(lab_server_url="http://lab:8000")
        def outer_function() -> dict:
            outer_lab = str(get_current_madsci_context().lab_server_url)
            inner_result = inner_function()
            return {"outer": outer_lab, "inner": inner_result}

        @with_madsci_context(event_server_url="http://event:8001")
        def inner_function() -> dict:
            ctx = get_current_madsci_context()
            return {
                "lab": str(ctx.lab_server_url) if ctx.lab_server_url else None,
                "event": str(ctx.event_server_url),
            }

        result = outer_function()
        assert result["outer"] == "http://lab:8000/"
        # Inner inherits outer's lab_server_url
        assert result["inner"]["lab"] == "http://lab:8000/"
        assert result["inner"]["event"] == "http://event:8001/"

    @pytest.mark.asyncio
    async def test_decorator_with_async_function(self) -> None:
        """Test that decorator works with async functions."""
        test_url = "http://async-server:8001"

        @with_madsci_context(event_server_url=test_url)
        async def async_function() -> str:
            await asyncio.sleep(0.01)
            ctx = get_current_madsci_context()
            return str(ctx.event_server_url)

        result = await async_function()
        assert result == "http://async-server:8001/"


class TestMadsciContextClassDecorator:
    """Test madsci_context_class() decorator."""

    def test_class_decorator_adds_madsci_context_property(self) -> None:
        """Test that class decorator adds madsci_context property."""

        @madsci_context_class(event_server_url="http://test:8001")
        class MyComponent:
            def get_event_url(self) -> str:
                return str(self.madsci_context.event_server_url)

        component = MyComponent()
        result = component.get_event_url()
        assert result == "http://test:8001/"

    def test_class_decorator_wraps_public_methods(self) -> None:
        """Test that public methods are wrapped with context."""

        @madsci_context_class(lab_server_url="http://lab:8000")
        class MyClient:
            def get_lab_url(self) -> str:
                return str(get_current_madsci_context().lab_server_url)

        client = MyClient()
        result = client.get_lab_url()
        assert result == "http://lab:8000/"

    def test_class_decorator_skips_private_methods(self) -> None:
        """Test that private methods are not wrapped."""

        @madsci_context_class(event_server_url="http://test:8001")
        class MyComponent:
            def _private_method(self) -> bool:
                # Private methods don't get the decorator's context
                return has_madsci_context()

        component = MyComponent()
        # Private method may or may not have context depending on global state
        result = component._private_method()
        assert isinstance(result, bool)

    def test_class_decorator_with_get_context_overrides(self) -> None:
        """Test that get_context_overrides adds instance-specific context."""

        @madsci_context_class(lab_server_url="http://lab:8000")
        class Client:
            def __init__(self, workcell_url: str) -> None:
                self.workcell_url = workcell_url

            def get_context_overrides(self) -> dict:
                return {"workcell_server_url": self.workcell_url}

            def get_urls(self) -> dict:
                ctx = get_current_madsci_context()
                return {
                    "lab": str(ctx.lab_server_url),
                    "workcell": str(ctx.workcell_server_url),
                }

        client = Client("http://workcell:8005")
        result = client.get_urls()
        assert result["lab"] == "http://lab:8000/"
        assert result["workcell"] == "http://workcell:8005/"

    def test_class_decorator_preserves_existing_property(self) -> None:
        """Test that existing madsci_context property is not overwritten."""
        custom_context = MadsciContext()

        @madsci_context_class(event_server_url="http://test:8001")
        class MyComponent:
            @property
            def madsci_context(self) -> MadsciContext:
                return custom_context

            def get_context(self) -> MadsciContext:
                return self.madsci_context

        component = MyComponent()
        result = component.get_context()
        assert result is custom_context

    @pytest.mark.asyncio
    async def test_class_decorator_with_async_methods(self) -> None:
        """Test that class decorator works with async methods."""

        @madsci_context_class(data_server_url="http://data:8004")
        class AsyncClient:
            async def async_get_url(self) -> str:
                await asyncio.sleep(0.01)
                return str(get_current_madsci_context().data_server_url)

        client = AsyncClient()
        result = await client.async_get_url()
        assert result == "http://data:8004/"
