# Principles & Design Decisions

## Glossary

- **EventClient**: MADSci's structured logging and event handling class
- **Context**: Thread-local state that propagates through the call stack via `contextvars`
- **Hierarchy**: The naming chain representing nested components (e.g., `experiment.workflow.step`)
- **Bound Context**: Key-value pairs attached to all log messages from a client

## Design Decisions

### 1. Single Log File Per Process

Child contexts created via `bind()` share the parent's underlying logger infrastructure (file handlers, HTTP session, buffers). Only truly "root" EventClients create new log files.

**Rationale**:
- Reduces file handle usage
- Simplifies log aggregation
- Hierarchical context in each log line provides filtering capability via structlog/EventManager/OTEL

### 2. `get_event_client()` Always Works

`get_event_client()` will always return a usable EventClient, creating a new one if no context exists. This ensures backward compatibility and prevents runtime errors in code that doesn't explicitly establish context.

**Behavior**:
```python
def get_event_client(...) -> EventClient:
    ctx = _event_client_context.get()
    if ctx is not None:
        # Return from context (possibly with additional binding)
        return ctx.client.bind(**additional_context) if additional_context else ctx.client

    # No context - create new client (never fails)
    return EventClient(name=inferred_name, **config)
```

### 3. OTEL Integration: Attributes Only (Initially)

The hierarchy will be reflected in OTEL as span **attributes**, not as new spans per context level.

**Rationale**:
- Lightweight - no span creation overhead
- Still queryable in tracing backends
- Avoids very deep span hierarchies
- Works even without explicit OTEL span management

**Attributes Added**:
```python
event_dict["madsci.hierarchy"] = "experiment.workflow.step"
event_dict["madsci.experiment_id"] = "exp-123"
event_dict["madsci.workflow_id"] = "wf-456"
```

**Future Option**: Add `create_otel_span=True` parameter to `event_client_context()` for users who want full span hierarchy.

### 4. Async Compatibility

The `contextvars` module is already async-safe by design - it automatically propagates context across `await` boundaries. No additional async-specific implementation is required.

```python
async def process_samples():
    with event_client_context(name="processor") as logger:
        await some_async_operation()  # Context automatically propagates
        logger.info("Done")  # Still works
```

### 5. Integration with MadsciClientMixin

The existing `MadsciClientMixin` will be updated to be context-aware while maintaining backward compatibility:

1. If an explicit EventClient is injected, use it
2. If context exists, use context client with component-specific binding
3. Otherwise, create a new client (existing behavior)

This is the **resolution order** for `event_client` property:
```
1. Explicitly set client (_event_client)
2. Current context client + component binding
3. New client from config (legacy fallback)
```

### 6. Backward Compatibility

All existing code must continue to work without modification:

- Direct `EventClient()` instantiation continues to work
- Classes using `MadsciClientMixin` work unchanged
- New context-aware behavior is opt-in via `get_event_client()` and `event_client_context()`

### 7. No Deprecation Warnings (Initially)

Direct `EventClient()` instantiation will not produce deprecation warnings in the initial implementation. This may be reconsidered after the pattern is widely adopted.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Global/Thread Context                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ _event_client_context (ContextVar)                              ││
│  │   └── EventClientContext                                        ││
│  │         ├── client: EventClient (the actual logger)             ││
│  │         ├── hierarchy: ["experiment", "workflow", "step"]       ││
│  │         └── metadata: {experiment_id: "...", workflow_id: "..."}││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## Hierarchy Naming Conventions

The hierarchy names should follow these conventions for consistency:

### Naming Rules

1. **Use lowercase with underscores** for multi-word names: `my_experiment`, `data_transfer`
2. **Use dot separation** for hierarchy levels: `experiment.workflow.step`
3. **Prefix with category** for clarity: `step.transfer`, `action.grab`, `node.robot`
4. **Keep names short** but descriptive: prefer `transfer` over `transfer_samples_to_plate`

### Standard Hierarchy Patterns

| Level | Pattern | Example |
|-------|---------|---------|
| Experiment | `experiment` | `experiment` |
| Workflow | `experiment.workflow` | `experiment.workflow` |
| Step | `experiment.workflow.step.{name}` | `experiment.workflow.step.transfer` |
| Node (server-side) | `node.{node_name}` | `node.robot` |
| Action (server-side) | `node.{node_name}.action.{action}` | `node.robot.action.grab` |
| Manager | `manager.{manager_name}` | `manager.event_manager` |
| CLI Command | `cli.{command_name}` | `cli.run_workflow` |

### Component Context (via `_get_component_context()`)

Components add their own context as **metadata**, not hierarchy:
- `component_type`: Class name (e.g., `"RestNodeClient"`)
- `component_name`: Instance name if available
- `node_url`: For node clients
- `server_url`: For manager clients

## Log Output Comparison

### Before (Current)
```
[madsci.client.node.rest_node_client] Starting action
[madsci.client.node.rest_node_client] Action complete
[madsci.client.resource_client] Updating resource
[madsci.client.node.rest_node_client] Starting action
```

### After (With Context)
```
[experiment.workflow.step.transfer] Starting action | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1 component_type=RestNodeClient
[experiment.workflow.step.transfer] Action complete | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1 component_type=RestNodeClient
[experiment.workflow] Updating resource | experiment_id=exp-123 workflow_id=wf-456 component_type=ResourceClient
[experiment.workflow.step.analyze] Starting action | experiment_id=exp-123 workflow_id=wf-456 step_id=step-2 component_type=RestNodeClient
```

## Interaction with Existing MadsciContext

The `EventClientContext` is kept **separate** from the existing `MadsciContext` (which holds server URLs).

**Rationale**:
- `MadsciContext` is for configuration/URLs
- `EventClientContext` is for logging hierarchy
- Separation allows independent evolution
- No breaking changes to existing `MadsciContext` usage

**Coordination**:
```python
# Both contexts can be active simultaneously
with madsci_context(event_server_url=...):
    with event_client_context(name="myapp") as logger:
        # MadsciContext provides URLs
        # EventClientContext provides logging hierarchy
        pass
```

## File Locations

| Component | Location |
|-----------|----------|
| EventClientContext dataclass | `src/madsci_common/madsci/common/types/event_types.py` |
| Context functions | `src/madsci_common/madsci/common/context.py` |
| EventClient (existing) | `src/madsci_client/madsci/client/event_client.py` |
| MadsciClientMixin updates | `src/madsci_client/madsci/client/client_mixin.py` |
| RestNodeClient updates | `src/madsci_client/madsci/client/node/rest_node_client.py` |
| Phase 1 & 2 Tests | `src/madsci_client/tests/test_event_client_context.py` |
| Phase 2 Integration Tests | `src/madsci_client/tests/test_client_context_integration.py` |
| Existing MadsciContext tests | `src/madsci_common/tests/test_context.py` (separate, unchanged) |
