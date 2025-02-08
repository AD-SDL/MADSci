# Resource Manager Usage Guide

## Overview
This guide explains how to interact with the Resource Manager system using the `ResourceClient`. You will learn how to create, modify, query, and manage various resource types, including stacks, queues, pools, consumables, and collections.

## Setup
Ensure you have access to the Resource Manager API and initialize the client:

```python
from madsci.client.resource_client import ResourceClient

base_url = "http://localhost:8012"
client = ResourceClient(base_url=base_url)
```

## Working with Stacks
### Creating a Stack
```python
from madsci.resource_manager.resource_tables import Stack, Asset

stack = Stack(resource_name="stack", resource_type="stack", capacity=10, ownership=None)
stack = client.add_resource(stack)
```

### Adding Assets to a Stack
```python
for i in range(5):
    asset = Asset(resource_name=f"Test plate {i}", resource_type="asset")
    asset = client.add_resource(asset)
    stack = client.push_to_stack(stack, asset)
```

### Retrieving and Popping Assets from a Stack
```python
retrieved_stack = client.get_resource(resource_id=stack.resource_id)
for _ in range(2):
    popped_asset, retrieved_stack = client.pop_from_stack(retrieved_stack)
    print(popped_asset)
```

## Working with Queues
### Creating a Queue
```python
from madsci.resource_manager.resource_tables import Queue

queue = Queue(resource_name="queue", resource_type="queue", capacity=10, ownership=None)
queue = client.add_resource(queue)
```

### Adding and Retrieving Assets from a Queue
```python
for i in range(5):
    asset = Asset(resource_name=f"Test plate {i}", resource_type="asset")
    asset = client.add_resource(asset)
    queue = client.push_to_queue(queue, asset)

retrieved_queue = client.get_resource(resource_id=queue.resource_id)
for _ in range(2):
    popped_asset, retrieved_queue = client.pop_from_queue(retrieved_queue)
queue = client.push_to_queue(queue, popped_asset)
```

## Working with Consumables and Pools
### Creating a Consumable
```python
from madsci.resource_manager.resource_tables import Consumable, Pool

consumable = Consumable(
    resource_name="Water",
    resource_type="consumable",
    quantity=50.0,
    ownership=None,
    capacity=100,
)
consumable = client.add_resource(consumable)
```

### Creating a Pool and Performing Operations
```python
pool = Pool(resource_name="Vial_1", resource_type="pool", capacity=500.0, children={"Water": consumable})
pool = client.add_resource(pool)

print(f"Initial Pool Quantity: {pool.quantity}")
pool = client.increase_pool_quantity(pool, 50.0)
print(f"After Increase: {pool.quantity}")

pool = client.decrease_pool_quantity(pool, 20.0)
print(f"After Decrease: {pool.quantity}")

pool = client.fill_pool(pool)
print(f"After Fill: {pool.quantity}")

pool = client.empty_pool(pool)
print(f"After Empty: {pool.quantity}")
```

## Working with Collections
### Creating and Modifying a Collection
```python
from madsci.resource_manager.resource_tables import Collection

pool1 = Pool(resource_name="Pool1", resource_type="pool", capacity=100, quantity=50)
pool1 = client.add_resource(pool1)

plate = Collection(resource_name="Microplate1", resource_type="collection", children={"A1": pool})
plate = client.add_resource(plate)

plate = client.increase_plate_well(plate, "A1", 30)
print(f"A1 Quantity after increase: {plate.children}")

plate = client.decrease_plate_well(plate, "A1", 20)
print(f"A1 Quantity after decrease: {plate.children}")

plate = client.update_collection_child(plate, "A2", pool1)
print(f"A2 Pool Name: {plate.children}")
```

## Updating and Removing Resources
### Updating a Resource
```python
pool.capacity = 1000
updated_resource = client.update_resource(pool)
print(updated_resource.capacity)
```

### Removing and Restoring a Resource
```python
test_asset = Asset(resource_name="Test Asset for Removal", resource_type="asset")
test_asset = client.add_resource(test_asset)
print("Test asset added:", test_asset)

removed_asset = client.remove_resource(stack.resource_id)
print("Resource removed:", removed_asset)

history_entries = client.get_history(resource_id=stack.resource_id, event_type="deleted")
print("History for removed resource:")
for entry in history_entries:
    print(entry)
```
