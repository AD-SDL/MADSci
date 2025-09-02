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
    attributes={"compound": "aspirin", "concentration": "10mM"}
)
added_sample = client.add_resource(sample)

# Add consumables with quantities
reagent = Consumable(
    resource_name="PBS Buffer",
    resource_class="reagent",
    quantity=500.0,
    attributes={"units": "mL"},
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
    # Get sample attributes from Resource Manager
    sample = self.resource_client.get_resource(sample_resource_id)

    # Process based on sample properties
    result = self.device.analyze(sample.attributes["compound"])

    # Update sample with results
    sample.attributes["analysis_result"] = result
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

## Resource Templates

ResourceTemplates provide reusable blueprints for creating standardized laboratory resources. Templates help ensure consistency across resource creation and reduce configuration errors.

### Creating Templates

Templates are created from existing resources and can be customized with metadata:

```python
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Grid, Consumable

client = ResourceClient("http://localhost:8003")

# Create a standard 96-well plate resource
standard_plate = Grid(
    resource_name="Standard 96-Well Plate",
    resource_class="plate",
    rows=8,
    columns=12,
    attributes={
        "well_volume": 200,  # µL
        "material": "polystyrene",
        "sterilized": True
    }
)

# Create template from the resource
plate_template = client.create_template(
    resource=standard_plate,
    template_name="standard_96_well_plate",
    description="Standard 96-well polystyrene plate for assays",
    required_overrides=["resource_name"],  # Must be customized when using
    tags=["plate", "96-well", "assay", "standard"],
    created_by="lab_manager",
    version="1.0.0"
)
```

### Using Templates to Create Resources

Templates streamline resource creation with consistent defaults:

```python
# Create new resources from template
assay_plate_1 = client.create_resource_from_template(
    template_name="standard_96_well_plate",
    resource_name="Assay Plate #001",
    overrides={
        "attributes": {"experiment_id": "EXP001", "assay_type": "ELISA"}
    }
)

assay_plate_2 = client.create_resource_from_template(
    template_name="standard_96_well_plate",
    resource_name="Assay Plate #002",
    overrides={
        "attributes": {"experiment_id": "EXP002", "assay_type": "cell_culture"}
    }
)

# Both plates inherit standard configuration but with custom attributes
```

### Template Management Operations

**Listing and Discovery:**
```python
# List all available templates
all_templates = client.list_templates()

# Filter templates by category
plate_templates = client.list_templates(base_type="container", tags=["plate"])
reagent_templates = client.list_templates(base_type="consumable", tags=["reagent"])

# Get templates organized by category
templates_by_category = client.get_templates_by_category()
# Returns: {"container": ["plate_template", "rack_template"], "consumable": ["buffer_template"]}

# Filter by creator
lab_templates = client.list_templates(created_by="lab_manager")
```

**Template Metadata:**
```python
# Get detailed template information
template_info = client.get_template_info("standard_96_well_plate")

# Returns metadata dictionary:
# {
#   "description": "Standard 96-well polystyrene plate for assays",
#   "required_overrides": ["resource_name"],
#   "tags": ["plate", "96-well", "assay", "standard"],
#   "created_by": "lab_manager",
#   "version": "1.0.0",
#   "created_at": "2024-01-15T10:30:00Z",
#   "resource": <template_resource_object>
# }
```

**Template Updates:**
```python
# Update template metadata
updated_template = client.update_template(
    template_name="standard_96_well_plate",
    updates={
        "description": "Updated standard 96-well plate with new specifications",
        "tags": ["plate", "96-well", "assay", "standard", "v2"],
        "version": "1.1.0",
        "attributes": {"well_volume": 250}  # Updated well volume
    }
)
```

**Template Deletion:**
```python
# Remove template (permanent)
success = client.delete_template("obsolete_template")
if success:
    print("Template successfully deleted")
```

### Template Use Cases

**1. Standardized Labware:**
```python
# Create templates for common labware
tip_box_template = client.create_template(
    resource=Grid(resource_name="Standard Tip Box", rows=8, columns=12, resource_class="tips"),
    template_name="standard_tip_box",
    description="200µL tip box template",
    required_overrides=["resource_name"],
    tags=["tips", "consumable", "standard"]
)

# Create multiple tip boxes from template
for i in range(5):
    client.create_resource_from_template(
        template_name="standard_tip_box",
        resource_name=f"Tip Box #{i+1:03d}",
        overrides={"attributes": {"batch_number": f"TB{i+1:03d}"}}
    )
```

**2. Reagent Standards:**
```python
# Create reagent template
buffer_template = client.create_template(
    resource=Consumable(
        resource_name="PBS Buffer",
        resource_class="buffer",
        quantity=1000.0,
        attributes={"pH": 7.4, "concentration": "1X", "units": "mL"}
    ),
    template_name="pbs_buffer_1x",
    description="1X PBS buffer, pH 7.4",
    required_overrides=["resource_name", "quantity"],
    tags=["buffer", "pbs", "cell_culture"]
)

# Create buffer instances
buffer_stock = client.create_resource_from_template(
    template_name="pbs_buffer_1x",
    resource_name="PBS Stock #001",
    overrides={"quantity": 5000.0, "attributes": {"lot_number": "PBS2024001"}}
)
```

**3. Container Hierarchies:**
```python
# Template for plate storage systems
storage_template = client.create_template(
    resource=Stack(resource_name="Plate Storage", resource_class="storage", capacity=20),
    template_name="plate_storage_stack",
    description="Standard plate storage stack (20 plates)",
    required_overrides=["resource_name"],
    tags=["storage", "plate", "stack"]
)

# Create storage locations
incubator_storage = client.create_resource_from_template(
    template_name="plate_storage_stack",
    resource_name="Incubator Plate Stack",
    overrides={"attributes": {"temperature": 37, "humidity": 95}}
)
```

### Template Best Practices

**1. Use Meaningful Names and Tags:**
```python
# ✅ Good - Descriptive and searchable
client.create_template(
    resource=plate,
    template_name="corning_96_well_flat_bottom",
    tags=["plate", "96-well", "flat-bottom", "corning", "cell-culture"]
)

# ❌ Avoid - Generic and hard to find
client.create_template(resource=plate, template_name="plate1", tags=["lab"])
```

**2. Define Required Overrides:**
```python
# ✅ Good - Enforce customization of unique fields
client.create_template(
    resource=sample,
    template_name="dna_sample_template",
    required_overrides=["resource_name", "attributes.sample_id", "attributes.source"]
)

# ❌ Avoid - No required overrides may lead to duplicate names
client.create_template(resource=sample, template_name="sample_template")
```

**3. Version Your Templates:**
```python
# Version templates for tracking changes
client.create_template(
    resource=updated_plate,
    template_name="assay_plate_v2",
    description="Updated assay plate with improved specifications",
    version="2.0.0",
    tags=["plate", "assay", "v2"]
)
```

**4. Organize with Categories:**
```python
# Use consistent tag hierarchies
consumable_tags = ["consumable", "reagent", "buffer"]
labware_tags = ["labware", "plate", "96-well"]
equipment_tags = ["equipment", "analyzer", "hplc"]
```


## Resource Locking and Concurrency Control

MADSci provides comprehensive resource locking to prevent conflicts when multiple processes or nodes access the same resources concurrently.

### Basic Resource Locking

```python
from madsci.client.resource_client import ResourceClient

client = ResourceClient("http://localhost:8003")

# Acquire lock on a single resource
success = client.acquire_lock(
    resource=sample_plate,
    lock_duration=300.0,  # 5 minutes
)

if success:
    try:
        # Perform operations on the locked resource
        client.set_child(resource=sample_plate, key=(0, 0), child=new_sample)
        client.update_resource(sample_plate)
    finally:
        # Always release the lock
        client.release_lock(resource=sample_plate)
```

### Context Manager for Automatic Lock Management

The recommended approach uses context managers for automatic lock acquisition and release:

```python
# Single resource locking
with client.lock(sample_plate) as locked_plate:
    # Resource is automatically locked
    locked_plate.set_child(key=(0, 0), child=new_sample)
    locked_plate.update_resource()
    # Lock automatically released when exiting context

# Multiple resource locking (atomic)
with client.lock(reagent_bottle, sample_rack, plate_stack) as (reagent, rack, stack):
    # All resources locked atomically or operation fails
    reagent.decrease_quantity(amount=50.0)
    new_sample = rack.get_child(key=5)
    stack.push(child=finished_plate)
    # All locks released automatically
```

### Advanced Locking Patterns

**Lock Duration and Auto-Refresh:**
```python
# Custom lock duration with auto-refresh
with client.lock(
    resource=long_running_plate,
    lock_duration=60.0,     # 1 minute initial lock
    auto_refresh=True,      # Automatically extend lock if needed
) as locked_plate:
    # Perform long-running operations
    # Lock automatically refreshed every 30 seconds
    for i in range(96):  # Process each well
        process_well(locked_plate, well_position=i)
```

**Lock Status Checking:**
```python
# Check if resource is currently locked
is_locked = client.is_locked(resource=sample_plate)

if not is_locked:
    with client.lock(sample_plate) as locked_plate:
        perform_analysis(locked_plate)
else:
    print("Resource currently in use by another process")
```

### Error Handling and Lock Recovery

```python
# Manual lock management with error handling
try:
    if client.acquire_lock(resource=critical_resource, lock_duration=120.0):
        try:
            # Critical operations
            perform_critical_work(critical_resource)
        finally:
            client.release_lock(resource=critical_resource)
    else:
        raise Exception("Failed to acquire lock on critical resource")
except Exception as e:
    print(f"Operation failed: {e}")
```

### Best Practices for Resource Locking

**1. Always Use Context Managers:**
```python
# ✅ Good - Automatic cleanup
with client.lock(resource) as locked_resource:
    work_with_resource(locked_resource)

# ❌ Avoid - Manual management prone to errors
client.acquire_lock(resource)
work_with_resource(resource)
client.release_lock(resource)  # May not execute if exception occurs
```

**2. Lock Multiple Resources Atomically:**
```python
# ✅ Good - All locks acquired or none
with client.lock(plate, reagent, tip_rack) as (p, r, t):
    transfer_samples(from_plate=p, reagent=r, tips=t)

# ❌ Avoid - Deadlock potential
with client.lock(plate) as p:
    with client.lock(reagent) as r:  # Could deadlock if another process locks in reverse order
        transfer_samples(p, r)
```

**3. Use Appropriate Lock Durations:**
```python
# Short operations - brief locks
with client.lock(sample, lock_duration=30.0) as s:
    result = quick_measurement(s)

# Long operations - longer locks with auto-refresh
with client.lock(plate_stack, lock_duration=300.0, auto_refresh=True) as stack:
    process_entire_stack(stack)  # May take several minutes
```

### Integration with Node Actions

Resource locking integrates seamlessly with MADSci node actions:

```python
from madsci.node_module.node_module import RestNode
from madsci.common.types.action_types import ActionResult, ActionSucceeded

class AnalyzerNode(RestNode):

    @action
    def analyze_sample(
        self,
        sample_plate_id: str,
        sample_position: tuple[int, int]
    ) -> ActionResult:
        # Acquire lock before manipulating resources
        with self.resource_client.lock(sample_plate_id) as plate:
            # Get sample from locked plate
            sample = plate.get_child(key=sample_position)

            # Perform analysis
            result = self.instrument.analyze(sample)

            # Update sample with results
            sample.attributes["analysis_result"] = result
            plate.set_child(key=sample_position, child=sample)

            return ActionSucceeded(data=result)
```

**Examples**: See [example_lab/](../../example_lab/) for complete resource management workflows integrated with laboratory operations.
