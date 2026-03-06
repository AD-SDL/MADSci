# Managing Resources

**Audience**: Experimentalist
**Prerequisites**: [Running Experiments](./01-running-experiments.md)
**Time**: ~25 minutes

## Overview

The Resource Manager tracks all physical items in your lab: samples, reagents, labware, tips, and consumables. This guide covers how to create, query, and manage resources during experiments.

## Resource Types

MADSci organizes resources into a hierarchy:

```
Resource (base)
├── Asset (tracked, non-consumed)
│   └── Container (holds other resources)
│       ├── Collection (keyed access)
│       ├── Row (1D indexed)
│       ├── Grid (2D indexed, e.g., 96-well plate)
│       ├── VoxelGrid (3D indexed)
│       ├── Stack (LIFO, e.g., plate magazine)
│       ├── Queue (FIFO, e.g., conveyor)
│       ├── Pool (mixed consumables, e.g., reservoir)
│       └── Slot (holds exactly one item)
└── Consumable (consumed during use)
    ├── DiscreteConsumable (whole units: tips, tubes)
    └── ContinuousConsumable (measured: liquids, powders)
```

## Creating Resources

### Using the ResourceClient

```python
from madsci.client import ResourceClient
from madsci.common.types.resource_types import (
    Asset,
    Grid,
    DiscreteConsumable,
    ContinuousConsumable,
    Slot,
)

rc = ResourceClient(resource_server_url="http://localhost:8003/")

# Create a simple asset (e.g., a sample)
sample = Asset(
    resource_name="Sample-001",
    attributes={
        "material": "polymer-A",
        "concentration": "10mM",
        "prepared_by": "Dr. Smith",
    },
)
result = rc.add_resource(sample)
print(f"Created: {result.resource_id}")
```

### Creating Containers

```python
# Create a 96-well plate
plate = Grid(
    resource_name="Plate-001",
    capacity=96,
    rows=8,
    columns=12,
    attributes={"plate_type": "96-well-flat-bottom"},
)
result = rc.add_resource(plate)
plate_id = result.resource_id

# Create a tip rack
tip_rack = Grid(
    resource_name="TipRack-001",
    capacity=96,
    rows=8,
    columns=12,
    attributes={"tip_type": "200uL"},
)
rc.add_resource(tip_rack)
```

### Creating Consumables

```python
# Discrete consumable (counted items)
tips = DiscreteConsumable(
    resource_name="Tips-200uL",
    quantity=96,
    capacity=96,
    unit="tips",
)
rc.add_resource(tips)

# Continuous consumable (measured quantity)
buffer = ContinuousConsumable(
    resource_name="PBS-Buffer",
    quantity=50.0,
    capacity=100.0,
    unit="mL",
)
rc.add_resource(buffer)
```

## Querying Resources

```python
# Get a specific resource by ID
resource = rc.get_resource("resource_id")
print(f"Name: {resource.resource_name}")
print(f"Type: {resource.base_type}")

# Query by name
resource = rc.query_resource(resource_name="Sample-001")

# Query by parent (children of a container)
children = rc.query_resource(parent_id="plate_id")

# Query by attributes
polymers = rc.query_resource(attributes={"material": "polymer-A"})
```

## Managing Container Contents

### Adding Items to Containers

```python
# Add a sample to a specific well in a plate
rc.set_child(
    resource="plate_id",
    key="A1",
    child="sample_id",
)

# Push onto a stack (LIFO)
rc.push(
    resource="stack_id",
    child="plate_id",
)
```

### Removing Items

```python
# Remove from a specific position
rc.remove_child(
    resource="plate_id",
    key="A1",
)

# Pop from a stack
container, item = rc.pop(resource="stack_id")
print(f"Popped: {item.resource_name}")
```

### Emptying and Filling

```python
# Empty a container
rc.empty(resource="plate_id")

# Fill a consumable to capacity
rc.fill(resource="buffer_id")
```

## Managing Quantities

For consumable resources:

```python
# Set exact quantity
rc.set_quantity(resource="buffer_id", quantity=45.0)

# Increase quantity (e.g., refill)
rc.increase_quantity(resource="buffer_id", amount=10.0)

# Decrease quantity (e.g., dispense)
rc.decrease_quantity(resource="buffer_id", amount=5.0)

# Change by relative amount
rc.change_quantity_by(resource="tips_id", amount=-8)  # Used 8 tips

# Check remaining
resource = rc.get_resource("buffer_id")
print(f"Remaining: {resource.quantity} {resource.unit}")
print(f"Capacity: {resource.capacity} {resource.unit}")
```

## Resource Templates

Templates let you create standardized resources quickly:

```python
# Create a template
rc.create_template(
    resource=Grid(
        resource_name="96-Well-Plate",
        capacity=96,
        rows=8,
        columns=12,
    ),
    template_name="standard_96_plate",
    description="Standard 96-well flat-bottom plate",
)

# Instantiate from template
new_plate = rc.init_template(
    resource=Grid(resource_name="Experiment-Plate-042"),
    template_name="standard_96_plate",
)
```

## Resource History

The Resource Manager tracks all changes to resources:

```python
# Get change history
history = rc.query_history(resource="sample_id")
for entry in history:
    print(f"{entry['timestamp']}: {entry['change_type']} - {entry['details']}")

# Filter by change type
creations = rc.query_history(change_type="create")
updates = rc.query_history(change_type="update")
```

## Resource Locking

Prevents concurrent modifications to resources:

```python
# Acquire a lock
rc.acquire_lock(resource="plate_id")

try:
    # Perform operations
    rc.set_child(resource="plate_id", key="A1", child="sample_id")
    rc.set_child(resource="plate_id", key="A2", child="sample2_id")
finally:
    # Always release the lock
    rc.release_lock(resource="plate_id")
```

## Locations

The Location Manager tracks where resources are physically located:

```python
from madsci.client import LocationClient

lc = LocationClient(location_server_url="http://localhost:8006/")

# Get all locations
locations = lc.get_locations()
for loc in locations:
    print(f"{loc.location_name}: {loc.description}")

# Attach a resource to a location
lc.attach_resource(
    location_id="deck_slot_1_id",
    resource_id="plate_id",
)

# Detach a resource
lc.detach_resource(location_id="deck_slot_1_id")

# Plan a transfer between locations
transfer = lc.plan_transfer(
    source_location_id="deck_slot_1_id",
    target_location_id="reader_slot_id",
    resource_id="plate_id",
)
print(f"Transfer path: {transfer}")
```

## Common Patterns

### Inventory Check Before Experiment

```python
def check_inventory(rc):
    """Verify sufficient resources before starting."""
    issues = []

    # Check tip count
    tips = rc.query_resource(resource_name="Tips-200uL")
    if tips and tips.quantity < 96:
        issues.append(f"Low tips: {tips.quantity}/96")

    # Check buffer volume
    buffer = rc.query_resource(resource_name="PBS-Buffer")
    if buffer and buffer.quantity < 10.0:
        issues.append(f"Low buffer: {buffer.quantity}mL")

    if issues:
        print("Inventory issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    print("Inventory OK")
    return True
```

### Track Sample Through Workflow

```python
def track_sample(rc, sample_id):
    """Get the current location and history of a sample."""
    resource = rc.get_resource(sample_id)
    print(f"Sample: {resource.resource_name}")
    print(f"Type: {resource.base_type}")
    print(f"Attributes: {resource.attributes}")

    history = rc.query_history(resource=sample_id)
    print(f"\nHistory ({len(history)} events):")
    for entry in history[-5:]:  # Last 5 events
        print(f"  {entry['timestamp']}: {entry['change_type']}")
```

## What's Next?

- [Experiment Design](./04-experiment-design.md) - Best practices for experiment structure
- [Jupyter Notebooks](./05-jupyter-notebooks.md) - Interactive resource exploration
- [Operator: Backup & Recovery](../operator/03-backup-recovery.md) - Protecting resource data
