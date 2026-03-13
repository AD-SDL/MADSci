# Configuration

Here you can find all available configuration options using ENV variables.

## DockerComposeSettings

These environment variables are used to configure the default Docker Compose in the MADSci example lab.

| Name                          | Type      | Default | Description                                                                                                                                                                                              | Example |
|-------------------------------|-----------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| `USER_ID`                     | `integer` | `1000`  | The user ID to use for the MADSci services inside Docker containers. This should match your host user ID to avoid file permission issues. If not set, the default value used by the container is 9999.   | `1000`  |
| `GROUP_ID`                    | `integer` | `1000`  | The group ID to use for the MADSci services inside Docker containers. This should match your host group ID to avoid file permission issues. If not set, the default value used by the container is 9999. | `1000`  |
| `REPO_PATH`                   | `string`  | `"./"`  | The path to the MADSci repository on the host machine. This is mounted into the Docker containers to provide access to the codebase.                                                                     | `"./"`  |
| `REDIS_PORT`                  | `integer` | `6379`  | The port on the host machine to bind the Redis service to. This allows other services to connect to Redis running inside the Docker container.                                                           | `6379`  |
| `DOCUMENT_DB_PORT`            | `integer` | `27017` | The port on the host machine to bind the document database service (FerretDB) to. This allows other services to connect to the document database running inside the Docker container.                    | `27017` |
| `POSTGRES_PORT`               | `integer` | `5432`  | The port on the host machine to bind the PostgreSQL service to. This allows other services to connect to PostgreSQL running inside the Docker container.                                                 | `5432`  |
| `OBJECT_STORAGE_PORT`         | `integer` | `8333`  | The port on the host machine to bind the S3-compatible object storage service (SeaweedFS) to. This allows other services to connect to object storage running inside the Docker container.               | `8333`  |
| `OBJECT_STORAGE_CONSOLE_PORT` | `integer` | `9333`  | The port on the host machine to bind the object storage console (SeaweedFS master) to. This allows monitoring of the object storage cluster.                                                             | `9333`  |

## MadsciDeveloperSettings

Developer-focused settings for MADSci behavior.

These settings control development experience features like rich tracebacks.
All settings use the MADSCI_ prefix for environment variables.

Environment Variables:
    MADSCI_DISABLE_RICH_TRACEBACKS: Set to true to disable rich tracebacks
        (default: false, rich tracebacks are enabled)
    MADSCI_RICH_TRACEBACKS_SHOW_LOCALS: Set to true to show local variables
        in tracebacks (default: false for security - can leak secrets)

Note:
    show_locals is disabled by default to prevent accidental exposure of
    sensitive data (tokens, passwords) that may be present in local variables
    during exceptions.

**Environment Prefix**: `MADSCI_`

| Name                                 | Type      | Default | Description                                                                                     | Example |
|--------------------------------------|-----------|---------|-------------------------------------------------------------------------------------------------|---------|
| `MADSCI_DISABLE_RICH_TRACEBACKS`     | `boolean` | `false` | Disable rich traceback handler for exception output.                                            | `false` |
| `MADSCI_RICH_TRACEBACKS_SHOW_LOCALS` | `boolean` | `false` | Show local variables in tracebacks. Disabled by default for security - can leak sensitive data. | `false` |

## MadsciContext

Base class for MADSci context settings.

| Name                    | Type                   | Default | Description                       | Example |
|-------------------------|------------------------|---------|-----------------------------------|---------|
| `LAB_SERVER_URL`        | `AnyUrl` \| `NoneType` | `null`  | The URL of the lab server.        | `null`  |
| `EVENT_SERVER_URL`      | `AnyUrl` \| `NoneType` | `null`  | The URL of the event server.      | `null`  |
| `EXPERIMENT_SERVER_URL` | `AnyUrl` \| `NoneType` | `null`  | The URL of the experiment server. | `null`  |
| `DATA_SERVER_URL`       | `AnyUrl` \| `NoneType` | `null`  | The URL of the data server.       | `null`  |
| `RESOURCE_SERVER_URL`   | `AnyUrl` \| `NoneType` | `null`  | The URL of the resource server.   | `null`  |
| `WORKCELL_SERVER_URL`   | `AnyUrl` \| `NoneType` | `null`  | The URL of the workcell server.   | `null`  |
| `LOCATION_SERVER_URL`   | `AnyUrl` \| `NoneType` | `null`  | The URL of the location server.   | `null`  |

## DataManagerSettings

Settings for the MADSci Data Manager.

**Environment Prefix**: `DATA_`

| Name                                                             | Type                                | Default                       | Description                                                                                                                                             | Example                       |
|------------------------------------------------------------------|-------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `DATA_SERVER_URL`                                                | `AnyUrl`                            | `"http://localhost:8004/"`    | The URL of the data manager server.                                                                                                                     | `"http://localhost:8004/"`    |
| `DATA_MANAGER_ID`                                                | `string` \| `NoneType`              | `null`                        | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                        |
| `DATA_MANAGER_TYPE`                                              | `ManagerType` \| `NoneType`         | `"data_manager"`              | The type of manager.                                                                                                                                    | `"data_manager"`              |
| `DATA_RATE_LIMIT_ENABLED`                                        | `boolean`                           | `true`                        | Enable rate limiting for API endpoints.                                                                                                                 | `true`                        |
| `DATA_RATE_LIMIT_REQUESTS`                                       | `integer`                           | `300`                         | Maximum number of requests allowed per long time window.                                                                                                | `300`                         |
| `DATA_RATE_LIMIT_WINDOW`                                         | `integer`                           | `60`                          | Long time window for rate limiting in seconds.                                                                                                          | `60`                          |
| `DATA_RATE_LIMIT_SHORT_REQUESTS`                                 | `integer` \| `NoneType`             | `50`                          | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                          |
| `DATA_RATE_LIMIT_SHORT_WINDOW`                                   | `integer` \| `NoneType`             | `1`                           | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                           |
| `DATA_RATE_LIMIT_CLEANUP_INTERVAL`                               | `integer`                           | `300`                         | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                         |
| `DATA_RATE_LIMIT_EXEMPT_IPS`                                     | `array` \| `NoneType`               | `null`                        | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                        |
| `DATA_UVICORN_WORKERS`                                           | `integer` \| `NoneType`             | `null`                        | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                        |
| `DATA_UVICORN_LIMIT_CONCURRENCY`                                 | `integer` \| `NoneType`             | `null`                        | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                        |
| `DATA_UVICORN_LIMIT_MAX_REQUESTS`                                | `integer` \| `NoneType`             | `null`                        | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                        |
| `DATA_ENABLE_REGISTRY_RESOLUTION`                                | `boolean`                           | `true`                        | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                        |
| `DATA_MANAGER_NAME`                                              | `string` \| `NoneType`              | `null`                        | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                        |
| `DATA_MANAGER_DESCRIPTION`                                       | `string` \| `NoneType`              | `null`                        | Human-readable description of this manager instance.                                                                                                    | `null`                        |
| `DATA_LAB_URL`                                                   | `AnyUrl` \| `NoneType`              | `null`                        | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                        |
| `DATA_REGISTRY_LOCK_TIMEOUT`                                     | `number`                            | `60.0`                        | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                        |
| `DATA_OTEL_ENABLED`                                              | `boolean`                           | `false`                       | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                       |
| `DATA_OTEL_SERVICE_NAME`                                         | `string` \| `NoneType`              | `null`                        | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                        |
| `DATA_OTEL_EXPORTER`                                             | `"console"` \| `"otlp"` \| `"none"` | `"console"`                   | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                   |
| `DATA_OTEL_ENDPOINT`                                             | `string` \| `NoneType`              | `null`                        | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                        |
| `DATA_OTEL_PROTOCOL`                                             | `"grpc"` \| `"http"`                | `"grpc"`                      | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                      |
| `DATA_DATABASE_NAME`                                             | `string`                            | `"madsci_data"`               | The name of the MongoDB database where events are stored.                                                                                               | `"madsci_data"`               |
| `DATA_COLLECTION_NAME`                                           | `string`                            | `"datapoints"`                | The name of the MongoDB collection where data are stored.                                                                                               | `"datapoints"`                |
| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` \| `DATA_DB_URL` \| `DB_URL` | `AnyUrl`                            | `"mongodb://localhost:27017"` | The URL of the MongoDB-compatible document database used by the Data Manager.                                                                           | `"mongodb://localhost:27017"` |
| `DATA_FILE_STORAGE_PATH`                                         | `string` \| `Path`                  | `".madsci/datapoints"`        | The path where files are stored on the server.                                                                                                          | `".madsci/datapoints"`        |

## ObjectStorageSettings

Settings for S3-compatible object storage.

**Environment Prefix**: `OBJECT_STORAGE_`

| Name                            | Type                   | Default         | Description                                                           | Example         |
|---------------------------------|------------------------|-----------------|-----------------------------------------------------------------------|-----------------|
| `OBJECT_STORAGE_ENDPOINT`       | `string` \| `NoneType` | `null`          | Endpoint for S3-compatible storage (e.g., 'storage.example.com:8333') | `null`          |
| `OBJECT_STORAGE_ACCESS_KEY`     | `string`               | `""`            | Access key for authentication                                         | `""`            |
| `OBJECT_STORAGE_SECRET_KEY`     | `string`               | `""`            | Secret key for authentication                                         | `""`            |
| `OBJECT_STORAGE_SECURE`         | `boolean`              | `false`         | Whether to use HTTPS (True) or HTTP (False)                           | `false`         |
| `OBJECT_STORAGE_DEFAULT_BUCKET` | `string`               | `"madsci-data"` | Default bucket to use for storing data                                | `"madsci-data"` |
| `OBJECT_STORAGE_REGION`         | `string` \| `NoneType` | `null`          | Optional for AWS S3/other providers                                   | `null`          |

## EventManagerSettings

Handles settings and configuration for the Event Manager.

**Environment Prefix**: `EVENT_`

| Name                                                              | Type                                | Default                       | Description                                                                                                                                             | Example                       |
|-------------------------------------------------------------------|-------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `EVENT_SERVER_URL`                                                | `AnyUrl`                            | `"http://localhost:8001/"`    | The URL of the Event Manager server.                                                                                                                    | `"http://localhost:8001/"`    |
| `EVENT_MANAGER_ID`                                                | `string` \| `NoneType`              | `null`                        | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                        |
| `EVENT_MANAGER_TYPE`                                              | `ManagerType` \| `NoneType`         | `"event_manager"`             | The type of manager.                                                                                                                                    | `"event_manager"`             |
| `EVENT_RATE_LIMIT_ENABLED`                                        | `boolean`                           | `true`                        | Enable rate limiting for API endpoints.                                                                                                                 | `true`                        |
| `EVENT_RATE_LIMIT_REQUESTS`                                       | `integer`                           | `300`                         | Maximum number of requests allowed per long time window.                                                                                                | `300`                         |
| `EVENT_RATE_LIMIT_WINDOW`                                         | `integer`                           | `60`                          | Long time window for rate limiting in seconds.                                                                                                          | `60`                          |
| `EVENT_RATE_LIMIT_SHORT_REQUESTS`                                 | `integer` \| `NoneType`             | `50`                          | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                          |
| `EVENT_RATE_LIMIT_SHORT_WINDOW`                                   | `integer` \| `NoneType`             | `1`                           | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                           |
| `EVENT_RATE_LIMIT_CLEANUP_INTERVAL`                               | `integer`                           | `300`                         | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                         |
| `EVENT_RATE_LIMIT_EXEMPT_IPS`                                     | `array` \| `NoneType`               | `null`                        | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                        |
| `EVENT_UVICORN_WORKERS`                                           | `integer` \| `NoneType`             | `null`                        | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                        |
| `EVENT_UVICORN_LIMIT_CONCURRENCY`                                 | `integer` \| `NoneType`             | `null`                        | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                        |
| `EVENT_UVICORN_LIMIT_MAX_REQUESTS`                                | `integer` \| `NoneType`             | `null`                        | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                        |
| `EVENT_ENABLE_REGISTRY_RESOLUTION`                                | `boolean`                           | `true`                        | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                        |
| `EVENT_MANAGER_NAME`                                              | `string` \| `NoneType`              | `null`                        | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                        |
| `EVENT_MANAGER_DESCRIPTION`                                       | `string` \| `NoneType`              | `null`                        | Human-readable description of this manager instance.                                                                                                    | `null`                        |
| `EVENT_LAB_URL`                                                   | `AnyUrl` \| `NoneType`              | `null`                        | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                        |
| `EVENT_REGISTRY_LOCK_TIMEOUT`                                     | `number`                            | `60.0`                        | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                        |
| `EVENT_OTEL_ENABLED`                                              | `boolean`                           | `false`                       | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                       |
| `EVENT_OTEL_SERVICE_NAME`                                         | `string` \| `NoneType`              | `null`                        | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                        |
| `EVENT_OTEL_EXPORTER`                                             | `"console"` \| `"otlp"` \| `"none"` | `"console"`                   | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                   |
| `EVENT_OTEL_ENDPOINT`                                             | `string` \| `NoneType`              | `null`                        | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                        |
| `EVENT_OTEL_PROTOCOL`                                             | `"grpc"` \| `"http"`                | `"grpc"`                      | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                      |
| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` \| `EVENT_DB_URL` \| `DB_URL` | `AnyUrl`                            | `"mongodb://localhost:27017"` | The URL of the MongoDB-compatible document database used by the Event Manager.                                                                          | `"mongodb://localhost:27017"` |
| `EVENT_DATABASE_NAME`                                             | `string`                            | `"madsci_events"`             | The name of the MongoDB database where events are stored.                                                                                               | `"madsci_events"`             |
| `EVENT_COLLECTION_NAME`                                           | `string`                            | `"events"`                    | The name of the MongoDB collection where events are stored.                                                                                             | `"events"`                    |
| `EVENT_ALERT_LEVEL`                                               | `EventLogLevel`                     | `40`                          | The log level at which to send an alert.                                                                                                                | `40`                          |
| `EVENT_EMAIL_ALERTS`                                              | `EmailAlertsConfig` \| `NoneType`   | `null`                        | The configuration for sending email alerts.                                                                                                             | `null`                        |
| `EVENT_RETENTION_ENABLED`                                         | `boolean`                           | `false`                       | Whether automatic event retention is enabled.                                                                                                           | `false`                       |
| `EVENT_SOFT_DELETE_AFTER_DAYS`                                    | `integer`                           | `90`                          | Days after which events are soft-deleted (archived).                                                                                                    | `90`                          |
| `EVENT_HARD_DELETE_AFTER_DAYS`                                    | `integer`                           | `365`                         | Days after archive when events are permanently deleted via TTL index.                                                                                   | `365`                         |
| `EVENT_RETENTION_CHECK_INTERVAL_HOURS`                            | `integer`                           | `24`                          | How often to run soft-delete retention checks (in hours).                                                                                               | `24`                          |
| `EVENT_ARCHIVE_BATCH_SIZE`                                        | `integer`                           | `1000`                        | Maximum number of events to archive in a single batch operation.                                                                                        | `1000`                        |
| `EVENT_MAX_BATCHES_PER_RUN`                                       | `integer`                           | `100`                         | Maximum number of batches to process per retention run (0 = unlimited).                                                                                 | `100`                         |
| `EVENT_BACKUP_ENABLED`                                            | `boolean`                           | `false`                       | Whether automatic event backups are enabled.                                                                                                            | `false`                       |
| `EVENT_BACKUP_SCHEDULE`                                           | `string` \| `NoneType`              | `null`                        | Cron expression for backup schedule (e.g., '0 2 * * *' for 2am daily).                                                                                  | `null`                        |
| `EVENT_BACKUP_DIR`                                                | `string` \| `Path`                  | `".madsci/backups/events"`    | Directory for event backups.                                                                                                                            | `".madsci/backups/events"`    |
| `EVENT_BACKUP_MAX_COUNT`                                          | `integer`                           | `10`                          | Maximum number of backup files to keep.                                                                                                                 | `10`                          |
| `EVENT_FAIL_ON_RETENTION_ERROR`                                   | `boolean`                           | `false`                       | If True, raise exceptions on retention failures. If False, log and continue.                                                                            | `false`                       |

## WorkcellManagerSettings

Settings for the MADSci Workcell Manager.

**Environment Prefix**: `WORKCELL_`

| Name                                                                       | Type                                | Default                                                  | Description                                                                                                                                                                                                                       | Example                                                  |
|----------------------------------------------------------------------------|-------------------------------------|----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| `WORKCELL_SERVER_URL`                                                      | `AnyUrl`                            | `"http://localhost:8005/"`                               | The URL of the workcell manager server.                                                                                                                                                                                           | `"http://localhost:8005/"`                               |
| `WORKCELL_MANAGER_ID`                                                      | `string` \| `NoneType`              | `null`                                                   | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.                                                                               | `null`                                                   |
| `WORKCELL_MANAGER_TYPE`                                                    | `ManagerType` \| `NoneType`         | `"workcell_manager"`                                     | The type of manager.                                                                                                                                                                                                              | `"workcell_manager"`                                     |
| `WORKCELL_RATE_LIMIT_ENABLED`                                              | `boolean`                           | `true`                                                   | Enable rate limiting for API endpoints.                                                                                                                                                                                           | `true`                                                   |
| `WORKCELL_RATE_LIMIT_REQUESTS`                                             | `integer`                           | `300`                                                    | Maximum number of requests allowed per long time window.                                                                                                                                                                          | `300`                                                    |
| `WORKCELL_RATE_LIMIT_WINDOW`                                               | `integer`                           | `60`                                                     | Long time window for rate limiting in seconds.                                                                                                                                                                                    | `60`                                                     |
| `WORKCELL_RATE_LIMIT_SHORT_REQUESTS`                                       | `integer` \| `NoneType`             | `50`                                                     | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                                                                                                        | `50`                                                     |
| `WORKCELL_RATE_LIMIT_SHORT_WINDOW`                                         | `integer` \| `NoneType`             | `1`                                                      | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                                                                                                    | `1`                                                      |
| `WORKCELL_RATE_LIMIT_CLEANUP_INTERVAL`                                     | `integer`                           | `300`                                                    | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                                                                                           | `300`                                                    |
| `WORKCELL_RATE_LIMIT_EXEMPT_IPS`                                           | `array` \| `NoneType`               | `null`                                                   | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                                                                                                      | `null`                                                   |
| `WORKCELL_UVICORN_WORKERS`                                                 | `integer` \| `NoneType`             | `null`                                                   | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                                                                                            | `null`                                                   |
| `WORKCELL_UVICORN_LIMIT_CONCURRENCY`                                       | `integer` \| `NoneType`             | `null`                                                   | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                                                                                          | `null`                                                   |
| `WORKCELL_UVICORN_LIMIT_MAX_REQUESTS`                                      | `integer` \| `NoneType`             | `null`                                                   | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                                                                                                   | `null`                                                   |
| `WORKCELL_ENABLE_REGISTRY_RESOLUTION`                                      | `boolean`                           | `true`                                                   | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                                                                                                | `true`                                                   |
| `WORKCELL_MANAGER_NAME`                                                    | `string` \| `NoneType`              | `null`                                                   | Name for this manager instance. Used for registry lookup and display.                                                                                                                                                             | `null`                                                   |
| `WORKCELL_MANAGER_DESCRIPTION`                                             | `string` \| `NoneType`              | `null`                                                   | Human-readable description of this manager instance.                                                                                                                                                                              | `null`                                                   |
| `WORKCELL_LAB_URL`                                                         | `AnyUrl` \| `NoneType`              | `null`                                                   | Lab Manager URL for distributed registry coordination.                                                                                                                                                                            | `null`                                                   |
| `WORKCELL_REGISTRY_LOCK_TIMEOUT`                                           | `number`                            | `60.0`                                                   | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts.                                                                           | `60.0`                                                   |
| `WORKCELL_OTEL_ENABLED`                                                    | `boolean`                           | `false`                                                  | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                                                                                             | `false`                                                  |
| `WORKCELL_OTEL_SERVICE_NAME`                                               | `string` \| `NoneType`              | `null`                                                   | Override service name for OpenTelemetry (defaults to manager name)                                                                                                                                                                | `null`                                                   |
| `WORKCELL_OTEL_EXPORTER`                                                   | `"console"` \| `"otlp"` \| `"none"` | `"console"`                                              | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                                                                                                  | `"console"`                                              |
| `WORKCELL_OTEL_ENDPOINT`                                                   | `string` \| `NoneType`              | `null`                                                   | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                                                                                                      | `null`                                                   |
| `WORKCELL_OTEL_PROTOCOL`                                                   | `"grpc"` \| `"http"`                | `"grpc"`                                                 | OTLP transport protocol ('grpc' or 'http')                                                                                                                                                                                        | `"grpc"`                                                 |
| `WORKCELL_NODES`                                                           | `object` \| `NoneType`              | `null`                                                   | Node URLs for the workcell, as a JSON dict mapping node names to their URLs.                                                                                                                                                      | `null`                                                   |
| `WORKCELLS_DIRECTORY` \| `WORKCELLS_DIRECTORY`                             | `string` \| `Path` \| `NoneType`    | `".madsci/workcells"`                                    | Directory used to store workcell-related files in. Defaults to .madsci/workcells. Workcell-related files will be stored in a sub-folder with the workcell name.                                                                   | `".madsci/workcells"`                                    |
| `WORKCELL_REDIS_HOST`                                                      | `string`                            | `"localhost"`                                            | The hostname for the redis server .                                                                                                                                                                                               | `"localhost"`                                            |
| `WORKCELL_REDIS_PORT`                                                      | `integer`                           | `6379`                                                   | The port for the redis server.                                                                                                                                                                                                    | `6379`                                                   |
| `WORKCELL_REDIS_PASSWORD`                                                  | `string` \| `NoneType`              | `null`                                                   | The password for the redis server.                                                                                                                                                                                                | `null`                                                   |
| `WORKCELL_SCHEDULER_UPDATE_INTERVAL`                                       | `number`                            | `5.0`                                                    | The interval at which the scheduler runs, in seconds. Must be >= node_update_interval                                                                                                                                             | `5.0`                                                    |
| `WORKCELL_NODE_UPDATE_INTERVAL`                                            | `number`                            | `2.0`                                                    | The interval at which the workcell queries its node's states and status, in seconds. Must be <= scheduler_update_interval                                                                                                         | `2.0`                                                    |
| `WORKCELL_RECONNECT_ATTEMPT_INTERVAL`                                      | `number`                            | `30.0`                                                   | The interval (in seconds) at which the workcell retries connecting to disconnected nodes. A non-disruptive retry: if the node responds, its status is restored naturally; if not, it remains disconnected until the next attempt. | `30.0`                                                   |
| `WORKCELL_NODE_INFO_UPDATE_INTERVAL`                                       | `number`                            | `60.0`                                                   | The interval at which the workcell queries its node's info, in seconds. Node info changes infrequently, so this can be much larger than node_update_interval to reduce network overhead.                                          | `60.0`                                                   |
| `WORKCELL_COLD_START_DELAY`                                                | `integer`                           | `0`                                                      | How long the Workcell engine should sleep on startup                                                                                                                                                                              | `0`                                                      |
| `WORKCELL_SCHEDULER`                                                       | `string`                            | `"madsci.workcell_manager.schedulers.default_scheduler"` | Scheduler module that contains a Scheduler class that inherits from AbstractScheduler to use                                                                                                                                      | `"madsci.workcell_manager.schedulers.default_scheduler"` |
| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` \| `WORKCELL_MONGO_URL` \| `MONGO_URL` | `AnyUrl` \| `NoneType`              | `"mongodb://localhost:27017"`                            | The URL for the MongoDB-compatible document database.                                                                                                                                                                             | `"mongodb://localhost:27017"`                            |
| `WORKCELL_DATABASE_NAME`                                                   | `string`                            | `"madsci_workcells"`                                     | The name of the MongoDB database where events are stored.                                                                                                                                                                         | `"madsci_workcells"`                                     |
| `WORKCELL_COLLECTION_NAME`                                                 | `string`                            | `"archived_workflows"`                                   | The name of the MongoDB collection where events are stored.                                                                                                                                                                       | `"archived_workflows"`                                   |
| `WORKCELL_GET_ACTION_RESULT_RETRIES`                                       | `integer`                           | `3`                                                      | Number of times to retry getting an action result                                                                                                                                                                                 | `3`                                                      |

## ExperimentManagerSettings

Settings for the MADSci Experiment Manager.

**Environment Prefix**: `EXPERIMENT_`

| Name                                                                   | Type                                | Default                       | Description                                                                                                                                             | Example                       |
|------------------------------------------------------------------------|-------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `EXPERIMENT_SERVER_URL`                                                | `AnyUrl`                            | `"http://localhost:8002/"`    | The URL of the experiment manager server.                                                                                                               | `"http://localhost:8002/"`    |
| `EXPERIMENT_MANAGER_ID`                                                | `string` \| `NoneType`              | `null`                        | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                        |
| `EXPERIMENT_MANAGER_TYPE`                                              | `ManagerType` \| `NoneType`         | `"experiment_manager"`        | The type of manager.                                                                                                                                    | `"experiment_manager"`        |
| `EXPERIMENT_RATE_LIMIT_ENABLED`                                        | `boolean`                           | `true`                        | Enable rate limiting for API endpoints.                                                                                                                 | `true`                        |
| `EXPERIMENT_RATE_LIMIT_REQUESTS`                                       | `integer`                           | `300`                         | Maximum number of requests allowed per long time window.                                                                                                | `300`                         |
| `EXPERIMENT_RATE_LIMIT_WINDOW`                                         | `integer`                           | `60`                          | Long time window for rate limiting in seconds.                                                                                                          | `60`                          |
| `EXPERIMENT_RATE_LIMIT_SHORT_REQUESTS`                                 | `integer` \| `NoneType`             | `50`                          | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                          |
| `EXPERIMENT_RATE_LIMIT_SHORT_WINDOW`                                   | `integer` \| `NoneType`             | `1`                           | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                           |
| `EXPERIMENT_RATE_LIMIT_CLEANUP_INTERVAL`                               | `integer`                           | `300`                         | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                         |
| `EXPERIMENT_RATE_LIMIT_EXEMPT_IPS`                                     | `array` \| `NoneType`               | `null`                        | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                        |
| `EXPERIMENT_UVICORN_WORKERS`                                           | `integer` \| `NoneType`             | `null`                        | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                        |
| `EXPERIMENT_UVICORN_LIMIT_CONCURRENCY`                                 | `integer` \| `NoneType`             | `null`                        | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                        |
| `EXPERIMENT_UVICORN_LIMIT_MAX_REQUESTS`                                | `integer` \| `NoneType`             | `null`                        | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                        |
| `EXPERIMENT_ENABLE_REGISTRY_RESOLUTION`                                | `boolean`                           | `true`                        | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                        |
| `EXPERIMENT_MANAGER_NAME`                                              | `string` \| `NoneType`              | `null`                        | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                        |
| `EXPERIMENT_MANAGER_DESCRIPTION`                                       | `string` \| `NoneType`              | `null`                        | Human-readable description of this manager instance.                                                                                                    | `null`                        |
| `EXPERIMENT_LAB_URL`                                                   | `AnyUrl` \| `NoneType`              | `null`                        | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                        |
| `EXPERIMENT_REGISTRY_LOCK_TIMEOUT`                                     | `number`                            | `60.0`                        | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                        |
| `EXPERIMENT_OTEL_ENABLED`                                              | `boolean`                           | `false`                       | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                       |
| `EXPERIMENT_OTEL_SERVICE_NAME`                                         | `string` \| `NoneType`              | `null`                        | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                        |
| `EXPERIMENT_OTEL_EXPORTER`                                             | `"console"` \| `"otlp"` \| `"none"` | `"console"`                   | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                   |
| `EXPERIMENT_OTEL_ENDPOINT`                                             | `string` \| `NoneType`              | `null`                        | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                        |
| `EXPERIMENT_OTEL_PROTOCOL`                                             | `"grpc"` \| `"http"`                | `"grpc"`                      | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                      |
| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` \| `EXPERIMENT_DB_URL` \| `DB_URL` | `AnyUrl`                            | `"mongodb://localhost:27017"` | The URL of the MongoDB-compatible document database for the experiment manager.                                                                         | `"mongodb://localhost:27017"` |
| `EXPERIMENT_DATABASE_NAME`                                             | `string`                            | `"madsci_experiments"`        | The name of the MongoDB database where events are stored.                                                                                               | `"madsci_experiments"`        |
| `EXPERIMENT_COLLECTION_NAME`                                           | `string`                            | `"experiments"`               | The name of the MongoDB collection where events are stored.                                                                                             | `"experiments"`               |

## ResourceManagerSettings

Settings for the MADSci Resource Manager.

**Environment Prefix**: `RESOURCE_`

| Name                                   | Type                                | Default                                                | Description                                                                                                                                             | Example                                                |
|----------------------------------------|-------------------------------------|--------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| `RESOURCE_SERVER_URL`                  | `AnyUrl`                            | `"http://localhost:8003"`                              | The URL of the resource manager server.                                                                                                                 | `"http://localhost:8003"`                              |
| `RESOURCE_MANAGER_ID`                  | `string` \| `NoneType`              | `null`                                                 | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                                                 |
| `RESOURCE_MANAGER_TYPE`                | `ManagerType` \| `NoneType`         | `"resource_manager"`                                   | The type of manager.                                                                                                                                    | `"resource_manager"`                                   |
| `RESOURCE_RATE_LIMIT_ENABLED`          | `boolean`                           | `true`                                                 | Enable rate limiting for API endpoints.                                                                                                                 | `true`                                                 |
| `RESOURCE_RATE_LIMIT_REQUESTS`         | `integer`                           | `300`                                                  | Maximum number of requests allowed per long time window.                                                                                                | `300`                                                  |
| `RESOURCE_RATE_LIMIT_WINDOW`           | `integer`                           | `60`                                                   | Long time window for rate limiting in seconds.                                                                                                          | `60`                                                   |
| `RESOURCE_RATE_LIMIT_SHORT_REQUESTS`   | `integer` \| `NoneType`             | `50`                                                   | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                                                   |
| `RESOURCE_RATE_LIMIT_SHORT_WINDOW`     | `integer` \| `NoneType`             | `1`                                                    | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                                                    |
| `RESOURCE_RATE_LIMIT_CLEANUP_INTERVAL` | `integer`                           | `300`                                                  | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                                                  |
| `RESOURCE_RATE_LIMIT_EXEMPT_IPS`       | `array` \| `NoneType`               | `null`                                                 | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                                                 |
| `RESOURCE_UVICORN_WORKERS`             | `integer` \| `NoneType`             | `null`                                                 | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                                                 |
| `RESOURCE_UVICORN_LIMIT_CONCURRENCY`   | `integer` \| `NoneType`             | `null`                                                 | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                                                 |
| `RESOURCE_UVICORN_LIMIT_MAX_REQUESTS`  | `integer` \| `NoneType`             | `null`                                                 | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                                                 |
| `RESOURCE_ENABLE_REGISTRY_RESOLUTION`  | `boolean`                           | `true`                                                 | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                                                 |
| `RESOURCE_MANAGER_NAME`                | `string` \| `NoneType`              | `null`                                                 | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                                                 |
| `RESOURCE_MANAGER_DESCRIPTION`         | `string` \| `NoneType`              | `null`                                                 | Human-readable description of this manager instance.                                                                                                    | `null`                                                 |
| `RESOURCE_LAB_URL`                     | `AnyUrl` \| `NoneType`              | `null`                                                 | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                                                 |
| `RESOURCE_REGISTRY_LOCK_TIMEOUT`       | `number`                            | `60.0`                                                 | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                                                 |
| `RESOURCE_OTEL_ENABLED`                | `boolean`                           | `false`                                                | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                                                |
| `RESOURCE_OTEL_SERVICE_NAME`           | `string` \| `NoneType`              | `null`                                                 | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                                                 |
| `RESOURCE_OTEL_EXPORTER`               | `"console"` \| `"otlp"` \| `"none"` | `"console"`                                            | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                                            |
| `RESOURCE_OTEL_ENDPOINT`               | `string` \| `NoneType`              | `null`                                                 | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                                                 |
| `RESOURCE_OTEL_PROTOCOL`               | `"grpc"` \| `"http"`                | `"grpc"`                                               | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                                               |
| `RESOURCE_DEFAULT_TEMPLATES`           | `array` \| `NoneType`               | `null`                                                 | Default resource template definitions to create or update on manager startup.                                                                           | `null`                                                 |
| `RESOURCE_DB_URL`                      | `string`                            | `"postgresql://madsci:madsci@localhost:5432/postgres"` | The URL of the database for the resource manager.                                                                                                       | `"postgresql://madsci:madsci@localhost:5432/postgres"` |

## LabManagerSettings

Settings for the MADSci Lab.

**Environment Prefix**: `LAB_`

| Name                              | Type                                | Default                    | Description                                                                                                                                             | Example                    |
|-----------------------------------|-------------------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| `LAB_SERVER_URL`                  | `AnyUrl`                            | `"http://localhost:8000/"` | The URL of the lab manager.                                                                                                                             | `"http://localhost:8000/"` |
| `LAB_MANAGER_ID`                  | `string` \| `NoneType`              | `null`                     | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                     |
| `LAB_MANAGER_TYPE`                | `ManagerType` \| `NoneType`         | `"lab_manager"`            | The type of manager.                                                                                                                                    | `"lab_manager"`            |
| `LAB_RATE_LIMIT_ENABLED`          | `boolean`                           | `true`                     | Enable rate limiting for API endpoints.                                                                                                                 | `true`                     |
| `LAB_RATE_LIMIT_REQUESTS`         | `integer`                           | `300`                      | Maximum number of requests allowed per long time window.                                                                                                | `300`                      |
| `LAB_RATE_LIMIT_WINDOW`           | `integer`                           | `60`                       | Long time window for rate limiting in seconds.                                                                                                          | `60`                       |
| `LAB_RATE_LIMIT_SHORT_REQUESTS`   | `integer` \| `NoneType`             | `50`                       | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                       |
| `LAB_RATE_LIMIT_SHORT_WINDOW`     | `integer` \| `NoneType`             | `1`                        | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                        |
| `LAB_RATE_LIMIT_CLEANUP_INTERVAL` | `integer`                           | `300`                      | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                      |
| `LAB_RATE_LIMIT_EXEMPT_IPS`       | `array` \| `NoneType`               | `null`                     | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                     |
| `LAB_UVICORN_WORKERS`             | `integer` \| `NoneType`             | `null`                     | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                     |
| `LAB_UVICORN_LIMIT_CONCURRENCY`   | `integer` \| `NoneType`             | `null`                     | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                     |
| `LAB_UVICORN_LIMIT_MAX_REQUESTS`  | `integer` \| `NoneType`             | `null`                     | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                     |
| `LAB_ENABLE_REGISTRY_RESOLUTION`  | `boolean`                           | `true`                     | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                     |
| `LAB_MANAGER_NAME`                | `string` \| `NoneType`              | `null`                     | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                     |
| `LAB_MANAGER_DESCRIPTION`         | `string` \| `NoneType`              | `null`                     | Human-readable description of this manager instance.                                                                                                    | `null`                     |
| `LAB_LAB_URL`                     | `AnyUrl` \| `NoneType`              | `null`                     | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                     |
| `LAB_REGISTRY_LOCK_TIMEOUT`       | `number`                            | `60.0`                     | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                     |
| `LAB_OTEL_ENABLED`                | `boolean`                           | `false`                    | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                    |
| `LAB_OTEL_SERVICE_NAME`           | `string` \| `NoneType`              | `null`                     | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                     |
| `LAB_OTEL_EXPORTER`               | `"console"` \| `"otlp"` \| `"none"` | `"console"`                | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                |
| `LAB_OTEL_ENDPOINT`               | `string` \| `NoneType`              | `null`                     | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                     |
| `LAB_OTEL_PROTOCOL`               | `"grpc"` \| `"http"`                | `"grpc"`                   | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                   |
| `LAB_DASHBOARD_FILES_PATH`        | `string` \| `Path` \| `NoneType`    | `"~/MADSci/ui/dist"`       | Path to the static files for the dashboard. Set to None to disable the dashboard.                                                                       | `"~/MADSci/ui/dist"`       |

## LocationManagerSettings

Settings for the LocationManager.

**Environment Prefix**: `LOCATION_`

| Name                                   | Type                                         | Default                    | Description                                                                                                                                             | Example                    |
|----------------------------------------|----------------------------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| `LOCATION_SERVER_URL`                  | `AnyUrl`                                     | `"http://localhost:8006/"` | The URL where this manager's server runs.                                                                                                               | `"http://localhost:8006/"` |
| `LOCATION_MANAGER_ID`                  | `string` \| `NoneType`                       | `null`                     | Unique identifier for this manager instance. If not set, a new ULID is generated at runtime. The registry system provides the stable ID thereafter.     | `null`                     |
| `LOCATION_MANAGER_TYPE`                | `ManagerType` \| `NoneType`                  | `"location_manager"`       | The type of manager.                                                                                                                                    | `"location_manager"`       |
| `LOCATION_RATE_LIMIT_ENABLED`          | `boolean`                                    | `true`                     | Enable rate limiting for API endpoints.                                                                                                                 | `true`                     |
| `LOCATION_RATE_LIMIT_REQUESTS`         | `integer`                                    | `300`                      | Maximum number of requests allowed per long time window.                                                                                                | `300`                      |
| `LOCATION_RATE_LIMIT_WINDOW`           | `integer`                                    | `60`                       | Long time window for rate limiting in seconds.                                                                                                          | `60`                       |
| `LOCATION_RATE_LIMIT_SHORT_REQUESTS`   | `integer` \| `NoneType`                      | `50`                       | Maximum number of requests allowed per short time window for burst protection. If None, short window limiting is disabled.                              | `50`                       |
| `LOCATION_RATE_LIMIT_SHORT_WINDOW`     | `integer` \| `NoneType`                      | `1`                        | Short time window for burst protection in seconds. If None, short window limiting is disabled.                                                          | `1`                        |
| `LOCATION_RATE_LIMIT_CLEANUP_INTERVAL` | `integer`                                    | `300`                      | Interval in seconds between cleanup operations to prevent memory leaks.                                                                                 | `300`                      |
| `LOCATION_RATE_LIMIT_EXEMPT_IPS`       | `array` \| `NoneType`                        | `null`                     | List of IP addresses exempt from rate limiting. Defaults to localhost IPs (127.0.0.1, ::1) if not specified.                                            | `null`                     |
| `LOCATION_UVICORN_WORKERS`             | `integer` \| `NoneType`                      | `null`                     | Number of uvicorn worker processes. If None, uses uvicorn default (1).                                                                                  | `null`                     |
| `LOCATION_UVICORN_LIMIT_CONCURRENCY`   | `integer` \| `NoneType`                      | `null`                     | Maximum number of concurrent connections. If None, no limit is enforced.                                                                                | `null`                     |
| `LOCATION_UVICORN_LIMIT_MAX_REQUESTS`  | `integer` \| `NoneType`                      | `null`                     | Maximum number of requests a worker will process before restarting. Helps prevent memory leaks.                                                         | `null`                     |
| `LOCATION_ENABLE_REGISTRY_RESOLUTION`  | `boolean`                                    | `true`                     | When true, resolve manager_id from the ID Registry at startup for stable identity across restarts.                                                      | `true`                     |
| `LOCATION_MANAGER_NAME`                | `string` \| `NoneType`                       | `null`                     | Name for this manager instance. Used for registry lookup and display.                                                                                   | `null`                     |
| `LOCATION_MANAGER_DESCRIPTION`         | `string` \| `NoneType`                       | `null`                     | Human-readable description of this manager instance.                                                                                                    | `null`                     |
| `LOCATION_LAB_URL`                     | `AnyUrl` \| `NoneType`                       | `null`                     | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`                     |
| `LOCATION_REGISTRY_LOCK_TIMEOUT`       | `number`                                     | `60.0`                     | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`                     |
| `LOCATION_OTEL_ENABLED`                | `boolean`                                    | `false`                    | Enable OpenTelemetry tracing and metrics integration for this manager                                                                                   | `false`                    |
| `LOCATION_OTEL_SERVICE_NAME`           | `string` \| `NoneType`                       | `null`                     | Override service name for OpenTelemetry (defaults to manager name)                                                                                      | `null`                     |
| `LOCATION_OTEL_EXPORTER`               | `"console"` \| `"otlp"` \| `"none"`          | `"console"`                | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable                                                        | `"console"`                |
| `LOCATION_OTEL_ENDPOINT`               | `string` \| `NoneType`                       | `null`                     | OTLP collector endpoint (required when otel_exporter='otlp')                                                                                            | `null`                     |
| `LOCATION_OTEL_PROTOCOL`               | `"grpc"` \| `"http"`                         | `"grpc"`                   | OTLP transport protocol ('grpc' or 'http')                                                                                                              | `"grpc"`                   |
| `LOCATION_LOCATIONS`                   | `array` \| `NoneType`                        | `null`                     | Location definitions managed by this LocationManager.                                                                                                   | `null`                     |
| `LOCATION_TRANSFER_CAPABILITIES`       | `LocationTransferCapabilities` \| `NoneType` | `null`                     | Transfer capabilities configuration for this LocationManager.                                                                                           | `null`                     |
| `LOCATION_REDIS_HOST`                  | `string`                                     | `"localhost"`              | The host of the Redis server for state storage.                                                                                                         | `"localhost"`              |
| `LOCATION_REDIS_PORT`                  | `integer`                                    | `6379`                     | The port of the Redis server for state storage.                                                                                                         | `6379`                     |
| `LOCATION_REDIS_PASSWORD`              | `string` \| `NoneType`                       | `null`                     | The password for the Redis server (if required).                                                                                                        | `null`                     |

## EventClientConfig

Configuration for an Event Client.

Inherits all HTTP client configuration from MadsciClientConfig including:
- Retry configuration (retry_enabled, retry_total, retry_backoff_factor, etc.)
- Timeout configuration (timeout_default, timeout_data_operations, etc.)
- Connection pooling (pool_connections, pool_maxsize)
- Rate limiting (rate_limit_tracking_enabled, rate_limit_warning_threshold, etc.)

**Environment Prefix**: `EVENT_CLIENT_`

| Name                                          | Type                                | Default                 | Description                                                                                        | Example                 |
|-----------------------------------------------|-------------------------------------|-------------------------|----------------------------------------------------------------------------------------------------|-------------------------|
| `EVENT_CLIENT_RETRY_ENABLED`                  | `boolean`                           | `true`                  | Whether to enable automatic retries for failed requests                                            | `true`                  |
| `EVENT_CLIENT_RETRY_TOTAL`                    | `integer`                           | `3`                     | Total number of retry attempts                                                                     | `3`                     |
| `EVENT_CLIENT_RETRY_BACKOFF_FACTOR`           | `number`                            | `0.3`                   | Backoff factor between retries in seconds                                                          | `0.3`                   |
| `EVENT_CLIENT_RETRY_STATUS_FORCELIST`         | `array`                             | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                                      | `[429,500,502,503,504]` |
| `EVENT_CLIENT_RETRY_ALLOWED_METHODS`          | `array` \| `NoneType`               | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                                    | `null`                  |
| `EVENT_CLIENT_TIMEOUT_DEFAULT`                | `number`                            | `10.0`                  | Default timeout in seconds for standard requests                                                   | `10.0`                  |
| `EVENT_CLIENT_TIMEOUT_DATA_OPERATIONS`        | `number`                            | `60.0`                  | Timeout in seconds for data-heavy operations                                                       | `60.0`                  |
| `EVENT_CLIENT_TIMEOUT_LONG_OPERATIONS`        | `number`                            | `100.0`                 | Timeout in seconds for long-running operations                                                     | `100.0`                 |
| `EVENT_CLIENT_POOL_CONNECTIONS`               | `integer`                           | `10`                    | Number of connection pool entries                                                                  | `10`                    |
| `EVENT_CLIENT_POOL_MAXSIZE`                   | `integer`                           | `10`                    | Maximum size of the connection pool                                                                | `10`                    |
| `EVENT_CLIENT_RATE_LIMIT_TRACKING_ENABLED`    | `boolean`                           | `true`                  | Whether to track rate limit headers from server responses                                          | `true`                  |
| `EVENT_CLIENT_RATE_LIMIT_WARNING_THRESHOLD`   | `number`                            | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits            | `0.8`                   |
| `EVENT_CLIENT_RATE_LIMIT_RESPECT_LIMITS`      | `boolean`                           | `false`                 | Whether to proactively delay requests when approaching rate limits                                 | `false`                 |
| `EVENT_CLIENT_NAME`                           | `string` \| `NoneType`              | `null`                  | The name of the event client.                                                                      | `null`                  |
| `EVENT_SERVER_URL` \| `EVENT_SERVER_URL`      | `AnyUrl` \| `NoneType`              | `null`                  | The URL of the event server.                                                                       | `null`                  |
| `EVENT_CLIENT_LOG_LEVEL`                      | `integer` \| `EventLogLevel`        | `20`                    | The log level of the event client.                                                                 | `20`                    |
| `EVENT_CLIENT_LOG_DIR`                        | `string` \| `Path`                  | `".madsci/logs"`        | The directory to store logs in.                                                                    | `".madsci/logs"`        |
| `EVENT_CLIENT_LOG_ROTATION_TYPE`              | `"size"` \| `"time"` \| `"none"`    | `"size"`                | Type of log rotation: 'size' (RotatingFileHandler), 'time' (TimedRotatingFileHandler), or 'none'   | `"size"`                |
| `EVENT_CLIENT_LOG_MAX_BYTES`                  | `integer`                           | `10485760`              | Maximum log file size in bytes before rotation (for size-based rotation)                           | `10485760`              |
| `EVENT_CLIENT_LOG_BACKUP_COUNT`               | `integer`                           | `5`                     | Number of backup log files to keep                                                                 | `5`                     |
| `EVENT_CLIENT_LOG_ROTATION_WHEN`              | `string`                            | `"midnight"`            | When to rotate logs (for time-based rotation): 'S', 'M', 'H', 'D', 'midnight', 'W0'-'W6'           | `"midnight"`            |
| `EVENT_CLIENT_LOG_ROTATION_INTERVAL`          | `integer`                           | `1`                     | Interval for time-based rotation                                                                   | `1`                     |
| `EVENT_CLIENT_LOG_COMPRESSION_ENABLED`        | `boolean`                           | `true`                  | Whether to compress rotated log files with gzip                                                    | `true`                  |
| `EVENT_CLIENT_LOG_OUTPUT_FORMAT`              | `"json"` \| `"console"`             | `"console"`             | Log output format: 'json' for structured machine-readable, 'console' for human-readable            | `"console"`             |
| `EVENT_CLIENT_FAIL_ON_ERROR`                  | `boolean`                           | `false`                 | If True, raise exceptions on logging/sending failures. If False, log errors silently and continue. | `false`                 |
| `EVENT_CLIENT_OTEL_ENABLED`                   | `boolean`                           | `false`                 | Enable OpenTelemetry tracing and metrics integration                                               | `false`                 |
| `EVENT_CLIENT_OTEL_SERVICE_NAME`              | `string` \| `NoneType`              | `null`                  | Override service name for OpenTelemetry (defaults to client name)                                  | `null`                  |
| `EVENT_CLIENT_OTEL_EXPORTER`                  | `"console"` \| `"otlp"` \| `"none"` | `"console"`             | OpenTelemetry exporter type: 'console' for development, 'otlp' for production, 'none' to disable   | `"console"`             |
| `EVENT_CLIENT_OTEL_ENDPOINT`                  | `string` \| `NoneType`              | `null`                  | OTLP collector endpoint (required when otel_exporter='otlp')                                       | `null`                  |
| `EVENT_CLIENT_OTEL_PROTOCOL`                  | `"grpc"` \| `"http"`                | `"grpc"`                | OTLP transport protocol ('grpc' or 'http')                                                         | `"grpc"`                |
| `EVENT_CLIENT_OTEL_METRIC_EXPORT_INTERVAL_MS` | `integer`                           | `10000`                 | Interval in milliseconds for exporting metrics to the collector                                    | `10000`                 |

### OwnershipInfo

Information about the ownership of a MADSci object.

**Environment Prefix**: `EVENT_CLIENT_SOURCE__`

| Name                                 | Type                   | Default | Description                                    | Example |
|--------------------------------------|------------------------|---------|------------------------------------------------|---------|
| `EVENT_CLIENT_SOURCE__USER_ID`       | `string` \| `NoneType` | `null`  | The ID of the user who owns the object.        | `null`  |
| `EVENT_CLIENT_SOURCE__EXPERIMENT_ID` | `string` \| `NoneType` | `null`  | The ID of the experiment that owns the object. | `null`  |
| `EVENT_CLIENT_SOURCE__CAMPAIGN_ID`   | `string` \| `NoneType` | `null`  | The ID of the campaign that owns the object.   | `null`  |
| `EVENT_CLIENT_SOURCE__PROJECT_ID`    | `string` \| `NoneType` | `null`  | The ID of the project that owns the object.    | `null`  |
| `EVENT_CLIENT_SOURCE__NODE_ID`       | `string` \| `NoneType` | `null`  | The ID of the node that owns the object.       | `null`  |
| `EVENT_CLIENT_SOURCE__WORKCELL_ID`   | `string` \| `NoneType` | `null`  | The ID of the workcell that owns the object.   | `null`  |
| `EVENT_CLIENT_SOURCE__LAB_ID`        | `string` \| `NoneType` | `null`  | The ID of the lab that owns the object.        | `null`  |
| `EVENT_CLIENT_SOURCE__STEP_ID`       | `string` \| `NoneType` | `null`  | The ID of the step that owns the object.       | `null`  |
| `EVENT_CLIENT_SOURCE__WORKFLOW_ID`   | `string` \| `NoneType` | `null`  | The ID of the workflow that owns the object.   | `null`  |
| `EVENT_CLIENT_SOURCE__MANAGER_ID`    | `string` \| `NoneType` | `null`  | The ID of the manager that owns the object.    | `null`  |

## RestNodeClientConfig

Configuration for Node REST clients.

Node clients handle action operations (create, upload, start, download)
that may require extended timeouts.

**Environment Prefix**: `NODE_CLIENT_`

| Name                                       | Type                  | Default                 | Description                                                                             | Example                 |
|--------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `NODE_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `NODE_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `NODE_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `NODE_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `NODE_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `NODE_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `NODE_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout for node action operations                                                      | `60.0`                  |
| `NODE_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `NODE_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `NODE_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `NODE_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `NODE_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `NODE_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## ResourceClientConfig

Configuration for the Resource Manager client.

**Environment Prefix**: `RESOURCE_CLIENT_`

| Name                                           | Type                  | Default                 | Description                                                                             | Example                 |
|------------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `RESOURCE_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `RESOURCE_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `RESOURCE_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `RESOURCE_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `RESOURCE_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `RESOURCE_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `RESOURCE_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `RESOURCE_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `RESOURCE_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `RESOURCE_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `RESOURCE_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `RESOURCE_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `RESOURCE_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## ExperimentClientConfig

Configuration for the Experiment Manager client.

**Environment Prefix**: `EXPERIMENT_CLIENT_`

| Name                                             | Type                  | Default                 | Description                                                                             | Example                 |
|--------------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `EXPERIMENT_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `EXPERIMENT_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `EXPERIMENT_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `EXPERIMENT_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `EXPERIMENT_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `EXPERIMENT_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `EXPERIMENT_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `EXPERIMENT_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `EXPERIMENT_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `EXPERIMENT_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `EXPERIMENT_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `EXPERIMENT_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `EXPERIMENT_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## DataClientConfig

Configuration for the Data Manager client.

The Data Manager handles data uploads and downloads that may require extended timeouts.

**Environment Prefix**: `DATA_CLIENT_`

| Name                                       | Type                  | Default                 | Description                                                                             | Example                 |
|--------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `DATA_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `DATA_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `DATA_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `DATA_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `DATA_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `DATA_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `DATA_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `DATA_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `DATA_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `DATA_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `DATA_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `DATA_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `DATA_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## MadsciClientConfig

Base configuration for MADSci HTTP clients.

This class provides standardized configuration for requests library usage,
including retry strategies, timeout values, and backoff algorithms.
All MADSci clients should use this configuration to ensure consistency.

Attributes
----------
retry_enabled : bool
    Whether to enable automatic retries for failed requests. Default: True.
retry_total : int
    Total number of retry attempts. Default: 3.
retry_backoff_factor : float
    Backoff factor between retries (in seconds). The actual delay is calculated
    as {backoff factor} * (2 ** ({retry number} - 1)). Default: 0.3.
retry_status_forcelist : list[int]
    HTTP status codes that should trigger a retry. Default: [429, 500, 502, 503, 504].
retry_allowed_methods : Optional[list[str]]
    HTTP methods that are allowed to be retried. If None, uses urllib3 defaults
    (HEAD, GET, PUT, DELETE, OPTIONS, TRACE). Default: None.
timeout_default : float
    Default timeout in seconds for standard requests. Default: 10.
timeout_data_operations : float
    Timeout in seconds for data-heavy operations (e.g., uploads, downloads). Default: 60.
timeout_long_operations : float
    Timeout in seconds for long-running operations (e.g., workflow queries, utilization). Default: 100.
pool_connections : int
    Number of connection pool entries for the session. Default: 10.
pool_maxsize : int
    Maximum size of the connection pool. Default: 10.
rate_limit_tracking_enabled : bool
    Whether to track rate limit headers from server responses. Default: True.
rate_limit_warning_threshold : float
    Threshold (0.0 to 1.0) at which to log warnings about approaching rate limits. Default: 0.8.
rate_limit_respect_limits : bool
    Whether to proactively delay requests when approaching rate limits. Default: False.

**Environment Prefix**: `MADSCI_CLIENT_`

| Name                                         | Type                  | Default                 | Description                                                                             | Example                 |
|----------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `MADSCI_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `MADSCI_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `MADSCI_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `MADSCI_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `MADSCI_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `MADSCI_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `MADSCI_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `MADSCI_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `MADSCI_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `MADSCI_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `MADSCI_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `MADSCI_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `MADSCI_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## LocationClientConfig

Configuration for the Location Manager client.

**Environment Prefix**: `LOCATION_CLIENT_`

| Name                                           | Type                  | Default                 | Description                                                                             | Example                 |
|------------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `LOCATION_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `LOCATION_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `LOCATION_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `LOCATION_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `LOCATION_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `LOCATION_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `LOCATION_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `LOCATION_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `LOCATION_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `LOCATION_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `LOCATION_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `LOCATION_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `LOCATION_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## WorkcellClientConfig

Configuration for the Workcell Manager client.

The Workcell Manager handles workflow queries that may require extended timeouts.

**Environment Prefix**: `WORKCELL_CLIENT_`

| Name                                           | Type                  | Default                 | Description                                                                             | Example                 |
|------------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `WORKCELL_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `WORKCELL_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `WORKCELL_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `WORKCELL_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `WORKCELL_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `WORKCELL_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `WORKCELL_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `WORKCELL_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `WORKCELL_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `WORKCELL_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `WORKCELL_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `WORKCELL_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `WORKCELL_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## LabClientConfig

Configuration for the Lab (Squid) client.

**Environment Prefix**: `LAB_CLIENT_`

| Name                                      | Type                  | Default                 | Description                                                                             | Example                 |
|-------------------------------------------|-----------------------|-------------------------|-----------------------------------------------------------------------------------------|-------------------------|
| `LAB_CLIENT_RETRY_ENABLED`                | `boolean`             | `true`                  | Whether to enable automatic retries for failed requests                                 | `true`                  |
| `LAB_CLIENT_RETRY_TOTAL`                  | `integer`             | `3`                     | Total number of retry attempts                                                          | `3`                     |
| `LAB_CLIENT_RETRY_BACKOFF_FACTOR`         | `number`              | `0.3`                   | Backoff factor between retries in seconds                                               | `0.3`                   |
| `LAB_CLIENT_RETRY_STATUS_FORCELIST`       | `array`               | `[429,500,502,503,504]` | HTTP status codes that should trigger a retry                                           | `[429,500,502,503,504]` |
| `LAB_CLIENT_RETRY_ALLOWED_METHODS`        | `array` \| `NoneType` | `null`                  | HTTP methods allowed to be retried (None uses urllib3 defaults)                         | `null`                  |
| `LAB_CLIENT_TIMEOUT_DEFAULT`              | `number`              | `10.0`                  | Default timeout in seconds for standard requests                                        | `10.0`                  |
| `LAB_CLIENT_TIMEOUT_DATA_OPERATIONS`      | `number`              | `60.0`                  | Timeout in seconds for data-heavy operations                                            | `60.0`                  |
| `LAB_CLIENT_TIMEOUT_LONG_OPERATIONS`      | `number`              | `100.0`                 | Timeout in seconds for long-running operations                                          | `100.0`                 |
| `LAB_CLIENT_POOL_CONNECTIONS`             | `integer`             | `10`                    | Number of connection pool entries                                                       | `10`                    |
| `LAB_CLIENT_POOL_MAXSIZE`                 | `integer`             | `10`                    | Maximum size of the connection pool                                                     | `10`                    |
| `LAB_CLIENT_RATE_LIMIT_TRACKING_ENABLED`  | `boolean`             | `true`                  | Whether to track rate limit headers from server responses                               | `true`                  |
| `LAB_CLIENT_RATE_LIMIT_WARNING_THRESHOLD` | `number`              | `0.8`                   | Threshold (as fraction of limit) at which to log warnings about approaching rate limits | `0.8`                   |
| `LAB_CLIENT_RATE_LIMIT_RESPECT_LIMITS`    | `boolean`             | `false`                 | Whether to proactively delay requests when approaching rate limits                      | `false`                 |

## NodeConfig

Basic Configuration for a MADSci Node.

**Environment Prefix**: `NODE_`

| Name                              | Type                     | Default | Description                                                                                                                                             | Example |
|-----------------------------------|--------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| `NODE_STATUS_UPDATE_INTERVAL`     | `number` \| `NoneType`   | `2.0`   | The interval in seconds at which the node should update its status.                                                                                     | `2.0`   |
| `NODE_STATE_UPDATE_INTERVAL`      | `number` \| `NoneType`   | `2.0`   | The interval in seconds at which the node should update its state.                                                                                      | `2.0`   |
| `NODE_NAME` \| `NODE_NAME`        | `string` \| `NoneType`   | `null`  | Name for this node. If not set, defaults to the class name.                                                                                             | `null`  |
| `NODE_ID` \| `NODE_ID`            | `string` \| `NoneType`   | `null`  | Unique ID for this node. If not set, a new ULID is generated.                                                                                           | `null`  |
| `NODE_TYPE` \| `NODE_TYPE`        | `NodeType` \| `NoneType` | `null`  | The type of thing this node provides an interface for.                                                                                                  | `null`  |
| `NODE_MODULE_NAME`                | `string` \| `NoneType`   | `null`  | Name of the node module implementation.                                                                                                                 | `null`  |
| `NODE_MODULE_VERSION`             | `string` \| `NoneType`   | `null`  | Version of the node module implementation.                                                                                                              | `null`  |
| `NODE_ENABLE_REGISTRY_RESOLUTION` | `boolean`                | `true`  | When true, resolve node_id from the ID Registry at startup for stable identity across restarts.                                                         | `true`  |
| `NODE_LAB_URL`                    | `AnyUrl` \| `NoneType`   | `null`  | Lab Manager URL for distributed registry coordination.                                                                                                  | `null`  |
| `NODE_REGISTRY_LOCK_TIMEOUT`      | `number`                 | `60.0`  | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts. | `60.0`  |

## RestNodeConfig

Default Configuration for a MADSci Node that communicates over REST.

**Environment Prefix**: `NODE_`

| Name                               | Type                     | Default                    | Description                                                                                                                                                            | Example                    |
|------------------------------------|--------------------------|----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| `NODE_STATUS_UPDATE_INTERVAL`      | `number` \| `NoneType`   | `2.0`                      | The interval in seconds at which the node should update its status.                                                                                                    | `2.0`                      |
| `NODE_STATE_UPDATE_INTERVAL`       | `number` \| `NoneType`   | `2.0`                      | The interval in seconds at which the node should update its state.                                                                                                     | `2.0`                      |
| `NODE_NAME` \| `NODE_NAME`         | `string` \| `NoneType`   | `null`                     | Name for this node. If not set, defaults to the class name.                                                                                                            | `null`                     |
| `NODE_ID` \| `NODE_ID`             | `string` \| `NoneType`   | `null`                     | Unique ID for this node. If not set, a new ULID is generated.                                                                                                          | `null`                     |
| `NODE_TYPE` \| `NODE_TYPE`         | `NodeType` \| `NoneType` | `null`                     | The type of thing this node provides an interface for.                                                                                                                 | `null`                     |
| `NODE_MODULE_NAME`                 | `string` \| `NoneType`   | `null`                     | Name of the node module implementation.                                                                                                                                | `null`                     |
| `NODE_MODULE_VERSION`              | `string` \| `NoneType`   | `null`                     | Version of the node module implementation.                                                                                                                             | `null`                     |
| `NODE_ENABLE_REGISTRY_RESOLUTION`  | `boolean`                | `true`                     | When true, resolve node_id from the ID Registry at startup for stable identity across restarts.                                                                        | `true`                     |
| `NODE_LAB_URL`                     | `AnyUrl` \| `NoneType`   | `null`                     | Lab Manager URL for distributed registry coordination.                                                                                                                 | `null`                     |
| `NODE_REGISTRY_LOCK_TIMEOUT`       | `number`                 | `60.0`                     | Seconds to retry registry lock acquisition on contention at startup. Should be at least 2x the lock TTL (30s) to survive ungraceful container restarts.                | `60.0`                     |
| `NODE_URL` \| `NODE_URL`           | `AnyUrl`                 | `"http://127.0.0.1:2000/"` | The URL used to communicate with the node. This is the base URL for the REST API.                                                                                      | `"http://127.0.0.1:2000/"` |
| `NODE_UVICORN_KWARGS`              | `object`                 | `{"limit_concurrency":10}` | Configuration for the Uvicorn server that runs the REST API. By default, sets limit_concurrency=10 to protect against connection exhaustion attacks.                   | `{"limit_concurrency":10}` |
| `NODE_ENABLE_RATE_LIMITING`        | `boolean`                | `true`                     | Enable rate limiting middleware for the REST API.                                                                                                                      | `true`                     |
| `NODE_RATE_LIMIT_REQUESTS`         | `integer`                | `100`                      | Maximum number of requests allowed per long time window (only used if enable_rate_limiting is True).                                                                   | `100`                      |
| `NODE_RATE_LIMIT_WINDOW`           | `integer`                | `60`                       | Long time window in seconds for rate limiting (only used if enable_rate_limiting is True).                                                                             | `60`                       |
| `NODE_RATE_LIMIT_SHORT_REQUESTS`   | `integer` \| `NoneType`  | `50`                       | Maximum number of requests allowed per short time window for burst protection (only used if enable_rate_limiting is True). If None, short window limiting is disabled. | `50`                       |
| `NODE_RATE_LIMIT_SHORT_WINDOW`     | `integer` \| `NoneType`  | `1`                        | Short time window for burst protection in seconds (only used if enable_rate_limiting is True). If None, short window limiting is disabled.                             | `1`                        |
| `NODE_RATE_LIMIT_CLEANUP_INTERVAL` | `integer`                | `300`                      | Interval in seconds between cleanup operations to prevent memory leaks (only used if enable_rate_limiting is True).                                                    | `300`                      |

## PostgreSQLBackupSettings

PostgreSQL-specific backup settings.

**Environment Prefix**: `POSTGRES_`

| Name                          | Type      | Default                                                | Description                                   | Example                                                |
|-------------------------------|-----------|--------------------------------------------------------|-----------------------------------------------|--------------------------------------------------------|
| `POSTGRES_BACKUP_DIR`         | `Path`    | `".madsci/backups"`                                    | Directory for storing backups                 | `".madsci/backups"`                                    |
| `POSTGRES_MAX_BACKUPS`        | `integer` | `10`                                                   | Maximum number of backups to retain           | `10`                                                   |
| `POSTGRES_VALIDATE_INTEGRITY` | `boolean` | `true`                                                 | Perform integrity validation after backup     | `true`                                                 |
| `POSTGRES_COMPRESSION`        | `boolean` | `true`                                                 | Enable backup compression                     | `true`                                                 |
| `DB_URL` \| `DB_URL`          | `string`  | `"postgresql://madsci:madsci@localhost:5432/postgres"` | PostgreSQL connection URL                     | `"postgresql://madsci:madsci@localhost:5432/postgres"` |
| `POSTGRES_BACKUP_FORMAT`      | `string`  | `"custom"`                                             | pg_dump format: custom, plain, directory, tar | `"custom"`                                             |

## DocumentDBBackupSettings

MongoDB-compatible document database backup settings.

**Environment Prefix**: `MONGODB_`

| Name                                                     | Type                   | Default                       | Description                                         | Example                       |
|----------------------------------------------------------|------------------------|-------------------------------|-----------------------------------------------------|-------------------------------|
| `MONGODB_BACKUP_DIR`                                     | `Path`                 | `".madsci/backups"`           | Directory for storing backups                       | `".madsci/backups"`           |
| `MONGODB_MAX_BACKUPS`                                    | `integer`              | `10`                          | Maximum number of backups to retain                 | `10`                          |
| `MONGODB_VALIDATE_INTEGRITY`                             | `boolean`              | `true`                        | Perform integrity validation after backup           | `true`                        |
| `MONGODB_COMPRESSION`                                    | `boolean`              | `true`                        | Enable backup compression                           | `true`                        |
| `DOCUMENT_DB_URL` \| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` | `AnyUrl`               | `"mongodb://localhost:27017"` | MongoDB-compatible document database connection URL | `"mongodb://localhost:27017"` |
| `MONGODB_DATABASE`                                       | `string` \| `NoneType` | `null`                        | Database name to backup                             | `null`                        |
| `MONGODB_COLLECTIONS`                                    | `array` \| `NoneType`  | `null`                        | Specific collections to backup (all if None)        | `null`                        |

## DocumentDBMigrationSettings

Configuration settings for MongoDB-compatible document database migration operations.

**Environment Prefix**: `MONGODB_MIGRATION_`

| Name                                                                                              | Type                             | Default                       | Description                                                                                                            | Example                       |
|---------------------------------------------------------------------------------------------------|----------------------------------|-------------------------------|------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `DOCUMENT_DB_URL` \| `MONGO_DB_URL` \| `MONGODB_URL` \| `MONGO_URL` \| `DATABASE_URL` \| `DB_URL` | `AnyUrl`                         | `"mongodb://localhost:27017"` | MongoDB-compatible document database connection URL (e.g., mongodb://localhost:27017). Defaults to localhost instance. | `"mongodb://localhost:27017"` |
| `MONGODB_MIGRATION_DATABASE`                                                                      | `string` \| `NoneType`           | `null`                        | Database name to migrate (e.g., madsci_events, madsci_data)                                                            | `null`                        |
| `SCHEMA_FILE` \| `MONGODB_SCHEMA_FILE`                                                            | `string` \| `Path` \| `NoneType` | `null`                        | Explicit path to schema.json. If not provided, will auto-detect based on database name.                                | `null`                        |
| `MONGODB_MIGRATION_BACKUP_DIR`                                                                    | `string` \| `Path`               | `".madsci/backups/mongodb"`   | Directory where database backups will be stored.                                                                       | `".madsci/backups/mongodb"`   |
| `MONGODB_MIGRATION_TARGET_VERSION`                                                                | `string` \| `NoneType`           | `null`                        | Target version to migrate to (defaults to current MADSci version)                                                      | `null`                        |
| `MONGODB_MIGRATION_BACKUP_ONLY`                                                                   | `boolean`                        | `false`                       | Only create a backup, do not run migration                                                                             | `false`                       |
| `MONGODB_MIGRATION_RESTORE_FROM`                                                                  | `string` \| `Path` \| `NoneType` | `null`                        | Restore from specified backup directory instead of migrating                                                           | `null`                        |
| `MONGODB_MIGRATION_CHECK_VERSION`                                                                 | `boolean`                        | `false`                       | Only check version compatibility, do not migrate                                                                       | `false`                       |
| `MONGODB_MIGRATION_VALIDATE_SCHEMA`                                                               | `boolean`                        | `false`                       | Validate current database schema against expected schema                                                               | `false`                       |

## DatabaseMigrationSettings

Configuration settings for PostgreSQL database migration operations.

**Environment Prefix**: `RESOURCES_MIGRATION_`

| Name                                     | Type                             | Default                        | Description                                                                                                                                        | Example                        |
|------------------------------------------|----------------------------------|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| `RESOURCES_MIGRATION_DB_URL`             | `string` \| `NoneType`           | `null`                         | PostgreSQL connection URL (e.g., postgresql://user:pass@localhost:5432/postgres). If not provided, will try RESOURCES_DB_URL environment variable. | `null`                         |
| `RESOURCES_MIGRATION_TARGET_VERSION`     | `string` \| `NoneType`           | `null`                         | Target version to migrate to (defaults to current MADSci version)                                                                                  | `null`                         |
| `RESOURCES_MIGRATION_BACKUP_DIR`         | `string` \| `Path`               | `".madsci/backups/postgresql"` | Directory where database backups will be stored.                                                                                                   | `".madsci/backups/postgresql"` |
| `RESOURCES_MIGRATION_BACKUP_ONLY`        | `boolean`                        | `false`                        | Only create a backup, do not run migration                                                                                                         | `false`                        |
| `RESOURCES_MIGRATION_RESTORE_FROM`       | `string` \| `Path` \| `NoneType` | `null`                         | Restore from specified backup file instead of migrating                                                                                            | `null`                         |
| `RESOURCES_MIGRATION_GENERATE_MIGRATION` | `string` \| `NoneType`           | `null`                         | Generate a new migration file with the given message                                                                                               | `null`                         |
