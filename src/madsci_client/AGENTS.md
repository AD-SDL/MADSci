# MADSci Client Package

## Overview
The `madsci_client` package provides client libraries for interacting with all MADSci manager services. It offers programmatic access to the Event Manager, Experiment Manager, Resource Manager, Data Manager, Workcell Manager, and Location Manager.

## Key Components
- **Client Classes**: Each manager has a corresponding client class (e.g., `EventClient`, `ExperimentClient`)
- **Node Clients**: Abstract and REST-based node client implementations for instrument communication
- **Type Safety**: Full type hints and Pydantic model integration for all client methods
- **Context Integration**: All clients participate in the hierarchical logging context system

## Client Pattern
All clients follow a consistent pattern:
- Synchronous operations with result polling support for long-running tasks
- Automatic request/response serialization using Pydantic models
- Built-in error handling with MADSci exception types
- Health check and service discovery capabilities
- Integration with EventClient context for hierarchical logging

## EventClient and Logging

The `EventClient` provides structured logging with context management:

```python
from madsci.client.event_client import EventClient
from madsci.common.context import event_client_context, get_event_client

# Direct instantiation
client = EventClient(name="my_component")
client.info("Structured message", key="value", count=42)

# Context-based usage (recommended for applications)
with event_client_context(name="my_app", app_id="app-123") as logger:
    logger.info("Starting application")
    # All nested code inherits this context

# In library code, use get_event_client()
def utility_function():
    logger = get_event_client()  # Inherits context if available
    logger.info("Utility running")
```

### Context Binding
```python
# Bind metadata for a scope of operations
client = client.bind(experiment_id="exp-123")
client.info("Logs include experiment_id")
client = client.unbind("experiment_id")  # Remove binding
```

### OpenTelemetry Integration
```python
from madsci.client.event_client import EventClient, EventClientConfig

config = EventClientConfig(
    otel_enabled=True,
    otel_service_name="my_service",
    otel_exporter="otlp",
    otel_endpoint="http://localhost:4317",
)
client = EventClient(name="traced", config=config)
# Events automatically include trace_id, span_id
```

## Usage Examples
```python
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.common.context import event_client_context

# Context-aware application pattern
with event_client_context(name="my_script") as logger:
    logger.info("Starting script")

    # Clients inherit context
    experiment_client = ExperimentClient(base_url="http://localhost:8002")
    experiments = experiment_client.list_experiments()
```

## Testing
- Unit tests focus on client method behavior and serialization
- Integration tests require running manager services
- Mock responses are provided for offline testing
- Context tests verify hierarchical logging propagation

## Development Patterns

### Structured Logging Best Practices
```python
# Good: Structured logging with kwargs
logger.info(
    "Workflow completed",
    event_type=EventType.WORKFLOW_COMPLETE,
    workflow_id=workflow_id,
    duration_ms=elapsed,
)

# Bad: F-string formatting (data not queryable)
logger.info(f"Workflow {workflow_id} completed in {elapsed}ms")
```

### Prefer get_event_client() in Library Code
```python
# Good: Participates in context
logger = get_event_client()

# Legacy: Creates isolated client
logger = EventClient()
```

## Service Communication Requirements

**All HTTP communication with MADSci services MUST go through client classes.** Direct httpx/requests calls in UI/CLI code are prohibited.

### Available Clients

| Client | Service | Async Methods |
|--------|---------|---------------|
| `EventClient` | Event Manager (8001) | `async_get_events`, `async_get_event`, `async_query_events` |
| `ExperimentClient` | Experiment Manager (8002) | `async_get_experiments`, `async_pause_experiment`, `async_cancel_experiment` |
| `WorkcellClient` | Workcell Manager (8005) | `async_get_nodes`, `async_get_active_workflows`, `async_pause_workflow` |
| `ResourceClient` | Resource Manager (8003) | `async_query_resource`, `async_remove_resource`, `async_is_locked` |
| `LocationClient` | Location Manager (8006) | `async_get_locations`, `async_get_transfer_graph` |
| `DataClient` | Data Manager (8004) | `async_get_datapoints`, `async_query_datapoints` |
| `RestNodeClient` | Node (direct) | `async_get_status`, `async_send_admin_command`, `async_send_action` |

### TUI Screen Pattern

See `experiments.py` for the canonical example. Key elements:
1. Lazy client initialization via `_get_X_client()` method
2. Client constructed from `ServiceURLMixin.get_service_url()`
3. All data fetching through async client methods
4. All data is Pydantic models, not raw dicts
5. Helper functions accept typed models, not dicts

### Anti-patterns
```python
# BAD: Raw httpx in TUI/CLI code
async with httpx.AsyncClient() as client:
    response = await client.get(f"{url}/experiments")
    data = response.json()  # raw dict, no type safety

# GOOD: Use typed client
client = ExperimentClient(experiment_server_url=url)
experiments = await client.async_get_experiments()  # list[Experiment]
```
