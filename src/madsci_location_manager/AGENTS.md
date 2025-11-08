# MADSci Location Manager

## Overview
The Location Manager (Port 8006) handles laboratory location management, resource attachments, and node-specific references. It provides a centralized service for managing laboratory locations with transfer planning capabilities and integration with the MADSci resource management ecosystem.

## Key Components

### Core Server
- **location_server.py**: Main FastAPI server inheriting from `AbstractManagerBase`
- REST API for location CRUD operations, resource attachments, and transfer planning
- Redis-backed state persistence via `LocationStateHandler`
- Automatic location initialization from definition files

### State Management
- **location_state_handler.py**: Redis-based persistent state storage for locations
- No complex state transitions - locations are simple data containers
- Thread-safe operations with ownership context support

### Transfer Planning
- **transfer_planner.py**: Graph-based transfer planning using Dijkstra's algorithm
- Dynamic transfer graph construction from location representations and transfer templates
- Multi-step transfer workflow generation
- Capacity-aware cost adjustments for intelligent routing
- Override transfer templates for specialized scenarios

## Core Features
- **Location CRUD**: Create, read, update, and delete locations with unique ULIDs
- **Resource Attachment**: Attach container resources to locations with automatic template creation
- **Node Representations**: Store arbitrary node-specific data for locations (JSON-serializable values)
- **Transfer Planning**: Plan optimal multi-step transfers between locations using transfer templates
- **Non-Transfer Locations**: Support for locations excluded from transfer operations
- **Resource Hierarchy Queries**: Query resource hierarchies for resources attached to locations

## Data Model
Locations are simple containers with the following structure:
- **location_id**: Unique ULID identifier
- **location_name**: Human-readable name
- **description**: Optional text description
- **representations**: Dictionary mapping node names to arbitrary JSON-serializable values
- **resource_id**: Optional attached resource ID
- **allow_transfers**: Boolean flag controlling transfer participation (default: true)

## API Endpoints

### Location Management
- `GET /locations` - List all locations
- `POST /location` - Create a new location
- `GET /location` - Get location by query (location_id or name parameter)
- `GET /location/{location_id}` - Get specific location by ID
- `DELETE /location/{location_id}` - Delete location
- `POST /location/{location_id}/set_representation/{node_name}` - Set node-specific representation
- `DELETE /location/{location_id}/remove_representation/{node_name}` - Remove node-specific representation
- `POST /location/{location_id}/attach_resource` - Attach resource to location
- `DELETE /location/{location_id}/detach_resource` - Detach resource from location

### Transfer Planning
- `POST /transfer/plan` - Plan transfer workflow from source to target location
- `GET /transfer/graph` - Get transfer graph as adjacency list

### Resource Queries
- `GET /location/{location_id}/resources` - Get resource hierarchy for location

### System Endpoints
- `GET /health` - Health check with Redis connection status
- `GET /definition` - Get Location Manager definition
- `GET /` - Root endpoint returning manager definition

## Configuration
Environment variables with `LOCATION_` prefix:
- `LOCATION_MANAGER_ID` - Unique manager instance identifier
- `LOCATION_SERVER_HOST` - Server host (default: localhost)
- `LOCATION_SERVER_PORT` - Server port (default: 8006)
- `LOCATION_REDIS_HOST` - Redis host for state storage
- `LOCATION_REDIS_PORT` - Redis port
- `LOCATION_REDIS_PASSWORD` - Redis password (optional)

## Transfer Capabilities
Transfer planning is configured through `transfer_capabilities` in the manager definition:

### Transfer Templates
Basic templates define how nodes can transfer resources:
```yaml
transfer_templates:
  - node_name: "robotarm_1"
    action: "transfer"
    source_argument_name: "source_location"
    target_argument_name: "target_location"
    cost_weight: 1.0
```

### Override Templates
Specialized templates for specific scenarios:
- **Source overrides**: Custom behavior when transferring FROM specific locations
- **Target overrides**: Custom behavior when transferring TO specific locations
- **Pair overrides**: Custom behavior for specific (source, target) combinations

### Capacity-Aware Planning
Optional feature that adjusts transfer costs based on target resource utilization to avoid congested resources.

## Integration Points
- **Resource Manager**: Resource attachment, template creation, and hierarchy queries
- **Workcell Manager**: Workflow location validation and transfer execution
- **Event Manager**: Logging and ownership context
- **UI Dashboard**: Location management interface

## Usage Notes
- All location IDs use ULIDs for better performance and lexicographical sorting
- Representations can store any JSON-serializable data (dicts, lists, strings, numbers)
- Transfer planning automatically rebuilds graphs when locations or representations change
- Non-transfer locations (`allow_transfers: false`) are excluded from transfer graph
- Redis is required for persistent state storage
