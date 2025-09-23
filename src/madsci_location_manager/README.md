# MADSci Location Manager

The Location Manager is a dedicated microservice for managing laboratory locations in the MADSci ecosystem. It provides centralized location management functionality including location CRUD operations, resource attachments, node-specific representations, and transfer planning capabilities.

## Features

- **Location CRUD Operations**: Create, read, update, and delete locations
- **Resource Attachment**: Attach resources to specific locations with automatic resource creation from templates
- **Node-Specific Representations**: Manage node-specific representations for locations to enable flexible integration
- **Transfer Planning**: Plan multi-step transfers between locations using transfer templates and graph algorithms
- **Non-Transfer Locations**: Support for locations that are excluded from transfer operations for safety or design requirements
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
2. **Override Transfer Templates**: Specify custom transfer templates for specific sources, destinations, or (source, destination) pairs
3. **Transfer Graph**: Dynamic graph built from location representations and transfer capabilities
4. **Path Finding**: Dijkstra's algorithm finds optimal transfer paths
5. **Workflow Generation**: Creates executable workflows for complex multi-step transfers
6. **Non-Transfer Location Support**: Locations can be marked as non-transferable to exclude them from transfer operations

### Non-Transfer Locations

Some locations may need to be excluded from transfer operations for safety, design, or operational reasons. The Location Manager supports this through the `allow_transfers` field:

- **Location Definition**: Set `allow_transfers: false` when defining locations that should not participate in transfers
- **Transfer Graph Exclusion**: Non-transfer locations are automatically excluded from the transfer graph
- **Error Handling**: Attempting to plan transfers to/from non-transfer locations returns clear error messages
- **Default Behavior**: All locations allow transfers by default (`allow_transfers: true`)

Example non-transfer location definition:
```yaml
locations:
  - location_name: "safety_zone"
    description: "Critical safety area - no automated transfers allowed"
    allow_transfers: false
    representations:
      sensor_array: {"zone": "restricted"}
```

### Override Transfer Templates

Lab operators often need specialized transfer behaviors for specific scenarios. The Location Manager supports override transfer templates that provide custom transfer logic for specific sources, destinations, or (source, destination) pairs.

#### Override Precedence

Override templates follow a strict precedence order:

1. **Pair-specific overrides** (highest priority): Custom templates for specific (source, destination) combinations
2. **Source-specific overrides**: Custom templates when transferring FROM specific locations
3. **Destination-specific overrides**: Custom templates when transferring TO specific locations
4. **Default templates** (lowest priority): Standard templates used when no overrides apply

#### Configuration

Override templates are configured in the `transfer_capabilities` section using location names or IDs as keys:

```yaml
transfer_capabilities:
  # Standard default templates
  transfer_templates:
    - node_name: robotarm_1
      action: transfer
      cost_weight: 1.0

  # Override templates for specific scenarios
  override_transfer_templates:
    # Source-specific: special behavior when transferring FROM these locations
    source_overrides:
      storage_rack:  # location name
        - node_name: robotarm_1
          action: heavy_transfer  # specialized action for heavy loads
          cost_weight: 0.8

    # Destination-specific: special behavior when transferring TO these locations
    destination_overrides:
      "01K5HDZZCF27YHD2WDGSXFPPKQ":  # location ID
        - node_name: robotarm_1
          action: gentle_transfer  # careful handling for sensitive equipment
          cost_weight: 1.2

    # Pair-specific: special behavior for specific transfer routes
    pair_overrides:
      liquidhandler_1.deck_1:  # source location
        liquidhandler_2.deck_1:  # destination location
          - node_name: liquidhandler_1
            action: direct_liquid_transfer  # bypass robot arm
            cost_weight: 0.5
```

#### Use Cases

Override transfer templates enable:

- **Safety protocols**: Gentle handling when transferring to sensitive equipment
- **Performance optimization**: Direct transfers that bypass intermediate nodes
- **Equipment specialization**: Heavy-duty modes for transfers from storage areas
- **Route-specific logic**: Custom behaviors for frequently used transfer paths
- **Cost optimization**: Lower costs for preferred transfer methods

#### Key Features

- **Flexible Keys**: Use either location names or location IDs as override keys
- **Multiple Templates**: Each override can specify multiple alternative templates
- **Cost-Based Selection**: When multiple templates apply, the lowest cost template is selected
- **Automatic Fallback**: Gracefully falls back to default templates when overrides don't apply

Transfer planning enables automatic resource movement between locations using the shortest available path, while respecting transfer restrictions and applying specialized behaviors when configured.

## Integration

The Location Manager integrates with:

- **Resource Manager**: For resource attachment, template-based creation, and hierarchy queries
- **Workcell Manager**: For workflow location validation and transfer execution
- **Event Manager**: For logging and ownership context
- **UI Dashboard**: For location management interface and transfer visualization
