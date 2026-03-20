# MADSci Location Manager

## Overview
The Location Manager (Port 8006) handles laboratory location management, resource attachments, and node-specific references. It provides a centralized service for managing laboratory locations with transfer planning capabilities and integration with the MADSci resource management ecosystem.

## Key Components

### Core Server
- **location_server.py**: Main FastAPI server inheriting from `AbstractManagerBase`
- REST API for location CRUD operations, resource attachments, transfer planning, and bulk import/export
- Dual-handler architecture: document database (FerretDB) for persistent location storage, cache (Valkey) for transient state (locks, change counters)
- Document database schema versioning via `schema.json` and `DocumentDBVersionChecker`
- One-time seed file loading from `seed_locations_file` on empty database startup

### State Management
- **location_state_handler.py**: Dual-handler state storage
  - Document storage handler: Persistent location CRUD (all location data)
  - Cache handler: Transient state only (locks, change counters)
- Thread-safe operations with ownership context support

### Transfer Planning
- **transfer_planner.py**: Graph-based transfer planning using Dijkstra's algorithm
- Dynamic transfer graph construction from location representations and transfer templates
- Multi-step transfer workflow generation
- Capacity-aware cost adjustments for intelligent routing
- Override transfer templates for specialized scenarios

### Migration
- **location_migration.py**: One-time migration tool from 0.7.1 Redis format to document database
- Auto-migration on startup if document database is empty but cache has legacy data
- CLI entry point: `python -m madsci.location_manager.location_migration`

## Core Features
- **Location CRUD**: Create, read, update, and delete locations with unique ULIDs
- **Bulk Import/Export**: Import multiple locations via `POST /locations/import`, export via `GET /locations/export`
- **Resource Attachment**: Attach container resources to locations with automatic template creation
- **Node Representations**: Store arbitrary node-specific data for locations (JSON-serializable values)
- **Transfer Planning**: Plan optimal multi-step transfers between locations using transfer templates
- **Non-Transfer Locations**: Support for locations excluded from transfer operations
- **Resource Hierarchy Queries**: Query resource hierarchies for resources attached to locations

## Data Model
Locations are simple containers with the following structure:
- **location_id**: Unique ULID identifier
- **location_name**: Human-readable name (unique constraint in document database)
- **description**: Optional text description
- **representations**: Dictionary mapping node names to arbitrary JSON-serializable values
- **resource_id**: Optional attached resource ID
- **allow_transfers**: Boolean flag controlling transfer participation (default: true)
- **reservation**: Optional reservation info (owned_by, created, expires)

## API Endpoints

### Location Management
- `GET /locations` - List all locations
- `POST /location` - Create a new location
- `GET /location` - Get location by query (location_id or name parameter)
- `GET /location/{location_name}` - Get specific location by name
- `DELETE /location/{location_name}` - Delete location
- `POST /location/{location_name}/set_representation/{node_name}` - Set node-specific representation
- `DELETE /location/{location_name}/remove_representation/{node_name}` - Remove node-specific representation
- `POST /location/{location_name}/attach_resource` - Attach resource to location
- `DELETE /location/{location_name}/detach_resource` - Detach resource from location

### Bulk Import/Export
- `POST /locations/import` - Import multiple locations (with optional `?overwrite=true`)
- `GET /locations/export` - Export all locations as JSON list

### Transfer Planning
- `POST /transfer/plan` - Plan transfer workflow from source to target location
- `GET /transfer/graph` - Get transfer graph as adjacency list

### Resource Queries
- `GET /location/{location_name}/resources` - Get resource hierarchy for location

### System Endpoints
- `GET /health` - Health check with document database and cache connection status
- `GET /definition` - Get Location Manager definition
- `GET /` - Root endpoint returning manager definition

## Configuration
Environment variables with `LOCATION_` prefix:
- `LOCATION_MANAGER_ID` - Unique manager instance identifier
- `LOCATION_SERVER_HOST` - Server host (default: localhost)
- `LOCATION_SERVER_PORT` - Server port (default: 8006)
- `LOCATION_DOCUMENT_DB_URL` - MongoDB/FerretDB URL for persistent storage (default: mongodb://localhost:27017/)
- `LOCATION_DATABASE_NAME` - Database name (default: madsci_locations)
- `LOCATION_SEED_LOCATIONS_FILE` - Path to seed file for one-time bootstrap (default: locations.yaml)
- `LOCATION_CACHE_HOST` - Cache host for transient state (locks, counters)
- `LOCATION_CACHE_PORT` - Cache port
- `LOCATION_CACHE_PASSWORD` - Cache password (optional)

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
- A document database (FerretDB) is required for persistent location storage; a cache (Valkey) for transient state (locks, counters)
- The `seed_locations_file` is loaded **once** to bootstrap an empty database; it is not re-read on subsequent startups
