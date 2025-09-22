# MADSci Location Manager

The Location Manager is a dedicated microservice for managing laboratory locations in the MADSci ecosystem. It provides centralized location management functionality including location CRUD operations, resource attachments, node-specific representations, and transfer planning capabilities.

## Features

- **Location CRUD Operations**: Create, read, update, and delete locations
- **Resource Attachment**: Attach resources to specific locations with automatic resource creation from templates
- **Node-Specific Representations**: Manage node-specific representations for locations to enable flexible integration
- **Transfer Planning**: Plan multi-step transfers between locations using transfer templates and graph algorithms
- **Resource Hierarchy Queries**: Query resource hierarchies for resources attached to locations
- **Redis State Management**: Persistent state storage using Redis
- **RESTful API**: Clean REST endpoints for all location operations

## API Endpoints

### Location Management
- `GET /locations` - List all locations
- `POST /location` - Create a new location
- `GET /location` - Get a location by query parameters (location_id or name)
- `GET /location/{location_id}` - Get a specific location by ID
- `DELETE /location/{location_id}` - Delete a location
- `POST /location/{location_id}/set_representation/{node_name}` - Set representations for a location and node
- `POST /location/{location_id}/attach_resource` - Attach a resource to a location

### Transfer Planning
- `POST /transfer/plan` - Plan a transfer workflow from source to destination location
- `GET /transfer/graph` - Get the current transfer graph as adjacency list

### Resource Queries
- `GET /location/{location_id}/resources` - Get resource hierarchy for resources at a location

### System Endpoints
- `GET /health` - Health check endpoint
- `GET /definition` - Get Location Manager definition and configuration
- `GET /` - Root endpoint returning manager definition

## Configuration

The Location Manager uses environment variables with the `LOCATION_` prefix:

- `LOCATION_MANAGER_ID` - Unique identifier for this manager instance
- `LOCATION_SERVER_HOST` - Server host (default: localhost)
- `LOCATION_SERVER_PORT` - Server port (default: 8006)
- `LOCATION_REDIS_HOST` - Redis host for state storage
- `LOCATION_REDIS_PORT` - Redis port
- `LOCATION_REDIS_PASSWORD` - Redis password (optional)

## Usage

### Starting the Server

```python
from madsci.location_manager.location_server import LocationManager

# Create and run the manager
manager = LocationManager()
manager.run_server()
```

### Using the Client

```python
from madsci.client.location_client import LocationClient

# Initialize client
client = LocationClient("http://localhost:8006")

# Basic location operations
locations = client.get_locations()
location = client.get_location("location_id")
location_by_name = client.get_location_by_name("location_name")

# Resource operations
client.attach_resource("location_id", "resource_id")
resources = client.get_location_resources("location_id")

# Transfer planning
transfer_graph = client.get_transfer_graph()
workflow = client.plan_transfer("source_id", "dest_id")

# Node representations
client.set_representations("location_id", "node_name", {"key": "value"})
```

## Key Components

### LocationManager
The main server class inheriting from `AbstractManagerBase` that provides:
- FastAPI-based REST API endpoints
- Redis-backed state management via `LocationStateHandler`
- Resource integration via `ResourceClient`
- Transfer planning via `TransferPlanner`
- Automatic location initialization from definition

### LocationClient
A comprehensive client for interacting with the Location Manager that supports:
- All location CRUD operations
- Transfer planning and graph queries
- Resource hierarchy queries
- Configurable retry strategies
- Ownership context handling

### TransferPlanner
Advanced transfer planning system that:
- Builds transfer graphs based on location representations and transfer templates
- Uses Dijkstra's algorithm for shortest path finding
- Creates composite workflows for multi-step transfers
- Supports cost-weighted transfer edges

## Transfer Capabilities

The Location Manager supports sophisticated transfer planning:

1. **Transfer Templates**: Define how transfers work between locations for specific nodes
2. **Transfer Graph**: Dynamic graph built from location representations and transfer capabilities
3. **Path Finding**: Dijkstra's algorithm finds optimal transfer paths
4. **Workflow Generation**: Creates executable workflows for complex multi-step transfers

Transfer planning enables automatic resource movement between locations using the shortest available path.

## Integration

The Location Manager integrates with:

- **Resource Manager**: For resource attachment, template-based creation, and hierarchy queries
- **Workcell Manager**: For workflow location validation and transfer execution
- **Event Manager**: For logging and ownership context
- **UI Dashboard**: For location management interface and transfer visualization
