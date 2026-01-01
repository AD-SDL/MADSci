"""MADSci Data Manager - Data capture, storage, and querying.

The Data Manager provides centralized DataPoint storage and retrieval for scientific
experiments in MADSci-powered laboratories. It handles JSON data values, file storage,
and integration with cloud object storage systems.

Key Features
------------
- **DataPoint Storage**: Store JSON values and files with rich metadata
- **Flexible Storage Backends**: Local filesystem or S3-compatible object storage (MinIO, AWS S3, GCS)
- **Metadata Tracking**: Automatic ownership, timestamps, and custom labels
- **Queryable Data**: MongoDB-backed search by value and metadata
- **Cloud Integration**: Multi-provider cloud storage support with automatic failover

Storage Backends
----------------
- **Local Filesystem**: Date-based hierarchy with automatic organization
- **Object Storage**: MinIO, AWS S3, Google Cloud Storage, or any S3-compatible service
- **Hybrid Mode**: Automatic fallback from object storage to local filesystem

Components
----------
- :mod:`data_server`: Main FastAPI server for DataPoint operations

Usage Example
-------------
The Data Manager is typically run as a standalone service:

.. code-block:: bash

    # Run the Data Manager server
    python -m madsci.data_manager.data_server

    # Or use Docker Compose
    docker compose up data-manager

For programmatic access, use the DataClient from madsci.client:

.. code-block:: python

    from madsci.client.data_client import DataClient
    from madsci.common.types.datapoint_types import DataPoint, DataPointTypeEnum

    client = DataClient(data_server_url="http://localhost:8004")

    # Store JSON data
    json_dp = DataPoint(
        label="Temperature Reading",
        data_type=DataPointTypeEnum.JSON,
        value={"temperature": 23.5, "unit": "Celsius"}
    )
    stored = client.submit_datapoint(json_dp)

    # Store files
    file_dp = DataPoint(
        label="Experiment Log",
        data_type=DataPointTypeEnum.FILE,
        path="/path/to/data.txt"
    )
    stored_file = client.submit_datapoint(file_dp)

    # Retrieve data
    retrieved = client.get_datapoint(stored.datapoint_id)

Configuration
-------------
The Data Manager uses environment variables with the ``DATA_`` prefix:

- ``DATA_SERVER_URL``: Server URL (default: http://localhost:8004)
- ``DATA_DB_URL``: MongoDB connection string
- ``DATA_FILE_STORAGE_PATH``: Local file storage path (default: ~/.madsci/datapoints)

For object storage, use the ``OBJECT_STORAGE_`` prefix:

- ``OBJECT_STORAGE_ENDPOINT``: MinIO/S3 endpoint
- ``OBJECT_STORAGE_ACCESS_KEY``: Storage access key
- ``OBJECT_STORAGE_SECRET_KEY``: Storage secret key
- ``OBJECT_STORAGE_DEFAULT_BUCKET``: Default storage bucket

See Also
--------
- :mod:`madsci.client.data_client`: Client library for DataPoint operations
- :mod:`madsci.common.types.datapoint_types`: DataPoint type definitions
- :mod:`madsci.common.mongodb_migration_tool`: Database migration utilities
"""
