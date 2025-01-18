# MADSci Event Manager

Handles distributed logging and events throughout a MADSci-powered Lab.

## Usage

## Manager

To create and run a new MADSci Event Manager, do the following in your MADSci lab directory:

```bash
# Create an Event Manager Definition
madsci manager add --type event_manager
# Start the Event Manager Server
python -m madsci.event_manager.event_server
```

You should see a REST server started on the configured host and port. Navigate in your browser to the URL you configured (default: `http://localhost:8001/`) to see if it's working.

You can see up-to-date documentation on the endpoints provided by your event manager, and try them out, via the swagger page served at `http://your-event-manager-url-here/docs`.

## Client

You can use MADSci's `EventClient` (`madsci.client.event_client.EventClient`) in your python code to log events to the event manager.

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
    event_data="This logs a more complex NODE_CREATE event at the DEBUG level. The event_data field should contain relevant data about the event (in this case, something like the NodeDefinition, for instance)"
)
event_client.log(event)
event_client.log_warning(event) # Log the same event, but override the log level.

# Query for recent events
event_client.get_events(number=50)
```
