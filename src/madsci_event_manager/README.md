# MADSci Event Manager

Handles distributed logging and events throughout a MADSci-powered Lab.

## Notable Features

- Collects logs from distributed components of the lab and centralizes them
- Allows for querying of events
- Can accept arbitrary event data
- Enforces a standard Event schema, allowing for structured querying and filtering of logs.
- Supports python `logging`-style log levels.

## Usage

### Manager

To create and run a new MADSci Event Manager, do the following in your MADSci lab directory:

- If you're not using docker compose, provision and configure a MongoDB instance.
- If you're using docker compose, create or add the following to your Lab's `compose.yaml`, defining your docker compose services for the EventManager and a MongoDB database to store events.


```yaml
name: madsci_example_lab
services:
  mongodb:
    container_name: mongodb
    image: mongodb/mongodb-community-server:latest
    ports:
      - 27017:27017
  event_manager:
    container_name: event_manager
    image: madsci:latest
    build:
      context: ..
      dockerfile: Dockerfile
    environment:
      - USER_ID=1000
      - GROUP_ID=1000
    network_mode: host
    volumes:
      - /path/to/your/lab/direcotry:/home/madsci/lab/
      - .madsci:/home/madsci/.madsci/
    command: python -m madsci.event_manager.event_server
    depends_on:
      - mongodb
```

```bash
# Create an Event Manager Definition
madsci manager add -t event_manager
# Start the database and Event Manager Server
docker compose up
# OR
python -m madsci.event_manager.event_server
```

You should see a REST server started on the configured host and port. Navigate in your browser to the URL you configured (default: `http://localhost:8001/`) to see if it's working.

You can see up-to-date documentation on the endpoints provided by your event manager, and try them out, via the swagger page served at `http://your-event-manager-url-here/docs`.

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
    event_data="This logs a more complex NODE_CREATE event at the DEBUG level. The event_data field should contain relevant data about the event (in this case, something like the NodeDefinition, for instance)"
)
event_client.log(event)
event_client.log_warning(event) # Log the same event, but override the log level.

# Get recent events
event_client.get_events(number=50)
# Get all events from a specific node
event_client.query_events({"source": {"node_id": "01JJ4S0WNGEF5FQAZG5KDGJRBV"}})
```
