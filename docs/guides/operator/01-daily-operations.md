# Daily Operations

**Audience**: Lab Operator
**Prerequisites**: [Tutorial: Full Lab](../../tutorials/05-full-lab.md)
**Time**: ~20 minutes

## Overview

This guide covers the day-to-day operations of running a MADSci-powered self-driving laboratory. You'll learn how to start and stop services, verify system health, and handle common operational tasks.

## Starting the Lab

### Full Lab Startup

```bash
# Start all services in the background
madsci start -d

# Verify everything is running
madsci status

# Or start in the foreground (logs streamed to terminal)
madsci start
```

### Local Mode (No Docker)

For development or environments without Docker:

```bash
# Start all managers in-process with in-memory backends
madsci start --mode=local

# Data is ephemeral and will not persist across restarts
```

### Full Lab Startup (Docker, Advanced)

```bash
# Use docker compose directly for more control
docker compose up -d

# Verify everything is running
docker compose ps

# Check health of all MADSci services
madsci status
```

### Startup Order

Docker Compose handles dependency ordering, but the logical startup sequence is:

```
1. Infrastructure    FerretDB, PostgreSQL, Valkey, SeaweedFS
       ↓
2. Managers          Event, Experiment, Resource, Data, Location, Workcell
       ↓
3. Lab Manager       Squid (central dashboard)
       ↓
4. Nodes             Instrument nodes (liquidhandler, robotarm, etc.)
```

### Starting Individual Services

```bash
# Start a specific manager
madsci start manager event

# Start a specific node
madsci start node ./path/to/node.py

# Start in the background with PID tracking
madsci start manager event -d
```

### Starting Individual Services (Docker, Advanced)

```bash
# Start only infrastructure
docker compose up -d madsci_ferretdb madsci_valkey postgres madsci_seaweedfs

# Start a specific manager via Docker
docker compose up -d event_manager

# Start a specific node via Docker
docker compose up -d liquidhandler_1

# Start managers without nodes
docker compose up -d lab_manager event_manager experiment_manager \
  resource_manager data_manager location_manager workcell_manager
```

### Starting Without Docker (Advanced)

For running individual services directly:

```bash
# Start a manager directly
python -m madsci.event_manager

# Start a node directly
python example_modules/liquidhandler.py

# Start with custom settings
EVENT_SERVER_PORT=8001 EVENT_DOCUMENT_DB_URL=mongodb://localhost:27017 \
  python -m madsci.event_manager
```

## Stopping the Lab

### Graceful Shutdown

```bash
# Stop all services (preserves data volumes)
madsci stop

# Stop a specific background manager
madsci stop manager event

# Stop a specific background node
madsci stop node <name>

# Stop and remove images
madsci stop --remove

# Stop and remove volumes (data loss — requires confirmation)
madsci stop --volumes
```

### Graceful Shutdown (Docker, Advanced)

```bash
# Stop all services via docker compose directly
docker compose down

# Stop a specific service
docker compose stop liquidhandler_1

# Stop and remove everything including data volumes (DESTRUCTIVE)
docker compose down -v
```

### Emergency Shutdown

If services are unresponsive:

```bash
# Force stop all containers
docker compose kill

# Force stop a specific container
docker kill <container_name>
```

## Health Checks

### Using the CLI

```bash
# Quick status check of all services
madsci status

# Watch status continuously (updates every 5 seconds)
madsci status --watch

# JSON output for scripting
madsci status --json

# Check specific service health
curl http://localhost:8000/health  # Lab Manager
curl http://localhost:8001/health  # Event Manager
curl http://localhost:8005/health  # Workcell Manager
```

### Service Health Endpoints

Every MADSci manager exposes a `/health` endpoint:

| Service | URL | What It Checks |
|---------|-----|----------------|
| Lab Manager | `http://localhost:8000/health` | Manager connectivity |
| Event Manager | `http://localhost:8001/health` | FerretDB connection |
| Experiment Manager | `http://localhost:8002/health` | FerretDB connection |
| Resource Manager | `http://localhost:8003/health` | PostgreSQL connection |
| Data Manager | `http://localhost:8004/health` | FerretDB + SeaweedFS connection |
| Workcell Manager | `http://localhost:8005/health` | FerretDB + Valkey + node connectivity |
| Location Manager | `http://localhost:8006/health` | FerretDB connection |

### Node Health

```bash
# Check a specific node
curl http://localhost:2000/health

# Get node info
curl http://localhost:2000/info

# Get node state
curl http://localhost:2000/state
```

### System Diagnostics

```bash
# Run comprehensive diagnostics
madsci doctor

# Check specific categories
madsci doctor --check python
madsci doctor --check docker
madsci doctor --check ports
```

## Viewing Logs

### Using the CLI

```bash
# View recent logs
madsci logs --tail 50

# Follow logs in real time
madsci logs --follow

# Filter by log level
madsci logs --level ERROR
madsci logs --level WARNING

# Filter by pattern
madsci logs --grep "workflow"
madsci logs --grep "liquidhandler"

# Logs from a specific time period
madsci logs --since 1h
madsci logs --since 30m
```

### Using Docker

```bash
# All service logs
docker compose logs -f

# Specific service logs
docker compose logs -f workcell_manager

# Last 100 lines
docker compose logs --tail 100 event_manager

# Logs since a timestamp
docker compose logs --since 2026-02-09T10:00:00 workcell_manager
```

### Using the TUI

```bash
madsci tui
```

Press `l` to navigate to the Logs screen. Use the filter controls to narrow down by level or search pattern.

## Managing Workflows

### Check Active Workflows

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")

# List active workflows
active = wc.get_active_workflows()
for wf_id, wf in active.items():
    print(f"{wf_id}: step {wf.status.current_step_index}, "
          f"started {wf.submitted_time}")

# Check the workflow queue
queue = wc.get_workflow_queue()
print(f"{len(queue)} workflows queued")
```

### Cancel a Stuck Workflow

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")
wc.cancel_workflow("workflow_id_here")
```

### Pause and Resume

```python
# Pause a running workflow
wc.pause_workflow("workflow_id_here")

# Resume a paused workflow
wc.resume_workflow("workflow_id_here")
```

## Managing Nodes

### Check Node Status

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")
nodes = wc.get_nodes()
for name, node in nodes.items():
    print(f"{name}: {node.status}")
```

### Restart a Node

```bash
# Restart via Docker
docker compose restart liquidhandler_1

# Or stop and start
docker compose stop liquidhandler_1
docker compose start liquidhandler_1
```

### Lock/Unlock a Node

Locking prevents the workcell from sending actions to a node (useful during maintenance):

```bash
# Lock a node
curl -X POST http://localhost:2000/admin/lock

# Unlock a node
curl -X POST http://localhost:2000/admin/unlock
```

## Daily Checklist

A recommended daily routine for lab operators:

1. **Morning startup**: `madsci start -d && madsci status`
2. **Verify health**: Check all services show HEALTHY
3. **Review overnight logs**: `madsci logs --since 12h --level WARNING`
4. **Check disk space**: `df -h` (especially for data and log volumes)
5. **Verify backups**: Check that scheduled backups completed
6. **End of day**: Review experiment results, check for errors

## What's Next?

- [Monitoring](./02-monitoring.md) - Detailed monitoring with TUI and observability tools
- [Backup & Recovery](./03-backup-recovery.md) - Database backup strategies
- [Troubleshooting](./04-troubleshooting.md) - Common issues and solutions
