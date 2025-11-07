# MADSci Location Manager

## Overview
The Location Manager (Port 8006) handles laboratory location management, resource attachments, and node-specific references. It provides spatial organization and tracking capabilities for laboratory resources and equipment within the physical lab environment.

## Key Components

### Core Server
- **location_server.py**: Main FastAPI server for location management operations
- REST API for location CRUD operations and spatial queries
- Integration with resource and node management systems

### State Management
- **location_state_handler.py**: Manage location states and transitions
- Track location occupancy and availability
- Handle location reservations and conflicts

### Transfer Planning
- **transfer_planner.py**: Plan and optimize resource transfers between locations
- Path finding and route optimization
- Transfer scheduling and coordination
- Integration with robotic systems and automated handlers

## Core Features
- **Location Hierarchy**: Organize locations in hierarchical structures (lab → workstation → slot)
- **Spatial Mapping**: Define physical relationships and distances between locations
- **Resource Tracking**: Track which resources are at which locations
- **Occupancy Management**: Monitor location availability and capacity
- **Transfer Coordination**: Plan and execute resource movements

## Location Types
- **Labs**: Top-level laboratory spaces
- **Workstations**: Equipment or work areas within labs
- **Slots**: Specific positions within workstations
- **Storage Areas**: Dedicated storage locations
- **Transfer Points**: Intermediate locations for resource handoffs
- **Waste Locations**: Designated waste disposal areas

## State Management
- **Available**: Location ready for use
- **Occupied**: Location currently contains resources
- **Reserved**: Location scheduled for specific use
- **Maintenance**: Location temporarily unavailable
- **Error**: Location in error state requiring attention

## API Endpoints
- Location management (create, read, update, delete)
- Resource attachment and tracking
- Transfer planning and execution
- Spatial queries and navigation
- Occupancy monitoring and reporting

## Configuration
Environment variables with `LOCATION_` prefix:
- Database connection settings
- Spatial mapping configuration
- Transfer planning parameters
- Node integration settings

## Integration Points
- **Resource Manager**: Track resource locations and movements
- **Workcell Manager**: Coordinate location usage in workflows
- **Node Modules**: Integration with automated handlers and robots
- **Event Manager**: Log location changes and transfer events
