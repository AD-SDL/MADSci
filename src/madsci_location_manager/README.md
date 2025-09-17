# MADSci Location Manager

The Location Manager is a dedicated microservice for managing laboratory locations in the MADSci ecosystem. It provides centralized location management functionality that was previously embedded in the WorkcellManager.

## Features

- **Location CRUD Operations**: Create, read, update, and delete locations
- **Resource Attachment**: Attach resources to specific locations
- **Lookup Values**: Manage node-specific lookup values for locations
- **Redis State Management**: Persistent state storage using Redis
- **RESTful API**: Clean REST endpoints for all location operations

## API Endpoints

- `GET /locations` - List all locations
- `POST /location` - Create a new location
- `GET /location/{location_id}` - Get a specific location
- `DELETE /location/{location_id}` - Delete a location
- `POST /location/{location_id}/add_lookup/{node_name}` - Add lookup values for a node
- `POST /location/{location_id}/attach_resource` - Attach a resource to a location

## Configuration

The Location Manager uses environment variables for configuration:

- `LOCATION_MANAGER_ID` - Unique identifier for this manager instance
- `LOCATION_SERVER_HOST` - Server host (default: localhost)
- `LOCATION_SERVER_PORT` - Server port (default: 8006)
- `LOCATION_REDIS_HOST` - Redis host for state storage
- `LOCATION_REDIS_PORT` - Redis port
- `LOCATION_REDIS_PASSWORD` - Redis password (optional)

## Usage

### Starting the Server

```python
from madsci.location_manager.location_server import main

main()
```

### Using the Client

```python
from madsci.client.location_client import LocationClient

client = LocationClient("http://localhost:8006")
locations = client.get_locations()
```

## Integration

The Location Manager integrates with:

- **Resource Manager**: For resource attachment and validation
- **Workcell Manager**: For workflow location validation
- **UI Dashboard**: For location management interface

## Development

This package follows MADSci's established patterns:

- Inherits from `AbstractManagerBase`
- Uses Redis for state management with `pottery` library
- Follows the standard manager port allocation (8006)
- Implements health and info endpoints
