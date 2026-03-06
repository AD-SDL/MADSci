# Troubleshooting

**Audience**: Lab Operator
**Prerequisites**: [Daily Operations](./01-daily-operations.md)
**Time**: ~20 minutes (reference guide)

## Overview

This guide covers common issues you may encounter when operating a MADSci lab, organized by symptom. Use the diagnostic tools first, then consult the specific issue sections.

## First Steps: Diagnostics

Before diving into specific issues, gather information:

```bash
# 1. Check all service health
madsci status

# 2. Run system diagnostics
madsci doctor

# 3. Check recent errors
madsci logs --level ERROR --tail 20

# 4. Check Docker container status
docker compose ps
```

## Service Issues

### Service Won't Start

**Symptom**: `docker compose up` fails or service exits immediately.

**Diagnosis**:
```bash
# Check container logs
docker compose logs <service_name>

# Check exit code
docker compose ps <service_name>
```

**Common Causes**:

| Cause | Log Message | Fix |
|-------|------------|-----|
| Port in use | `Address already in use` | Stop conflicting process: `lsof -i :<port>` |
| Database not ready | `Connection refused` to MongoDB/PostgreSQL | Wait for DB startup or check DB health |
| Missing env vars | `ValidationError` or `Field required` | Check `.env` file has all required variables |
| Image not built | `No such image` | Run `docker compose build <service>` |
| Volume permissions | `Permission denied` | Check volume ownership: `ls -la` |

### Service Unhealthy

**Symptom**: `madsci status` shows UNHEALTHY or OFFLINE.

**Diagnosis**:
```bash
# Check the specific health endpoint
curl -v http://localhost:<port>/health

# Check container resource usage
docker stats <container_name>
```

**Common Causes**:

| Cause | Fix |
|-------|-----|
| Database connection lost | Restart the database: `docker compose restart mongodb` |
| Out of memory | Increase Docker memory limit or reduce workload |
| Deadlocked process | Restart the service: `docker compose restart <service>` |
| Network issue | Check Docker network: `docker network inspect madsci_default` |

### Service Crash Loop

**Symptom**: Service keeps restarting (visible in `docker compose ps`).

```bash
# Check restart count
docker inspect <container> --format '{{.RestartCount}}'

# View logs from the crash
docker compose logs --tail 50 <service_name>

# Temporarily disable restart to debug
docker compose stop <service_name>
docker compose run --rm <service_name>  # Run interactively
```

## Database Issues

### MongoDB Connection Failures

**Symptom**: Managers report database connection errors.

```bash
# Check MongoDB is running
docker compose ps mongodb

# Test connection
docker compose exec mongodb mongosh --eval "db.runCommand({ping: 1})"

# Check MongoDB logs
docker compose logs mongodb
```

**Fixes**:
- Restart MongoDB: `docker compose restart mongodb`
- Check disk space: `df -h` (MongoDB needs free space for journaling)
- Check connection string in environment variables

### PostgreSQL Connection Failures

**Symptom**: Resource Manager reports database errors.

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec postgres pg_isready

# Check PostgreSQL logs
docker compose logs postgres
```

### Redis Connection Failures

**Symptom**: Workcell Manager can't queue workflows.

```bash
# Check Redis
docker compose ps redis
docker compose exec redis redis-cli ping
# Should return: PONG
```

## Workflow Issues

### Workflow Stuck

**Symptom**: Workflow shows as active but no progress.

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")

# Check workflow status
wf = wc.query_workflow("workflow_id_here")
print(f"Status: {wf.status}")
print(f"Current step: {wf.status.current_step_index}")

# Check the current step
step = wf.steps[wf.status.current_step_index]
print(f"Step: {step.name}")
print(f"Step status: {step.status}")
print(f"Node: {step.node}")
```

**Common Causes**:

| Cause | Fix |
|-------|-----|
| Node is locked | Unlock the node: `curl -X POST http://<node>:2000/admin/unlock` |
| Node is offline | Restart the node: `docker compose restart <node>` |
| Action timed out | Check node logs, restart node if needed |
| Resource condition not met | Check resource state in Resource Manager |

### Workflow Fails on Specific Step

```bash
# Check the workcell logs around the failure time
madsci logs --grep "workflow_id" --tail 50

# Check the specific node's logs
docker compose logs <node_name> --tail 50
```

### All Workflows Queued But Not Running

**Symptom**: Workflows are submitted but never start.

**Check**:
1. Is the workcell in a paused state?
2. Are all required nodes registered and healthy?
3. Is Redis accessible?

```bash
# Check workcell state
curl http://localhost:8005/state | python -m json.tool
```

## Node Issues

### Node Not Responding

```bash
# Check if the node process is running
docker compose ps <node_name>

# Check node health directly
curl http://localhost:2000/health

# Restart the node
docker compose restart <node_name>
```

### Action Fails

```bash
# Check the node's action history
curl http://localhost:2000/actions/history | python -m json.tool

# Check node logs
docker compose logs <node_name> --tail 50

# Try the action directly (bypassing workcell)
curl -X POST http://localhost:2000/actions/<action_name> \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

### Hardware Communication Error

See the [Debugging Guide](../integrator/07-debugging.md) for detailed hardware troubleshooting.

Quick checks:
```bash
# Check if device is visible
ls -la /dev/ttyUSB*  # Serial devices
lsusb               # USB devices

# Check device permissions
groups $USER  # Should include 'dialout' for serial access

# Check if Docker has device access
docker compose exec <node_name> ls -la /dev/ttyUSB0
```

## Network Issues

### Services Can't Find Each Other

**Symptom**: Services report connection errors to other services.

```bash
# Check Docker network
docker network ls
docker network inspect madsci_default

# Test connectivity between containers
docker compose exec workcell_manager curl http://event_manager:8001/health

# Check DNS resolution
docker compose exec workcell_manager nslookup event_manager
```

### Port Conflicts

```bash
# Find what's using a port
lsof -i :8000  # macOS/Linux
netstat -tlnp | grep 8000  # Linux

# Kill the conflicting process
kill <PID>

# Or change the MADSci port in .env
EVENT_SERVER_PORT=8011  # Use a different port
```

## Performance Issues

### Slow Workflow Execution

1. Check node response times:
   ```bash
   time curl http://localhost:2000/health
   ```

2. Check database performance:
   ```bash
   docker stats  # Watch CPU/memory usage
   ```

3. Check disk I/O:
   ```bash
   iostat -x 1  # Linux
   ```

4. If using OTEL, check Jaeger traces for bottlenecks at `http://localhost:16686`

### High Memory Usage

```bash
# Check container memory usage
docker stats --no-stream

# Check MongoDB memory
docker compose exec mongodb mongosh --eval "db.serverStatus().mem"

# Restart memory-heavy service
docker compose restart <service_name>
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up unused Docker resources
docker system prune  # Remove stopped containers, unused images

# Check log file sizes
du -sh /var/lib/docker/containers/*/
```

## Recovery Procedures

### Full Lab Reset (Preserving Data)

```bash
# Stop everything
docker compose down

# Restart everything
docker compose up -d

# Verify
madsci status
```

### Full Lab Reset (Clean Slate)

```bash
# WARNING: This deletes all data!
docker compose down -v
docker compose up -d
```

### Restore from Backup

See [Backup & Recovery](./03-backup-recovery.md) for detailed restore procedures.

## Getting Help

If you can't resolve an issue:

1. Collect diagnostic information:
   ```bash
   madsci doctor --json > diagnostics.json
   madsci status --json > status.json
   madsci logs --tail 200 --json > recent_logs.json
   ```

2. Check the [MADSci documentation](https://ad-sdl.github.io/MADSci/)

3. Open an issue on [GitHub](https://github.com/AD-SDL/MADSci) with:
   - MADSci version (`madsci version`)
   - Operating system and Docker version
   - Steps to reproduce
   - Diagnostic output from step 1

## What's Next?

- [Updates & Maintenance](./05-updates-maintenance.md) - Upgrading MADSci
- [Monitoring](./02-monitoring.md) - Set up proactive monitoring
