# MADSci Resource Manager

Tracks and manages the full lifecycle of laboratory resources - assets, consumables, samples, containers, and labware.

## Features

- **Comprehensive resource types**: Assets, consumables, containers with specialized behaviors
- **Complete history tracking**: Full audit trail with restore capabilities
- **Container hierarchy**: Supports racks, plates, stacks, queues, grids, and custom containers
- **Quantity management**: Track consumable quantities with capacity limits
- **Query system**: Find resources by type, name, properties, or relationships
- **Constraint validation**: Prevents logical errors like negative quantities or overflow

## Installation

See the main [README](../../README.md#installation) for installation options. This package is available as:
- PyPI: `pip install madsci.resource_manager`
- Docker: Included in `ghcr.io/ad-sdl/madsci`
- **Example configuration**: See [example_lab/managers/example_resource.manager.yaml](../../example_lab/managers/example_resource.manager.yaml)

**Dependencies**: PostgreSQL database (see [example_lab](../../example_lab/))

## Usage

### Quick Start

Use the [example_lab](../../example_lab/) as a starting point:

```bash
# Start with working example
docker compose up  # From repo root
# Resource Manager available at http://localhost:8003/docs

# Or run standalone
python -m madsci.resource_manager.resource_server
```

### Manager Setup

For custom deployments, see [example_resource.manager.yaml](../../example_lab/managers/example_resource.manager.yaml) for configuration options.

### Resource Client

Use `ResourceClient` to manage laboratory resources:

```python
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset, Consumable, Grid
from madsci.common.types.resource_types.definitions import ResourceDefinition

client = ResourceClient("http://localhost:8003")

# Add a new asset (samples, labware, equipment)
sample = Asset(
    resource_name="Sample A1",
    resource_class="sample",
    metadata={"compound": "aspirin", "concentration": "10mM"}
)
added_sample = client.add_resource(sample)

# Add consumables with quantities
reagent = Consumable(
    resource_name="PBS Buffer",
    resource_class="reagent",
    quantity=500.0,
    units="mL"
)
added_reagent = client.add_resource(reagent)

# Create containers (plates, racks, etc.)
plate = Grid(
    resource_name="96-well Plate #1",
    resource_class="plate",
    rows=8,
    columns=12
)
added_plate = client.add_resource(plate)

# Place samples in containers
client.set_child(resource=added_plate, key=(0, 0), child=added_sample)

# Query resources
samples = client.query_resource(resource_class="sample", multiple=True)
consumables = client.query_resource(resource_class="reagent", multiple=True)

# Manage consumable quantities
client.decrease_quantity(resource=added_reagent, amount=50.0)  # Use 50mL
client.increase_quantity(resource=added_reagent, amount=100.0) # Add 100mL

# Resource history and restoration
history = client.query_history(resource_id=added_sample.resource_id)
client.remove_resource(resource_id=added_sample.resource_id)  # Soft delete
client.restore_deleted_resource(resource_id=added_sample.resource_id)
```

## Resource Types

### Core Resource Hierarchy

**Base Types:**
- **Resource**: Base class for all resources
- **Asset**: Non-consumable resources (samples, labware, equipment)
- **Consumable**: Resources with quantities that can be consumed

**Container Types:**
- **Container**: Base for resources that hold other resources
- **Collection**: Supports random access by key
- **Row**: Single-dimensional containers
- **Grid**: Two-dimensional containers (plates, racks)
- **VoxelGrid**: Three-dimensional containers
- **Slot**: Holds exactly zero or one child (plate nests)
- **Stack**: LIFO access (stacked plates)
- **Queue**: FIFO access (sample queues)
- **Pool**: Mixed/collocated consumables

### Usage Examples

```python
# Different container types
tip_box = Grid(resource_name="Tip Box", rows=8, columns=12, resource_class="tips")
plate_stack = Stack(resource_name="Plate Stack", resource_class="plate_storage")
sample_rack = Row(resource_name="Sample Rack", length=24, resource_class="rack")

# Container operations
client.set_child(resource=tip_box, key=(0, 0), child=tip_sample)    # Grid access
client.push(resource=plate_stack, child=new_plate)                  # Stack push
client.pop(resource=plate_stack)                                    # Stack pop
client.set_child(resource=sample_rack, key=5, child=sample)         # Row access
```

## Integration with MADSci Ecosystem

Resources integrate seamlessly with other MADSci components:

- **Workflows**: Reference resources in step locations and arguments
- **Nodes**: Access resource information during actions
- **Data Manager**: Link data to specific resources and samples
- **Event Manager**: Track resource lifecycle events

```python
# Example: Node action using resources
@action
def process_sample(self, sample_resource_id: str) -> ActionResult:
    # Get sample metadata from Resource Manager
    sample = self.resource_client.get_resource(sample_resource_id)

    # Process based on sample properties
    result = self.device.analyze(sample.metadata["compound"])

    # Update sample with results
    sample.metadata["analysis_result"] = result
    self.resource_client.update_resource(sample)

    return ActionSucceeded(data=result)
```

## Advanced Operations

### Resource Definitions
Use `ResourceDefinition` for idempotent resource creation:

```python
from madsci.common.types.resource_types.definitions import ResourceDefinition

# Creates new resource or attaches to existing one
resource_def = ResourceDefinition(
    resource_name="Standard Buffer",
    resource_class="reagent"
)
resource = client.init_resource(resource_def)  # Idempotent
```

### Bulk Operations
```python
# Query multiple resources
all_samples = client.query_resource(resource_class="sample", multiple=True)
empty_containers = client.query_resource(is_empty=True, multiple=True)

# Batch operations for consumables
for reagent in reagents:
    client.decrease_quantity(resource=reagent, amount=usage_amounts[reagent.resource_id])
```

### History and Auditing
```python
# Full resource history
history = client.query_history(resource_id=sample.resource_id)

# Query by time range and change type
import datetime
recent_updates = client.query_history(
    start_date=datetime.datetime.now() - datetime.timedelta(days=7),
    change_type="Updated"
)
```

**Examples**: See [example_lab/](../../example_lab/) for complete resource management workflows integrated with laboratory operations.
