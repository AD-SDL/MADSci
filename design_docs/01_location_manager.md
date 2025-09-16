# LocationManager Design Document

**Status**: Planning
**Created**: 2025-09-16
**Last Updated**: 2025-09-16

## Overview

This document outlines the plan to extract Location functionality from the WorkcellManager into a dedicated LocationManager service. This separation will improve modularity, scalability, and maintainability of the MADSci system.

## Current State Analysis

### Location Functionality in WorkcellManager

The Location functionality is currently embedded throughout the WorkcellManager:

**WorkcellManager (`workcell_server.py:513-580`)**:
- `GET /locations` - Get all locations
- `POST /location` - Add location
- `GET /location/{location_id}` - Get/Delete specific location
- `DELETE /location/{location_id}` - Delete location
- `POST /location/{location_id}/add_lookup/{node_name}` - Add lookup values
- `POST /location/{location_id}/attach_resource` - Attach resources

**WorkcellStateHandler (`state_handler.py:456-500`)**:
- Location storage in Redis (`_locations` RedisDict)
- CRUD operations: `get_location`, `get_locations`, `set_location`, `delete_location`, `update_location`
- Location initialization from workcell definition

**Dependencies Identified**:
- **WorkcellClient** (`workcell_client.py:801-920`): Location management methods
- **Scheduler** (`default_scheduler.py:location_checks`): Location validation for workflows
- **Condition Checks** (`condition_checks.py`): Resource-in-location validations
- **UI Components**: LocationsPanel, LocationModal, AddLocationModal
- **Types**: `location_types.py`, `workcell_types.py` (locations field)

## Target Architecture

### New LocationManager Service
- **Port**: 8006 (next available after WorkcellManager's 8005)
- **Database**: Redis (maintaining consistency with existing pattern)
- **Integration**: Standalone service that integrates with ResourceManager and WorkcellManager

### API Design
```
GET    /locations                              # List all locations
POST   /location                               # Create location
GET    /location/{location_id}                 # Get location
DELETE /location/{location_id}                 # Delete location
POST   /location/{location_id}/add_lookup/{node_name}  # Update lookup
POST   /location/{location_id}/attach_resource # Attach resource
GET    /health                                 # Health check
GET    /info                                   # Manager info
```

## Implementation Plan

### Phase 1: Create LocationManager Infrastructure

- [ ] **1.1** Create LocationManager package structure
```
src/
└── madsci_location_manager/
    ├── madsci/
    │   └── location_manager/
    │       ├── __init__.py
    │       ├── location_server.py
    │       └── location_state_handler.py
    ├── tests/
    │   ├── test_location_server.py
    │   └── test_location_client.py
    ├── README.md
    └── pyproject.toml
```

- [ ] **1.2** Create LocationClient package
  ```
  src/madsci_client/madsci/client/location_client.py
  ```

- [ ] **1.3** Define Location Manager types
  - [ ] Add `LocationManagerSettings` and `LocationManagerDefinition` to `location_types.py`
  - [ ] Add `location_server_url` to `MadsciContext` (`context_types.py`)
  - [ ] Update `ManagerType` enum to include `LOCATION_MANAGER`

### Phase 2: Implement LocationManager Core

- [ ] **2.1** LocationManager Server (`location_server.py`)
  - [ ] Inherit from `AbstractManagerBase`
  - [ ] Port all location endpoints from WorkcellManager
  - [ ] Implement health and info endpoints
  - [ ] Configure for port 8006

- [ ] **2.2** LocationStateHandler (`location_state_handler.py`)
  - [ ] Extract location state management from WorkcellStateHandler
  - [ ] Maintain Redis-based storage pattern
  - [ ] Handle location initialization from definitions
  - [ ] Manage location reservations and resource attachments

- [ ] **2.3** LocationClient (`location_client.py`)
  - [ ] Extract location methods from WorkcellClient
  - [ ] Implement retry logic and session management
  - [ ] All CRUD operations for locations

### Phase 3: Update Dependencies

- [ ] **3.1** Update WorkcellManager
  - [ ] Remove location endpoints from `workcell_server.py:513-580`
  - [ ] Remove location methods from `WorkcellStateHandler:456-500`
  - [ ] Remove location storage (`_locations` RedisDict)
  - [ ] Update initialization to use LocationClient
  - [ ] Modify `initialize_locations_and_resources()` to delegate to LocationManager

- [ ] **3.2** Update WorkcellClient
  - [ ] Remove location methods (`workcell_client.py:801-920`)
  - [ ] Add LocationClient integration where needed

- [ ] **3.3** Update Scheduler and Condition Checks
  - [ ] Modify `default_scheduler.py:location_checks()` to use LocationClient
  - [ ] Update `condition_checks.py` location evaluation functions

- [ ] **3.4** Update WorkcellTypes
  - [ ] Modify `WorkcellManagerDefinition` to remove `locations` field
  - [ ] Update `WorkcellState` to remove `locations` field
  - [ ] Create migration path for existing workcell definitions

### Phase 4: Configuration and Integration

- [ ] **4.1** Update Root Configuration
  - [ ] Add LocationManager to `pyproject.toml` dev dependencies
  - [ ] Add LocationManagerSettings to pydantic settings export

- [ ] **4.2** Update MadsciContext
  - [ ] Add `location_server_url: Optional[AnyUrl]` with default `http://localhost:8006/`
  - [ ] Update context initialization in applications

### Phase 5: Testing and Documentation (Early Implementation)

- [ ] **5.1** Create Initial Tests
  - [ ] `test_location_server.py` - Server endpoint testing
  - [ ] `test_location_client.py` - Client functionality testing
  - [ ] Integration tests for LocationManager with WorkcellManager

- [ ] **5.2** Create Documentation
  - [ ] Create LocationManager README.md
  - [ ] Update CLAUDE.md with LocationManager information
  - [ ] Document migration path

### Phase 6: Update Dashboard UI

- [ ] **6.1** Update UI Components
  - [ ] Modify `LocationsPanel.vue` to use LocationManager API
  - [ ] Update `LocationModal.vue` and `AddLocationModal.vue`
  - [ ] Update `store.ts` to fetch locations from LocationManager
  - [ ] Change API endpoints from `/workcell/locations` to `/location/`

- [ ] **6.2** Update Types
  - [ ] Update `ui/src/types/workcell_types.ts` to remove location fields
  - [ ] Ensure location types are properly defined for frontend

### Phase 7: Final Testing and Updates

- [ ] **7.1** Complete Test Coverage
  - [ ] Update WorkcellManager tests to remove location testing
  - [ ] End-to-end integration testing
  - [ ] Performance testing and validation

- [ ] **7.2** Final Documentation Updates
  - [ ] Validate all documentation is current
  - [ ] Update migration instructions
  - [ ] Create deployment guides

### Phase 8: Migration Strategy

- [ ] **8.1** Data Migration
  - [ ] Create migration scripts to extract locations from existing workcell definitions
  - [ ] Handle location data in Redis during transition
  - [ ] Provide backwards compatibility during rollout

- [ ] **8.2** Deployment Strategy
  - [ ] Deploy LocationManager alongside existing WorkcellManager
  - [ ] Gradual migration of location calls
  - [ ] Update example lab configurations

## Key Design Decisions

1. **Port Assignment**: LocationManager uses port **8006** (next available after WorkcellManager's 8005)

2. **State Management**: Maintain Redis-based approach for consistency with existing WorkcellManager pattern

3. **API Compatibility**: Keep similar endpoint structure but under `/location/` prefix instead of workcell endpoints

4. **Resource Integration**: LocationManager integrates with ResourceManager for container attachment but won't manage resources directly

5. **Workflow Integration**: Workflows continue to reference locations by ID, but validation goes through LocationManager instead of WorkcellManager

## Risk Assessment

### Low Risk
- Location functionality is well-defined and isolated
- Existing patterns in MADSci provide clear implementation guidance
- Redis storage approach is proven

### Medium Risk
- UI component updates require careful coordination
- Workflow validation changes need thorough testing
- Migration of existing location data

### High Risk
- Breaking changes to WorkcellManager API
- Coordination between multiple service deployments
- Potential data loss during migration if not handled properly

## Success Criteria

- [ ] LocationManager successfully handles all location operations
- [ ] WorkcellManager no longer contains location-specific code
- [ ] UI components work seamlessly with new LocationManager API
- [ ] All existing workflows continue to function
- [ ] No data loss during migration
- [ ] Performance meets or exceeds current implementation
- [ ] Integration tests pass for all affected components

## Notes

- This extraction follows MADSci's established architectural patterns
- Backward compatibility is prioritized during transition phase
- Location functionality remains functionally identical to users
- Implementation maintains existing Redis-based state management for consistency

---

**Next Steps**: Begin Phase 1 implementation starting with package structure creation.
