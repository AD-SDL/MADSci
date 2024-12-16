# MADSci Event Manager

Handles distributed logging and events throughout a MADSci-powered Lab.

## Usage

## Manager

Run the following in your MADSci lab directory:

```bash
# Create an Event Manager Definition
madsci manager add --type event_manager
# Start the Event Manager Server
python -m madsci.event_manager.event_server
```

You should see a REST server started on the configured host and port.

## Client

You can use the EventClient (`madsci.client.event_client.EventClient`) to log events to the event manager.

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
```
