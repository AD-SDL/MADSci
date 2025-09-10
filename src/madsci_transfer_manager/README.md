# MADSci Transfer Manager

A comprehensive transfer orchestration system for multi-robot laboratory automation. The transfer manager handles complex transfer operations by automatically determining optimal robot sequences and coordinating multi-hop transfers across different instrument zones.

## Architecture

The transfer manager operates as a standard REST node within the MADSci ecosystem, treating transfer orchestration as an instrument capability. It receives abstract transfer requests and converts them into concrete robot actions through intelligent pathfinding and workflow management.

### Key Components

- **Transfer Node**: REST API server that handles transfer requests
- **Transfer Manager**: Core logic for pathfinding and step resolution
- **Transfer Graph**: Graph-based routing engine using Dijkstra's algorithm
- **Configuration System**: Unified YAML configuration for robots and locations

## Features

### Multi-Robot Pathfinding
- Automatic route optimization across multiple robot zones
- Support for single-hop and multi-hop transfers
- Cost-based path selection with configurable weights
- Handles complex lab topologies with multiple connection points

### Robot-Specific Coordination
- Per-robot parameter configuration and overrides
- Robot-specific coordinate lookup tables
- Automatic LocationArgument population with precise coordinates
- Support for different robot coordinate systems

### Transfer Actions
- **`transfer`**: Standard location-to-location transfers
- **`transfer_resource`**: Resource ID-based transfers with automatic source resolution
- **`get_transfer_options`**: Query available transfer paths
- **`validate_transfer`**: Validate transfer feasibility

### Thread-Safe Operations
- Thread locking prevents concurrent transfer conflicts
- Sequential execution of transfer workflows

## Installation

1. Install the transfer manager package:
```bash
pip install madsci-transfer-manager
```

2. Configure your compose file if you are running Docker:
```yaml
services:
  transfer_manager:
    image: madsci/transfer_manager
    command: python -m madsci.transfer_manager.transfer_server --node_definition node_definitions/transfer_manager.node.yaml
    ports:
      - "8006:8006"
```
3. Create your transfer configuration file (`transfer_config.yaml`)

## Configuration

### Transfer Configuration Structure
Example config file is located at [transfer_config.yaml](../../example_lab/managers/transfer_config.yaml)

```yaml
robots:
  robotarm_1:
    robot_name: robotarm_1
    default_step_template:
      name: "Transfer via {robot_name}"
      node: robotarm_1
      action: transfer
      locations:
        source: "{source}"
        target: "{target}"
    default_args: {}

  pf400:
    robot_name: pf400
    default_step_template:
      name: "Transfer via {robot_name}"
      node: pf400
      action: transfer
      locations:
        source: "{source}"
        target: "{target}"
    default_args: {}

locations:
  location_1:
    location_name: location_1
    description: "Robot arm position 1"
    accessible_by: ["robotarm_1"]
    capacity: 1
    default_args: {}
    lookup:
      robotarm_1: [1, 2, 3, 4]  # Robot-specific coordinates

  camera_station:
    location_name: camera_station
    description: "Camera imaging station"
    accessible_by: ["pf400"]
    capacity: 1
    default_args: {}
    robot_overrides:
      pf400:
        source_plate_rotation: "narrow"
        target_plate_rotation: "narrow"
    lookup:
      pf400: [94.597, 26.416, 66.422, 714.811, 81.916, 995.074]
```

### Configuration Elements

#### Robot Definitions
- **`robot_name`**: Unique identifier for the robot
- **`default_step_template`**: Template for creating transfer steps
- **`default_args`**: Default parameters for this robot's transfers
- **Template Variables**: `{robot_name}`, `{source}`, `{target}` are automatically replaced

#### Location Constraints
- **`location_name`**: Unique identifier for the location
- **`accessible_by`**: List of robots that can access this location
- **`default_args`**: Default parameters for transfers involving this location
- **`robot_overrides`**: Robot-specific parameter overrides
- **`lookup`**: Robot-specific coordinate mappings

#### Lookup Tables
Each location can contain robot-specific coordinates:
```yaml
lookup:
  pf400: [94.597, 26.416, 66.422, 714.811, 81.916, 995.074]
  robotarm_1: [1, 2, 3, 4]
```

## Usage

### Integration with Workcell Workflows

```yaml
# workflow.yaml
steps:
  - name: "Transfer Plate"
    node: "transfer_manager"
    action: "transfer"
    locations:
      source: "location_1"
      target: "location_2"
  - name: "Transfer Resource"
    node: "transfer_manager"
    action: "transfer_resource"
    args:
      source_resource: {RESOURCE_ID}
    locations:
      target: "location_2"
```


## Transfer Flow

1. **Request Reception**: Transfer node receives abstract transfer request
2. **Graph Analysis**: Transfer manager analyzes available paths using graph algorithms
3. **Path Selection**: Optimal path selected based on cost and availability
4. **Step Resolution**: Abstract transfer converted to robot-specific steps
5. **Coordinate Lookup**: Robot-specific coordinates populated from lookup tables
6. **Workflow Creation**: Child workflow created with resolved steps
7. **Execution**: Child workflow submitted to workcell manager for execution
8. **Result Handling**: Success/failure status returned to requesting workflow

## Multi-Hop Transfers

For transfers requiring multiple robots, the transfer manager automatically:

1. Identifies intermediate locations (hubs) accessible by multiple robots
2. Creates a sequence of transfer steps
3. Ensures proper coordination between robots
4. Handles parameter merging and robot-specific overrides

Example: Transfer from `tower1` (sciclops only) to `camera_station` (pf400 only):
```
tower1 → exchange (sciclops) → camera_station (pf400)
```

## Error Handling

- **Invalid Locations**: Returns error if source or target locations don't exist
- **No Path Available**: Returns error if no transfer path exists between locations
- **Resource Conflicts**: Queues requests if target resources are unavailable
- **Robot Failures**: Propagates robot-level failures to parent workflow

### Adding New Robots

1. Add robot definition to `transfer_config.yaml`
2. Specify accessible locations
3. Configure lookup coordinates for each accessible location

### Debug Output

The transfer manager provides detailed logging:
- Transfer path planning
- Robot selection rationale
- Coordinate lookup results
- Step construction details
