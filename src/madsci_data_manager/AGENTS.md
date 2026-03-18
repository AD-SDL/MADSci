# MADSci Data Manager

## Overview
The Data Manager (Port 8004) handles DataPoint capture, storage, and querying for scientific experiments. It provides a centralized service for managing experimental data, analysis results, and associated metadata.

## Key Responsibilities
- **DataPoint Storage**: Centralized storage of experimental data and results
- **DataPoint Querying**: Efficient retrieval and filtering of stored DataPoints
- **Metadata Management**: Tracking DataPoint provenance, ownership, and relationships
- **Type Validation**: Ensuring DataPoint type safety using discriminated unions
- **Analysis Integration**: Support for data analysis pipelines and results storage

## Server Architecture
- **DataManager class**: Inherits from `AbstractManagerBase[DataManagerSettings]`
- **Document Database Integration**: Uses `DocumentStorageHandler` abstraction for datapoint metadata storage in the `madsci_data` database (`document_handler` parameter)
- **Object Storage Integration**: Uses `ObjectStorageHandler` abstraction for S3-compatible object storage (`object_storage_handler` parameter), with fallback to local filesystem when no object storage is configured
- **FastAPI Server**: Provides REST endpoints with automatic OpenAPI documentation
- **Discriminated Union Types**: Uses `DataPoint.discriminate()` for type-safe datapoint handling

## DataPoint Implementation

### Base DataPoint Class
- **ULID IDs**: Uses `new_ulid_str()` for `datapoint_id` generation
- **Ownership Tracking**: Automatic `ownership_info` from current context
- **Timestamps**: Auto-generated `data_timestamp` using `datetime.now()`
- **MongoDB Serialization**: Custom `to_mongo()` method for database storage

### Type-Specific Fields
- **FileDataPoint**: Requires `path` field pointing to local file
- **ValueDataPoint**: Requires `value` field containing JSON-serializable data
- **ObjectStorageDataPoint**: Contains storage metadata (bucket, object_name, etag, etc.)

### Storage Behavior
- **Local Files**: Organized by date hierarchy (`year/month/day/ulid_filename`)
- **Object Storage**: All S3-compatible operations routed through `self._object_storage_handler` (no direct client usage). Uses label-based object naming for uploads.
- **Automatic Fallback**: Object storage upload failure falls back to local storage with warning

## API Endpoints

### Core Endpoints
- `POST /datapoint`: Create datapoints with automatic file upload handling
- `GET /datapoint/{datapoint_id}`: Retrieve datapoint metadata by ID
- `GET /datapoint/{datapoint_id}/value`: Get datapoint value (JSON response or file download)
- `GET /datapoints`: List recent datapoints (default 100, configurable)
- `POST /datapoints/query`: MongoDB-style query interface for complex searches

### DataPoint Types
- **JSON DataPoints**: Store structured data with `data_type: "json"` and `value` field
- **File DataPoints**: Store file references with `data_type: "file"` and `path` field
- **Object Storage DataPoints**: Store S3-compatible object references with `data_type: "object_storage"`

## Configuration

### DataManagerSettings (Environment prefix: `DATA_`)
- `DATA_SERVER_URL`: Server URL (default: `http://localhost:8004`)
- `DATA_DB_URL`: FerretDB/MongoDB-compatible connection string (default: `mongodb://localhost:27017`)
- `DATA_FILE_STORAGE_PATH`: Local file storage path (default: `~/.madsci/datapoints`)


### ObjectStorageSettings (Environment prefix: `OBJECT_STORAGE_`)
- `OBJECT_STORAGE_ENDPOINT`: S3-compatible endpoint (e.g., SeaweedFS, MinIO, AWS S3)
- `OBJECT_STORAGE_ACCESS_KEY`: Storage access key
- `OBJECT_STORAGE_SECRET_KEY`: Storage secret key
- `OBJECT_STORAGE_SECURE`: Use HTTPS (default: false)
- `OBJECT_STORAGE_DEFAULT_BUCKET`: Default storage bucket (default: `madsci-data`)

## Integration Points
- **Event Manager**: Log data operations and access events
- **Experiment Manager**: Store experimental results and measurements
- **Resource Manager**: Track data associated with specific resources
- **Workcell Manager**: Store workflow execution data and outputs
