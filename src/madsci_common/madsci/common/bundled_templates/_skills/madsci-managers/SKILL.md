---
name: madsci-managers
description: Working with MADSci manager services (Event, Experiment, Resource, Data, Workcell, Location, Lab). Use when creating, modifying, debugging, or configuring manager servers.
---

# MADSci Manager Services

MADSci has 7 manager services, all built on `AbstractManagerBase[SettingsT]` with FastAPI via `classy_fastapi.Routable`. Each follows the pattern: **Settings class** -> **Server class** -> **Client class**.

## Key Files

| File | Purpose |
|------|---------|
| `src/madsci_common/madsci/common/manager_base.py` | `AbstractManagerBase` - common server lifecycle, health, CORS, OTEL |
| `src/madsci_common/madsci/common/types/manager_types.py` | `ManagerSettings`, `ManagerHealth` base types |
| `src/madsci_common/madsci/common/types/base_types.py` | `MadsciBaseSettings`, `prefixed_alias_generator()` |
| `src/madsci_common/madsci/common/db_handlers/` | 4 handler ABCs + real + in-memory implementations |
| `src/madsci_*/madsci/*/*_server.py` | Each manager's server implementation |
| `src/madsci_client/madsci/client/` | All client implementations |
| `src/madsci_client/madsci/client/client_mixin.py` | `MadsciClientMixin` for lazy client access |

## The 7 Managers

| Manager | Port | Database | Handler Params | Key Domain |
|---------|------|----------|----------------|------------|
| **Lab (Squid)** | 8000 | None | N/A | Dashboard, service discovery, health aggregation |
| **Event** | 8001 | FerretDB | `document_handler` | Distributed event logging, retention, analytics |
| **Experiment** | 8002 | FerretDB | `document_handler` | Experiment lifecycle (start/pause/cancel/end) |
| **Resource** | 8003 | PostgreSQL | `postgres_handler` | Inventory, containers (Queue/Stack/Slot), templates |
| **Data** | 8004 | FerretDB + S3 | `document_handler`, `object_storage_handler` | DataPoints (value/file), dual storage |
| **Workcell** | 8005 | FerretDB + Valkey | `document_handler`, `cache_handler` | Workflow execution, scheduling, node coordination |
| **Location** | 8006 | FerretDB + Valkey | `document_handler`, `cache_handler` | Location management, transfer planning, representations |

## Manager Implementation Pattern

### 1. Settings Class

```python
from madsci.common.types.manager_types import ManagerSettings
from madsci.common.types.base_types import prefixed_alias_generator, prefixed_model_validator

class MyManagerSettings(ManagerSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYMANAGER_",
        alias_generator=prefixed_alias_generator("mymanager"),
        populate_by_name=True,
    )
    _accept_prefixed_keys = prefixed_model_validator("mymanager")

    server_url: AnyUrl = Field(default="http://localhost:8007/")
    document_db_url: AnyUrl = Field(default="mongodb://localhost:27017/")
    database_name: str = Field(default="madsci_mymanager")
```

**Key points:**
- `env_prefix`: Environment variable prefix (e.g., `MYMANAGER_SERVER_URL`)
- `prefixed_alias_generator`: Enables prefixed keys in YAML (e.g., `mymanager_server_url`)
- `prefixed_model_validator`: Accepts prefixed keys during model initialization
- Code uses unprefixed names (`server_url`), YAML/export uses prefixed (`mymanager_server_url`)
- `model_dump(by_alias=True)` -> prefixed keys; `model_dump()` -> unprefixed

### 2. Server Class

```python
from madsci.common.manager_base import AbstractManagerBase

class MyManager(AbstractManagerBase[MyManagerSettings]):
    SETTINGS_CLASS = MyManagerSettings

    def initialize(self, **kwargs):
        """Called during __init__ after base setup. Set up DB connections, etc."""
        self._document_handler = kwargs.get("document_handler") or PyDocumentStorageHandler(
            url=str(self.settings.document_db_url),
            database_name=self.settings.database_name,
        )

    def get_health(self) -> MyManagerHealth:
        """Override to add DB connectivity checks."""
        try:
            connected = self._document_handler.ping()
            return MyManagerHealth(healthy=connected, db_connected=connected)
        except Exception as e:
            return MyManagerHealth(healthy=False, description=str(e))

    @get("/items")
    def list_items(self) -> list[Item]:
        """Custom endpoint using classy_fastapi @get/@post decorators."""
        ...

    @post("/items")
    def create_item(self, item: Item) -> Item:
        ...
```

**AbstractManagerBase provides:**
- `GET /health` -> calls `get_health()`
- `GET /settings` -> exports settings with secret redaction
- CORS middleware (configurable)
- Rate limiting middleware
- OpenTelemetry instrumentation (if enabled)
- Ownership context middleware
- Registry identity resolution (stable IDs across restarts)
- `self.logger` (EventClient) for structured logging
- `self.span(name, attributes)` context manager for OTEL tracing
- `create_server()` and `run_server()` for lifecycle management

### 3. Client Class

```python
from madsci.common.utils import create_http_session
from pydantic import AnyUrl

class MyManagerClient:
    def __init__(self, server_url: AnyUrl, config=None, event_client=None):
        self.server_url = str(server_url)
        self._session = None  # Lazy HTTP session

    def list_items(self, timeout=None) -> list[Item]:
        response = self._get("/items", timeout=timeout)
        return [Item(**item) for item in response.json()]

    def create_item(self, item: Item, timeout=None) -> Item:
        response = self._post("/items", json=item.model_dump(), timeout=timeout)
        return Item(**response.json())

    def close(self):
        """Release HTTP session resources."""
        if self._session:
            self._session.close()
```

**All clients have:**
- Lazy HTTP session initialization
- `close()` method for cleanup
- Optional `EventClient` injection for logging
- Configurable retry behavior

## Settings and Configuration

### Prefixed Alias System

Each manager uses `prefixed_alias_generator()` for YAML-friendly configuration:

```yaml
# settings.yaml (shared across managers)
event_server_url: http://localhost:8001/
event_database_name: madsci_events
resource_postgres_db_url: postgresql://localhost/resources
workcell_cache_url: redis://localhost:6379/
```

```python
# In code, use unprefixed names:
self.settings.server_url       # "http://localhost:8001/"
self.settings.database_name    # "madsci_events"
```

### Secret Marking and Redaction

```python
# Type-based:
password: SecretStr

# Metadata-based:
api_key: str = Field(json_schema_extra={"secret": True})

# Safe export (redacts secrets):
settings.model_dump_safe()

# Settings endpoint uses:
get_settings_export(include_secrets=False)  # Default
```

### Environment Variable Precedence
CLI args > init kwargs > env vars > .env > file secrets > JSON > TOML > YAML > field defaults

## Database Handler Abstraction

4 handler ABCs with real and in-memory implementations:

### DocumentStorageHandler (FerretDB/MongoDB)

```python
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,       # ABC
    PyDocumentStorageHandler,     # Real (pymongo)
    InMemoryDocumentStorageHandler,  # Testing
)

# Production:
handler = PyDocumentStorageHandler(url="mongodb://localhost:27017", database_name="madsci_events")
collection = handler.get_collection("events")
collection.insert_one({"event": "data"})

# Testing:
handler = InMemoryDocumentStorageHandler()
```

**Used by:** Event, Experiment, Data, Workcell, Location managers

### CacheHandler (Valkey/Redis)

```python
from madsci.common.db_handlers.cache_handler import (
    CacheHandler,          # ABC
    PyCacheHandler,        # Real (redis + pottery)
    InMemoryCacheHandler,  # Testing
)

# Production:
handler = PyCacheHandler(url="redis://localhost:6379")
state_dict = handler.create_dict("workcell_state")  # pottery RedisDict-like
lock = handler.create_lock("operation_lock", auto_release_time=30)

# Testing:
handler = InMemoryCacheHandler()
```

**Used by:** Workcell, Location managers

### PostgresHandler (PostgreSQL)

```python
from madsci.common.db_handlers.postgres_handler import (
    PostgresHandler,     # ABC
    SQLAlchemyHandler,   # Real (SQLAlchemy + PostgreSQL)
    SQLiteHandler,       # Testing (in-memory SQLite)
)

# Production:
handler = SQLAlchemyHandler(url="postgresql://localhost/resources")
engine = handler.get_engine()

# Testing:
handler = SQLiteHandler()  # StaticPool, check_same_thread=False
```

**Used by:** Resource manager

### ObjectStorageHandler (S3-compatible)

```python
from madsci.common.db_handlers.object_storage_handler import (
    ObjectStorageHandler,          # ABC
    RealObjectStorageHandler,      # Real (MinIO/SeaweedFS/S3)
    InMemoryObjectStorageHandler,  # Testing
)

# Production:
handler = RealObjectStorageHandler(settings=ObjectStorageSettings(...))

# Testing:
handler = InMemoryObjectStorageHandler()
```

**Used by:** Data manager (optional, for file storage)

## Manager-Specific Notes

### Event Manager (8001)
- **Retention system**: Background loop archives old events (soft-delete), TTL indexes for hard-delete
- **Utilization analytics**: Session-based, time-series, and per-user utilization reports
- **Email alerts**: Configurable alert level triggers email notifications
- **Recursive logging prevention**: EventClient initialized with `event_server_url=None`
- **Key types**: `Event`, `EventLogLevel`, `EventType`

### Experiment Manager (8002)
- **Simple state machine**: IN_PROGRESS -> PAUSED/COMPLETED/FAILED/CANCELLED
- **Timestamp tracking**: `started_at`, `ended_at` on Experiment model
- **Key types**: `Experiment`, `ExperimentDesign`, `ExperimentStatus`, `ExperimentalCampaign`

### Resource Manager (8003)
- **Only PostgreSQL manager**: Uses SQLModel ORM, not document database
- **Container types**: Queue (FIFO), Stack (LIFO), Slot (single item)
- **Resource hierarchies**: Parent-child relationships with recursive queries
- **Template system**: Create resources from templates, extract templates from existing resources
- **Audit trail**: `ResourceHistoryTable` tracks all changes
- **Key types**: `Resource`, `ResourceTemplate`, `Queue`, `Stack`, `Slot`

### Data Manager (8004)
- **Dual storage**: Metadata in FerretDB, files in local filesystem or S3-compatible storage
- **DataPoint discriminated union**: `FileDataPoint`, `ValueDataPoint`, `ObjectStorageDataPoint`
- **File organization**: Local files stored as `{year}/{month}/{day}/{ulid_filename}`
- **Key types**: `DataPoint`, `FileDataPoint`, `ValueDataPoint`

### Workcell Manager (8005)
- **Workflow engine**: Executes workflow DAGs with branching and error recovery
- **Dual-handler**: FerretDB for workflow definitions, Valkey for runtime state/locks
- **Required clients**: event, data, location (for workflow execution)
- **Node coordination**: Discovers and communicates with registered nodes
- **Key types**: `WorkflowDefinition`, `WorkflowRun`, `WorkflowStep`

### Location Manager (8006)
- **Dual-handler**: FerretDB for persistent data, Valkey for transient state (locks, counters)
- **Transfer planning**: Dijkstra's algorithm via `TransferPlanner`
- **Node-specific representations**: Arbitrary JSON data per node per location
- **Seed file loading**: Bootstrap from `locations.yaml` on empty database
- **Key types**: `Location`, `TransferPlan`, `ReservationInfo`

### Lab Manager / Squid (8000)
- **No database**: Coordination-only, no persistent storage
- **Service discovery**: `/context` endpoint returns all manager URLs
- **Health aggregation**: `/lab_health` checks all 6 managers with 5s timeout
- **Dashboard**: Serves Vue 3 + Vuetify SPA as static files
- **Key types**: `LabHealth`, `LabContext`

## EventClient Dual Nature

EventClient serves as both a logging interface and an HTTP client:

```python
# Logging (always works, even without Event Manager)
self.logger.info("Operation started", event_type=EventType.WORKFLOW_START, workflow_id=wf_id)
self.logger.warning("Threshold exceeded", value=42.5)
self.logger.error("Connection failed", error=str(e))

# HTTP client (requires Event Manager)
events = self.event_client.get_events(number=10)
event = self.event_client.get_event(event_id)
```

**Structured logging best practice:**
```python
# Good: kwargs are queryable
self.logger.info("Step completed", step_index=3, duration_ms=150)

# Bad: f-string data is not queryable
self.logger.info(f"Step 3 completed in 150ms")
```

## Health Check Pattern

```python
def get_health(self) -> MyManagerHealth:
    health = MyManagerHealth(healthy=True)
    try:
        health.db_connected = self._document_handler.ping()
        health.total_items = self._get_count()
    except Exception as e:
        health.healthy = False
        health.description = f"Database error: {e}"
    return health
```

`ManagerHealth` uses `model_config = ConfigDict(extra="allow")` so subclasses can freely add fields.

## Testing Managers

```python
from madsci.common.db_handlers import (
    InMemoryDocumentStorageHandler,
    InMemoryCacheHandler,
    SQLiteHandler,
)

def test_event_manager():
    manager = EventManager(
        settings=EventManagerSettings(enable_registry_resolution=False),
        document_handler=InMemoryDocumentStorageHandler(),
    )
    app = manager.create_server()
    client = TestClient(app)

    # Test endpoints
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["healthy"] is True

def test_workcell_manager():
    manager = WorkcellManager(
        settings=WorkcellManagerSettings(enable_registry_resolution=False),
        document_handler=InMemoryDocumentStorageHandler(),
        cache_handler=InMemoryCacheHandler(),
    )
    ...

def test_resource_manager():
    manager = ResourceManager(
        settings=ResourceManagerSettings(enable_registry_resolution=False),
        postgres_handler=SQLiteHandler(),
    )
    ...
```

**Critical test pattern:** Always set `enable_registry_resolution=False` to prevent registry lockfile usage in tests.

## OpenTelemetry Integration

Per-manager configuration via environment:
```bash
EVENT_OTEL_ENABLED=true
EVENT_OTEL_SERVICE_NAME="madsci.event"
EVENT_OTEL_EXPORTER="otlp"           # or "console"
EVENT_OTEL_ENDPOINT="http://localhost:4317"
EVENT_OTEL_PROTOCOL="grpc"           # or "http"
```

In code:
```python
with self.span("process_data", attributes={"data.size": 100}) as span:
    result = process(data)
    span.set_attribute("result.count", len(result))
```

## Common Pitfalls

- **ULID not UUID**: Use `new_ulid_str()` for all IDs
- **prefixed vs unprefixed**: Code uses `self.settings.server_url`, YAML uses `event_server_url`
- **`model_dump(by_alias=True)`**: Produces prefixed keys for YAML export
- **Registry in tests**: Always `enable_registry_resolution=False`
- **Handler injection**: Pass handlers via constructor for dependency injection (production and test)
- **FerretDB, not MongoDB**: The system uses FerretDB (MongoDB wire protocol on PostgreSQL). pymongo client works unchanged.
- **Valkey, not Redis**: Drop-in Redis replacement. redis-py client works unchanged.
- **EventClient recursive logging**: Event Manager's own EventClient must have `event_server_url=None`
- **AnyUrl trailing slash**: All URLs stored via Pydantic AnyUrl get a trailing slash
- **Secret fields**: Use `json_schema_extra={"secret": True}` or `SecretStr` type
