# Configuration

Here you can find all available configuration options using ENV variables.

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

## EventClientConfig

Configuration for an Event Client.

**Environment Prefix**: `EVENT_CLIENT_`

| Name                                     | Type                         | Default            | Description                        | Example            |
|------------------------------------------|------------------------------|--------------------|------------------------------------|--------------------|
| `EVENT_CLIENT_NAME`                      | `string` \| `NoneType`       | `null`             | The name of the event client.      | `null`             |
| `EVENT_SERVER_URL` \| `EVENT_SERVER_URL` | `AnyUrl` \| `NoneType`       | `null`             | The URL of the event server.       | `null`             |
| `EVENT_CLIENT_LOG_LEVEL`                 | `integer` \| `EventLogLevel` | `20`               | The log level of the event client. | `20`               |
| `EVENT_CLIENT_LOG_DIR`                   | `string` \| `Path`           | `"~/.madsci/logs"` | The directory to store logs in.    | `"~/.madsci/logs"` |

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

## ObjectStorageSettings

Settings for S3-compatible object storage.

**Environment Prefix**: `OBJECT_STORAGE_`

| Name                            | Type                   | Default         | Description                                                         | Example         |
|---------------------------------|------------------------|-----------------|---------------------------------------------------------------------|-----------------|
| `OBJECT_STORAGE_ENDPOINT`       | `string` \| `NoneType` | `null`          | Endpoint for S3-compatible storage (e.g., 'minio.example.com:9000') | `null`          |
| `OBJECT_STORAGE_ACCESS_KEY`     | `string`               | `""`            | Access key for authentication                                       | `""`            |
| `OBJECT_STORAGE_SECRET_KEY`     | `string`               | `""`            | Secret key for authentication                                       | `""`            |
| `OBJECT_STORAGE_SECURE`         | `boolean`              | `false`         | Whether to use HTTPS (True) or HTTP (False)                         | `false`         |
| `OBJECT_STORAGE_DEFAULT_BUCKET` | `string`               | `"madsci-data"` | Default bucket to use for storing data                              | `"madsci-data"` |
| `OBJECT_STORAGE_REGION`         | `string` \| `NoneType` | `null`          | Optional for AWS S3/other providers                                 | `null`          |

## DataManagerSettings

Settings for the MADSci Data Manager.

**Environment Prefix**: `DATA_`

| Name                      | Type               | Default                       | Description                                               | Example                       |
|---------------------------|--------------------|-------------------------------|-----------------------------------------------------------|-------------------------------|
| `DATA_SERVER_URL`         | `AnyUrl`           | `"http://localhost:8004/"`    | The URL of the data manager server.                       | `"http://localhost:8004/"`    |
| `DATA_MANAGER_DEFINITION` | `string` \| `Path` | `"data.manager.yaml"`         | Path to the data manager definition file to use.          | `"data.manager.yaml"`         |
| `DATA_COLLECTION_NAME`    | `string`           | `"madsci_data"`               | The name of the MongoDB collection where data are stored. | `"madsci_data"`               |
| `DATA_DB_URL`             | `string`           | `"mongodb://localhost:27017"` | The URL of the database used by the Data Manager.         | `"mongodb://localhost:27017"` |
| `DATA_FILE_STORAGE_PATH`  | `string` \| `Path` | `"~/.madsci/datapoints"`      | The path where files are stored on the server.            | `"~/.madsci/datapoints"`      |

## EventManagerSettings

Handles settings and configuration for the Event Manager.

**Environment Prefix**: `EVENT_`

| Name                       | Type                              | Default                       | Description                                                 | Example                       |
|----------------------------|-----------------------------------|-------------------------------|-------------------------------------------------------------|-------------------------------|
| `EVENT_SERVER_URL`         | `AnyUrl` \| `NoneType`            | `"http://localhost:8001"`     | The URL of the Event Manager server.                        | `"http://localhost:8001"`     |
| `EVENT_MANAGER_DEFINITION` | `string` \| `Path`                | `"event.manager.yaml"`        | Path to the event manager definition file to use.           | `"event.manager.yaml"`        |
| `EVENT_DB_URL`             | `string`                          | `"mongodb://localhost:27017"` | The URL of the database used by the Event Manager.          | `"mongodb://localhost:27017"` |
| `EVENT_DATABASE_NAME`      | `string`                          | `"madsci_events"`             | The name of the MongoDB database where events are stored.   | `"madsci_events"`             |
| `EVENT_COLLECTION_NAME`    | `string`                          | `"events"`                    | The name of the MongoDB collection where events are stored. | `"events"`                    |
| `EVENT_ALERT_LEVEL`        | `EventLogLevel`                   | `40`                          | The log level at which to send an alert.                    | `40`                          |
| `EVENT_EMAIL_ALERTS`       | `EmailAlertsConfig` \| `NoneType` | `null`                        | The configuration for sending email alerts.                 | `null`                        |

## WorkcellManagerSettings

Settings for the MADSci Workcell Manager.

**Environment Prefix**: `WORKCELL_`

| Name                                                                           | Type                             | Default                                                  | Description                                                                                                                                                        | Example                                                  |
|--------------------------------------------------------------------------------|----------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| `WORKCELL_SERVER_URL`                                                          | `AnyUrl`                         | `"http://localhost:8005/"`                               | The URL of the workcell manager server.                                                                                                                            | `"http://localhost:8005/"`                               |
| `WORKCELL_MANAGER_DEFINITION` \| `WORKCELL_DEFINITION` \| `MANAGER_DEFINITION` | `string` \| `Path`               | `"workcell.manager.yaml"`                                | Path to the workcell definition file to use.                                                                                                                       | `"workcell.manager.yaml"`                                |
| `WORKCELLS_DIRECTORY` \| `WORKCELLS_DIRECTORY`                                 | `string` \| `Path` \| `NoneType` | `"~/.madsci/workcells"`                                  | Directory used to store workcell-related files in. Defaults to ~/.madsci/workcells. Workcell-related filess will be stored in a sub-folder with the workcell name. | `"~/.madsci/workcells"`                                  |
| `WORKCELL_REDIS_HOST`                                                          | `string`                         | `"localhost"`                                            | The hostname for the redis server .                                                                                                                                | `"localhost"`                                            |
| `WORKCELL_REDIS_PORT`                                                          | `integer`                        | `6379`                                                   | The port for the redis server.                                                                                                                                     | `6379`                                                   |
| `WORKCELL_REDIS_PASSWORD`                                                      | `string` \| `NoneType`           | `null`                                                   | The password for the redis server.                                                                                                                                 | `null`                                                   |
| `WORKCELL_SCHEDULER_UPDATE_INTERVAL`                                           | `number`                         | `2.0`                                                    | The interval at which the scheduler runs, in seconds. Must be >= node_update_interval                                                                              | `2.0`                                                    |
| `WORKCELL_NODE_UPDATE_INTERVAL`                                                | `number`                         | `1.0`                                                    | The interval at which the workcell queries its node's states, in seconds.Must be <= scheduler_update_interval                                                      | `1.0`                                                    |
| `WORKCELL_COLD_START_DELAY`                                                    | `integer`                        | `0`                                                      | How long the Workcell engine should sleep on startup                                                                                                               | `0`                                                      |
| `WORKCELL_SCHEDULER`                                                           | `string`                         | `"madsci.workcell_manager.schedulers.default_scheduler"` | Scheduler module that contains a Scheduler class that inherits from AbstractScheduler to use                                                                       | `"madsci.workcell_manager.schedulers.default_scheduler"` |
| `WORKCELL_MONGO_URL`                                                           | `string` \| `NoneType`           | `"mongodb://localhost:27017"`                            | The URL for the mongo database.                                                                                                                                    | `"mongodb://localhost:27017"`                            |
| `WORKCELL_DATABASE_NAME`                                                       | `string`                         | `"madsci_workcells"`                                     | The name of the MongoDB database where events are stored.                                                                                                          | `"madsci_workcells"`                                     |
| `WORKCELL_COLLECTION_NAME`                                                     | `string`                         | `"archived_workflows"`                                   | The name of the MongoDB collection where events are stored.                                                                                                        | `"archived_workflows"`                                   |
| `WORKCELL_GET_ACTION_RESULT_RETRIES`                                           | `integer`                        | `3`                                                      | Number of times to retry getting an action result                                                                                                                  | `3`                                                      |

## ExperimentManagerSettings

Settings for the MADSci Experiment Manager.

**Environment Prefix**: `EXPERIMENT_`

| Name                            | Type               | Default                       | Description                                                 | Example                       |
|---------------------------------|--------------------|-------------------------------|-------------------------------------------------------------|-------------------------------|
| `EXPERIMENT_SERVER_URL`         | `AnyUrl`           | `"http://localhost:8002/"`    | The URL of the experiment manager server.                   | `"http://localhost:8002/"`    |
| `EXPERIMENT_MANAGER_DEFINITION` | `string` \| `Path` | `"experiment.manager.yaml"`   | Path to the experiment manager definition file to use.      | `"experiment.manager.yaml"`   |
| `EXPERIMENT_DB_URL`             | `string`           | `"mongodb://localhost:27017"` | The URL of the database for the experiment manager.         | `"mongodb://localhost:27017"` |
| `EXPERIMENT_DATABASE_NAME`      | `string`           | `"madsci_experiments"`        | The name of the MongoDB database where events are stored.   | `"madsci_experiments"`        |
| `EXPERIMENT_COLLECTION_NAME`    | `string`           | `"experiments"`               | The name of the MongoDB collection where events are stored. | `"experiments"`               |

## ResourceManagerSettings

Settings for the MADSci Resource Manager.

**Environment Prefix**: `RESOURCE_`

| Name                          | Type               | Default                                                 | Description                                          | Example                                                 |
|-------------------------------|--------------------|---------------------------------------------------------|------------------------------------------------------|---------------------------------------------------------|
| `RESOURCE_SERVER_URL`         | `AnyUrl`           | `"http://localhost:8003"`                               | The URL of the resource manager server.              | `"http://localhost:8003"`                               |
| `RESOURCE_MANAGER_DEFINITION` | `string` \| `Path` | `"resource.manager.yaml"`                               | Path to the resource manager definition file to use. | `"resource.manager.yaml"`                               |
| `RESOURCE_DB_URL`             | `string`           | `"postgresql://madsci:madsci@localhost:5432/resources"` | The URL of the database for the resource manager.    | `"postgresql://madsci:madsci@localhost:5432/resources"` |

## LabManagerSettings

Settings for the MADSci Lab.

**Environment Prefix**: `LAB_`

| Name                       | Type                             | Default                    | Description                                                                       | Example                    |
|----------------------------|----------------------------------|----------------------------|-----------------------------------------------------------------------------------|----------------------------|
| `LAB_SERVER_URL`           | `AnyUrl`                         | `"http://localhost:8000/"` | The URL of the lab manager.                                                       | `"http://localhost:8000/"` |
| `LAB_MANAGER_DEFINITION`   | `string` \| `Path`               | `"lab.manager.yaml"`       | Path to the lab definition file to use.                                           | `"lab.manager.yaml"`       |
| `LAB_DASHBOARD_FILES_PATH` | `string` \| `Path` \| `NoneType` | `"~/MADSci/ui/dist"`       | Path to the static files for the dashboard. Set to None to disable the dashboard. | `"~/MADSci/ui/dist"`       |

## LocationManagerSettings

Settings for the LocationManager.

**Environment Prefix**: `LOCATION_`

| Name                          | Type                   | Default                    | Description                                          | Example                    |
|-------------------------------|------------------------|----------------------------|------------------------------------------------------|----------------------------|
| `LOCATION_SERVER_URL`         | `AnyUrl`               | `"http://localhost:8006/"` | The URL where this manager's server runs.            | `"http://localhost:8006/"` |
| `LOCATION_MANAGER_DEFINITION` | `string` \| `Path`     | `"location.manager.yaml"`  | Path to the location manager definition file to use. | `"location.manager.yaml"`  |
| `LOCATION_SERVER_HOST`        | `string`               | `"localhost"`              | The host to run the server on.                       | `"localhost"`              |
| `LOCATION_SERVER_PORT`        | `integer`              | `8006`                     | The port to run the server on.                       | `8006`                     |
| `LOCATION_REDIS_HOST`         | `string`               | `"localhost"`              | The host of the Redis server for state storage.      | `"localhost"`              |
| `LOCATION_REDIS_PORT`         | `integer`              | `6379`                     | The port of the Redis server for state storage.      | `6379`                     |
| `LOCATION_REDIS_PASSWORD`     | `string` \| `NoneType` | `null`                     | The password for the Redis server (if required).     | `null`                     |
