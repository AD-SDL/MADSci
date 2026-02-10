# Lab Operator Guide

This guide is for the **Lab Operator** persona - those who run and maintain MADSci-powered self-driving laboratories.

## Guide Contents

1. [Daily Operations](01-daily-operations.md) - Starting, monitoring, and stopping the lab
2. [Monitoring & Health Checks](02-monitoring.md) - Using TUI, CLI, and observability tools
3. [Backup & Recovery](03-backup-recovery.md) - Database backups and disaster recovery
4. [Troubleshooting](04-troubleshooting.md) - Common issues and solutions
5. [Updates & Maintenance](05-updates-maintenance.md) - Upgrading MADSci and dependencies

## Who is a Lab Operator?

A Lab Operator:

- Starts and stops the lab services
- Monitors system health and status
- Performs backups and maintenance
- Troubleshoots issues when they arise
- Coordinates with Equipment Integrators and Experimentalists

## Quick Reference

### Starting the Lab

```bash
# Start all services
cd my_lab
docker compose up -d

# Verify everything is running
madsci status

# Watch logs
madsci logs --follow
```

### Checking Health

```bash
# Quick status check
madsci status

# Detailed diagnostics
madsci doctor

# Launch TUI for monitoring
madsci tui
```

### Stopping the Lab

```bash
# Graceful stop (preserves data)
docker compose stop

# Stop and remove containers
docker compose down

# Full cleanup (WARNING: deletes data)
docker compose down -v
```

### Backups

```bash
# Quick backup
madsci-backup create --db-url mongodb://localhost:27017 --output ./backups

# Full backup with verification
madsci-backup create --db-url mongodb://localhost:27017 --output ./backups --validate
```

### Viewing Logs

```bash
# All services
madsci logs --follow

# Specific service
madsci logs workcell_manager --tail 100

# Filter by level
madsci logs --level error --since 1h
```

## Key Concepts

### Service Types

| Type | Examples | Purpose |
|------|----------|--------|
| **Infrastructure** | MongoDB, PostgreSQL, Redis, MinIO | Data storage |
| **Managers** | Event, Experiment, Resource, Workcell | Coordination |
| **Nodes** | temp_sensor, robot_arm | Instruments |

### Ports Reference

| Service | Port | URL |
|---------|------|-----|
| Lab Manager | 8000 | http://localhost:8000 |
| Event Manager | 8001 | http://localhost:8001 |
| Experiment Manager | 8002 | http://localhost:8002 |
| Resource Manager | 8003 | http://localhost:8003 |
| Data Manager | 8004 | http://localhost:8004 |
| Workcell Manager | 8005 | http://localhost:8005 |
| Location Manager | 8006 | http://localhost:8006 |
| MongoDB | 27017 | mongodb://localhost:27017 |
| PostgreSQL | 5432 | postgresql://localhost:5432 |
| Redis | 6379 | redis://localhost:6379 |
| MinIO | 9000/9001 | http://localhost:9000 |

### Health Check Endpoints

All managers expose:

- `GET /health` - Basic health check
- `GET /info` - Service information
- `GET /status` - Detailed status

### Log Levels

| Level | Meaning |
|-------|--------|
| `DEBUG` | Detailed diagnostic information |
| `INFO` | General operational events |
| `WARNING` | Something unexpected but not critical |
| `ERROR` | Something failed |
| `CRITICAL` | System is in a critical state |

## Common Tasks

### Restarting a Single Service

```bash
# Restart workcell manager
docker compose restart workcell_manager

# View its logs
docker compose logs -f workcell_manager
```

### Checking Why a Service Failed

```bash
# View recent logs
docker compose logs --tail 50 <service_name>

# Check container status
docker compose ps

# Inspect container
docker inspect <container_id>
```

### Checking Port Usage

```bash
# See what's using ports
lsof -i :8000-8006

# Or with netstat
netstat -tuln | grep -E '800[0-6]'
```

### Emergency Shutdown

```bash
# If compose is unresponsive, stop all containers
docker stop $(docker ps -q --filter "network=madsci")

# Force stop if needed
docker kill $(docker ps -q --filter "network=madsci")
```

## Prerequisites

- Docker and Docker Compose installed
- Access to the lab's `compose.yaml` and `.env` files
- Understanding of basic Docker commands
- SSH access to the lab server (if remote)
