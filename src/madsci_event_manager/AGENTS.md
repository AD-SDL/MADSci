# MADSci Event Manager

## Overview
The Event Manager (Port 8001) provides distributed event logging and querying capabilities. It serves as the central nervous system for monitoring laboratory operations, tracking system state changes, and enabling real-time notifications.

## Key Components

### Core Server
- **event_server.py**: Main FastAPI server handling event ingestion and querying
- High-throughput event logging with batch processing support
- Real-time event streaming and subscription capabilities
- Event filtering, search, and aggregation endpoints

### EventClient Integration
- The `EventClient` in `madsci_client` is the primary interface for logging events
- Supports structured logging with kwargs (not f-strings)
- Context binding for hierarchical logging across components
- OpenTelemetry integration for distributed tracing correlation

### Analysis Tools
- **time_series_analyzer.py**: Time-based event analysis and pattern detection
- **utilization_analyzer.py**: Resource and system utilization tracking
- Performance metrics and trend analysis
- Anomaly detection in event patterns

### Export and Notifications
- **events_csv_exporter.py**: Export events to CSV format for external analysis
- **notifications.py**: Real-time notification system for critical events
- Integration with external monitoring and alerting systems

## Event Types
- System lifecycle events (startup, shutdown, errors)
- Workflow execution events (start, step completion, failures)
- Resource state changes (allocation, release, errors)
- Node communication events (requests, responses, timeouts)
- User actions and administrative commands
- Data operations and access logs

## Logging Best Practices

### Structured Logging
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

### Context-Aware Logging
```python
from madsci.common.context import event_client_context, get_event_client

# Establish context at entry points
with event_client_context(name="operation", op_id="123") as logger:
    logger.info("Starting")  # Includes op_id

# In library code, inherit context
logger = get_event_client()
```

## Features
- **High Performance**: Optimized for high-volume event ingestion
- **Real-time Streaming**: WebSocket support for live event monitoring
- **Flexible Querying**: Complex filtering by time, source, type, and metadata
- **Batch Processing**: Efficient handling of bulk event operations
- **Export Capabilities**: Multiple export formats for analysis and reporting
- **OpenTelemetry**: Trace correlation with distributed tracing systems

## Configuration
Environment variables with `EVENT_` prefix:
- Database connection and performance tuning
- Event retention policies
- Notification service settings
- Export format configurations
- OpenTelemetry settings (`EVENT_OTEL_ENABLED`, `EVENT_OTEL_ENDPOINT`, etc.)

## Integration Points
- **All Managers**: Receive events from all other MADSci services
- **Dashboard**: Provide real-time monitoring data
- **External Systems**: Integration with laboratory LIMS and monitoring tools
- **OpenTelemetry**: Export traces, metrics, and logs to observability backends
