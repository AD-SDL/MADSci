"""Tests for EventClient context propagation."""

import asyncio
from unittest.mock import Mock

import pytest
from madsci.client.event_client import EventClient
from madsci.common.context import (
    _event_client_context,
    event_client_context,
    get_event_client,
    get_event_client_context,
    has_event_client_context,
)
from madsci.common.types.event_types import EventClientContext


class TestEventClientContext:
    """Test EventClientContext dataclass."""

    def test_context_stores_client(self):
        """Test that EventClientContext stores an EventClient."""
        client = EventClient(name="test")
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
        explicit_client = EventClient(name="explicit")

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
