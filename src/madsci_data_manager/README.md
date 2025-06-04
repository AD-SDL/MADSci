# MADSci Data Manager

Handles capturing, storing, and querying data, in either JSON value or file form, created during the course of an experiment (either collected by instruments, or synthesized during anaylsis).

![MADSci Data Manager Diagram](./assets/data_manager.drawio.svg)

## Notable Features

- Collects and stores data generated in the course of an experiment as "datapoints"
- Current datapoint types supported:
  - Values, as JSON-serializable data
  - Files, stored as-is
- Datapoints include metadata such as ownership info and date-timestamps
- Datapoints are queryable and searchable based on both value and metadata

## Installation

The MADSci Data Manager is available via [the Python Package Index](https://pypi.org/project/madsci.data_manager/), and can be installed via:

```bash
pip install madsci.data_manager
```

This python package is also included as part of the [madsci Docker image](https://github.com/orgs/AD-SDL/packages/container/package/madsci). You can see example docker usage in [the Example Lab Compose File](../../compose.yaml).

Note that you will also need a MongoDB database (included in the example compose file), and can optionally use a MinIO or other S3 compatible object storage for storing files.

## Usage

### Manager

To create and run a new MADSci Data Manager, do the following in your MADSci lab directory:

- If you're not using docker compose, provision and configure a MongoDB instance.
- If you're using docker compose, define your data manager and mongodb services based on the [example compose file](../../compose.yaml).

```bash
# Start the database and Data Manager Server
docker compose up
# OR
python -m madsci.data_manager.data_server
```

You should see a REST server started on the configured host and port. Navigate in your browser to the URL you configured (default: `http://localhost:8004/`) to see if it's working.

You can see up-to-date documentation on the endpoints provided by your event manager, and try them out, via the swagger page served at `http://your-data-manager-url-here/docs`.

### Client

You can use MADSci's `DataClient` (`madsci.client.data_client.DataClient`) in your python code to save, get, or query datapoints.

Here are some examples of using the `DataClient` to interact with the Data Manager:

```python
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import ValueDataPoint, FileDataPoint
from datetime import datetime

# Initialize the DataClient
client = DataClient(url="http://localhost:8004")

# Create a ValueDataPoint
value_datapoint = ValueDataPoint(
    label="Temperature Reading",
    value={"temperature": 23.5, "unit": "Celsius"},
    data_timestamp=datetime.now()
)

# Submit the ValueDataPoint
submitted_value_datapoint = client.submit_datapoint(value_datapoint)
print(f"Submitted ValueDataPoint: {submitted_value_datapoint}")

# Retrieve the ValueDataPoint by ID
retrieved_value_datapoint = client.get_datapoint(submitted_value_datapoint.datapoint_id)
print(f"Retrieved ValueDataPoint: {retrieved_value_datapoint}")

# Create a FileDataPoint
file_datapoint = FileDataPoint(
    label="Experiment Log",
    path="/path/to/experiment_log.txt",
    data_timestamp=datetime.now()
)

# Submit the FileDataPoint
submitted_file_datapoint = client.submit_datapoint(file_datapoint)
print(f"Submitted FileDataPoint: {submitted_file_datapoint}")

# Retrieve the FileDataPoint by ID
retrieved_file_datapoint = client.get_datapoint(submitted_file_datapoint.datapoint_id)
print(f"Retrieved FileDataPoint: {retrieved_file_datapoint}")

# Save the file from the FileDataPoint to a local path
client.save_datapoint_value(submitted_file_datapoint.datapoint_id, "/local/path/to/save/experiment_log.txt")
print("File saved successfully.")
```
## Object Storage Integration

The MADSci Data Manager supports optional **MinIO object storage** for efficient handling of large files. When configured, file datapoints are automatically stored in object storage instead of local filesystem storage. [MinIO Documentation](https://min.io/docs/minio/container/index.html)

### How It Works

**With Object Storage Configured:**
- **File datapoints** are uploaded to MinIO object storage during submission
- **Object storage metadata** (bucket name, object name, public URL, etc.) is stored in the database
- **Datapoint type** automatically changes from `file` to `object_storage`
- **Automatic fallback** to local storage if object storage upload fails

**Without Object Storage (Default Behavior):**
- **File datapoints** are stored locally on the filesystem
- **File paths** are stored in the database
- **Existing behavior** is preserved with no changes required

### Configuration

Enable object storage by adding MinIO configuration to your Data Manager definition:

```yaml
# example_data_manager.manager.yaml
name: example_data_manager
db_url: mongodb://localhost:27017
host: localhost
port: 8004
file_storage_path: ./data

# Add MinIO object storage configuration
minio_client_config:
  endpoint: "localhost:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  secure: false
  default_bucket: "madsci-data"
```

### Docker Compose Setup

The `/MADSci/compose.yaml` includes a pre-configured MinIO service:

```bash
# Start all services including MinIO
docker compose up

# Access MinIO Console
open http://localhost:9001
# Login: minioadmin / minioadmin
```

MinIO will be available at:
- **API Endpoint**: `http://localhost:9000`
- **Web Console**: `http://localhost:9001`


# Cloud Storage Integration

The MadSci Data Client supports multiple cloud storage providers through S3-compatible APIs. This allows you to store large files efficiently across different cloud platforms.

## Supported Providers

- **Amazon Web Services (AWS) S3**
- **Google Cloud Storage (GCS)** - using S3-compatible HMAC authentication
- **MinIO** (self-hosted or cloud)
- **Any S3-compatible storage service**

## Configuration

### AWS S3

```python
from madsci.common.types.datapoint_types import ObjectStorageSettings
from madsci.client.data_client import DataClient

aws_config = ObjectStorageSettings(
    endpoint="s3.amazonaws.com",
    access_key="AKIAIOSFODNN7EXAMPLE",  # Your AWS Access Key ID
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # Your AWS Secret Access Key
    secure=True,
    default_bucket="my-madsci-bucket",
    region="us-east-1"  # Specify your AWS region
)

client = DataClient(object_storage_settings=aws_config)
```

### Google Cloud Storage (GCS)

GCS requires HMAC keys for S3-compatible access:

```python
gcs_config = ObjectStorageSettings(
    endpoint="storage.googleapis.com",
    access_key="GOOGTS7C7FIS2E4U4RBGEXAMPLE",  # Your GCS HMAC Access Key
    secret_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo8rkEXAMPLE",  # Your GCS HMAC Secret
    secure=True,
    default_bucket="my-gcs-bucket"
)

client = DataClient(object_storage_settings=gcs_config)
```

## Authentication Setup

### AWS S3 Authentication

1. **IAM User Method** (Recommended):
   ```bash
   # Create IAM user with S3 permissions
   # Get Access Key ID and Secret Access Key from AWS Console
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   ```

3. **AWS CLI Profile**:
   ```bash
   aws configure --profile madsci
   # Then reference the profile in your application
   ```

### Google Cloud Storage Authentication

1. **Generate HMAC Keys**:
   ```bash
   # In Google Cloud Console:
   # Storage > Settings > Interoperability > Create Key
   ```

2. **Service Account Method**:
   ```bash
   # Create service account with Storage Admin role
   # Generate HMAC key for the service account
   ```

## Usage Examples

```python
from madsci.common.types.datapoint_types import ObjectStorageDataPoint

# Create object storage datapoint directly
storage_datapoint = ObjectStorageDataPoint(
    label="Preprocessed Data",
    path="/path/to/local-file.parquet",
    bucket_name="my-bucket",
    object_name="datasets/processed_data.parquet",
    storage_endpoint="s3.amazonaws.com",
    public_endpoint="s3.amazonaws.com",
    content_type="application/octet-stream",
    custom_metadata={
        "dataset_version": "v2.1",
        "processing_date": "2024-01-15"
    }
)

uploaded = client.submit_datapoint(storage_datapoint)
```

## Regional Endpoints

### AWS S3 Regional Endpoints
```python
# US East (N. Virginia) - Default
endpoint="s3.amazonaws.com"

# US West (Oregon)
endpoint="s3.us-west-2.amazonaws.com"

# Europe (Ireland)
endpoint="s3.eu-west-1.amazonaws.com"

# Asia Pacific (Tokyo)
endpoint="s3.ap-northeast-1.amazonaws.com"
```
