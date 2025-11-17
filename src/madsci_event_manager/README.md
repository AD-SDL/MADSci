# MADSci Event Manager

Handles distributed logging and events throughout a MADSci-powered Lab.

![MADSci Event Manager Architecture Diagram](./assets/event_manager.drawio.svg)

## Features

- Centralized logging from distributed lab components
- Event querying with structured filtering
- Arbitrary event data support with standard schema
- Python `logging`-style log levels
- Alert notifications (email, etc.)

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:

- PyPI: `pip install madsci.event_manager`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example configuration**: See [example_lab/managers/example_event.manager.yaml](../../example_lab/managers/example_event.manager.yaml)

**Dependencies**: MongoDB database (see the [example_lab](../../example_lab/))

## Usage

### Quick Start

Use the [example_lab](../../example_lab/) as a starting point:

```bash
# Start with working example
docker compose up  # From repo root
# Event Manager available at http://localhost:8001/docs

# Or run standalone
python -m madsci.event_manager.event_server
```

### Manager Setup

For custom deployments, create an Event Manager definition:

```bash
madsci manager add -t event_manager
```

See [example_event.manager.yaml](../../example_lab/managers/example_event.manager.yaml) for configuration options.

### Client

You can use MADSci's `EventClient` (`madsci.client.event_client.EventClient`) in your python code to log new events to the event manager, or fetch/query existing events.

```python
from madsci.client.event_client import EventClient
from madsci.common.types.event_types import Event, EventLogLevel, EventType

event_client = EventClient(
    event_server="http://localhost:8001", # Update with the host/port you configured for your EventManager server
)

event_client.log_info("This logs a simple string at the INFO level, with event_type LOG_INFO")
# Alternative: event_client.info("Same as log_info")
event = Event(
    event_type=EventType.NODE_CREATE,
    log_level=EventLogLevel.DEBUG,
    event_data="This logs a NODE_CREATE event at the DEBUG level. The event_data field should contain relevant data about the event (in this case, something like the NodeDefinition, for instance)"
)
event_client.log(event)
event_client.log_warning(event) # Log the same event, but override the log level.

# Get the 50 most recent events
event_client.get_events(number=50)
# Get all events from a specific node
event_client.query_events({"source": {"node_id": "01JJ4S0WNGEF5FQAZG5KDGJRBV"}})

event_client.alert(event) # Will force firing any configured alert notifiers on this event
```

### Alerts

The Event Manager provides some native alerting functionality. A default alert level can be set in the event manager definition's `alert_level`, which will determine the minimum log level at which to send an alert. Calls directly to the `EventClient.alert` method will send alerts regardless of the `alert_level`.

You can configure Email Alerts by setting up an `EmailAlertsConfig` (`madsci.common.types.event_types.EmailAlertsConfig`) in the `email_alerts` field of your `EventManagerSettings`.

## Database Migration Tools

MADSci Event Manager includes automated MongoDB migration tools that handle schema changes and version tracking for the event management system.

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
# Run migration for events database (auto-detects schema file)
python -m madsci.common.mongodb_migration_tool --database madsci_events

# Migrate with explicit database URL
python -m madsci.common.mongodb_migration_tool --db-url mongodb://localhost:27017 --database madsci_events

# Use custom schema file
python -m madsci.common.mongodb_migration_tool --database madsci_events --schema-file /path/to/schema.json

# Create backup only
python -m madsci.common.mongodb_migration_tool --database madsci_events --backup-only

# Restore from backup
python -m madsci.common.mongodb_migration_tool --database madsci_events --restore-from /path/to/backup

# Check version compatibility without migrating
python -m madsci.common.mongodb_migration_tool --database madsci_events --check-version
```

#### Docker Usage
When running in Docker containers, use docker-compose to execute migration commands:

```bash
# Run migration for events database in Docker
docker-compose run --rm event-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_events' --schema-file '/app/madsci/event_manager/schema.json'

# Create backup only in Docker
docker-compose run --rm event-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_events' --schema-file '/app/madsci/event_manager/schema.json' --backup-only

# Check version compatibility in Docker
docker-compose run --rm event-manager python -m madsci.common.mongodb_migration_tool --db-url 'mongodb://mongodb:27017' --database 'madsci_events' --schema-file '/app/madsci/event_manager/schema.json' --check-version
```

### Server Integration

The Event Manager server automatically checks for version compatibility on startup. If a mismatch is detected, the server will refuse to start and display migration instructions:

```bash
DATABASE INITIALIZATION REQUIRED! SERVER STARTUP ABORTED!
The database exists but needs version tracking setup.
To resolve this issue, run the migration tool and restart the server.
```

### Schema File Location

The migration tool automatically searches for schema files in:
- `madsci/event_manager/schema.json`

### Backup Location

Backups are stored in `.madsci/mongodb/backups/` with timestamped filenames:
- Format: `madsci_events_backup_YYYYMMDD_HHMMSS`
- Can be restored using the `--restore-from` option

### Requirements

- MongoDB server running and accessible
- MongoDB tools (`mongodump`, `mongorestore`) installed
- Appropriate database permissions for the specified user
## API Reference

The Event Manager provides a REST API for logging and querying events. The API is available at `http://localhost:8001` by default.

### Event Operations

#### POST /event
Log a new event to the system.

**Request Body**: `Event` object
```json
{
  "event_type": "LOG_INFO",
  "log_level": 20,
  "event_data": "Event message or data",
  "alert": false
}
```

**Response**: The logged `Event` object with assigned `event_id` and `event_timestamp`.

#### GET /event/{event_id}
Retrieve a specific event by its ID.

**Parameters**:
- `event_id` (path): The unique event identifier

**Response**: `Event` object or 404 if not found.

#### GET /events
Get the latest events from the system.

**Query Parameters**:
- `number` (int, default: 100): Maximum number of events to return
- `level` (int, default: 0): Minimum log level to include

**Response**: Dictionary mapping event IDs to `Event` objects.

#### POST /events/query
Query events using MongoDB selector syntax.

**Request Body**: MongoDB query selector object
```json
{
  "source.node_id": "01JJ4S0WNGEF5FQAZG5KDGJRBV",
  "log_level": {"$gte": 20}
}
```

**Response**: Dictionary mapping event IDs to matching `Event` objects.

### Utilization Analysis

#### GET /utilization/sessions
Generate session-based utilization reports.

**Query Parameters**:
- `start_time` (string, optional): ISO format start time
- `end_time` (string, optional): ISO format end time
- `csv_format` (bool, default: false): Return data in CSV format
- `save_to_file` (bool, default: false): Save CSV to server filesystem
- `output_path` (string, optional): Server path to save CSV files

**Response**: JSON utilization report or CSV data.

### Standard Manager Endpoints

The Event Manager also provides standard manager endpoints:

- **GET /definition**: Get manager definition and metadata
- **GET /health**: Get health status including database connectivity and event counts

### Interactive API Documentation

Visit `http://localhost:8001/docs` when the Event Manager is running for interactive Swagger UI documentation.

## MongoDB Setup

The Event Manager requires MongoDB for event storage. For local development:

1. **Using Docker** (recommended):
   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   ```

2. **Using the example lab**:
   The [example_lab](../../example_lab/) includes a pre-configured MongoDB instance.

3. **Configuration**:
   Set the database URL in your environment or manager configuration:
   ```yaml
   # In manager YAML config
   db_url: "mongodb://localhost:27017"
   collection_name: "madsci_events"
   ```

   Or as environment variables:
   ```bash
   export EVENT_DB_URL="mongodb://localhost:27017"
   export EVENT_COLLECTION_NAME="madsci_events"
   ```
