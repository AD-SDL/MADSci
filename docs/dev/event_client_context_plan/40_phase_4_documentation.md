# Phase 4: Documentation & Migration

**Estimated Effort:** Small (1-2 days)
**Breaking Changes:** None
**Prerequisites:** Phase 3 complete

## Goals

- Document the new context system
- Provide migration guide for existing code
- Update examples
- Add to developer guidelines

## 4.1 Documentation Tasks

### 4.1.1 Update Logging Guidelines

Update `docs/dev/logging_guidelines.md` to include context usage:

```markdown
## EventClient Context System

MADSci provides a hierarchical logging context system that automatically
propagates context through your code. This enables logs from related
operations to share common identifiers for easier debugging and analysis.

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

4. **Override `_get_component_context()` in custom components**
   ```python
   class MyComponent(MadsciClientMixin):
       def _get_component_context(self) -> dict[str, Any]:
           return {
               "component_type": "MyComponent",
               "component_id": self.id,
           }
   ```
```

### 4.1.2 Create API Reference

Add to docstrings (already done in implementation) and optionally generate API docs.

### 4.1.3 Update README Examples

Update relevant package READMEs to show context usage:

**madsci_client/README.md:**
```markdown
## Logging with Context

MADSci clients automatically participate in the logging context system:

```python
from madsci.common.context import event_client_context
from madsci.client.resource_client import ResourceClient

# All clients created within this context share logging context
with event_client_context(name="my_app", app_id="app-123"):
    resource_client = ResourceClient()
    resource_client.logger.info("Using resource client")
    # Log includes app_id="app-123"
```
```

### 4.1.4 Add to Configuration.md

Document any new configuration options related to context.

## 4.2 Migration Guide

### 4.2.1 Create Migration Document

Create `docs/dev/event_client_context_plan/migration_guide.md`:

```markdown
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
@click.command()
def my_command():
    logger = EventClient(name="my_command")
    logger.info("Running command")
    do_work()

# After
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
@app.post("/process")
async def process_endpoint(request: ProcessRequest):
    logger = EventClient(name="process_endpoint")
    logger.info("Processing")
    result = await do_processing(request)
    return result

# After (with middleware - see Phase 3)
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

## Troubleshooting

### Logs Missing Context

**Symptom:** Logs don't include expected context metadata.

**Cause:** Code is using `EventClient()` directly instead of `get_event_client()`.

**Fix:** Replace `EventClient()` with `get_event_client()`.

### Too Many Log Files

**Symptom:** Many separate log files being created.

**Cause:** Multiple `EventClient()` instances with different names.

**Fix:** Use context system to share single root client.

### Context Not Propagating to Async Code

**Symptom:** Async operations lose context.

**Cause:** This shouldn't happen with `contextvars`, but verify you're
using `await` properly (not `threading` or `multiprocessing`).

**Note:** Context does NOT propagate across process boundaries. For
multiprocessing, establish context in each subprocess.
```

## 4.3 Update Examples

### 4.3.1 Update Example Lab

Update example lab to demonstrate context usage:

```python
# example_lab/experiment.py
from madsci.common.context import event_client_context

def run_example_experiment():
    with event_client_context(
        name="example_experiment",
        experiment_type="demonstration",
    ) as logger:
        logger.info("Starting example experiment")

        # All clients and nested operations inherit this context
        run_workflow()

        logger.info("Example experiment complete")
```

## 4.4 Acceptance Criteria

- [ ] Logging guidelines updated with context documentation
- [ ] Migration guide created
- [ ] Package READMEs updated with context examples
- [ ] Example lab demonstrates context usage
- [ ] API docstrings complete and accurate
- [ ] Troubleshooting section covers common issues
- [ ] All documentation reviewed for accuracy

## 4.5 Future Considerations

Document these as potential future enhancements:

1. **Cross-process context propagation** via serialization
2. **OTEL span creation** option for full tracing
3. **Context visualization** in UI dashboard
4. **Context-based log filtering** in EventManager queries
5. **Automatic context from environment** (e.g., K8s pod info)
