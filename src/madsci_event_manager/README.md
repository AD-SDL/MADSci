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
    event_server="https://127.0.0.1:8001", # Update with the host/port you configured for your EventManager server
)

event_client.log_info("This logs a simple string at the INFO level, with event_type LOG_INFO")
event = Event(
    event_type="NODE_CREATE",
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
