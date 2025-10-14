# MADSci Location Manager

The Location Manager is a dedicated microservice for managing laboratory locations in the MADSci ecosystem. It provides centralized location management functionality including location CRUD operations, resource attachments, node-specific representations, and transfer planning capabilities.

## Features

- **Location CRUD Operations**: Create, read, update, and delete locations
- **Resource Attachment**: Attach resources to specific locations with automatic resource creation from templates
- **Node-Specific Representations**: Manage node-specific representations for locations to enable flexible integration
- **Transfer Planning**: Plan multi-step transfers between locations using transfer templates and graph algorithms
- **Capacity-Aware Routing**: Intelligent transfer planning that avoids congested resources by adjusting costs based on utilization
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
- `POST /location/{location_id}/set_representation/{node_name}` - Set a node-specific representation for a location (accepts any JSON-serializable value)
- `POST /location/{location_id}/attach_resource` - Attach a container resource to a location
- `DELETE /location/{location_id}/detach_resource` - Detach a container resource from a location

### Transfer Planning
- `POST /transfer/plan` - Plan a transfer workflow from source to target location
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
workflow = client.plan_transfer("source_id", "target_id")

# Node representations (any type can be stored)
client.set_representations("location_id", "node_name", {"key": "value"})  # dict
client.set_representations("location_id", "robot_arm", [1, 2, 3])        # list
client.set_representations("location_id", "sensor", "position_A")         # string
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
- Includes capacity-aware cost adjustments for intelligent routing optimization

## Transfer Capabilities

The Location Manager supports sophisticated transfer planning:

1. **Transfer Templates**: Define how transfers work between locations for specific nodes
2. **Override Transfer Templates**: Specify custom transfer templates for specific sources, targets, or (source, target) pairs
3. **Transfer Graph**: Dynamic graph built from location representations and transfer capabilities
4. **Path Finding**: Dijkstra's algorithm finds optimal transfer paths
5. **Workflow Generation**: Creates executable workflows for complex multi-step transfers
6. **Non-Transfer Location Support**: Locations can be marked as non-transferable to exclude them from transfer operations

### Transfer Templates

Transfer templates define how resources can be moved between locations using specific laboratory equipment (nodes). Each template specifies the action to perform, which node to use, and various configuration parameters.

#### Basic Transfer Template Configuration

Transfer templates are configured in the `transfer_capabilities` section of your location manager definition:

```yaml
transfer_capabilities:
  transfer_templates:
    - node_name: "robotarm_1"                    # Node that performs the transfer
      action: "transfer"                         # Action to execute on the node
      source_argument_name: "source_location"   # Parameter name for source location
      target_argument_name: "target_location"   # Parameter name for target location
      cost_weight: 1.0                          # Cost weight for path finding (optional)
      additional_args: {}                       # Extra static arguments (optional)
      additional_location_args: {}              # Extra location arguments (optional)

    - node_name: "conveyor_belt"
      action: "move"
      source_argument_name: "from_station"
      target_argument_name: "to_station"
      cost_weight: 0.5                          # Lower cost = preferred path
```

#### Template Fields

- **`node_name`**: The name of the laboratory equipment/node that will perform the transfer
- **`action`**: The specific action/method to call on that node
- **`source_argument_name`**: Parameter name the node expects for the source location
- **`target_argument_name`**: Parameter name the node expects for the target location
- **`cost_weight`** (optional): Relative cost for path finding (default: 1.0). The transfer planning algorithm will use this weighting to determine the most efficient way to transfer a resource in the system. The transfer planner prioritizes lower weights over higher ones.
- **`additional_args`** (optional): Static arguments to pass to the action
- **`additional_location_args`** (optional): Additional location parameters to include

#### Advanced Template Features

**Static Arguments**: Add constant parameters to every transfer action:

```yaml
- node_name: "precision_arm"
  action: "careful_transfer"
  source_argument_name: "pickup_location"
  target_argument_name: "dropoff_location"
  additional_args:
    grip_force: "gentle"
    speed: "slow"
    vibration_dampening: true
```

**Multiple Location Arguments**: Include additional locations in the transfer:

```yaml
- node_name: "dual_arm_robot"
  action: "coordinated_transfer"
  source_argument_name: "source"
  target_argument_name: "target"
  additional_location_args:
    staging_area: "intermediate_platform"
    tool_rack: "gripper_storage"
```

#### How Transfer Templates Work

1. **Graph Building**: The system examines all locations and their representations
2. **Template Matching**: For each location pair, it finds templates where both locations have representations for the template's `node_name`
3. **Cost Calculation**: Multiple templates for the same pair are compared by cost weight
4. **Path Finding**: Dijkstra's algorithm finds the lowest-cost path using these templates
5. **Workflow Generation**: Selected templates become steps in the final transfer workflow

#### Example: Multi-Node Laboratory

```yaml
# Define multiple transfer options for different equipment
transfer_capabilities:
  transfer_templates:
    # Robot arm - precise but slow
    - node_name: "kuka_robot"
      action: "transfer_sample"
      source_argument_name: "pickup_location"
      target_argument_name: "dropoff_location"
      cost_weight: 2.0
      additional_args:
        safety_check: true

    # Conveyor belt - fast but limited paths
    - node_name: "main_conveyor"
      action: "belt_transfer"
      source_argument_name: "origin"
      target_argument_name: "destination"
      cost_weight: 0.8
      additional_args:
        speed: "medium"

    # Direct liquid transfer - specialized
    - node_name: "liquid_handler"
      action: "aspirate_dispense"
      source_argument_name: "source_well"
      target_argument_name: "target_well"
      cost_weight: 0.3                        # Preferred when available
      additional_location_args:
        waste_location: "liquid_waste_container"
```

This configuration allows the system to automatically choose the best transfer method based on available equipment at each location and the relative costs of different approaches.

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

Lab operators often need specialized transfer behaviors for specific scenarios. The Location Manager supports override transfer templates that provide custom transfer logic for specific sources, targets, or (source, target) pairs.

#### Override Precedence

Override templates follow a strict precedence order:

1. **Pair-specific overrides** (highest priority): Custom templates for specific (source, target) combinations
2. **Source-specific overrides**: Custom templates when transferring FROM specific locations
3. **Target-specific overrides**: Custom templates when transferring TO specific locations
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

    # Target-specific: special behavior when transferring TO these locations
    target_overrides:
      "01K5HDZZCF27YHD2WDGSXFPPKQ":  # location ID
        - node_name: robotarm_1
          action: gentle_transfer  # careful handling for sensitive equipment
          cost_weight: 1.2

    # Pair-specific: special behavior for specific transfer routes
    pair_overrides:
      liquidhandler_1.deck_1:  # source location
        liquidhandler_2.deck_1:  # target location
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

### Capacity-Aware Transfer Planning

The Location Manager includes capacity-aware transfer planning that dynamically adjusts transfer costs based on target resource utilization. This helps optimize transfer routes by avoiding congested or full resources.

#### How It Works

When enabled, the transfer planner checks each target location's attached resource for current quantity and capacity:

1. **Resource Check**: For each transfer edge, check if the target location has an attached resource
2. **Utilization Calculation**: Calculate the utilization ratio (quantity/capacity) for consumable resources
3. **Cost Adjustment**: Apply cost multipliers based on configurable utilization thresholds
4. **Path Optimization**: The shortest path algorithm automatically favors less congested targets

#### Configuration

Capacity-aware cost adjustments are configured through the `capacity_cost_config` section:

```yaml
transfer_capabilities:
  # Standard transfer templates
  transfer_templates:
    - node_name: robotarm_1
      action: transfer
      cost_weight: 1.0

  # Capacity-aware cost configuration
  capacity_cost_config:
    enabled: true                      # Enable capacity-aware adjustments
    high_capacity_threshold: 0.8       # Apply multiplier above 80% utilization
    full_capacity_threshold: 1.0       # Apply higher multiplier at/above 100%
    high_capacity_multiplier: 2.0      # 2x cost for high capacity targets
    full_capacity_multiplier: 10.0     # 10x cost for full/over capacity targets
```

#### Cost Multiplier Logic

- **Low utilization** (below `high_capacity_threshold`): No cost adjustment (1x multiplier)
- **High utilization** (≥ `high_capacity_threshold`): Apply `high_capacity_multiplier`
- **Full/over capacity** (≥ `full_capacity_threshold`): Apply `full_capacity_multiplier`

#### Example Scenarios

With a 10-unit capacity resource:

- **5 units used (50%)**: Base transfer cost (no penalty)
- **8 units used (80%)**: 2x transfer cost (high capacity penalty)
- **10+ units used (100%+)**: 10x transfer cost (full capacity penalty)

#### Benefits

- **Congestion Avoidance**: Automatically routes around full or nearly full resources
- **Load Balancing**: Distributes transfers across available capacity
- **Predictable Behavior**: Clear, configurable thresholds for cost adjustments
- **Graceful Degradation**: Falls back to base costs when resource data unavailable
- **Error Resilience**: Continues operation even if resource client errors occur

#### Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Enable/disable capacity-aware cost adjustments |
| `high_capacity_threshold` | `0.8` | Utilization ratio for high capacity penalty (0.0-1.0) |
| `full_capacity_threshold` | `1.0` | Utilization ratio for full capacity penalty (0.0-1.0) |
| `high_capacity_multiplier` | `2.0` | Cost multiplier for high capacity targets (≥1.0) |
| `full_capacity_multiplier` | `10.0` | Cost multiplier for full capacity targets (≥1.0) |

Capacity-aware transfer planning works seamlessly with existing transfer templates and override configurations, providing an additional layer of intelligent routing optimization.

## Integration

The Location Manager integrates with:

- **Resource Manager**: For resource attachment, template-based creation, and hierarchy queries
- **Workcell Manager**: For workflow location validation and transfer execution
- **Event Manager**: For logging and ownership context
- **UI Dashboard**: For location management interface and transfer visualization
