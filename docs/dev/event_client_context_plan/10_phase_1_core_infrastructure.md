# Phase 1: Core Infrastructure

**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** None
**Prerequisites:** None

## Goals

- Implement `EventClientContext` dataclass
- Implement context management functions (`get_event_client`, `event_client_context`, etc.)
- Ensure full backward compatibility
- Establish test patterns for context propagation

## 0.1 Pre-Implementation Verification (Completed Feb 2026)

The following prerequisites have been verified:

- **`EventClient.bind()` exists** at `src/madsci_client/madsci/client/event_client.py:358-381`
  - Creates a shallow copy with merged `_bound_context`
  - Also binds to underlying structlog logger
  - Returns new EventClient (immutable pattern)
- **`EventClient._bound_context`** is accessible as `dict[str, Any]` (line 81, initialized line 114)
- **`EventClient.unbind(*keys)`** also exists for removing context keys
- **Existing `context.py`** at `src/madsci_common/madsci/common/context.py` already uses `contextvars` for `MadsciContext` - the EventClient context will follow the same pattern

## 1.0 Implementation Principles

### 1.0.1 Context Variable Semantics

The context uses Python's `contextvars.ContextVar` which provides:
- Thread-safety by default
- Automatic async propagation across `await` boundaries
- Proper isolation between concurrent operations

### 1.0.2 Graceful Fallback

`get_event_client()` must **never** raise an exception due to missing context. It should always return a usable EventClient.

### 1.0.3 Child Context Creation

When extending context, child clients are created via `EventClient.bind()` to share underlying resources (file handlers, HTTP session, buffers).

## 1.1 Test Specifications (TDD)

Create `src/madsci_client/tests/test_event_client_context.py`:

```python
"""Tests for EventClient context propagation."""

import pytest
from unittest.mock import Mock, patch


class TestEventClientContext:
    """Test EventClientContext dataclass."""

    def test_context_stores_client(self):
        """Test that EventClientContext stores an EventClient."""
        from madsci.common.types.event_types import EventClientContext
        from madsci.client.event_client import EventClient

        client = EventClient(name="test")
        ctx = EventClientContext(client=client)

        assert ctx.client is client
        assert ctx.hierarchy == []
        assert ctx.metadata == {}

    def test_context_name_from_hierarchy(self):
        """Test that context name is built from hierarchy."""
        from madsci.common.types.event_types import EventClientContext

        client = Mock()
        ctx = EventClientContext(
            client=client,
            hierarchy=["experiment", "workflow", "step"],
        )

        assert ctx.name == "experiment.workflow.step"

    def test_context_name_empty_hierarchy(self):
        """Test that empty hierarchy returns default name."""
        from madsci.common.types.event_types import EventClientContext

        client = Mock()
        ctx = EventClientContext(client=client)

        assert ctx.name == "madsci"

    def test_child_context_extends_hierarchy(self):
        """Test that child() extends the hierarchy."""
        from madsci.common.types.event_types import EventClientContext

        parent_client = Mock()
        parent_client.bind.return_value = Mock()

        parent_ctx = EventClientContext(
            client=parent_client,
            hierarchy=["experiment"],
            metadata={"experiment_id": "exp-123"},
        )

        child_ctx = parent_ctx.child("workflow", workflow_id="wf-456")

        assert child_ctx.hierarchy == ["experiment", "workflow"]
        assert child_ctx.metadata == {"experiment_id": "exp-123", "workflow_id": "wf-456"}
        parent_client.bind.assert_called_once_with(workflow_id="wf-456")

    def test_child_context_with_explicit_client(self):
        """Test that child() can use an explicit client."""
        from madsci.common.types.event_types import EventClientContext

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
        from madsci.common.context import get_event_client, _event_client_context

        # Ensure no context
        _event_client_context.set(None)

        client = get_event_client()

        assert client is not None
        # Should have a name derived from caller
        assert client.name is not None

    def test_get_event_client_with_context_returns_context_client(self):
        """Test that get_event_client returns context client when available."""
        from madsci.common.context import get_event_client, event_client_context

        with event_client_context(name="test") as ctx_client:
            client = get_event_client()
            # Should be the same client (or bound version)
            assert client is ctx_client

    def test_get_event_client_with_additional_context_binds(self):
        """Test that get_event_client with kwargs binds additional context."""
        from madsci.common.context import get_event_client, event_client_context

        with event_client_context(name="test") as ctx_client:
            client = get_event_client(step_id="step-1")
            # Should be a bound version, not the original
            assert client is not ctx_client
            assert "step_id" in client._bound_context

    def test_get_event_client_with_name_uses_name(self):
        """Test that explicit name is used."""
        from madsci.common.context import get_event_client, _event_client_context

        _event_client_context.set(None)

        client = get_event_client(name="custom_name")

        assert client.name == "custom_name"

    def test_get_event_client_always_works(self):
        """Test that get_event_client never raises due to missing context."""
        from madsci.common.context import get_event_client, _event_client_context

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
        from madsci.common.context import event_client_context, has_event_client_context

        assert not has_event_client_context()

        with event_client_context(name="test"):
            assert has_event_client_context()

        assert not has_event_client_context()

    def test_context_manager_yields_client(self):
        """Test that context manager yields the EventClient."""
        from madsci.common.context import event_client_context
        from madsci.client.event_client import EventClient

        with event_client_context(name="test") as client:
            assert isinstance(client, EventClient)

    def test_nested_context_inherits_parent(self):
        """Test that nested context inherits parent context."""
        from madsci.common.context import event_client_context, get_event_client_context

        with event_client_context(name="parent", parent_id="p-123"):
            parent_ctx = get_event_client_context()
            assert parent_ctx.hierarchy == ["parent"]
            assert parent_ctx.metadata == {"parent_id": "p-123"}

            with event_client_context(name="child", child_id="c-456"):
                child_ctx = get_event_client_context()
                assert child_ctx.hierarchy == ["parent", "child"]
                assert child_ctx.metadata == {"parent_id": "p-123", "child_id": "c-456"}

            # After child exits, should be back to parent
            restored_ctx = get_event_client_context()
            assert restored_ctx.hierarchy == ["parent"]

    def test_context_with_explicit_client(self):
        """Test that explicit client is used when provided."""
        from madsci.common.context import event_client_context
        from madsci.client.event_client import EventClient

        explicit_client = EventClient(name="explicit")

        with event_client_context(client=explicit_client) as client:
            assert client is explicit_client

    def test_context_inherit_false_creates_fresh(self):
        """Test that inherit=False creates fresh context."""
        from madsci.common.context import event_client_context, get_event_client_context

        with event_client_context(name="parent", parent_id="p-123"):
            with event_client_context(name="isolated", inherit=False, isolated_id="i-789"):
                ctx = get_event_client_context()
                # Should NOT have parent's metadata
                assert "parent_id" not in ctx.metadata
                assert ctx.metadata == {"isolated_id": "i-789"}
                assert ctx.hierarchy == ["isolated"]

    def test_context_binds_metadata_to_logs(self):
        """Test that context metadata is included in log messages."""
        from madsci.common.context import event_client_context

        with event_client_context(name="test", experiment_id="exp-123") as client:
            # The bound context should include experiment_id
            assert "experiment_id" in client._bound_context
            assert client._bound_context["experiment_id"] == "exp-123"


class TestHasEventClientContext:
    """Test has_event_client_context() function."""

    def test_returns_false_when_no_context(self):
        """Test returns False when no context exists."""
        from madsci.common.context import has_event_client_context, _event_client_context

        _event_client_context.set(None)

        assert has_event_client_context() is False

    def test_returns_true_when_context_exists(self):
        """Test returns True when context exists."""
        from madsci.common.context import has_event_client_context, event_client_context

        with event_client_context(name="test"):
            assert has_event_client_context() is True


class TestContextAsyncPropagation:
    """Test that context propagates correctly in async code."""

    @pytest.mark.asyncio
    async def test_context_propagates_across_await(self):
        """Test that context propagates across await boundaries."""
        import asyncio
        from madsci.common.context import event_client_context, get_event_client, has_event_client_context

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
        import asyncio
        from madsci.common.context import event_client_context, get_event_client

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
        from madsci.common.context import get_event_client, _event_client_context

        _event_client_context.set(None)

        client = get_event_client()

        # Should have inferred name from this test module
        # (exact name depends on test runner, but should not be empty)
        assert client.name is not None
        assert len(client.name) > 0
```

## 1.2 Implementation Tasks

### 1.2.1 Add EventClientContext Dataclass

Add to `src/madsci_common/madsci/common/types/event_types.py`:

```python
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient


@dataclass
class EventClientContext:
    """
    Holds the current EventClient and its hierarchical context.

    This dataclass is used internally by the context management system
    to track the current EventClient and accumulated context metadata.

    Attributes:
        client: The actual EventClient instance for logging.
        hierarchy: The naming hierarchy, e.g., ["experiment", "workflow", "step"].
        metadata: Accumulated context metadata (experiment_id, workflow_id, etc.).

    Example:
        ctx = EventClientContext(
            client=event_client,
            hierarchy=["experiment", "workflow"],
            metadata={"experiment_id": "exp-123", "workflow_id": "wf-456"},
        )
        print(ctx.name)  # "experiment.workflow"
    """

    client: "EventClient"
    """The actual EventClient instance."""

    hierarchy: list[str] = field(default_factory=list)
    """The naming hierarchy, e.g., ["experiment", "workflow", "step"]."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Accumulated context metadata (experiment_id, workflow_id, etc.)."""

    @property
    def name(self) -> str:
        """
        Get the full hierarchical name.

        Returns:
            Dot-separated hierarchy string, or "madsci" if empty.
        """
        return ".".join(self.hierarchy) if self.hierarchy else "madsci"

    def child(
        self,
        name: str,
        client: Optional["EventClient"] = None,
        **metadata: Any,
    ) -> "EventClientContext":
        """
        Create a child context with extended hierarchy.

        Args:
            name: Name for this context level, added to hierarchy.
            client: Optional explicit EventClient. If None, creates a bound
                   child from the parent's client.
            **metadata: Additional context metadata to merge.

        Returns:
            New EventClientContext with extended hierarchy and metadata.

        Example:
            parent_ctx = EventClientContext(client=client, hierarchy=["experiment"])
            child_ctx = parent_ctx.child("workflow", workflow_id="wf-123")
            # child_ctx.hierarchy == ["experiment", "workflow"]
            # child_ctx.metadata == {"workflow_id": "wf-123"}
        """
        merged_metadata = {**self.metadata, **metadata}

        if client is not None:
            child_client = client
        else:
            # Create bound child from parent's client
            child_client = self.client.bind(**metadata) if metadata else self.client

        return EventClientContext(
            client=child_client,
            hierarchy=[*self.hierarchy, name],
            metadata=merged_metadata,
        )
```

### 1.2.2 Add Context Management Functions

Add to `src/madsci_common/madsci/common/context.py`:

```python
# Add these imports at the top
from typing import TYPE_CHECKING, Any, Optional, Generator
import inspect

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import EventClientContext


# Add new ContextVar for EventClient context
_event_client_context: contextvars.ContextVar[Optional["EventClientContext"]] = (
    contextvars.ContextVar(
        "event_client_context",
        default=None,
    )
)


def get_event_client(
    name: Optional[str] = None,
    create_if_missing: bool = True,
    **context_kwargs: Any,
) -> "EventClient":
    """
    Get the current EventClient from context, or create one if none exists.

    This is the primary way to obtain an EventClient in MADSci code.
    It enables automatic context propagation and hierarchical logging.

    Args:
        name: Optional name override. If provided without existing context,
              uses this as the client name. Ignored if context exists.
        create_if_missing: If True (default), create a new EventClient when
                          no context exists. If False, raises RuntimeError.
        **context_kwargs: Additional context to bind to the returned client.
                         If context exists, returns a bound child client.
                         If creating new, these become initial bound context.

    Returns:
        An EventClient instance, potentially with inherited context.

    Raises:
        RuntimeError: If create_if_missing=False and no context exists.

    Example:
        # In a component that should inherit context:
        logger = get_event_client()
        logger.info("Processing...")

        # In a component that wants to add context:
        logger = get_event_client(node_id="node-123")
        logger.info("Node action")  # Includes node_id
    """
    from madsci.common.types.event_types import EventClientContext

    ctx = _event_client_context.get()

    if ctx is not None:
        # We have an existing context - use it or extend it
        if context_kwargs:
            # Caller wants to add context - return a bound child
            return ctx.client.bind(**context_kwargs)
        return ctx.client

    # No context exists
    if not create_if_missing:
        raise RuntimeError(
            "No EventClient context available. "
            "Wrap your code in an event_client_context() block or use create_if_missing=True."
        )

    # Create a new root EventClient
    # Use stack inspection as fallback for name
    if name is None:
        name = _infer_caller_name()

    from madsci.client.event_client import EventClient
    client = EventClient(name=name)

    # Bind any provided context
    if context_kwargs:
        client = client.bind(**context_kwargs)

    return client


def _infer_caller_name() -> str:
    """
    Infer a reasonable name from the call stack.

    Walks up the stack to find the first frame that's not in the
    context module, and uses its module name.

    Returns:
        Inferred module name, or "madsci" as fallback.
    """
    stack = inspect.stack()
    for frame_info in stack[1:]:  # Skip this function
        module = frame_info.frame.f_globals.get("__name__", "")
        # Skip context module frames
        if not module.startswith("madsci.common.context"):
            return module
    return "madsci"


@contextlib.contextmanager
def event_client_context(
    name: Optional[str] = None,
    client: Optional["EventClient"] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Generator["EventClient", None, None]:
    """
    Establish or extend an EventClient context.

    All code executed within this context manager will have access to
    the EventClient via get_event_client(), with accumulated context.

    Args:
        name: Name for this context level (e.g., "workflow", "node").
              Added to the hierarchy.
        client: Explicit EventClient to use. If None, inherits from
               parent context or creates a new one.
        inherit: If True (default), inherit and extend parent context.
                If False, create a fresh context.
        **context_metadata: Additional context to bind to all log messages
                           (e.g., experiment_id, workflow_id).

    Yields:
        The EventClient for this context.

    Example:
        # Establish root context in an experiment
        with event_client_context(name="experiment", experiment_id="exp-123") as logger:
            logger.info("Starting experiment")

            # Nested context for workflow
            with event_client_context(name="workflow", workflow_id="wf-456") as wf_logger:
                wf_logger.info("Running workflow")
                # Log includes both experiment_id and workflow_id
    """
    from madsci.common.types.event_types import EventClientContext
    from madsci.client.event_client import EventClient

    parent_ctx = _event_client_context.get()

    if client is not None:
        # Explicit client provided - use it
        new_client = client.bind(**context_metadata) if context_metadata else client
        hierarchy = [name] if name else []
        new_ctx = EventClientContext(
            client=new_client,
            hierarchy=hierarchy,
            metadata=dict(context_metadata),
        )
    elif parent_ctx is not None and inherit:
        # Inherit from parent context
        # Use provided name, or generate one from caller if not provided
        effective_name = name or _infer_caller_name().split(".")[-1]
        new_ctx = parent_ctx.child(effective_name, **context_metadata)
    else:
        # Create new root context
        effective_name = name or _infer_caller_name()
        new_client = EventClient(name=effective_name)
        if context_metadata:
            new_client = new_client.bind(**context_metadata)
        # Use effective_name for hierarchy to ensure consistency
        new_ctx = EventClientContext(
            client=new_client,
            hierarchy=[effective_name] if effective_name else [],
            metadata=dict(context_metadata),
        )

    token = _event_client_context.set(new_ctx)
    try:
        yield new_ctx.client
    finally:
        _event_client_context.reset(token)


def get_event_client_context() -> Optional["EventClientContext"]:
    """
    Get the current EventClientContext, if any.

    Returns:
        The current EventClientContext, or None if no context is active.

    Example:
        ctx = get_event_client_context()
        if ctx:
            print(f"Current hierarchy: {ctx.name}")
            print(f"Metadata: {ctx.metadata}")
    """
    return _event_client_context.get()


def has_event_client_context() -> bool:
    """
    Check if an EventClient context is currently active.

    Returns:
        True if a context is active, False otherwise.

    Example:
        if has_event_client_context():
            logger = get_event_client()  # Uses context
        else:
            logger = EventClient(name="standalone")  # Create new
    """
    return _event_client_context.get() is not None
```

### 1.2.3 Update Module Exports

Update `src/madsci_common/madsci/common/context.py` exports and `__init__.py` files to expose the new functions.

In context.py, ensure these are importable:
```python
__all__ = [
    # Existing
    "GlobalMadsciContext",
    "madsci_context",
    "get_current_madsci_context",
    "set_current_madsci_context",
    # New
    "get_event_client",
    "event_client_context",
    "get_event_client_context",
    "has_event_client_context",
]
```

### 1.2.4 Add Optional OTEL Hierarchy Attributes

Update the structlog processor to add hierarchy information when available.

In `src/madsci_client/madsci/client/structlog_config.py`, add a processor:

```python
def add_event_client_hierarchy(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Add EventClient hierarchy information to log events.

    This processor adds madsci.hierarchy and madsci.* metadata fields
    when an EventClientContext is active.
    """
    from madsci.common.context import get_event_client_context

    ctx = get_event_client_context()
    if ctx is not None:
        if ctx.hierarchy:
            event_dict["madsci.hierarchy"] = ctx.name
        for key, value in ctx.metadata.items():
            event_dict[f"madsci.{key}"] = value

    return event_dict
```

Add this processor to the processor chain in `build_processors()` (before the final renderer).

## 1.3 Acceptance Criteria

- [ ] `EventClientContext` dataclass implemented with `client`, `hierarchy`, `metadata` fields
- [ ] `EventClientContext.name` property returns dot-separated hierarchy
- [ ] `EventClientContext.child()` creates child context with extended hierarchy
- [ ] `get_event_client()` returns context client when available
- [ ] `get_event_client()` creates new client when no context (never fails)
- [ ] `get_event_client()` with kwargs returns bound client
- [ ] `event_client_context()` establishes new context
- [ ] `event_client_context()` with `inherit=True` extends parent context
- [ ] `event_client_context()` with `inherit=False` creates fresh context
- [ ] `event_client_context()` with explicit `client` uses that client
- [ ] `has_event_client_context()` returns correct boolean
- [ ] `get_event_client_context()` returns current context or None
- [ ] Context propagates correctly across async/await boundaries
- [ ] Concurrent async operations have isolated contexts
- [ ] All tests pass
- [ ] No breaking changes to existing code

## 1.4 Integration Notes

### Import Structure

To avoid circular imports, use `TYPE_CHECKING` guards:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madsci.client.event_client import EventClient
```

Actual imports are done inside function bodies where needed.

### Testing Dependencies

Tests require:
- `pytest`
- `pytest-asyncio` (for async tests)

**Note:** `pytest-asyncio` is NOT currently in the project's test dependencies. Add it to the root `pyproject.toml` under `[dependency-groups]` -> `dev`:

```toml
[dependency-groups]
dev = [
    # ... existing deps ...
    "pytest-asyncio>=0.24.0",
]
```

### Test File Location

The context infrastructure tests should be placed in `src/madsci_client/tests/` rather than `src/madsci_common/tests/` because:
1. The tests import and use `EventClient` from `madsci_client`
2. Placing them in `madsci_common` would create a circular dependency
3. The existing `src/madsci_common/tests/test_context.py` tests the `MadsciContext` system, not `EventClientContext`

Create `src/madsci_client/tests/test_event_client_context.py` for Phase 1 tests.
