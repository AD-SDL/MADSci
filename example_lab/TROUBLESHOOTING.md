# Example Lab Troubleshooting Guide

This guide provides solutions to common issues when running the MADSci example lab, with specific commands and debugging steps.

## Quick Diagnostic Commands

Before diving into specific issues, run these commands to get an overview of your lab status:

```bash
# Check all service status
docker compose ps

# View recent logs from all services
docker compose logs --tail=20

# Check if all expected ports are listening
netstat -tuln | grep -E '(8000|8001|8002|8003|8004|8005|8006|2000|2001|2002|2003|2004)'

# Test manager health endpoints
for port in 8000 8001 8002 8003 8004 8005 8006; do
  echo "Testing port $port:"
  curl -s http://localhost:$port/health || echo "  ❌ Failed"
done
```

## Startup Issues

### Problem: Services Won't Start

**Symptoms:**
- `docker compose up` fails immediately
- Container exit codes 1 or 125
- "Port already in use" errors

**Diagnostic Steps:**
```bash
# Check Docker status
docker --version
docker info

# Verify compose file syntax
docker compose config

# Check port conflicts
ss -tulpn | grep -E ':(8000|8001|8002|8003|8004|8005|8006|2000|2001|2002|2003|2004|5432|6379|27017|9000|9001)\s'
```

**Solutions:**

1. **Port Conflicts:**
```bash
# Find process using conflicting port
sudo lsof -i :8000  # Replace with conflicting port
# Kill the process or change MADSci port configuration
```

2. **Docker Resources:**
```bash
# Clean up old containers and images
docker compose down -v --remove-orphans
docker system prune -f

# Check available disk space
df -h
```

3. **Permission Issues:**
```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Check file permissions
ls -la .env compose.yaml
```

### Problem: Database Connection Errors

**Symptoms:**
- "Connection refused" errors
- Managers fail to start after databases
- Database containers restart repeatedly

**Diagnostic Steps:**
```bash
# Check database container status
docker compose ps postgres mongodb redis

# View database logs
docker compose logs postgres
docker compose logs mongodb
docker compose logs redis

# Test database connections directly
docker compose exec postgres psql -U madsci -d resources -c "\dt"
docker compose exec mongodb mongosh --eval "db.adminCommand('listDatabases')"
docker compose exec redis redis-cli ping
```

**Solutions:**

1. **PostgreSQL Issues:**
```bash
# Reset PostgreSQL data
docker compose down
docker volume rm madsci_example_lab_postgres_data  # if using named volumes
sudo rm -rf .madsci/postgres/*  # if using bind mounts
docker compose up postgres

# Check PostgreSQL logs
docker compose logs postgres | grep -i error
```

2. **MongoDB Issues:**
```bash
# Reset MongoDB data
docker compose down
sudo rm -rf .madsci/mongodb/*
docker compose up mongodb

# Verify MongoDB is accepting connections
docker compose exec mongodb mongosh --eval "db.runCommand({ping: 1})"
```

3. **Redis Issues:**
```bash
# Reset Redis data
docker compose down
sudo rm -rf .madsci/redis/*
docker compose up redis

# Test Redis connectivity
docker compose exec redis redis-cli ping
```

## Node Communication Issues

### Problem: Nodes Not Registering

**Symptoms:**
- Nodes start but don't appear in dashboard
- "Node not found" errors in workflows
- Empty node list in API responses

**Diagnostic Steps:**
```bash
# Check node container status
docker compose ps | grep -E "(liquidhandler|robotarm|platereader|advanced_example)"

# Test node health endpoints
for port in 2000 2001 2002 2003 2004; do
  echo "Testing node on port $port:"
  curl -s http://localhost:$port/health || echo "  ❌ Failed"
done

# Check node registration with lab manager
curl http://localhost:8000/api/nodes | jq '.[].node_name'

# Check workcell manager node status
curl http://localhost:8005/nodes | jq '.[].node_id'
```

**Solutions:**

1. **Node Configuration Issues:**
```bash
# Verify node definition files exist
ls -la example_lab/node_definitions/

# Check YAML syntax
python -c "import yaml; print(yaml.safe_load(open('node_definitions/liquidhandler_1.node.yaml')))"

# Verify environment variables
docker compose exec liquidhandler_1 env | grep NODE_
```

2. **Network Connectivity:**
```bash
# Test inter-container communication
docker compose exec liquidhandler_1 curl http://lab_manager:8000/health

# Check Docker network
docker network ls
docker network inspect madsci_example_lab_default
```

3. **Node Module Errors:**
```bash
# Check node startup logs
docker compose logs liquidhandler_1 | grep -i error

# Test node module directly
docker compose exec liquidhandler_1 python -c "from example_modules.liquidhandler import LiquidHandlerNode; print('Import successful')"
```

### Problem: Action Execution Failures

**Symptoms:**
- Actions timeout or fail
- HTTP 500 errors from node endpoints
- "Action not found" errors

**Diagnostic Steps:**
```bash
# Test action execution directly
curl -X POST http://localhost:2000/actions/run_command \
  -H "Content-Type: application/json" \
  -d '{"command": "test"}' \
  -v

# Check available actions
curl http://localhost:2000/definition | jq '.actions'

# Monitor action execution
docker compose logs -f liquidhandler_1
```

**Solutions:**

1. **Action Definition Issues:**
```bash
# Verify action methods are decorated
grep -n "@action" example_modules/liquidhandler.py

# Check method signatures
python -c "
from example_modules.liquidhandler import LiquidHandlerNode
import inspect
node = LiquidHandlerNode()
print([m for m in dir(node) if hasattr(getattr(node, m), '_is_action')])
"
```

2. **Hardware Interface Problems:**
```bash
# Check hardware interface initialization
docker compose logs liquidhandler_1 | grep -i "hardware\|initialized\|startup"

# Test with minimal action
curl -X POST http://localhost:2000/actions/get_location
```

## Workflow Execution Problems

### Problem: Workflows Fail to Start

**Symptoms:**
- Workflow submission returns errors
- "Resource not found" errors
- "Node unavailable" messages

**Diagnostic Steps:**
```bash
# Check workcell manager status
curl http://localhost:8005/health
curl http://localhost:8005/status

# List available workflows
ls -la workflows/

# Validate workflow YAML syntax
python -c "import yaml; print(yaml.safe_load(open('workflows/simple_transfer.workflow.yaml')))"

# Check resource availability
curl http://localhost:8003/resources | jq '.[].resource_name'
```

**Solutions:**

1. **Resource Management Issues:**
```bash
# Check resource templates
curl http://localhost:8003/templates | jq '.[].template_name'

# Verify resource creation
curl http://localhost:8003/resources | jq '.[] | select(.node_id != null)'

# Check resource locations
curl http://localhost:8006/locations | jq '.'
```

2. **Workflow Configuration:**
```bash
# Test with minimal workflow
cat > test_workflow.yaml << 'EOF'
name: Test Workflow
steps:
  - name: Test Step
    key: test
    action: get_status
    node: liquidhandler_1
EOF

# Submit test workflow via API
curl -X POST http://localhost:8005/workflows \
  -H "Content-Type: application/json" \
  -d '{"workflow_file": "test_workflow.yaml"}'
```

### Problem: Workflows Hang or Timeout

**Symptoms:**
- Workflows start but never complete
- Steps remain in "executing" state indefinitely
- No progress updates in dashboard

**Diagnostic Steps:**
```bash
# Check active workflows
curl http://localhost:8005/workflows | jq '.[] | select(.status == "running")'

# Monitor workflow execution
curl http://localhost:8005/workflows/{workflow_id}/status

# Check node action queues
curl http://localhost:2000/queue
```

**Solutions:**

1. **Node Communication Issues:**
```bash
# Test direct node communication
curl -X POST http://localhost:2000/actions/run_command \
  -H "Content-Type: application/json" \
  -d '{"command": "ping"}' \
  -w "%{time_total}s\n"

# Check node resource states
curl http://localhost:2000/resources
```

2. **Resource Lock Issues:**
```bash
# Check for locked resources
curl http://localhost:8003/resources | jq '.[] | select(.locked == true)'

# Reset resource states (if safe to do so)
curl -X POST http://localhost:8003/resources/unlock-all
```

## Dashboard and UI Issues

### Problem: Dashboard Won't Load

**Symptoms:**
- Browser shows "Connection refused"
- Dashboard loads but shows no data
- JavaScript errors in browser console

**Diagnostic Steps:**
```bash
# Check lab manager status
curl http://localhost:8000/health
docker compose logs lab_manager

# Test API endpoints
curl http://localhost:8000/api/status
curl http://localhost:8000/api/nodes

# Check static file serving
curl -I http://localhost:8000/
```

**Solutions:**

1. **Lab Manager Issues:**
```bash
# Restart lab manager
docker compose restart lab_manager

# Check configuration
docker compose logs lab_manager | grep -i "config\|error"

# Verify dashboard files
docker compose exec lab_manager ls -la /home/madsci/ui/dist/
```

2. **Network Configuration:**
```bash
# Check Docker port mapping
docker compose port lab_manager 8000

# Test from different network
curl http://127.0.0.1:8000/health
```

### Problem: Data Not Appearing in Dashboard

**Symptoms:**
- Dashboard loads but shows empty node lists
- Historical data missing
- Real-time updates not working

**Diagnostic Steps:**
```bash
# Check all manager connectivity
for port in 8001 8002 8003 8004 8005 8006; do
  echo "Manager on port $port:"
  curl -s http://localhost:$port/status | jq '.status' || echo "Failed"
done

# Check database connectivity
curl http://localhost:8001/events | jq '.[] | .timestamp' | head -5
curl http://localhost:8003/resources | jq 'length'
```

**Solutions:**

1. **Manager Synchronization:**
```bash
# Restart all managers in order
docker compose restart event_manager
sleep 10
docker compose restart resource_manager location_manager
sleep 10
docker compose restart experiment_manager data_manager workcell_manager
sleep 10
docker compose restart lab_manager
```

2. **Database Seeding:**
```bash
# Check if initial data exists
docker compose exec mongodb mongosh madsci --eval "db.events.countDocuments()"
docker compose exec postgres psql -U madsci -d resources -c "SELECT COUNT(*) FROM resources;"

# If needed, reinitialize the lab
docker compose down
docker compose up
```

## Performance Issues

### Problem: Slow Response Times

**Symptoms:**
- API calls take >5 seconds
- Dashboard updates are sluggish
- Workflow steps time out

**Diagnostic Steps:**
```bash
# Check system resources
docker stats

# Monitor response times
time curl http://localhost:8000/api/nodes
time curl http://localhost:8003/resources

# Check database performance
docker compose exec mongodb mongosh --eval "db.runCommand({serverStatus: 1}).connections"
docker compose exec postgres psql -U madsci -d resources -c "SELECT * FROM pg_stat_activity;"
```

**Solutions:**

1. **Resource Allocation:**
```bash
# Increase Docker memory limits (if using Docker Desktop)
# Edit Docker Desktop settings: Resources > Advanced > Memory

# Check available system memory
free -h
```

2. **Database Optimization:**
```bash
# Create database indexes (if needed)
docker compose exec mongodb mongosh madsci --eval "db.events.createIndex({timestamp: -1})"

# PostgreSQL maintenance
docker compose exec postgres psql -U madsci -d resources -c "VACUUM ANALYZE;"
```

### Problem: High Memory Usage

**Symptoms:**
- Containers being killed (OOMKilled)
- System becomes unresponsive
- "No space left on device" errors

**Diagnostic Steps:**
```bash
# Check container memory usage
docker stats --no-stream

# Check disk usage
df -h
docker system df

# Monitor log file sizes
ls -lah .madsci/logs/
```

**Solutions:**

1. **Log Rotation:**
```bash
# Configure Docker log rotation
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF
sudo systemctl restart docker
```

2. **Data Cleanup:**
```bash
# Clean old Docker data
docker system prune -f --volumes

# Rotate log files
find .madsci/logs/ -name "*.log" -mtime +7 -delete
```

## Advanced Debugging

### Enable Debug Logging

```bash
# Add debug environment variables
echo "EVENT_CLIENT_LOG_LEVEL=10" >> .env
echo "WORKCELL_SCHEDULER_LOG_LEVEL=10" >> .env

# Restart with debug logging
docker compose down
docker compose up
```

### Database Direct Access

```bash
# MongoDB debugging
docker compose exec mongodb mongosh madsci

# PostgreSQL debugging
docker compose exec postgres psql -U madsci -d resources

# Redis debugging
docker compose exec redis redis-cli
```

### Network Analysis

```bash
# Capture network traffic between containers
docker run --rm --net container:madsci_example_lab_lab_manager_1 \
  nicolaka/netshoot tcpdump -i eth0 port 8001

# Test DNS resolution
docker compose exec lab_manager nslookup event_manager
```

### Resource Monitoring

```bash
# Real-time resource monitoring
watch -n 2 'docker stats --no-stream'

# Process monitoring inside containers
docker compose exec lab_manager top
```

## Getting Additional Help

### Log Collection

When reporting issues, collect comprehensive logs:

```bash
# Create comprehensive log archive
mkdir -p madsci_logs
docker compose logs > madsci_logs/all_services.log
docker compose ps > madsci_logs/container_status.txt
docker info > madsci_logs/docker_info.txt
cp .env madsci_logs/ 2>/dev/null || echo "No .env file"
tar -czf madsci_debug_logs_$(date +%Y%m%d_%H%M%S).tar.gz madsci_logs/
```

### System Information

```bash
# Collect system information
echo "=== System Info ===" > system_info.txt
uname -a >> system_info.txt
docker --version >> system_info.txt
docker compose --version >> system_info.txt
free -h >> system_info.txt
df -h >> system_info.txt
```

### Configuration Validation

```bash
# Validate all YAML files
for file in node_definitions/*.yaml managers/*.yaml workflows/*.yaml; do
  echo "Checking $file:"
  python -c "import yaml; yaml.safe_load(open('$file'))" && echo "  ✅ Valid" || echo "  ❌ Invalid"
done

# Check environment configuration
docker compose config --quiet && echo "Compose config valid" || echo "Compose config invalid"
```

## Prevention Best Practices

1. **Regular Health Checks:**
```bash
# Add to crontab for automated monitoring
*/5 * * * * curl -f http://localhost:8000/health >/dev/null 2>&1 || echo "Lab manager down" | mail admin@lab.com
```

2. **Backup Important Data:**
```bash
# Backup lab configuration and data
tar -czf backup_$(date +%Y%m%d).tar.gz \
  .env \
  example_lab/node_definitions/ \
  example_lab/managers/ \
  example_lab/workflows/ \
  .madsci/
```

3. **Resource Monitoring:**
```bash
# Monitor disk space
df -h | awk '$5 > 80 {print "Disk usage warning: " $0}'

# Monitor container health
docker compose ps | grep -v "Up" && echo "Containers down!"
```

4. **Update Management:**
```bash
# Pull latest images regularly
docker compose pull
docker compose up -d

# Clean up old images
docker image prune -f
```

For more help:
- Check the main [README](README.md) for setup instructions
- Review [Configuration.md](../Configuration.md) for all available settings
- Search issues in the [MADSci repository](https://github.com/AD-SDL/MADSci/issues)
- Join the MADSci community discussions
