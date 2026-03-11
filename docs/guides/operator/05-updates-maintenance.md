# Updates and Maintenance

**Audience**: Lab Operator
**Prerequisites**: [Backup & Recovery](./03-backup-recovery.md)
**Time**: ~20 minutes

## Overview

Keeping MADSci up to date ensures you have the latest features, bug fixes, and security patches. This guide covers upgrade procedures, database migrations, and routine maintenance tasks.

## Checking for Updates

### Current Version

```bash
# Check installed MADSci version
madsci version

# Check all installed package versions
pip list | grep madsci
```

### Available Updates

Check the [MADSci releases page](https://github.com/AD-SDL/MADSci/releases) for new versions and changelogs.

## Upgrade Procedure

### Step 1: Read the Changelog

Before upgrading, review the changelog for:
- **Breaking changes** that require configuration updates
- **Database migrations** that need to be run
- **Deprecation notices** for features being removed
- **New dependencies** that may need to be installed

### Step 2: Create Backups

Always back up before upgrading:

```bash
# Back up all databases
madsci-postgres-backup create \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-dir ./backups/pre-upgrade

for db in events experiments data workcell locations; do
  madsci-document-db-backup create \
    --mongo-url mongodb://localhost:27017 \
    --database $db \
    --backup-dir ./backups/pre-upgrade/document_db
done
```

### Step 3: Stop Services

```bash
# Stop all services
docker compose down
```

### Step 4: Update Code

```bash
# If using git (development install)
git pull origin main
pdm install -G:all

# If using pip (released packages)
pip install --upgrade madsci_common madsci_client madsci_node_module \
  madsci_squid madsci_event_manager madsci_experiment_manager \
  madsci_resource_manager madsci_data_manager madsci_workcell_manager \
  madsci_location_manager madsci_experiment_application
```

### Step 5: Rebuild Docker Images

```bash
# Rebuild all images
docker compose build

# Or rebuild specific services
docker compose build workcell_manager event_manager
```

### Step 6: Run Database Migrations

```bash
# PostgreSQL migrations (Resource Manager)
python -m madsci.resource_manager.migration_tool \
  --db-url postgresql://postgres:postgres@localhost:5432/resources

# Document database migrations (per manager, if needed)
# Check release notes for specific migration commands
```

### Step 7: Start Services

```bash
# Start all services
docker compose up -d

# Verify health
madsci status

# Check for migration warnings
madsci logs --level WARNING --tail 50
```

### Step 8: Verify

```bash
# Run diagnostics
madsci doctor

# Test a simple workflow
# (Use your lab's standard smoke test)
```

## Database Migrations

### PostgreSQL Migrations

The Resource Manager uses Alembic for schema migrations:

```bash
# Check current migration status
python -m madsci.resource_manager.migration_tool --status \
  --db-url postgresql://postgres:postgres@localhost:5432/resources

# Run pending migrations
python -m madsci.resource_manager.migration_tool \
  --db-url postgresql://postgres:postgres@localhost:5432/resources
```

The migration tool automatically:
- Creates a backup before migrating
- Restores the backup if migration fails
- Reports success/failure

### Document Database Migrations

Document database managers (using the MongoDB wire protocol via FerretDB) handle index creation and schema validation on startup. Specific migrations are documented in release notes.

### Definition File Migration

If upgrading from a version that uses definition files (pre-v0.7.0):

```bash
# Scan for files needing migration
madsci migrate scan

# Preview migration
madsci migrate convert --dry-run

# Apply migration
madsci migrate convert --apply

# Verify
madsci migrate status

# After confirming everything works, clean up
madsci migrate finalize
```

## Routine Maintenance

### Log Rotation

MADSci event logs grow over time. Configure retention:

```bash
# Environment variable for Event Manager
EVENT_RETENTION_DAYS=90
EVENT_ARCHIVE_ENABLED=true
EVENT_ARCHIVE_DIR=/data/event_archives
```

### Database Maintenance

#### FerretDB (Document Database)

```bash
# Check database sizes (using the MongoDB wire protocol)
docker compose exec madsci_ferretdb mongosh --eval "
  db.adminCommand('listDatabases').databases.forEach(function(d) {
    print(d.name + ': ' + (d.sizeOnDisk / 1024 / 1024).toFixed(2) + ' MB');
  });
"

# Compact a collection (reclaim disk space)
docker compose exec madsci_ferretdb mongosh events --eval "
  db.runCommand({compact: 'events'})
"
```

#### PostgreSQL

```bash
# Check database size
docker compose exec postgres psql -U postgres -c "
  SELECT pg_database.datname,
         pg_size_pretty(pg_database_size(pg_database.datname))
  FROM pg_database
  ORDER BY pg_database_size(pg_database.datname) DESC;
"

# Run vacuum (reclaim space, update statistics)
docker compose exec postgres psql -U postgres -d resources -c "VACUUM ANALYZE;"
```

### Docker Cleanup

```bash
# Remove unused images
docker image prune

# Remove unused volumes (careful - don't remove data volumes!)
docker volume prune --filter "label!=keep"

# Remove build cache
docker builder prune

# Full cleanup (stopped containers, unused images, unused networks)
docker system prune
```

### Disk Space Monitoring

```bash
# Check overall disk usage
df -h

# Check Docker disk usage
docker system df

# Find large log files
find /var/lib/docker/containers -name "*.log" -size +100M

# Truncate a large container log (if needed)
truncate -s 0 /var/lib/docker/containers/<container_id>/<container_id>-json.log
```

## Rollback Procedure

If an upgrade causes issues:

### Step 1: Stop Services

```bash
docker compose down
```

### Step 2: Restore Code

```bash
# If using git
git checkout <previous_version_tag>
pdm install -G:all

# If using pip
pip install madsci_common==<previous_version> ...
```

### Step 3: Restore Database (if migrations were run)

```bash
# Restore PostgreSQL
madsci-postgres-backup restore \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-path ./backups/pre-upgrade/resources_backup.sql

# Restore document databases
for db in events experiments data workcell locations; do
  madsci-document-db-backup restore \
    --mongo-url mongodb://localhost:27017 \
    --database $db \
    --backup-path ./backups/pre-upgrade/document_db/${db}_backup.bson
done
```

### Step 4: Rebuild and Restart

```bash
docker compose build
docker compose up -d
madsci status
```

## Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Health check | Continuous | `madsci status --watch` |
| Log review | Daily | `madsci logs --level WARNING --since 24h` |
| Database backup | Every 6 hours | Automated via cron |
| Backup validation | Weekly | Restore to test environment |
| Disk space check | Weekly | `df -h && docker system df` |
| Docker cleanup | Monthly | `docker system prune` |
| MADSci update | As released | Follow upgrade procedure |
| Full recovery test | Quarterly | Restore from backup to clean environment |

## What's Next?

- [Daily Operations](./01-daily-operations.md) - Day-to-day lab management
- [Monitoring](./02-monitoring.md) - Set up proactive monitoring
- [Troubleshooting](./04-troubleshooting.md) - When things go wrong
