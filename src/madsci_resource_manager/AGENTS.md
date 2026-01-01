# MADSci Resource Manager

## Overview
The Resource Manager (Port 8003) handles laboratory resource and inventory tracking. It provides comprehensive management of physical and virtual laboratory resources, including samples, reagents, equipment, and consumables.

## Key Components

### Core Server
- **resource_server.py**: Main FastAPI server providing resource management endpoints
- REST API for resource operations (CRUD, queries, reservations)
- Integration with inventory tracking and procurement systems

### Resource Interface
- **resource_interface.py**: Abstract interfaces and protocols for resource interactions
- Standardized resource operations and state management
- Type-safe resource manipulation APIs

### Database Layer
- **resource_tables.py**: Database models and table definitions for resource storage
- SQLModel integration for PostgreSQL database operations
- Relationship modeling between resources, locations, and usage

## Resource Types
- **Samples**: Biological, chemical, and physical samples
- **Reagents**: Chemical reagents and solutions
- **Consumables**: Tips, plates, containers, and disposable items
- **Equipment**: Reusable laboratory equipment and tools
- **Instruments**: Connected laboratory instruments and devices
- **Virtual Resources**: Software licenses, computational resources

## Resource Properties
- **Identity**: Unique identifiers, names, and descriptions
- **State**: Current status (available, in-use, reserved, expired)
- **Location**: Physical or virtual location tracking
- **Metadata**: Custom properties, tags, and annotations
- **Relationships**: Parent-child and dependency relationships
- **History**: Complete audit trail of resource operations

## Core Features
- **Inventory Tracking**: Real-time inventory levels and locations
- **Reservation System**: Resource booking and scheduling
- **Usage Monitoring**: Track resource consumption and utilization
- **Lifecycle Management**: Handle resource creation, usage, and disposal
- **Quality Control**: Expiration dates, quality metrics, and validation

## API Endpoints
- Resource management (create, read, update, delete)
- Inventory queries and search capabilities
- Reservation and booking operations
- Usage tracking and reporting
- Batch operations for bulk resource management

## Configuration
Environment variables with `RESOURCE_` prefix:
- Database connection settings
- Inventory management rules
- Integration service configurations
- Resource validation parameters

## Integration Points
- **Location Manager**: Track resource physical locations
- **Workcell Manager**: Reserve and allocate resources for workflows
- **Event Manager**: Log resource operations and state changes
- **Data Manager**: Store resource-associated data and measurements
