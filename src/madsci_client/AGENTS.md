# MADSci Client Package

## Overview
The `madsci_client` package provides client libraries for interacting with all MADSci manager services. It offers programmatic access to the Event Manager, Experiment Manager, Resource Manager, Data Manager, Workcell Manager, and Location Manager.

## Key Components
- **Client Classes**: Each manager has a corresponding client class (e.g., `EventClient`, `ExperimentClient`)
- **Node Clients**: Abstract and REST-based node client implementations for instrument communication
- **Type Safety**: Full type hints and Pydantic model integration for all client methods

## Client Pattern
All clients follow a consistent pattern:
- Async/await support for all operations
- Automatic request/response serialization using Pydantic models
- Built-in error handling with MADSci exception types
- Health check and service discovery capabilities

## Usage Examples
```python
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient

# Initialize clients
event_client = EventClient(base_url="http://localhost:8001")
experiment_client = ExperimentClient(base_url="http://localhost:8002")

# Use clients
await event_client.log_event(event_data)
experiments = await experiment_client.list_experiments()
```

## Testing
- Unit tests focus on client method behavior and serialization
- Integration tests require running manager services
- Mock responses are provided for offline testing
