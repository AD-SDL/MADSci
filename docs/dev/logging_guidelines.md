# MADSci Logging Guidelines

This document defines the preferred logging patterns for MADSci components.

## Principles

1. Use structured logging: put data in kwargs, not f-strings.
2. Set `event_type`: use the most specific `EventType` available.
3. Include context: include relevant IDs (workflow_id, node_id, resource_id, etc.).
4. Use `exc_info=True` on exception logs.
5. Avoid high-cardinality OTEL span attributes (ULIDs); log them to EventManager and rely on trace correlation.
6. Use the EventClient context system for hierarchical logging across components.

## Examples

Good:

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

Bad:

```python
self.event_client.info(
    f"Workflow {workflow.workflow_id} step {step_index} completed in {elapsed_ms}ms"
)
```

## Recommended EventType Ownership

- Manager lifecycle (process/service): `MANAGER_*` emitted by managers.
- Workflow lifecycle + steps: `WORKFLOW_*` and `WORKFLOW_STEP_*` emitted by the workcell/workflow execution layer.
- Node lifecycle and node action execution: `NODE_*` and `ACTION_*` emitted by the node module layer.
- Resource/location/data domain events: emitted by the manager owning that domain.

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

### Context Hierarchy Patterns

The following patterns show standard hierarchy naming conventions:

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

### For More Information

See the [Migration Guide](./event_client_context_plan/migration_guide.md) for detailed migration patterns and examples.
