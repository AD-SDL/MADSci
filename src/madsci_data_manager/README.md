# MADSci Data Manager

Handles capturing, storing, and querying data generated during experiments - both JSON values and files.

![MADSci Data Manager Diagram](./assets/data_manager.drawio.svg)

## Features

- **DataPoint storage**: JSON values and files with metadata
- **Flexible storage**: Local filesystem or S3-compatible object storage (MinIO, AWS S3, GCS)
- **Rich metadata**: Ownership info, timestamps, custom labels
- **Queryable**: Search by value and metadata
- **Cloud integration**: Multi-provider cloud storage support

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:

- PyPI: `pip install madsci.data_manager`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example configuration**: See [example_lab/managers/example_data.manager.yaml](../../example_lab/managers/example_data.manager.yaml)

**Dependencies**: MongoDB database, optional MinIO/S3 storage (see [example_lab](../../example_lab/))

## Usage

### Quick Start

Use the [example_lab](../../example_lab/) as a starting point:

```bash
# Start with working example
docker compose up  # From repo root
# Data Manager available at http://localhost:8004/docs

# Or run standalone
python -m madsci.data_manager.data_server
```

### Manager Setup

For custom deployments, see [example_data.manager.yaml](../../example_lab/managers/example_data.manager.yaml) for configuration options.

### Data Client

Use `DataClient` to store and retrieve experimental data:

```python
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import ValueDataPoint, FileDataPoint
from datetime import datetime

client = DataClient(url="http://localhost:8004")

# Store JSON data
value_dp = ValueDataPoint(
    label="Temperature Reading",
    value={"temperature": 23.5, "unit": "Celsius"},
    data_timestamp=datetime.now()
)
submitted = client.submit_datapoint(value_dp)

# Store files
file_dp = FileDataPoint(
    label="Experiment Log",
    path="/path/to/data.txt",
    data_timestamp=datetime.now()
)
submitted_file = client.submit_datapoint(file_dp)

# Retrieve data
retrieved = client.get_datapoint(submitted.datapoint_id)

# Save file locally
client.save_datapoint_value(submitted_file.datapoint_id, "/local/save/path.txt")
```

**Examples**: See [example_lab/notebooks/experiment_notebook.ipynb](../../example_lab/notebooks/experiment_notebook.ipynb) for data management workflows.
## Storage Options

### Local Storage (Default)
- Files stored on filesystem
- Simple setup, no additional dependencies
- File paths stored in database

### Object Storage (Optional)
Supports S3-compatible storage (MinIO, AWS S3, Google Cloud Storage):
- Automatic upload to object storage
- Fallback to local storage if upload fails
- Better for large files and distributed setups

### Object Storage Configuration

See [example_data.manager.yaml](../../example_lab/managers/example_data.manager.yaml) for MinIO configuration.

**Quick setup with example_lab:**
```bash
docker compose up  # Includes pre-configured MinIO
# MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
```


## Cloud Storage Integration

Supports S3-compatible storage providers for large file handling:

### Supported Providers
- **AWS S3**
- **Google Cloud Storage** (with HMAC keys)
- **MinIO** (self-hosted or cloud)
- **Any S3-compatible service**

### Configuration Examples

**AWS S3:**
```python
from madsci.common.types.datapoint_types import ObjectStorageSettings

aws_config = ObjectStorageSettings(
    endpoint="s3.amazonaws.com",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    secure=True,
    default_bucket="my-bucket",
    region="us-east-1"
)
client = DataClient(object_storage_settings=aws_config)
```

**Google Cloud Storage:**
```python
gcs_config = ObjectStorageSettings(
    endpoint="storage.googleapis.com",
    access_key="YOUR_HMAC_ACCESS_KEY",
    secret_key="YOUR_HMAC_SECRET",
    secure=True,
    default_bucket="my-gcs-bucket"
)
```

### Direct Object Storage DataPoints
```python
from madsci.common.types.datapoint_types import ObjectStorageDataPoint

storage_dp = ObjectStorageDataPoint(
    label="Large Dataset",
    path="/path/to/data.parquet",
    bucket_name="my-bucket",
    object_name="datasets/data.parquet",
    custom_metadata={"version": "v2.1"}
)
uploaded = client.submit_datapoint(storage_dp)
```

**Authentication**: Use IAM users/service accounts with appropriate storage permissions. See cloud provider documentation for detailed setup.

## Database Migration Tools

MADSci Data Manager includes automated MongoDB migration tools that handle schema changes and version tracking for the data management system.

### Features

- **Version Compatibility Checking**: Automatically detects mismatches between MADSci package version and MongoDB schema version
- **Automated Backup**: Creates MongoDB dumps using `mongodump` before applying migrations to enable rollback on failure
- **Schema Management**: Creates collections and indexes based on schema definitions
- **Index Management**: Ensures required indexes exist for optimal query performance
- **Location Independence**: Auto-detects schema files or accepts explicit paths
- **Safe Migration**: All changes are applied transactionally with automatic rollback on failure

### Usage

#### Standard Usage
```bash
# Run migration for data database (auto-detects schema file)
python -m madsci.common.mongodb_migration_tool --database madsci_data

# Migrate with explicit database URL
python -m madsci.common.mongodb_migration_tool --db-url mongodb://localhost:27017 --database madsci_data

# Use custom schema file
python -m madsci.common.mongodb_migration_tool --database madsci_data --schema-file /path/to/schema.json

# Create backup only
python -m madsci.common.mongodb_migration_tool --database madsci_data --backup-only

# Restore from backup
python -m madsci.common.mongodb_migration_tool --database madsci_data --restore-from /path/to/backup

# Check version compatibility without migrating
python -m madsci.common.mongodb_migration_tool --database madsci_data --check-version
```

#### Docker Usage
When running in Docker containers, use docker-compose to execute migration commands:

```bash
# Run migration for data database in Docker
docker-compose run --rm data-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_data' --schema-file '/app/madsci/data_manager/schema.json'

# Create backup only in Docker
docker-compose run --rm data-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_data' --schema-file '/app/madsci/data_manager/schema.json' --backup-only

# Check version compatibility in Docker
docker-compose run --rm data-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_data' --schema-file '/app/madsci/data_manager/schema.json' --check-version
```

### Server Integration

The Data Manager server automatically checks for version compatibility on startup. If a mismatch is detected, the server will refuse to start and display migration instructions:

```bash
DATABASE INITIALIZATION REQUIRED! SERVER STARTUP ABORTED!
The database exists but needs version tracking setup.
To resolve this issue, run the migration tool and restart the server.
```

### Schema File Location

The migration tool automatically searches for schema files in:
- `madsci/data_manager/schema.json`

### Backup Location

Backups are stored in `.madsci/mongodb/backups/` with timestamped filenames:
- Format: `madsci_data_backup_YYYYMMDD_HHMMSS`
- Can be restored using the `--restore-from` option

### Requirements

- MongoDB server running and accessible
- MongoDB tools (`mongodump`, `mongorestore`) installed
- Appropriate database permissions for the specified user
