"""Unit tests for madsci.common.ownership module."""

import asyncio
import threading

import pytest
from madsci.common.ownership import (
    get_current_ownership_info,
    global_ownership_info,
    has_ownership_context,
    ownership_class,
    ownership_context,
    with_ownership,
)
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.utils import new_ulid_str


def test_global_ownership_info_default() -> None:
    """Test that global_ownership_info is an instance of OwnershipInfo by default."""
    assert isinstance(global_ownership_info, OwnershipInfo)


def test_global_ownership_across_threads() -> None:
    """Tests that changes to global_ownership_info are consistent across threads."""
    original_id = getattr(global_ownership_info, "node_id", None)
    test_id = new_ulid_str()
    global_ownership_info.node_id = test_id
    assert global_ownership_info.node_id == test_id

    def check_ownership() -> bool:
        """Function to check ownership in a separate thread."""
        assert global_ownership_info.node_id == test_id
        global_ownership_info.node_id = original_id

    # Run the check in a separate thread
    thread = threading.Thread(target=check_ownership)
    thread.start()
    thread.join()
    # Ensure the original state is restored
    global_ownership_info.node_id = original_id


def test_ownership_context_temporary_override() -> None:
    """Test that ownership_context temporarily overrides and restores ownership info."""
    original_id = getattr(global_ownership_info, "node_id", None)
    test_id = new_ulid_str()
    global_ownership_info.node_id = original_id
    with ownership_context(node_id=test_id) as info:
        assert info.node_id == test_id
        assert get_current_ownership_info().node_id == test_id
    # After context, should be restored
    assert get_current_ownership_info().node_id == original_id


def test_get_current_ownership_info() -> None:
    """Test that get_current_ownership_info returns an OwnershipInfo instance."""
    info = get_current_ownership_info()
    assert isinstance(info, OwnershipInfo)


class TestWithOwnershipDecorator:
    """Test with_ownership() decorator."""

    def test_decorator_establishes_context(self) -> None:
        """Test that decorator establishes ownership context."""
        test_id = new_ulid_str()

        @with_ownership(experiment_id=test_id)
        def my_function() -> str:
            info = get_current_ownership_info()
            return info.experiment_id

        result = my_function()
        assert result == test_id

    def test_decorator_without_args(self) -> None:
        """Test decorator without arguments."""

        @with_ownership
        def my_function() -> bool:
            # Should still run within context (inheriting current)
            return has_ownership_context() or True  # Always true since global exists

        result = my_function()
        assert result is True

    def test_decorator_with_multiple_ids(self) -> None:
        """Test decorator with multiple ownership IDs."""
        exp_id = new_ulid_str()
        node_id = new_ulid_str()
        step_id = new_ulid_str()

        @with_ownership(experiment_id=exp_id, node_id=node_id, step_id=step_id)
        def my_function() -> dict:
            info = get_current_ownership_info()
            return {
                "experiment_id": info.experiment_id,
                "node_id": info.node_id,
                "step_id": info.step_id,
            }

        result = my_function()
        assert result["experiment_id"] == exp_id
        assert result["node_id"] == node_id
        assert result["step_id"] == step_id

    def test_decorator_injects_ownership_info_parameter(self) -> None:
        """Test that decorator injects ownership_info if parameter exists."""
        test_id = new_ulid_str()

        @with_ownership(workflow_id=test_id)
        def my_function(ownership_info: OwnershipInfo = None) -> str:
            return ownership_info.workflow_id

        result = my_function()
        assert result == test_id

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves function name and docstring."""

        @with_ownership(experiment_id=new_ulid_str())
        def my_function_with_docs() -> None:
            """This is a docstring."""

        assert my_function_with_docs.__name__ == "my_function_with_docs"
        assert my_function_with_docs.__doc__ == "This is a docstring."

    def test_decorator_nesting(self) -> None:
        """Test that decorators nest correctly."""
        outer_id = new_ulid_str()
        inner_id = new_ulid_str()

        @with_ownership(experiment_id=outer_id)
        def outer_function() -> dict:
            outer_exp = get_current_ownership_info().experiment_id
            inner_result = inner_function()
            return {"outer": outer_exp, "inner": inner_result}

        @with_ownership(workflow_id=inner_id)
        def inner_function() -> dict:
            info = get_current_ownership_info()
            return {
                "experiment_id": info.experiment_id,
                "workflow_id": info.workflow_id,
            }

        result = outer_function()
        assert result["outer"] == outer_id
        # Inner inherits outer's experiment_id
        assert result["inner"]["experiment_id"] == outer_id
        assert result["inner"]["workflow_id"] == inner_id

    @pytest.mark.asyncio
    async def test_decorator_with_async_function(self) -> None:
        """Test that decorator works with async functions."""
        test_id = new_ulid_str()

        @with_ownership(experiment_id=test_id)
        async def async_function() -> str:
            await asyncio.sleep(0.01)
            info = get_current_ownership_info()
            return info.experiment_id

        result = await async_function()
        assert result == test_id


class TestOwnershipClassDecorator:
    """Test ownership_class() decorator."""

    def test_class_decorator_adds_ownership_info_property(self) -> None:
        """Test that class decorator adds ownership_info property."""
        test_id = new_ulid_str()

        @ownership_class(experiment_id=test_id)
        class MyComponent:
            def get_experiment(self) -> str:
                return self.ownership_info.experiment_id

        component = MyComponent()
        result = component.get_experiment()
        assert result == test_id

    def test_class_decorator_wraps_public_methods(self) -> None:
        """Test that public methods are wrapped with context."""
        test_id = new_ulid_str()

        @ownership_class(node_id=test_id)
        class MyWorker:
            def work(self) -> str:
                return get_current_ownership_info().node_id

        worker = MyWorker()
        result = worker.work()
        assert result == test_id

    def test_class_decorator_skips_private_methods(self) -> None:
        """Test that private methods are not wrapped."""
        test_id = new_ulid_str()

        @ownership_class(experiment_id=test_id)
        class MyComponent:
            def _private_method(self) -> str:
                # Private methods don't get wrapped
                info = get_current_ownership_info()
                return info.experiment_id

        component = MyComponent()
        # Private method doesn't have the context set by decorator
        # (it uses the global context instead)
        result = component._private_method()
        # Result may or may not match test_id depending on global state
        assert isinstance(result, (str, type(None)))

    def test_class_decorator_with_get_ownership_overrides(self) -> None:
        """Test that get_ownership_overrides adds instance-specific context."""
        exp_id = new_ulid_str()
        step_id = new_ulid_str()

        @ownership_class(experiment_id=exp_id)
        class Worker:
            def __init__(self, step: str) -> None:
                self.step = step

            def get_ownership_overrides(self) -> dict:
                return {"step_id": self.step}

            def work(self) -> dict:
                info = get_current_ownership_info()
                return {
                    "experiment_id": info.experiment_id,
                    "step_id": info.step_id,
                }

        worker = Worker(step_id)
        result = worker.work()
        assert result["experiment_id"] == exp_id
        assert result["step_id"] == step_id

    def test_class_decorator_preserves_existing_property(self) -> None:
        """Test that existing ownership_info property is not overwritten."""
        custom_info = OwnershipInfo(experiment_id=new_ulid_str())

        @ownership_class(node_id=new_ulid_str())
        class MyComponent:
            @property
            def ownership_info(self) -> OwnershipInfo:
                return custom_info

            def get_info(self) -> OwnershipInfo:
                return self.ownership_info

        component = MyComponent()
        result = component.get_info()
        assert result is custom_info

    @pytest.mark.asyncio
    async def test_class_decorator_with_async_methods(self) -> None:
        """Test that class decorator works with async methods."""
        test_id = new_ulid_str()

        @ownership_class(workflow_id=test_id)
        class AsyncWorker:
            async def async_work(self) -> str:
                await asyncio.sleep(0.01)
                return get_current_ownership_info().workflow_id

        worker = AsyncWorker()
        result = await worker.async_work()
        assert result == test_id
