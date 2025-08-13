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
