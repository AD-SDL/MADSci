# ruff: noqa
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import (
    Asset,
    Collection,
    Consumable,
    Pool,
    Queue,
    Stack,
)

# Initialize the ResourcesClient with the database URL
base_url = "http://localhost:8003"
client = ResourceClient(url=base_url)

# stack = Stack(
#     resource_name="stack", resource_class="stack", capacity=10, ownership=None
# )
# stack = client.add_resource(stack)
# # # Add assets to the stack and push them
# for i in range(5):
#     asset = Asset(resource_name=f"Test plate {i}", resource_class="asset")
#     asset = client.add_resource(asset)
#     stack = client.push(stack, asset)

# # # # Retrieve the stack and pop two assets
# retrieved_stack = client.query_resource(resource_id=stack.resource_id)
# for _ in range(2):
#     popped_asset, retrieved_stack = client.pop(retrieved_stack)
#     print(popped_asset)

# # # Create and add a queue
# queue = Queue(
#     resource_name="queue", resource_class="queue", capacity=10, ownership=None
# )
# queue = client.add_resource(queue)

# # Add assets to the queue and push them
# for i in range(5):
#     asset = Asset(resource_name=f"Test plate {i}", resource_class="asset")
#     asset = client.add_resource(asset)
#     queue = client.push(queue, asset)

# # Retrieve the queue and pop two assets, then push one back
# retrieved_queue = client.query_resource(resource_id=queue.resource_id)
# for _ in range(2):
#     popped_asset, retrieved_queue = client.pop(retrieved_queue)
# queue = client.push(queue, popped_asset)

# # # # # Create and add a consumable resource
# consumable = Consumable(
#     resource_name="Water",
#     resource_class="consumable",
#     quantity=50.0,
#     ownership=None,
#     capacity=100,
# )
# consumable = client.add_resource(consumable)

# # Create and add a pool resource with the consumable as a child
pool = Pool(
    resource_name="Vial_1",
    resource_class="pool",
    capacity=500.0,
    # children={"Water": consumable},
)
pool = client.add_resource(pool)

# # Perform operations on the pool
print(f"Initial Pool Quantity: {pool.quantity}")
pool = client.increase_quantity(pool, 50.0)
print(f"After Increase: {pool.quantity}")

pool = client.decrease_quantity(pool, 20.0)
print(f"After Decrease: {pool.quantity}")

pool = client.fill(pool)
print(f"After Fill: {pool.quantity}")

pool = client.empty(pool)
print(f"After Empty: {pool.quantity}")

# Add another pool resource
pool1 = Pool(resource_name="Pool1", resource_class="pool", capacity=100, quantity=50)
pool1 = client.add_resource(pool1)

# # Create and add a plate resource with an initial child pool
# plate = Collection(
#     resource_name="Microplate1",
#     resource_class="collection",
#     children={"A1": pool},
# )
# plate = client.add_resource(plate)
# # print(plate.children)

# # Increase and decrease quantity in a specific well of the plate
# plate = client.increase_plate_well(plate, "A1", 30)
# print(f"A1 Quantity after increase: {plate.children}")
# # plate = client.get_resource()
# plate = client.decrease_plate_well(plate, "A1", 20)
# print(f"A1 Quantity after decrease: {plate.children}")

# # Update or add a new well to the plate
# plate = client.update_collection_child(plate, "A2", pool1)
# print(f"A2 Pool Name: {plate.children}")

# pool.capacity = 1000
# updated_resource = client.update_resource(pool)
# print(updated_resource.capacity)

# print("\n=== Testing get_history, remove_resource, and restore_deleted_resource ===")

# # Create a test asset to remove and then restore
# test_asset = Asset(resource_name="Test Asset for Removal", resource_class="asset")
# test_asset = client.add_resource(test_asset)
# print("Test asset added:", test_asset)


# # Wait a moment to ensure the history timestamps will be distinct
# # time.sleep(1)

# # Remove the test resource
# removed_asset = client.remove_resource(stack.resource_id)
# print("Resource removed:", removed_asset)

# # Wait again to let the removal event register in history
# # time.sleep(1)

# # Retrieve history for the removed resource.
# history_entries = client.query_history(
#     resource_id=stack.resource_id, event_type="deleted"
# )
# print("History for removed resource:")
# for entry in history_entries:
#     print(entry)
