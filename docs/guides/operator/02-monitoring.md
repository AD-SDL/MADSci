# Monitoring

**Audience**: Lab Operator
**Prerequisites**: [Daily Operations](./01-daily-operations.md)
**Time**: ~25 minutes

## Overview

Effective monitoring helps you detect issues before they affect experiments. MADSci provides multiple monitoring layers: the CLI, the TUI, structured event logs, and an optional observability stack (OpenTelemetry + Jaeger + Prometheus + Grafana).

## CLI Monitoring

### Service Status

```bash
# One-shot status check
madsci status

# Continuous monitoring (refreshes every 5 seconds)
madsci status --watch

# Faster refresh
madsci status --watch --interval 2

# JSON for scripting/alerting
madsci status --json | python -c "
import sys, json
data = json.load(sys.stdin)
unhealthy = [s for s in data['services'] if s['status'] != 'healthy']
if unhealthy:
    print(f'ALERT: {len(unhealthy)} unhealthy services')
    for s in unhealthy:
        print(f'  {s[\"name\"]}: {s[\"status\"]}')
    sys.exit(1)
"
```

### Log Monitoring

```bash
# Follow all logs in real time
madsci logs --follow

# Only errors and critical
madsci logs --follow --level ERROR

# Filter to specific component
madsci logs --follow --grep "workcell"

# Show timestamps
madsci logs --follow --timestamps
```

## TUI Monitoring

The TUI provides a live dashboard for monitoring:

```bash
madsci tui
```

### Dashboard Screen (`d`)

Shows an overview of all services with color-coded health status:
- Green: Service is healthy
- Yellow: Service is responding but degraded
- Red: Service is offline or unhealthy

### Status Screen (`s`)

Detailed table view of each service including:
- Service name and URL
- Health status
- Response time
- Version information

### Logs Screen (`l`)

Live log viewer with:
- Level filtering (DEBUG through CRITICAL)
- Text search
- Auto-scroll with follow mode

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Dashboard screen |
| `s` | Status screen |
| `l` | Logs screen |
| `r` | Refresh data |
| `q` | Quit |

## Event System

MADSci's Event Manager captures structured events from all components. This is the primary audit trail for your lab.

### Querying Events

```python
from madsci.client import EventClient

ec = EventClient()

# Recent events
events = ec.get_events(number=50)
for event_id, event in events.items():
    print(f"[{event.log_level}] {event.event_timestamp}: {event.event_data}")

# Query by type
from madsci.common.types.event_types import EventType

workflow_events = ec.query_events({
    "event_type": EventType.WORKFLOW_COMPLETE.value
})

# Query by time range
error_events = ec.query_events({
    "log_level": {"$gte": 40},  # ERROR and above
    "event_timestamp": {"$gte": "2026-02-09T00:00:00Z"}
})
```

### Event Types

Key event types to monitor:

| Event Type | Significance |
|------------|-------------|
| `WORKFLOW_COMPLETE` | Workflow finished successfully |
| `WORKFLOW_ABORT` | Workflow failed or was cancelled |
| `WORKFLOW_STEP_FAILED` | Individual step failed |
| `NODE_ERROR` | Node reported an error |
| `NODE_STATUS_UPDATE` | Node status changed |
| `EXPERIMENT_FAILED` | Experiment failed |
| `MANAGER_ERROR` | Manager service error |
| `BACKUP_CREATE` | Backup was created |

### Utilization Reports

The Event Manager provides utilization analytics:

```python
from madsci.client import EventClient

ec = EventClient()

# Daily utilization summary
daily = ec.get_utilization_periods(
    analysis_type="daily",
    start_time="2026-02-01T00:00:00Z",
    end_time="2026-02-09T00:00:00Z",
)

# Session-based utilization
sessions = ec.get_session_utilization(
    start_time="2026-02-01T00:00:00Z",
    end_time="2026-02-09T00:00:00Z",
)

# Export as CSV
csv_data = ec.get_user_utilization_report(
    csv_export=True,
    start_time="2026-02-01T00:00:00Z",
)
```

## Observability Stack (OpenTelemetry)

For production labs, MADSci integrates with OpenTelemetry for distributed tracing, metrics, and log correlation.

### Architecture

```
MADSci Services
      │
      ▼ (OTLP gRPC/HTTP)
┌─────────────────────┐
│  OTEL Collector      │  Port 4317
│  (receive, process,  │
│   export)            │
└─────────────────────┘
      │
      ├──► Jaeger (traces)      Port 16686
      ├──► Prometheus (metrics)  Port 9090
      ├──► Loki (logs)          Port 3100
      └──► Grafana (dashboards) Port 3000
```

### Enabling OTEL

Add the observability stack to your Docker Compose:

The OTEL stack is included automatically via the root `compose.yaml`. Enable it with the `otel` profile:

```bash
docker compose --profile otel up
```

Enable OTEL per manager via environment variables:

```bash
# .env
EVENT_OTEL_ENABLED=true
EVENT_OTEL_SERVICE_NAME=madsci.event
EVENT_OTEL_EXPORTER=otlp
EVENT_OTEL_ENDPOINT=http://otel-collector:4317
EVENT_OTEL_PROTOCOL=grpc

WORKCELL_OTEL_ENABLED=true
WORKCELL_OTEL_SERVICE_NAME=madsci.workcell
WORKCELL_OTEL_EXPORTER=otlp
WORKCELL_OTEL_ENDPOINT=http://otel-collector:4317
WORKCELL_OTEL_PROTOCOL=grpc
```

### Jaeger (Traces)

Access at `http://localhost:16686`

Use Jaeger to:
- **Trace workflow execution**: See the full timeline of a workflow from submission through each step
- **Identify bottlenecks**: Find slow steps or services
- **Debug failures**: See where in the chain a failure occurred
- **Correlate events**: Link traces to logs and metrics

### Prometheus (Metrics)

Access at `http://localhost:9090`

Key metrics to monitor:
- `madsci_events_total`: Total events by type and level
- `madsci_event_send_latency_seconds`: Event send latency
- `madsci_event_buffer_size`: Event buffer size (indicates backpressure)
- `madsci_event_retries_total`: Event send retries (indicates connectivity issues)

### Grafana (Dashboards)

Access at `http://localhost:3000` (default: admin/admin)

Pre-configured dashboards include:
- **MADSci Overview**: Service health, event rates, error rates
- **Workflow Performance**: Step durations, success rates
- **Resource Utilization**: Node busy/idle time

### Loki (Log Aggregation)

Access through Grafana's Explore view.

Query logs across all services:
```
{service_name="madsci.workcell"} |= "error"
```

## Automated Alerting

### Simple Script-Based Alerting

```python
#!/usr/bin/env python3
"""Simple health check alerter. Run via cron."""

import httpx
import sys

SERVICES = {
    "Lab Manager": "http://localhost:8000/health",
    "Event Manager": "http://localhost:8001/health",
    "Workcell Manager": "http://localhost:8005/health",
}

failures = []
for name, url in SERVICES.items():
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code != 200:
            failures.append(f"{name}: HTTP {r.status_code}")
    except Exception as e:
        failures.append(f"{name}: {e}")

if failures:
    print("ALERT: Service health check failures:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All services healthy")
```

### Cron-Based Monitoring

```bash
# Check every 5 minutes
*/5 * * * * /path/to/health_check.py >> /var/log/madsci_health.log 2>&1
```

### Prometheus Alerting

For production, configure Prometheus alerting rules:

```yaml
# prometheus_alerts.yml
groups:
  - name: madsci
    rules:
      - alert: ServiceDown
        expr: up{job="madsci"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "MADSci service {{ $labels.instance }} is down"

      - alert: HighErrorRate
        expr: rate(madsci_events_total{level="ERROR"}[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
```

## What's Next?

- [Backup & Recovery](./03-backup-recovery.md) - Database backup strategies
- [Troubleshooting](./04-troubleshooting.md) - Common issues and solutions
