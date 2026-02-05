# Phase 3: Logging Audit and EventType Enhancement

**Estimated Effort:** Large (5-7 days)
**Breaking Changes:** Minor (new EventType values, improved logging)

## Goals

- Audit all EventClient usage across the codebase
- Ensure proper `event_type` is set for all significant operations
- Expand EventType enum to cover all operational scenarios
- Standardize logging patterns across components

## Progress (February 2026)

Completed in this iteration (Phase 3A, scoped):

- Added Phase 3A MVP `EventType` values in `src/madsci_common/madsci/common/types/event_types.py`.
- Added `EVENT_TYPE_DESCRIPTIONS` mapping (code-governed documentation) and tests in
  `src/madsci_common/tests/test_event_types_phase3.py`.
- Added logging guidelines in `docs/dev/logging_guidelines.md`.
- Added a repo-local pre-commit hook for structured logging patterns (`scripts/precommit_check_logging_patterns.py`).
- Tightened hook scope to a small set of audited “system components” so we can ratchet over time.

Audited/cleaned (passes the logging-pattern hook):

- `src/madsci_common/madsci/common/manager_base.py`
- `src/madsci_common/madsci/common/types/event_types.py`
- `src/madsci_event_manager/madsci/event_manager/event_server.py`
- `src/madsci_event_manager/madsci/event_manager/notifications.py`
- `src/madsci_resource_manager/madsci/resource_manager/resource_server.py`
- `src/madsci_location_manager/madsci/location_manager/location_server.py`
- `src/madsci_location_manager/madsci/location_manager/transfer_planner.py`
- `src/madsci_data_manager/madsci/data_manager/data_server.py`
- `src/madsci_experiment_manager/madsci/experiment_manager/experiment_server.py`
- `src/madsci_squid/madsci/squid/lab_server.py`
- `src/madsci_squid/madsci/squid/__init__.py`
- `src/madsci_event_manager/madsci/event_manager/utilization_analyzer.py`
- `src/madsci_event_manager/madsci/event_manager/time_series_analyzer.py`
- `src/madsci_workcell_manager/madsci/workcell_manager/workcell_engine.py`
- `src/madsci_workcell_manager/madsci/workcell_manager/workcell_server.py`
- `src/madsci_node_module/madsci/node_module/abstract_node_module.py`
- `src/madsci_node_module/madsci/node_module/__init__.py`
- `src/madsci_node_module/madsci/node_module/helpers.py`
- `src/madsci_node_module/madsci/node_module/rest_node_module.py`
- `src/madsci_node_module/madsci/node_module/type_analyzer.py`

Additional updates in February 2026 (now audited and included in the hook scope):

- `src/madsci_client/madsci/client/client_mixin.py`
- `src/madsci_experiment_application/madsci/experiment_application/experiment_application.py`
- `src/madsci_client/madsci/client/location_client.py`
- `src/madsci_resource_manager/madsci/resource_manager/migration_tool.py`
- `src/madsci_experiment_manager/madsci/experiment_manager/experiment_server.py`

Additional updates in February 2026 (this change):

- Added `src/madsci_common/madsci/common/backup_tools/backup_manager.py` to the `madsci-logging-patterns` pre-commit hook scope.
- Audited and updated BackupManager logging to avoid f-strings and to include `event_type` for all EventClient log calls (using `EventType.LOG_*`).

Additional updates in February 2026 (logging-audit ratchet):

- Added `src/madsci_event_manager/madsci/event_manager/events_csv_exporter.py` to the `madsci-logging-patterns` pre-commit hook scope.
- Audited CSVExporter logging to ensure structured logging (no f-strings) and `event_type` on EventClient-style log calls.

Notes:

- This Phase 3 doc previously listed some of these files as deferred; they are now included above under
  audited/cleaned or additional updates.

Operational notes:

- Ruff linting remains enabled; scripts under `scripts/` are permitted to use `print`.
- Type checking is disabled via `pyrightconfig.json` to reduce editor noise while this work is in flux.

## 3.0 EventType Emission Mapping (Normative)

To reduce duplicate events and keep EventType usage consistent, use the
following ownership rules:

- Manager lifecycle (process/service): `MANAGER_START`, `MANAGER_STOP`,
  `MANAGER_ERROR`, `MANAGER_HEALTH_CHECK` are emitted by managers.
- Workflow lifecycle + steps: `WORKFLOW_*` and `WORKFLOW_STEP_*` are emitted by
  the workflow/workcell execution layer.
- Node lifecycle and node action execution: `NODE_*` and `NODE_ACTION_*` are
  emitted by the node module layer (and/or the node client boundary when that
  is where execution is coordinated).
- Resource/location/data domain events: `RESOURCE_*`, `LOCATION_*`,
  `ATTACHMENT_*`, `DATA_*` are emitted by the manager that owns that domain.

Guideline:

- If multiple layers want visibility into the same operation, prefer having the
  higher layer emit one high-level event, and rely on trace correlation (trace_id
  + span_id) plus structured fields for drill-down, rather than duplicating the
  same EventType at multiple layers.

## 3.1 EventType Gap Analysis

### Current EventTypes (from `event_types.py`)

```python
# Generic
UNKNOWN, TEST

# Log Events
LOG, LOG_DEBUG, LOG_INFO, LOG_WARNING, LOG_ERROR, LOG_CRITICAL

# Lab Events
LAB_CREATE, LAB_START, LAB_STOP

# Node Events
NODE_CREATE, NODE_START, NODE_STOP, NODE_CONFIG_UPDATE, NODE_STATUS_UPDATE, NODE_ERROR

# Workcell Events
WORKCELL_CREATE, WORKCELL_START, WORKCELL_STOP, WORKCELL_CONFIG_UPDATE, WORKCELL_STATUS_UPDATE

# Workflow Events
WORKFLOW_CREATE, WORKFLOW_START, WORKFLOW_COMPLETE, WORKFLOW_ABORT

# Experiment Events
EXPERIMENT_CREATE, EXPERIMENT_START, EXPERIMENT_COMPLETE, EXPERIMENT_FAILED,
EXPERIMENT_CANCELLED, EXPERIMENT_PAUSE, EXPERIMENT_CONTINUED

# Campaign Events
CAMPAIGN_CREATE, CAMPAIGN_START, CAMPAIGN_COMPLETE, CAMPAIGN_ABORT

# Action Events
ACTION_STATUS_CHANGE
```

### Proposed New EventTypes

```python
class EventType(str, Enum):
    # ... existing types ...

    # Resource Events (NEW)
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    RESOURCE_ALLOCATE = "resource_allocate"
    RESOURCE_RELEASE = "resource_release"
    RESOURCE_TRANSFER = "resource_transfer"
    RESOURCE_CONSUME = "resource_consume"

    # Location Events (NEW)
    LOCATION_CREATE = "location_create"
    LOCATION_UPDATE = "location_update"
    LOCATION_DELETE = "location_delete"
    ATTACHMENT_CREATE = "attachment_create"
    ATTACHMENT_UPDATE = "attachment_update"
    ATTACHMENT_DELETE = "attachment_delete"

    # Data Events (NEW)
    DATA_CAPTURE = "data_capture"
    DATA_STORE = "data_store"
    DATA_QUERY = "data_query"
    DATA_EXPORT = "data_export"
    DATA_DELETE = "data_delete"

    # Manager Lifecycle Events (NEW)
    MANAGER_START = "manager_start"
    MANAGER_STOP = "manager_stop"
    MANAGER_ERROR = "manager_error"
    MANAGER_HEALTH_CHECK = "manager_health_check"

    # Workflow Step Events (NEW)
    WORKFLOW_STEP_START = "workflow_step_start"
    WORKFLOW_STEP_COMPLETE = "workflow_step_complete"
    WORKFLOW_STEP_FAILED = "workflow_step_failed"
    WORKFLOW_STEP_RETRY = "workflow_step_retry"

    # Action Events (EXPANDED)
    ACTION_START = "action_start"
    ACTION_COMPLETE = "action_complete"
    ACTION_FAILED = "action_failed"
    ACTION_RETRY = "action_retry"
    ACTION_TIMEOUT = "action_timeout"

    # Node Action Events (NEW)
    NODE_ACTION_START = "node_action_start"
    NODE_ACTION_COMPLETE = "node_action_complete"
    NODE_ACTION_FAILED = "node_action_failed"

    # Alert Events (NEW)
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"

    # System Events (NEW)
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
```

## 3.1.1 Staged Rollout (Recommended)

To reduce churn and keep Phase 3 deliverable-sized, roll out EventType additions in two passes.

Phase 3A (MVP EventTypes):

- Resource events: `RESOURCE_CREATE`, `RESOURCE_UPDATE`, `RESOURCE_DELETE`, `RESOURCE_ALLOCATE`, `RESOURCE_RELEASE`
- Location events: `LOCATION_CREATE`, `LOCATION_UPDATE`, `LOCATION_DELETE`, `ATTACHMENT_CREATE`, `ATTACHMENT_DELETE`
- Data events: `DATA_STORE`, `DATA_QUERY`, `DATA_EXPORT`
- Manager lifecycle: `MANAGER_START`, `MANAGER_STOP`, `MANAGER_ERROR`, `MANAGER_HEALTH_CHECK`
- Workflow step events: `WORKFLOW_STEP_START`, `WORKFLOW_STEP_COMPLETE`, `WORKFLOW_STEP_FAILED`
- Action events (minimal): `ACTION_START`, `ACTION_COMPLETE`, `ACTION_FAILED`

Phase 3B (Follow-up / nice-to-have):

- Remaining/expanded types (retries, timeouts, alerts, system startup/shutdown, backup create/restore, consume/transfer,
  node-action specific types if they prove valuable beyond ACTION_*).

Guideline:

- Prefer adding an EventType only when there is code ready to emit it consistently and tests/docs can cover it.

## 3.2 Logging Audit Checklist

For each component, verify:

| Component | File(s) | Audit Items |
|-----------|---------|-------------|
| AbstractNodeModule | `abstract_node_module.py` | Action start/complete, state changes, errors |
| WorkcellEngine | `workcell_engine.py` | Workflow lifecycle, step execution, scheduling |
| EventManager | `event_server.py` | Event receipt, archival, backup |
| ExperimentManager | `experiment_server.py` | Experiment lifecycle, campaign management |
| ResourceManager | `resource_server.py` | Resource CRUD, allocation, transfers |
| DataManager | `data_server.py` | Data capture, storage, queries |
| LocationManager | `location_server.py` | Location/attachment CRUD |
| LabManager (Squid) | `lab_server.py` | Lab lifecycle, manager health |
| MadsciClientMixin | `client_mixin.py` | Client initialization |

## 3.3 Test Specifications

Create `src/madsci_common/tests/test_event_type_coverage.py`:

```python
class TestEventTypeCoverage:
    """Test that EventTypes are used correctly throughout the codebase."""

    def test_all_event_types_documented(self):
        """Test that all EventType values have descriptions."""
        for event_type in EventType:
            assert event_type.value  # Has a value
            # Could also check docstrings or metadata

    def test_node_operations_use_node_event_types(self):
        """Test that node operations emit NODE_* event types."""

    def test_workflow_operations_use_workflow_event_types(self):
        """Test that workflow operations emit WORKFLOW_* event types."""

    def test_resource_operations_use_resource_event_types(self):
        """Test that resource operations emit RESOURCE_* event types."""


class TestLoggingPatterns:
    """Test consistent logging patterns across components."""

    def test_error_logging_includes_exception_info(self):
        """Test that error logs include exception information."""

    def test_operation_logging_includes_context(self):
        """Test that operation logs include relevant context (IDs, status)."""

    def test_structured_data_used_not_string_formatting(self):
        """Test that logs use structured kwargs, not f-strings for data."""
```

## 3.4 Implementation Tasks

### 3.4.1 Add New EventTypes

Update `src/madsci_common/madsci/common/types/event_types.py`:

```python
class EventType(str, Enum):
    """Event types for categorizing and querying events.

    Events should use the most specific type available. The LOG_* types
    are for general logging; prefer domain-specific types when applicable.
    """

    # ... add all new event types as specified above ...
```

### 3.4.2 Create Logging Guidelines Document

Create `docs/dev/logging_guidelines.md`:

```markdown
# MADSci Logging Guidelines

## Principles

1. **Use structured logging**: Pass data as kwargs, not in the message string
2. **Set event_type**: Always use the most specific EventType for the operation
3. **Include context**: Include relevant IDs (workflow_id, resource_id, etc.)
4. **Log at appropriate levels**: DEBUG for details, INFO for operations, WARNING for issues, ERROR for failures

## Examples

### Good

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

### Bad

```python
self.event_client.info(f"Workflow {workflow.workflow_id} step {step_index} completed in {elapsed_ms}ms")
```
```

### 3.4.3 Update Components to Use Correct EventTypes

Example updates for each component:

**WorkcellEngine** (`workcell_engine.py`):

```python
# Before
self.logger.info(f"Starting workflow {workflow.name}")

# After
self.logger.info(
    "Starting workflow",
    event_type=EventType.WORKFLOW_START,
    workflow_id=workflow.workflow_id,
    workflow_name=workflow.name,
    step_count=len(workflow.steps),
)
```

**ResourceManager** (`resource_server.py`):

```python
# Before
self.event_client.info(f"Created resource {resource.resource_id}")

# After
self.event_client.info(
    "Resource created",
    event_type=EventType.RESOURCE_CREATE,
    resource_id=resource.resource_id,
    resource_type=resource.resource_type,
    location_id=resource.location_id,
)
```

## 3.5 Logging Pattern Updates

For each component, ensure logging follows this pattern:

```python
# Operation start
self.event_client.info(
    "Operation starting",
    event_type=EventType.<OPERATION>_START,
    <entity>_id=entity.id,
    # ... other relevant context
)

try:
    result = perform_operation()

    # Operation success
    self.event_client.info(
        "Operation completed",
        event_type=EventType.<OPERATION>_COMPLETE,
        <entity>_id=entity.id,
        result_status=result.status,
        duration_ms=elapsed,
    )
except Exception as e:
    # Operation failure
    self.event_client.error(
        "Operation failed",
        event_type=EventType.<OPERATION>_FAILED,
        <entity>_id=entity.id,
        error=str(e),
        exc_info=True,
    )
    raise
```

## 3.7 Log Correlation (Structlog)

Goal: make it easy to correlate logs/events with traces.

- When OTEL is enabled, ensure structlog includes `trace_id` and `span_id` (via OTEL processors).
- When OTEL is disabled, keep these fields absent or set to `None` (avoid misleading values).

MADSci must have a single OTEL-aware trace context helper in `madsci.common.otel` (e.g., `current_trace_context()`).
Use this (or an OTEL-aware structlog processor) consistently rather than re-implementing ID extraction in multiple
places.

## 3.8 Metrics Cardinality Guidelines

Metric attributes/labels must be low-cardinality and bounded. In particular:

- Prefer `event.type` values that come from `EventType` (bounded enum).
- Do not label metrics with ULIDs, `workflow_id`, `resource_id`, `experiment_id`, or similar identifiers.
- For debugging drill-down, use trace attributes sparingly and only when sampling/cost is understood.

## 3.6 Acceptance Criteria

- [ ] Phase 3A (MVP) EventTypes added to enum
- [ ] Phase 3B (follow-up) EventTypes tracked as a separate task/phase if still desired
- [ ] Each EventType has clear documentation
- [ ] All components audited for logging patterns
- [ ] Logging guidelines document created
- [ ] All operations use appropriate EventType
- [ ] Structured logging used consistently (no f-string data embedding)
- [ ] Context IDs included in all operation logs
- [ ] Tests verify EventType coverage
