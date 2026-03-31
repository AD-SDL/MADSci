# FOSS Stack Migration Guide

Migrate your MADSci lab from the proprietary infrastructure stack (MongoDB, Redis, MinIO) to the fully open-source alternatives (FerretDB, Valkey, SeaweedFS).

## Overview

Starting with MADSci v0.7.1, the default infrastructure uses FOSS (Free and Open-Source Software) alternatives:

| Old (Proprietary) | New (FOSS) | Protocol Compatibility |
|---|---|---|
| MongoDB | FerretDB (backed by PostgreSQL) | MongoDB wire protocol |
| Redis | Valkey | Redis API-compatible |
| MinIO | SeaweedFS | S3-compatible |
| PostgreSQL | PostgreSQL (unchanged) | N/A |

The Python clients (`pymongo`, `redis`, `minio`) remain the same — only the server-side software changes.

## Prerequisites

### Required Tools

- **Docker** and Docker Compose
- **MongoDB Database Tools** (`mongodump`, `mongorestore`) — [Install guide](https://www.mongodb.com/docs/database-tools/installation/)
- **PostgreSQL client tools** (`pg_dump`, `pg_restore`, `psql`) — usually included with `postgresql-client`
- **MADSci CLI** (`madsci`) — installed from the MADSci package

Verify prerequisites:
```bash
madsci migrate foss --dry-run
```

### Existing Data

The migration tool looks for data in these directories (relative to your project root):

| Component | Expected Path |
|---|---|
| MongoDB | `.madsci/mongodb/` |
| PostgreSQL | `.madsci/postgresql/data/` |
| Redis | `.madsci/redis/` |
| MinIO | `.madsci/minio/` |

## Quick Start

```bash
# 1. Preview the migration plan
madsci migrate foss --dry-run

# 2. Run the full migration
madsci migrate foss --apply

# 3. Verify the results
madsci migrate foss --apply --step document-db  # Re-run individual steps if needed
```

## Automated Migration

### Full Migration

```bash
madsci migrate foss --apply
```

This will:
1. Check prerequisites (CLI tools on PATH)
2. Create a pre-migration backup of old data directories
3. Start old MongoDB, PostgreSQL, and Redis containers on alternate ports
4. Start new FOSS infrastructure (FerretDB, Valkey, SeaweedFS)
5. Migrate document databases (`mongodump` / `mongorestore`)
6. Migrate PostgreSQL data (`pg_dump` / `pg_restore`)
7. Migrate Location Manager data from old Redis to document database
8. Copy MinIO objects to SeaweedFS (if any)
9. Verify data in the new FOSS stack
10. Stop old containers

> **Important**: Step 7 migrates Location Manager data (locations, resource attachments, node representations) that was stored in Redis in v0.7.x. This data is **not** ephemeral — it is the primary location store. The migration reads from old Redis (port 6380) and writes to FerretDB via the Location Manager migration tool.

### Options

```bash
# Run a single migration step
madsci migrate foss --apply --step document-db
madsci migrate foss --apply --step postgresql
madsci migrate foss --apply --step redis
madsci migrate foss --apply --step object-storage

# Skip pre-migration backup (not recommended)
madsci migrate foss --apply --skip-backup

# Skip Docker container lifecycle (if old containers are already running)
madsci migrate foss --apply --skip-docker

# Override connection URLs
madsci migrate foss --apply \
  --old-mongo-url mongodb://localhost:27018/ \
  --new-mongo-url mongodb://madsci:madsci@localhost:27017/ \
  --old-postgres-url postgresql://madsci:madsci@localhost:5433/resources \
  --new-postgres-url postgresql://madsci:madsci@localhost:5434/resources

# Specify compose file directory
madsci migrate foss --apply --compose-dir /path/to/lab
```

### Environment Variables

All settings can be overridden via environment variables with the `FOSS_MIGRATION_` prefix:

```bash
export FOSS_MIGRATION_OLD_DOCUMENT_DB_URL=mongodb://localhost:27018/
export FOSS_MIGRATION_NEW_DOCUMENT_DB_URL=mongodb://madsci:madsci@localhost:27017/
export FOSS_MIGRATION_OLD_POSTGRES_URL=postgresql://madsci:madsci@localhost:5433/resources
export FOSS_MIGRATION_NEW_POSTGRES_URL=postgresql://madsci:madsci@localhost:5434/resources
```

## Manual Migration

If you prefer to run each step manually, follow the sections below.

### 1. Start the FOSS Stack

```bash
cd examples/example_lab
docker compose -f compose.infra.yaml up -d
```

### 2. Start Old Containers

Use the migration overlay to start old MongoDB, PostgreSQL, and Redis on alternate ports:

```bash
docker compose -f compose.infra.yaml -f compose.migration.yaml up -d \
  madsci_old_mongodb madsci_old_postgres madsci_old_redis
```

This starts:
- Old MongoDB on port **27018** (avoids conflict with FerretDB on 27017)
- Old PostgreSQL on port **5433** (avoids conflict with FerretDB's PostgreSQL on 5432 and Resource Manager's PostgreSQL on 5434)
- Old Redis on port **6380** (avoids conflict with Valkey on 6379)

### 3. Migrate Document Databases

For each database (`madsci_events`, `madsci_experiments`, `madsci_data`, `madsci_workcells`):

```bash
# Dump from old MongoDB
mongodump --host localhost:27018 --db madsci_events --out /tmp/foss_dump

# Restore to FerretDB (with authentication)
mongorestore --host localhost:27017 \
  --username madsci --password madsci \
  --drop --db madsci_events \
  /tmp/foss_dump/madsci_events
```

### 4. Migrate PostgreSQL

```bash
# Dump from old PostgreSQL (port 5433)
PGPASSWORD=madsci pg_dump -h localhost -p 5433 -U madsci -d resources \
  --format=custom --file /tmp/pg_dump.dump

# Restore to new PostgreSQL (port 5434)
PGPASSWORD=madsci pg_restore -h localhost -p 5434 -U madsci -d resources \
  --clean --if-exists /tmp/pg_dump.dump
```

### 5. Migrate Location Manager Data (Redis → Document Database)

In v0.7.x, the Location Manager stores all location data (resource attachments, node representations, transfer state) in Redis. In v0.8.0+, this data is stored in the document database (FerretDB). This step performs an application-level migration.

> **Note**: Direct file copy from Redis to Valkey is not possible because Redis 7.4+ uses RDB format v12, which is incompatible with Valkey 8 (RDB v11). This step reads from old Redis via the Python client and writes to FerretDB.

First, find your Location Manager ID:

```bash
# From old Redis (port 6380)
redis-cli -p 6380 KEYS 'madsci:location_manager:*:locations'
# Output: madsci:location_manager:<MANAGER_ID>:locations
```

Then run the migration tool:

```bash
python -m madsci.location_manager.location_migration \
  --redis-host localhost --redis-port 6380 \
  --document-db-url "mongodb://madsci:madsci@localhost:27017/" \
  --database madsci_locations \
  --manager-id <MANAGER_ID>
```

Verify the migration:

```bash
python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://madsci:madsci@localhost:27017/')
db = client['madsci_locations']
count = db['locations'].count_documents({})
print(f'Migrated {count} locations')
client.close()
"
```

> **Note**: Other Redis data (workcell state, caches) is ephemeral and will be repopulated automatically by managers on startup. Only Location Manager data requires explicit migration.

### 6. Migrate MinIO to SeaweedFS

If you have objects in MinIO, use the `mc` (MinIO Client) tool or the Python SDK to copy them bucket-by-bucket. The automated migration tool handles this with the `minio` Python package.

### 7. Stop Old Containers

```bash
docker compose -f compose.infra.yaml -f compose.migration.yaml down --remove-orphans
```

## Configuration Changes

After migration, update your `.env` file to use the new field names:

```bash
# Old settings (still work via backward-compatible aliases)
MONGO_DB_URL=mongodb://madsci:madsci@localhost:27017/

# New settings (recommended)
DOCUMENT_DB_URL=mongodb://madsci:madsci@localhost:27017/
```

Key renames:
- `MONGO_DB_URL` → `DOCUMENT_DB_URL`
- `MONGODB_PORT` → `DOCUMENT_DB_PORT`
- `MINIO_PORT` → `OBJECT_STORAGE_PORT`

The old names are still accepted via `validation_alias` for backward compatibility.

## Verification

After migration, verify that data is accessible:

```bash
# Check document databases
python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://madsci:madsci@localhost:27017/')
for db_name in ['madsci_events', 'madsci_experiments', 'madsci_data', 'madsci_workcells']:
    db = client[db_name]
    collections = db.list_collection_names()
    print(f'{db_name}: {len(collections)} collections')
    for c in collections:
        count = db[c].count_documents({})
        print(f'  {c}: {count} documents')
client.close()
"

# Check PostgreSQL (Resource Manager on port 5434)
PGPASSWORD=madsci psql -h localhost -p 5434 -U madsci -d resources \
  -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"

# Check Valkey
redis-cli ping
```

## Rollback

If something goes wrong, restore from the pre-migration backup:

```bash
# Backups are stored in .madsci/backups/foss_migration/
ls -la .madsci/backups/foss_migration/

# Restore MongoDB data
docker compose -f compose.infra.yaml down
cp -r .madsci/backups/foss_migration/pre_migration_YYYYMMDD_HHMMSS/mongodb/ .madsci/mongodb/
# Restart your original stack (you'll need to switch compose files back)
```

## Troubleshooting

### FerretDB Authentication Errors

FerretDB requires authentication (unlike standalone MongoDB). Ensure your connection URLs include credentials:

```
mongodb://madsci:madsci@localhost:27017/
```

### PostgreSQL Architecture

The FOSS stack runs two separate PostgreSQL containers for clean separation of concerns:

- **`madsci_postgres`** (port 5432) — `ghcr.io/ferretdb/postgres-documentdb-dev:17-ferretdb`. Used exclusively by FerretDB for document storage (Event, Experiment, Data, Workcell managers). The DocumentDB extension and `pg_cron` are installed by the image's built-in init scripts.
- **`madsci_postgres_resources`** (port 5434) — Standard `postgres:17`. Used exclusively by the Resource Manager for relational data (SQLModel/Alembic). No special extensions needed.

This two-container approach avoids schema conflicts and allows each service to use the most appropriate PostgreSQL image. The Resource Manager container is lightweight (plain upstream postgres), while the FerretDB backend gets the heavier DocumentDB-enabled image it requires.

### Permission Errors on Data Directories

PostgreSQL requires read-write access to its data directory for WAL recovery. If running Docker with volume mounts, ensure the directory permissions allow the `postgres` user (UID 999) to write.

### mongodump/mongorestore Not Found

Install MongoDB Database Tools:

```bash
# macOS
brew tap mongodb/brew
brew install mongodb-database-tools

# Ubuntu/Debian
wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2204-x86_64-100.9.4.deb
sudo dpkg -i mongodb-database-tools-*.deb

# Or download from: https://www.mongodb.com/try/download/database-tools
```

### MongoDB Version Mismatch

If old MongoDB data was created with a newer version (e.g., MongoDB 8.0 with Feature Compatibility Version 8.0), the old container must use a matching image version. Set the `OLD_MONGODB_VERSION` environment variable:

```bash
export OLD_MONGODB_VERSION=8
madsci migrate foss --apply
```

Or in your `.env` file:
```bash
OLD_MONGODB_VERSION=8
```

### PostgreSQL Data Directory Conflict

The migration tool automatically handles the conflict between old and new PostgreSQL data directories. The old data is moved from `.madsci/postgresql/data/` to `.madsci/postgresql_old/data/` so the new FOSS PostgreSQL can initialize fresh with the DocumentDB extension required by FerretDB.

If you see `schema "documentdb_api" does not exist` or `extension "documentdb" does not exist` errors, ensure the `madsci_postgres` (DocumentDB) container started with a clean data directory so the built-in init scripts ran.

### Valkey RDB Format Incompatibility

Redis RDB format version 12 (from Redis 7.4+) is not compatible with Valkey 8. Direct file copy from `.madsci/redis/` to `.madsci/valkey/` will not work.

The automated migration tool handles this by performing an application-level migration of Location Manager data (the only non-ephemeral Redis data) directly from old Redis to FerretDB. Other Redis data (workcell state, caches) is ephemeral and repopulated by managers on startup.

If you see `Can't handle RDB format version 12` errors in Valkey logs, clear the data directory:
```bash
rm -rf .madsci/valkey/*
```
Restart Valkey — it will start fresh. This is safe because all persistent data has been migrated to the document database.

### Migration Hangs on "Start Old Containers"

Check that Docker is running and the old data directories exist at the expected paths. The migration overlay expects `.madsci/mongodb/` and `.madsci/postgresql_old/data/` to contain valid database files. The migration tool moves old PostgreSQL data from `.madsci/postgresql/data/` to `.madsci/postgresql_old/data/` automatically.

### MinIO Data Directory Contains Only Metadata

If `.madsci/minio/` exists but only contains the `.minio.sys/` internal metadata directory, the migration tool will skip the object storage step automatically. This is common for labs that haven't stored any objects in MinIO.

### SeaweedFS S3 Compatibility Issues

SeaweedFS supports the core S3 API but may not support all MinIO-specific extensions. If you encounter issues with specific bucket policies or lifecycle rules, those may need to be reconfigured manually in SeaweedFS.
