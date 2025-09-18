# MADSci Resource Transfer Feature Design Document

## Overview

This document outlines the design for implementing resource transfer capabilities in MADSci, allowing users to request movement of resources between locations without specifying the exact transfer mechanisms.

## Current Architecture Analysis

### Location Manager
- **Current State**: Manages locations with representations (node-specific mappings)
- **Key Components**:
  - `Location` objects with optional resource associations
  - `LocationDefinition` for configuration
  - Node-specific representations via `representations` dict
  - Resource attachment capabilities
- **Port**: 8006
- **State Storage**: Redis-backed with LocationStateHandler

### Workcell Manager
- **Current State**: Manages workflow execution and node coordination
- **Key Components**:
  - Workflow execution engine
  - Built-in actions (currently only `wait` action)
  - Node management and communication
  - Step execution with ActionRequest/ActionResult pattern
- **Port**: 8005
- **Dependencies**: Location manager, Resource manager, Data manager

### Action System
- **Current State**: Well-defined action framework with:
  - `ActionRequest` with args, files, and action_name
  - `ActionResult` with status, data, and files
  - `ActionDefinition` for node capability declaration
  - Built-in workcell actions in `workcell_actions.py`

## Design Proposal

### 1. Transfer Actions in Workcell Manager

#### 1.1 Two Transfer Action Types
Add two distinct built-in transfer actions to handle different use cases:

**Location**: `src/madsci_workcell_manager/madsci/workcell_manager/workcell_actions.py`

##### 1.1.1 Resource-Based Transfer
```python
def transfer_resource(
    resource_id: str,
    destination_location_id: str,
    **kwargs
) -> ActionResult:
    """
    Transfer a specific resource to a destination location.

    The system will:
    1. Query the resource manager to find the resource's current location
    2. Identify the parent container and associated location
    3. Plan transfer from current location to destination
    4. Execute the transfer workflow

    Args:
        resource_id: ID of the resource to transfer
        destination_location_id: Destination location ID

    Returns:
        ActionResult: Success if transfer completed, failure otherwise

    Raises:
        HTTPException: If resource not found, location manager unreachable, or no transfer path
    """
```

##### 1.1.2 Location-Based Transfer
```python
def transfer_location_contents(
    source_location_id: str,
    destination_location_id: str,
    **kwargs
) -> ActionResult:
    """
    Transfer all contents from source location to destination location.

    The system will:
    1. Query the location manager to identify resources at source location
    2. Plan transfer workflow from source to destination
    3. Execute transfer for all resources found

    Args:
        source_location_id: Source location ID
        destination_location_id: Destination location ID

    Returns:
        ActionResult: Success if transfer completed, failure otherwise

    Raises:
        HTTPException: If locations not found, location manager unreachable, or no transfer path
    """
```

#### 1.2 Integration Points
- Check for `location_server_url` and `resource_server_url` in workcell context/settings
- Raise clear error if required managers are not configured
- For `transfer_resource`: Query resource manager to find current location, then location manager for transfer plan
- For `transfer_location_contents`: Query location manager for resources at source, then plan transfer
- Execute returned composite workflow as blocking child workflow
- Update workcell_action_dict to include both transfer actions:
  ```python
  workcell_action_dict = {
      "wait": wait,
      "transfer_resource": transfer_resource,
      "transfer_location_contents": transfer_location_contents
  }
  ```

### 2. Location Manager Transfer System

#### 2.1 Transfer Graph Construction

**New Types** (add to `src/madsci_common/madsci/common/types/location_types.py`):

```python
class TransferWorkflowTemplate(MadsciBaseModel):
    """Template for transfer workflows between compatible locations."""

    node_name: str = Field(
        title="Node Name",
        description="Name of the node that can perform this transfer"
    )
    workflow_template: WorkflowDefinition = Field(
        title="Workflow Template",
        description="Template workflow with source/destination parameters"
    )
    cost_weight: Optional[float] = Field(
        title="Cost Weight",
        description="Weight for shortest path calculation (default: 1.0)",
        default=1.0
    )

class TransferGraphEdge(MadsciBaseModel):
    """Represents a transfer path between two locations."""

    source_location_id: str
    destination_location_id: str
    transfer_template: TransferWorkflowTemplate
    cost: float = 1.0

class LocationTransferCapabilities(MadsciBaseModel):
    """Transfer capabilities for a location manager."""

    transfer_templates: list[TransferWorkflowTemplate] = Field(
        title="Transfer Templates",
        description="Available transfer workflow templates",
        default_factory=list
    )
```

#### 2.2 Enhanced LocationManagerDefinition

```python
class LocationManagerDefinition(ManagerDefinition):
    # ... existing fields ...

    transfer_capabilities: Optional[LocationTransferCapabilities] = Field(
        title="Transfer Capabilities",
        description="Transfer workflow templates and capabilities",
        default=None
    )
```

#### 2.3 Transfer Graph Logic

**New Methods** (add to `LocationManager` class):

```python
def _build_transfer_graph(self) -> dict[tuple[str, str], TransferGraphEdge]:
    """
    Build transfer graph based on location representations and transfer templates.

    Returns:
        Dict mapping (source_id, dest_id) tuples to TransferGraphEdge objects
    """

def _can_transfer_between_locations(
    self,
    source: Location,
    dest: Location,
    template: TransferWorkflowTemplate
) -> bool:
    """
    Check if transfer is possible between two locations using a template.

    Based on simple representation key matching: if both locations have
    representations for the template's node_name, transfer is possible.
    """

def _find_shortest_transfer_path(
    self,
    source_id: str,
    dest_id: str
) -> Optional[list[TransferGraphEdge]]:
    """
    Find shortest path using Dijkstra's algorithm with edge weights.

    Returns:
        List of edges representing the transfer path, or None if no path exists
    """

def _composite_transfer_workflow(
    self,
    path: list[TransferGraphEdge],
    resource_id: str
) -> WorkflowDefinition:
    """
    Create a single composite workflow from multiple transfer steps.

    For multi-leg transfers, chains the workflows together with proper
    parameter passing between steps.
    """
```

#### 2.4 New API Endpoints

**Add to LocationManager class**:

```python
@post("/transfer/plan", tags=["Transfer"])
def plan_transfer(
    self,
    source_location_id: str,
    destination_location_id: str,
    resource_id: Optional[str] = None
) -> WorkflowDefinition:
    """
    Plan a transfer workflow from source to destination.

    Args:
        source_location_id: Source location ID
        destination_location_id: Destination location ID
        resource_id: Optional resource ID for transfer tracking

    Returns:
        Composite workflow definition to execute the transfer

    Raises:
        HTTPException: If no transfer path exists
    """

@get("/transfer/graph", tags=["Transfer"])
def get_transfer_graph(self) -> dict[str, list[str]]:
    """
    Get the current transfer graph as adjacency list.

    Returns:
        Dict mapping location IDs to lists of reachable location IDs
    """

@get("/location/{location_id}/resources", tags=["Resources"])
def get_location_resources(self, location_id: str) -> list[str]:
    """
    Get all resource IDs currently at a specific location.

    Args:
        location_id: Location ID to query

    Returns:
        List of resource IDs at the location

    Raises:
        HTTPException: If location not found
    """
```

### 3. Error Handling & Validation

#### 3.1 Workcell Manager Error Cases
- `location_server_url` not configured → Clear error message
- Location manager unreachable → HTTP connection error
- No transfer path exists → Error from location manager
- Transfer workflow execution fails → Normal workflow error handling

#### 3.2 Location Manager Error Cases
- Source/destination location not found → 404 error
- No transfer path between locations → 404 error with explanation
- Transfer template validation failures → 422 error

### 4. Implementation Plan

#### Phase 1: Core Transfer Actions
1. Add both `transfer_resource` and `transfer_location_contents` actions to `workcell_actions.py`
2. Add basic integration with location and resource managers
3. Update `workcell_action_dict` with both actions
4. **Add comprehensive unit tests for both actions**
5. **Ensure `just checks` passes**

#### Phase 2: Location Manager Transfer System
1. Add new types to `location_types.py`
2. Implement transfer graph construction
3. Add transfer planning and resource location endpoints
4. Implement shortest path algorithm
5. **Add unit tests for transfer graph logic**
6. **Add integration tests for API endpoints**
7. **Run `pytest` to ensure all tests pass**

#### Phase 3: Advanced Features
1. Add transfer graph caching/optimization
2. Enhanced error handling and validation
3. Transfer status tracking and logging
4. **Add end-to-end integration tests**
5. **Performance testing for graph algorithms**

### 5. Configuration Example

**Example location manager configuration** (`location.manager.yaml`):

```yaml
name: "Lab Location Manager"
locations:
  - location_name: "storage_rack"
    location_id: "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    representations:
      robot_arm: {"joint_angles": [0, 45, 90]}
      mobile_robot: {"coordinates": {"x": 100, "y": 200}}

  - location_name: "analysis_station"
    location_id: "01ARZ3NDEKTSV4RRFFQ69G5FAW"
    representations:
      robot_arm: {"joint_angles": [180, 45, 90]}
      mobile_robot: {"coordinates": {"x": 300, "y": 400}}

transfer_capabilities:
  transfer_templates:
    - node_name: "robot_arm"
      cost_weight: 1.0
      workflow_template:
        name: "arm_transfer"
        parameters:
          json_inputs:
            - key: "source_location"
              description: "Source location for pickup"
            - key: "destination_location"
              description: "Destination location for dropoff"
            - key: "resource_id"
              description: "Resource to transfer"
        steps:
          - name: "pickup"
            parameters:
              action: "pickup"
              node: "robot_arm"
              locations:
                pickup_location: "source_location"
              args:
                resource_id: "resource_id"
          - name: "dropoff"
            parameters:
              action: "dropoff"
              node: "robot_arm"
              locations:
                dropoff_location: "destination_location"
              args:
                resource_id: "resource_id"
```

### 6. Usage Examples

#### 6.1 Resource-Based Transfer
**User workflow** (`user_workflow.yaml`):

```yaml
name: "Sample Analysis Workflow"
steps:
  - name: "move_specific_sample"
    parameters:
      action: "transfer_resource"
      args:
        resource_id: "sample_123"
        destination_location_id: "analysis_station"

  - name: "analyze_sample"
    parameters:
      action: "analyze"
      node: "spectrometer"
      locations:
        sample_location: "analysis_station"
```

#### 6.2 Location-Based Transfer
**User workflow** (`batch_transfer_workflow.yaml`):

```yaml
name: "Batch Processing Workflow"
steps:
  - name: "move_all_samples"
    parameters:
      action: "transfer_location_contents"
      args:
        source_location_id: "storage_rack"
        destination_location_id: "analysis_station"

  - name: "batch_analyze"
    parameters:
      action: "batch_analyze"
      node: "spectrometer"
      locations:
        sample_location: "analysis_station"
```

### 7. Testing Requirements

#### 7.1 Unit Tests
**Workcell Manager Tests** (`src/madsci_workcell_manager/tests/test_workcell_actions.py`):
- Test `transfer_resource` with valid resource ID and destination
- Test `transfer_resource` with invalid resource ID (should fail gracefully)
- Test `transfer_resource` with unreachable location/resource managers
- Test `transfer_location_contents` with valid source and destination
- Test `transfer_location_contents` with empty source location
- Test error handling when no transfer path exists

**Location Manager Tests** (`src/madsci_location_manager/tests/test_transfer_system.py`):
- Test transfer graph construction from location definitions
- Test representation matching logic for edge inference
- Test shortest path algorithm with various graph topologies
- Test workflow composition for single and multi-leg transfers
- Test API endpoints for transfer planning and resource location

#### 7.2 Integration Tests
- End-to-end transfer execution with mock nodes
- Multi-manager integration (workcell ↔ location ↔ resource)
- Error propagation across manager boundaries
- Transfer workflow execution and completion

#### 7.3 Test Coverage Requirements
- Maintain >90% code coverage for new transfer functionality
- All error paths must be tested
- Performance benchmarks for graph algorithms with realistic lab sizes

### 8. Dependencies and Considerations

#### 8.1 Dependency Management
- Workcell manager already has location client dependency
- Add resource manager client dependency to workcell manager
- No new external dependencies required
- Transfer workflows execute as normal child workflows

#### 8.2 Performance Considerations
- Transfer graph computation on location manager startup
- Graph caching for repeated path queries
- Shortest path algorithm scales O(V²) for typical lab sizes
- Resource location queries may need caching for frequently accessed resources

#### 8.3 Future Extensions
- Resource state tracking integration
- Transfer queue management
- Multi-resource batch transfers
- Dynamic cost calculation based on node availability
- Real-time transfer status updates

## Conclusion

This design provides a clean abstraction for resource transfers while leveraging existing MADSci patterns. The implementation is incremental and maintains backward compatibility while enabling powerful transfer orchestration capabilities.
