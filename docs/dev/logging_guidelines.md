# MADSci Logging Guidelines

This document defines the preferred logging patterns for MADSci components.

## Principles

1. Use structured logging: put data in kwargs, not f-strings.
2. Set `event_type`: use the most specific `EventType` available.
3. Include context: include relevant IDs (workflow_id, node_id, resource_id, etc.).
4. Use `exc_info=True` on exception logs.
5. Avoid high-cardinality OTEL span attributes (ULIDs); log them to EventManager and rely on trace correlation.

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
