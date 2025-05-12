# MADSci Event Manager

Handles distributed logging and events throughout a MADSci-powered Lab.

![MADSci Event Manager Architecture Diagram](./assets/event_manager.drawio.svg)

## Notable Features

- Collects logs from distributed components of the lab and centralizes them
- Allows for querying of events
- Can accept arbitrary event data
- Enforces a standard Event schema, allowing for structured querying and filtering of logs.
- Supports python `logging`-style log levels.

## Installation

The MADSci event manager is available via [the Python Package Index](https://pypi.org/project/madsci.event_manager/), and can be installed via:

```bash
pip install madsci.event_manager
```

This python package is also included as part of the [madsci Docker image](https://github.com/orgs/AD-SDL/packages/container/package/madsci). You can see an example docker image in [this example compose file](./event_manager.compose.yaml).

Note that you will also need a MongoDB database (included in the example compose file)

## Usage

### Manager

To create and run a new MADSci Event Manager, do the following in your MADSci lab directory:

- If you're not using docker compose, provision and configure a MongoDB instance.
- If you're using docker compose, define your event manager and mongodb services based on the [example compose file](./event_manager.compose.yaml).


```bash
# Create an Event Manager Definition
madsci manager add -t event_manager
# Start the database and Event Manager Server
docker compose up
# OR
python -m madsci.event_manager.event_server
```

You should see a REST server started on the configured host and port. Navigate in your browser to the URL you configured (default: `http://localhost:8001/`) to see if it's working.

You can see up-to-date documentation on the endpoints provided by your event manager, and try them out, via the OpenAPI docs served by your manager at the event server's `/docs` page.

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

You can configure Email Alerts by setting up an `EmailAlertConfig` (`madsci.common.types.event_types.EmailAlertConfig`) in the `email_alerts` field of your `EventManagerDefinition`.
