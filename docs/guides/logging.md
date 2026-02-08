# Logging and Event Context

This guide covers MADSci's structured logging system and the EventClient context system for hierarchical logging.

## Overview

MADSci uses the `EventClient` class for structured logging throughout the system. The EventClient:

- Logs events locally to files with rotation
- Sends events to the EventManager for centralized storage and querying
- Integrates with OpenTelemetry for distributed tracing
- Supports hierarchical context propagation

## Logging Principles

1. **Use structured logging**: Put data in kwargs, not f-strings
2. **Set `event_type`**: Use the most specific `EventType` available
3. **Include context**: Include relevant IDs (workflow_id, node_id, resource_id, etc.)
4. **Use `exc_info=True`** on exception logs
5. **Use the context system** for hierarchical logging across components

## Examples

### Good: Structured Logging

```python
self.event_client.info(
    "Workflow step completed",
    event_type=EventType.WORKFLOW_STEP_COMPLETE,
    workflow_id=workflow.workflow_id,
    step_index=step_index,
    step_action=step.action,
    duration_ms=elapsed_ms,
)
```

### Bad: F-String Formatting

```python
# Don't do this - data is not queryable
self.event_client.info(
    f"Workflow {workflow.workflow_id} step {step_index} completed in {elapsed_ms}ms"
)
```

## EventType Ownership

| Category | EventTypes | Emitted By |
|----------|------------|------------|
| Manager lifecycle | `MANAGER_*` | Manager services |
| Workflow lifecycle | `WORKFLOW_*`, `WORKFLOW_STEP_*` | Workcell/workflow execution layer |
| Node operations | `NODE_*`, `ACTION_*` | Node module layer |
| Domain events | `RESOURCE_*`, `LOCATION_*`, `DATA_*` | Respective managers |

---

## EventClient Context System

MADSci provides a hierarchical logging context system that automatically propagates context through your code. This enables logs from related operations to share common identifiers for easier debugging and analysis.

### Basic Usage

```python
from madsci.common.context import get_event_client, event_client_context

# Get a logger (uses context if available, creates new if not)
logger = get_event_client()
logger.info("Processing request")

# Establish context at entry points
with event_client_context(name="my_operation", operation_id="op-123") as logger:
    logger.info("Starting operation")
    # All logs within this block include operation_id

    # Nested context adds more metadata
    with event_client_context(name="substep", substep_id="sub-456") as step_logger:
        step_logger.info("Executing substep")
        # Logs include both operation_id and substep_id
```

### When to Use Context

**Establish context at:**
- Application entry points (main functions, CLI commands)
- Experiment runs
- Workflow executions
- Request handlers (via middleware)
- Long-running operations

**Use `get_event_client()` in:**
- Library code
- Utility functions
- Classes that may be used in different contexts
- Any code that should inherit parent context

### Best Practices

1. **Prefer `get_event_client()` over `EventClient()`**
   ```python
   # Good - participates in context
   logger = get_event_client()

   # Legacy - creates isolated client
   logger = EventClient()
   ```

2. **Add meaningful context metadata**
   ```python
   with event_client_context(
       name="workflow",
       workflow_id=workflow.id,
       workflow_name=workflow.name,
       user_id=user.id,
   ):
       # All nested logs include this context
   ```

3. **Use descriptive hierarchy names**
   ```python
   # Good - clear hierarchy
   "experiment.workflow.step.action"

   # Avoid - too generic
   "process.subprocess.task"
   ```

### Context Hierarchy Patterns

| Level | Pattern | Example |
|-------|---------|---------|
| Experiment | `experiment` | `experiment` |
| Workflow | `experiment.workflow` | `experiment.workflow` |
| Step | `experiment.workflow.step.{name}` | `experiment.workflow.step.transfer` |
| Node (server-side) | `node.{node_name}` | `node.robot` |
| Action (server-side) | `node.{node_name}.action.{action}` | `node.robot.action.grab` |
| Manager | `manager.{manager_name}` | `manager.event_manager` |
| CLI Command | `cli.{command_name}` | `cli.run_workflow` |

### Log Output Comparison

**Before (Without Context):**
```
[madsci.client.node.rest_node_client] Starting action
[madsci.client.node.rest_node_client] Action complete
[madsci.client.resource_client] Updating resource
```

**After (With Context):**
```
[experiment.workflow.step.transfer] Starting action | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1
[experiment.workflow.step.transfer] Action complete | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1
[experiment.workflow] Updating resource | experiment_id=exp-123 workflow_id=wf-456
```

---

## Migration Guide

The context system is **fully backward compatible**. Your existing code will continue to work without changes.

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

### Level 2: Establish Context at Entry Points

Wrap your main operations in context:

```python
# Before
def process_batch(batch_id: str):
    logger = EventClient(name="batch_processor")
    logger.info(f"Processing batch {batch_id}")
    for item in items:
        process_item(item)

# After
from madsci.common.context import event_client_context

def process_batch(batch_id: str):
    with event_client_context(name="batch", batch_id=batch_id) as logger:
        logger.info("Processing batch")
        for item in items:
            process_item(item)  # Inherits batch context
```

### Common Patterns

#### CLI Command

```python
import click
from madsci.common.context import event_client_context

@click.command()
def my_command():
    with event_client_context(name="cli.my_command") as logger:
        logger.info("Running command")
        do_work()  # Inherits context
```

#### Workflow Script

```python
from madsci.common.context import event_client_context
from madsci.client.workcell_client import WorkcellClient

with event_client_context(name="my_script", script_name="transfer_samples") as logger:
    logger.info("Starting script")

    # All clients now share the script context
    workcell = WorkcellClient()
    workcell.start_workflow("my_workflow.yaml")
```

---

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

---

## Troubleshooting

### Logs Missing Context

**Symptom:** Logs don't include expected context metadata.

**Cause:** Code is using `EventClient()` directly instead of `get_event_client()`.

**Fix:** Replace `EventClient()` with `get_event_client()`.

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

### Context Not Propagating to Threads

**Note:** Context propagates automatically with `async/await` but does NOT propagate across thread or process boundaries. For threading or multiprocessing, establish context in each thread/process:

```python
import multiprocessing
from madsci.common.context import event_client_context

def worker_process(task_id: str):
    # Must establish context within each process
    with event_client_context(name="worker", task_id=task_id) as logger:
        logger.info("Worker starting")
        do_work()
```

---

## Context Decorators

For cleaner code, use decorators instead of context managers:

### `@with_event_client`

Wrap functions with EventClient context:

```python
from madsci.common.context import with_event_client

@with_event_client(name="my_workflow", workflow_id="wf-123")
def my_workflow(event_client=None):
    event_client.info("Running workflow")
    do_work()

# Called normally - context is established automatically
my_workflow()
```

### `@event_client_class`

Wrap all methods of a class with context:

```python
from madsci.common.context import event_client_class

@event_client_class(component_type="processor")
class DataProcessor:
    def process(self, data):
        # self.event_client is available in all methods
        self.event_client.info("Processing data", data_size=len(data))
        return transform(data)

    def get_context_overrides(self) -> dict:
        # Optional: provide instance-specific context
        return {"processor_id": self.id}
```

---

## OpenTelemetry Integration

When OpenTelemetry is enabled, logs are automatically correlated with distributed traces.

### Configuration

Enable OTEL per-manager or per-EventClient:

```python
from madsci.client.event_client import EventClient, EventClientConfig

config = EventClientConfig(
    otel_enabled=True,
    otel_service_name="my_service",
    otel_exporter="otlp",
    otel_endpoint="http://localhost:4317",
    otel_protocol="grpc",
)
client = EventClient(name="traced_component", config=config)
```

Or via environment variables:
```bash
EVENT_OTEL_ENABLED=true
EVENT_OTEL_SERVICE_NAME="madsci.event"
EVENT_OTEL_EXPORTER="otlp"
EVENT_OTEL_ENDPOINT="http://localhost:4317"
```

### Automatic Trace Context

With OTEL enabled, events automatically include:
- `trace_id`: W3C trace identifier
- `span_id`: Current span identifier
- `parent_span_id`: Parent span identifier (if available)

This enables:
- Clicking on a trace ID in logs to jump to the full trace in Jaeger
- Seeing which logs were generated during a specific request
- Understanding the full flow of a workflow across all managers

### Tracing Decorators

For explicit span creation:

```python
from madsci.common.otel import span_context, with_span

# Context manager
with span_context("process_data", attributes={"data.size": 100}) as span:
    result = process(data)
    span.set_attribute("result.count", len(result))

# Decorator
@with_span(name="fetch_user")
def get_user(user_id: str):
    return api.fetch(user_id)
```

See [OBSERVABILITY.md](../../example_lab/OBSERVABILITY.md) for the full observability stack setup.
