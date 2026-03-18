# Backup and Recovery

**Audience**: Lab Operator
**Prerequisites**: [Daily Operations](./01-daily-operations.md)
**Time**: ~25 minutes

## Overview

MADSci stores critical data across multiple databases. Regular backups protect against data loss from hardware failures, software bugs, or accidental deletion. This guide covers backup strategies for all MADSci data stores.

## Data Stores

| Database | Used By | Data Stored |
|----------|---------|-------------|
| FerretDB (document database) | Event, Experiment, Data, Workcell, Location Managers | Events, experiments, datapoints, workflows, locations |
| PostgreSQL | Resource Manager | Resources, resource history, templates |
| SeaweedFS (object storage) | Data Manager | File datapoints (CSVs, images, etc.) |
| Valkey | Workcell Manager | Workflow queue, node locks (ephemeral) |

**Note**: Valkey data is ephemeral (workflow queue state). It does not require backup; the workcell recovers from the document database on restart.

## Backup Tools

MADSci provides unified backup tools in the `madsci_common` package.

### PostgreSQL Backups

```python
from madsci.common.backup_tools import PostgreSQLBackupTool
from madsci.common.types.backup_types import PostgreSQLBackupSettings

settings = PostgreSQLBackupSettings(
    db_url="postgresql://postgres:postgres@localhost:5432/resources",
    backup_dir=Path("./backups/postgres"),
    max_backups=10,
    validate_integrity=True,
)

backup_tool = PostgreSQLBackupTool(settings)

# Create a backup
backup_path = backup_tool.create_backup("daily")
print(f"Backup created: {backup_path}")

# List available backups
backups = backup_tool.list_available_backups()
for b in backups:
    print(f"  {b.backup_path} ({b.backup_size} bytes, {b.created_at})")

# Validate a backup
is_valid = backup_tool.validate_backup_integrity(backup_path)
print(f"Backup valid: {is_valid}")

# Restore from backup
backup_tool.restore_from_backup(backup_path)
```

### Document Database Backups

```python
from madsci.common.backup_tools import DocumentDBBackupTool
from madsci.common.types.backup_types import DocumentDBBackupSettings
from pydantic import AnyUrl

settings = DocumentDBBackupSettings(
    document_db_url=AnyUrl("mongodb://localhost:27017/"),
    database="events",
    backup_dir=Path("./backups/document_db"),
    max_backups=10,
)

backup_tool = DocumentDBBackupTool(settings)

# Create a backup
backup_path = backup_tool.create_backup("daily")

# List backups
backups = backup_tool.list_available_backups()

# Restore
backup_tool.restore_from_backup(backup_path)
```

### CLI Backup Commands

```bash
# PostgreSQL backup
madsci-postgres-backup create \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-dir ./backups/postgres

# Document database backup
madsci-document-db-backup create \
  --mongo-url mongodb://localhost:27017 \
  --database events \
  --backup-dir ./backups/document_db

# Unified CLI (auto-detects database type)
madsci-backup create --db-url postgresql://localhost:5432/resources
madsci-backup create --db-url mongodb://localhost:27017/events

# List backups
madsci-backup list --backup-dir ./backups/postgres

# Restore
madsci-backup restore \
  --db-url postgresql://localhost:5432/resources \
  --backup-path ./backups/postgres/backup_20260209_daily.sql
```

## Backup Strategy

### Recommended Schedule

| Database | Frequency | Retention | Notes |
|----------|-----------|-----------|-------|
| PostgreSQL (Resources) | Every 6 hours | 30 days | Critical - contains resource state |
| FerretDB (Events) | Daily | 90 days | Large volume, archivable |
| FerretDB (Experiments) | Every 6 hours | 90 days | Contains experiment results |
| FerretDB (Data) | Daily | 90 days | Metadata only; files in SeaweedFS |
| FerretDB (Workcell) | Daily | 30 days | Workflow history |
| FerretDB (Locations) | Daily | 30 days | Location configuration |
| SeaweedFS (Files) | Daily | 90 days | Use SeaweedFS's built-in replication |

### Automated Backups with Cron

```bash
# /etc/cron.d/madsci-backups

# PostgreSQL - every 6 hours
0 */6 * * * madsci-postgres-backup create \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-dir /data/backups/postgres \
  --max-backups 120

# Document database events - daily at 2 AM
0 2 * * * madsci-document-db-backup create \
  --mongo-url mongodb://localhost:27017 \
  --database events \
  --backup-dir /data/backups/document_db/events \
  --max-backups 90

# Document database experiments - every 6 hours
0 */6 * * * madsci-document-db-backup create \
  --mongo-url mongodb://localhost:27017 \
  --database experiments \
  --backup-dir /data/backups/document_db/experiments \
  --max-backups 120
```

### Backup Validation

Always validate backups periodically:

```python
from madsci.common.backup_tools import BackupValidator

validator = BackupValidator()

# Validate a specific backup
result = validator.validate(backup_path)
print(f"Valid: {result.is_valid}")
print(f"Checksum: {result.checksum}")
print(f"Size: {result.backup_size} bytes")
```

## Recovery Procedures

### Scenario 1: Single Database Corruption

```bash
# 1. Stop the affected manager
docker compose stop resource_manager

# 2. Restore from latest backup
madsci-postgres-backup restore \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-path /data/backups/postgres/latest.sql

# 3. Restart the manager
docker compose start resource_manager

# 4. Verify health
curl http://localhost:8003/health
```

### Scenario 2: Full System Recovery

```bash
# 1. Start infrastructure only
docker compose up -d madsci_ferretdb postgres madsci_valkey madsci_seaweedfs

# 2. Wait for databases to be ready
sleep 10

# 3. Restore PostgreSQL
madsci-postgres-backup restore \
  --db-url postgresql://postgres:postgres@localhost:5432/resources \
  --backup-path /data/backups/postgres/latest.sql

# 4. Restore document databases
for db in events experiments data workcell locations; do
  madsci-document-db-backup restore \
    --mongo-url mongodb://localhost:27017 \
    --database $db \
    --backup-path /data/backups/document_db/$db/latest.bson
done

# 5. Start managers
docker compose up -d

# 6. Verify all services
madsci status
```

### Scenario 3: Pre-Migration Backup

Before running database migrations, always create a backup:

```bash
# The migration tool creates automatic backups
python -m madsci.resource_manager.migration_tool \
  --db-url postgresql://postgres:postgres@localhost:5432/resources

# If migration fails, it auto-restores from the backup
```

## SeaweedFS Backup

SeaweedFS stores file datapoints (CSVs, images, raw instrument data). SeaweedFS provides an S3-compatible API, so you can use standard S3 tools:

```bash
# Using the MinIO client (mc) for S3-compatible access
mc alias set myseaweedfs http://localhost:8333 madsci madsci

# Mirror to backup location
mc mirror myseaweedfs/madsci-data /data/backups/seaweedfs/

# Or use mc cp for specific buckets
mc cp --recursive myseaweedfs/madsci-data/ /data/backups/seaweedfs/madsci-data/
```

## Docker Volume Backups

For simple setups, you can back up Docker volumes directly:

```bash
# List volumes
docker volume ls | grep madsci

# Backup a volume
docker run --rm \
  -v madsci_ferretdb_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/ferretdb_data.tar.gz /data

# Restore a volume
docker run --rm \
  -v madsci_ferretdb_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/ferretdb_data.tar.gz -C /
```

## Backup Checklist

- [ ] Backup schedule configured and running
- [ ] Backup retention policy set (avoid filling disk)
- [ ] Backups stored on separate physical storage
- [ ] Backup validation running periodically
- [ ] Recovery procedure tested at least once
- [ ] Team knows where backups are stored
- [ ] Monitoring alerts on backup failures

## What's Next?

- [Troubleshooting](./04-troubleshooting.md) - Common issues and solutions
- [Updates & Maintenance](./05-updates-maintenance.md) - Upgrading MADSci
