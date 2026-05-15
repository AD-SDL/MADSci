# Per-Manager Notes

Per-manager domain details. SKILL.md links here when the task targets a specific manager. For the shared patterns (settings, server class, client class, health, OTEL) stay in SKILL.md.

## Contents

- [Event Manager (8001)](#event-manager-8001)
- [Experiment Manager (8002)](#experiment-manager-8002)
- [Resource Manager (8003)](#resource-manager-8003)
- [Data Manager (8004)](#data-manager-8004)
- [Workcell Manager (8005)](#workcell-manager-8005)
- [Location Manager (8006)](#location-manager-8006)
- [Lab Manager / Squid (8000)](#lab-manager--squid-8000)

## Event Manager (8001)
- **Retention system**: Background loop archives old events (soft-delete), TTL indexes for hard-delete
- **Utilization analytics**: Session-based, time-series, and per-user utilization reports
- **Email alerts**: Configurable alert level triggers email notifications
- **Recursive logging prevention**: EventClient initialized with `event_server_url=None`
- **Key types**: `Event`, `EventLogLevel`, `EventType`

## Experiment Manager (8002)
- **Simple state machine**: IN_PROGRESS -> PAUSED/COMPLETED/FAILED/CANCELLED
- **Timestamp tracking**: `started_at`, `ended_at` on Experiment model
- **Key types**: `Experiment`, `ExperimentDesign`, `ExperimentStatus`, `ExperimentalCampaign`

## Resource Manager (8003)
- **Only PostgreSQL manager**: Uses SQLModel ORM, not document database
- **Container types**: Queue (FIFO), Stack (LIFO), Slot (single item)
- **Resource hierarchies**: Parent-child relationships with recursive queries
- **Template system**: Create resources from templates, extract templates from existing resources
- **Audit trail**: `ResourceHistoryTable` tracks all changes
- **Key types**: `Resource`, `ResourceTemplate`, `Queue`, `Stack`, `Slot`

## Data Manager (8004)
- **Dual storage**: Metadata in FerretDB, files in local filesystem or S3-compatible storage
- **DataPoint discriminated union**: `FileDataPoint`, `ValueDataPoint`, `ObjectStorageDataPoint`
- **File organization**: Local files stored as `{year}/{month}/{day}/{ulid_filename}`
- **Key types**: `DataPoint`, `FileDataPoint`, `ValueDataPoint`

## Workcell Manager (8005)
- **Workflow engine**: Executes workflow DAGs with branching and error recovery
- **Dual-handler**: FerretDB for workflow definitions, Valkey for runtime state/locks
- **Required clients**: event, data, location (for workflow execution)
- **Node coordination**: Discovers and communicates with registered nodes
- **Key types**: `WorkflowDefinition`, `WorkflowRun`, `WorkflowStep`

## Location Manager (8006)
- **Dual-handler**: FerretDB for persistent data, Valkey for transient state (locks, counters)
- **Transfer planning**: Dijkstra's algorithm via `TransferPlanner`
- **Node-specific representations**: Arbitrary JSON data per node per location
- **Seed file loading**: Bootstrap from `locations.yaml` on empty database
- **Key types**: `Location`, `TransferPlan`, `ReservationInfo`

## Lab Manager / Squid (8000)
- **No database**: Coordination-only, no persistent storage
- **Service discovery**: `/context` endpoint returns all manager URLs
- **Health aggregation**: `/lab_health` checks all 6 managers with 5s timeout
- **Dashboard**: Serves Vue 3 + Vuetify SPA as static files
- **Key types**: `LabHealth`, `LabContext`
