# Migration Guide: EventClient Context System

This guide helps you migrate existing code to use the new EventClient
context system for hierarchical logging.

## Overview

The context system is **fully backward compatible**. Your existing code
will continue to work without changes. This guide shows how to opt-in
to the new features.

## Migration Levels

### Level 0: No Changes Required

Your existing code continues to work:

```python
# Still works
logger = EventClient(name="my_module")
logger.info("Hello")
```

### Level 1: Use `get_event_client()` (Recommended)

Replace direct `EventClient()` instantiation:

```python
# Before
class MyComponent:
    def __init__(self):
        self.logger = EventClient()

# After
from madsci.common.context import get_event_client

class MyComponent:
    def __init__(self):
        self.logger = get_event_client()
```

**Benefits:**
- Automatically uses context when available
- Falls back to creating new client when not
- Reduces duplicate EventClient instantiation

### Level 2: Accept Optional EventClient Parameter

Allow client injection for flexibility:

```python
# Before
class MyComponent:
    def __init__(self):
        self.logger = EventClient()

# After
from madsci.common.context import get_event_client
from madsci.client.event_client import EventClient
from typing import Optional

class MyComponent:
    def __init__(self, event_client: Optional[EventClient] = None):
        self.logger = event_client or get_event_client()
```

**Benefits:**
- Explicit control when needed
- Easy testing with mock clients
- Context-aware by default

### Level 3: Establish Context at Entry Points

Wrap your main operations in context:

```python
# Before
def process_batch(batch_id: str):
    logger = EventClient(name="batch_processor")
    logger.info(f"Processing batch {batch_id}")
    for item in items:
        process_item(item)  # Each might create its own logger

# After
from madsci.common.context import event_client_context

def process_batch(batch_id: str):
    with event_client_context(name="batch", batch_id=batch_id) as logger:
        logger.info("Processing batch")
        for item in items:
            process_item(item)  # Inherits batch context
```

**Benefits:**
- All nested logs share `batch_id`
- Clear hierarchy in log output
- Easier debugging and log filtering

### Level 4: Add Component Context

For classes using `MadsciClientMixin`:

```python
# Before
class MyProcessor(MadsciClientMixin):
    REQUIRED_CLIENTS = ["event"]

# After
from typing import Any

class MyProcessor(MadsciClientMixin):
    REQUIRED_CLIENTS = ["event"]

    def __init__(self, processor_id: str):
        self.processor_id = processor_id

    def _get_component_context(self) -> dict[str, Any]:
        return {
            **super()._get_component_context(),
            "processor_id": self.processor_id,
        }
```

**Benefits:**
- Component-specific context in all logs
- Automatic identification in shared context

## Common Migration Patterns

### Pattern: CLI Command

```python
# Before
import click
from madsci.client.event_client import EventClient

@click.command()
def my_command():
    logger = EventClient(name="my_command")
    logger.info("Running command")
    do_work()

# After
import click
from madsci.common.context import event_client_context

@click.command()
def my_command():
    with event_client_context(name="cli.my_command") as logger:
        logger.info("Running command")
        do_work()  # Inherits context
```

### Pattern: API Endpoint

```python
# Before
from fastapi import FastAPI
from madsci.client.event_client import EventClient

app = FastAPI()

@app.post("/process")
async def process_endpoint(request: ProcessRequest):
    logger = EventClient(name="process_endpoint")
    logger.info("Processing")
    result = await do_processing(request)
    return result

# After (with middleware - automatically configured in managers)
from madsci.common.context import get_event_client

@app.post("/process")
async def process_endpoint(request: ProcessRequest):
    logger = get_event_client()  # Uses middleware context
    logger.info("Processing")
    result = await do_processing(request)
    return result
```

### Pattern: Background Task

```python
# Before
from madsci.client.event_client import EventClient

def background_task(task_id: str):
    logger = EventClient(name="background_task")
    logger.info(f"Task {task_id} starting")
    do_work()

# After
from madsci.common.context import event_client_context

def background_task(task_id: str):
    with event_client_context(name="background_task", task_id=task_id) as logger:
        logger.info("Task starting")
        do_work()  # Inherits task context
```

### Pattern: Experiment Application

```python
# Before
from madsci.experiment_application import ExperimentApplication

class MyExperiment(ExperimentApplication):
    def run_experiment(self):
        # Context is automatically established by ExperimentApplication
        self.event_client.info("Running experiment")

        # But nested operations might not share context
        result = self.process_samples()
        return result

# After
from madsci.experiment_application import ExperimentApplication
from madsci.common.context import event_client_context, get_event_client

class MyExperiment(ExperimentApplication):
    def run_experiment(self):
        # ExperimentApplication already establishes context!
        # Just use get_event_client() in nested operations
        self.event_client.info("Running experiment")

        # Create nested context for major operations
        with event_client_context(name="sample_processing", sample_count=10):
            result = self.process_samples()
        return result
```

### Pattern: Workflow Script

```python
# Before
from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient

# Each client creates its own EventClient
workcell = WorkcellClient()
resource = ResourceClient()

# No shared context between these clients
workcell.start_workflow("my_workflow.yaml")

# After
from madsci.common.context import event_client_context
from madsci.client.workcell_client import WorkcellClient
from madsci.client.resource_client import ResourceClient

with event_client_context(name="my_script", script_name="transfer_samples") as logger:
    logger.info("Starting script")

    # All clients now share the script context
    workcell = WorkcellClient()
    resource = ResourceClient()

    # Logs from both clients will include script context
    workcell.start_workflow("my_workflow.yaml")
```

## Testing with Context

### Mocking in Tests

```python
from unittest.mock import Mock
from madsci.common.context import event_client_context

def test_my_component():
    mock_client = Mock()

    with event_client_context(client=mock_client):
        component = MyComponent()  # Uses mock client
        component.do_something()

    mock_client.info.assert_called()
```

### Verifying Context in Tests

```python
from madsci.common.context import event_client_context, get_event_client_context

def test_context_propagation():
    with event_client_context(name="test", test_id="t-123"):
        ctx = get_event_client_context()

        assert ctx.metadata["test_id"] == "t-123"
        assert "test" in ctx.name
```

### Testing Context Isolation

```python
import pytest
import asyncio
from madsci.common.context import event_client_context, get_event_client

@pytest.mark.asyncio
async def test_concurrent_contexts_isolated():
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
```

## Troubleshooting

### Logs Missing Context

**Symptom:** Logs don't include expected context metadata.

**Cause:** Code is using `EventClient()` directly instead of `get_event_client()`.

**Fix:** Replace `EventClient()` with `get_event_client()`.

```python
# Before (doesn't use context)
logger = EventClient()

# After (uses context)
from madsci.common.context import get_event_client
logger = get_event_client()
```

### Too Many Log Files

**Symptom:** Many separate log files being created.

**Cause:** Multiple `EventClient()` instances with different names.

**Fix:** Use context system to share single root client.

```python
# Establish context once at entry point
with event_client_context(name="my_app") as logger:
    # All components within this context share the same underlying logger
    run_operations()
```

### Context Not Propagating to Async Code

**Symptom:** Async operations lose context.

**Cause:** This shouldn't happen with `contextvars`, but verify you're
using `await` properly (not `threading` or `multiprocessing`).

**Note:** Context does NOT propagate across process boundaries. For
multiprocessing, establish context in each subprocess:

```python
import multiprocessing
from madsci.common.context import event_client_context

def worker_process(task_id: str):
    # Must establish context within each process
    with event_client_context(name="worker", task_id=task_id) as logger:
        logger.info("Worker starting")
        do_work()

if __name__ == "__main__":
    with multiprocessing.Pool(4) as pool:
        pool.map(worker_process, ["task1", "task2", "task3", "task4"])
```

### Context Lost After Exception

**Symptom:** After an exception, subsequent code loses context.

**Cause:** Exception caused premature exit from context manager.

**Fix:** Use proper exception handling:

```python
from madsci.common.context import event_client_context

with event_client_context(name="operation", op_id="123") as logger:
    try:
        risky_operation()
    except Exception as e:
        logger.exception("Operation failed")  # Still has context
        # Handle or re-raise
```

## API Reference

### `get_event_client()`

```python
def get_event_client(
    name: Optional[str] = None,
    create_if_missing: bool = True,
    **context_kwargs: Any,
) -> EventClient:
    """
    Get the current EventClient from context, or create one if none exists.

    Args:
        name: Optional name override (used when creating new client)
        create_if_missing: If False, raises RuntimeError when no context
        **context_kwargs: Additional context to bind to the returned client

    Returns:
        EventClient with inherited context
    """
```

### `event_client_context()`

```python
@contextlib.contextmanager
def event_client_context(
    name: Optional[str] = None,
    client: Optional[EventClient] = None,
    inherit: bool = True,
    **context_metadata: Any,
) -> Generator[EventClient, None, None]:
    """
    Establish or extend an EventClient context.

    Args:
        name: Name for this context level (added to hierarchy)
        client: Explicit EventClient to use
        inherit: If True, inherit parent context; if False, create fresh
        **context_metadata: Additional context to bind to all logs

    Yields:
        EventClient for this context
    """
```

### `has_event_client_context()`

```python
def has_event_client_context() -> bool:
    """Check if an EventClient context is currently active."""
```

### `get_event_client_context()`

```python
def get_event_client_context() -> Optional[EventClientContext]:
    """Get the current EventClientContext, if any."""
```

## Future Considerations

The following enhancements may be added in future releases:

1. **Cross-process context propagation** via serialization
2. **OTEL span creation** option for full tracing integration
3. **Context visualization** in UI dashboard
4. **Context-based log filtering** in EventManager queries
5. **Automatic context from environment** (e.g., K8s pod info)
