
from resource_client import ResourceClient
from db_tables import Stack, Asset, Queue, Pool, Plate, Consumable

# Initialize the ResourcesClient with the database URL
database_url = "postgresql://rpl:rpl@127.0.0.1:5432/resources"
base_url = "http://localhost:8012" 
client = ResourceClient(base_url=base_url, database_url=database_url)

# message = "Hello, FastAPI!"
# response = client.send_message(message)
# print(response)
# Create and add a stack
stack = Stack(
    resource_name="stack",
    resource_type="stack",
    capacity=10,
    ownership=None
)
stack = client.add_resource(stack)

# # Add assets to the stack and push them
# for i in range(5):
#     asset = Asset(resource_name=f"Test plate {i}")
#     asset = client.add_resource(asset)
#     client.push_to_stack(stack, asset)

# # Retrieve the stack and pop two assets
# retrieved_stack = client.get_resource(resource_id=stack.resource_id)
# for _ in range(2):
#     popped_asset = client.pop_from_stack(retrieved_stack)

# # Create and add a queue
# queue = Queue(
#     resource_name="queue",
#     resource_type="queue",
#     capacity=10,
#     ownership=None
# )
# queue = client.add_resource(queue)

# # Add assets to the queue and push them
# for i in range(5):
#     asset = Asset(resource_name=f"Test plate {i}")
#     asset = client.add_resource(asset)
#     client.push_to_queue(queue, asset)

# # Retrieve the queue and pop two assets, then push one back
# retrieved_queue = client.get_resource(resource_id=queue.resource_id)
# for _ in range(2):
#     popped_asset = client.pop_from_queue(retrieved_queue)
# client.push_to_queue(queue, popped_asset)

# # Create and add a consumable resource
# consumable = Consumable(
#     resource_name="Water",
#     resource_type="consumable",
#     quantity=50.0,
#     ownership=None,
#     capacity=100,
# )
# client.add_resource(consumable)

# # Create and add a pool resource with the consumable as a child
# pool = Pool(
#     resource_name="Vial_1",
#     resource_type="pool",
#     capacity=500.0,
#     children={"Water": consumable}
# )
# pool = client.add_resource(pool)

# # Perform operations on the pool
# print(f"Initial Pool Quantity: {pool.quantity}")
# client.increase_pool_quantity(pool, 50.0)
# print(f"After Increase: {pool.quantity}")

# client.decrease_pool_quantity(pool, 20.0)
# print(f"After Decrease: {pool.quantity}")

# # client.fill_pool(pool)
# # print(f"After Fill: {pool.quantity}")

# # client.empty_pool(pool)
# # print(f"After Empty: {pool.quantity}")

# # Add another pool resource
# pool1 = Pool(resource_name="Pool1", resource_type="pool", capacity=100, quantity=50)
# pool1 = client.add_resource(pool1)

# # Create and add a plate resource with an initial child pool
# plate = Plate(
#     resource_name="Microplate1",
#     resource_type="plate",
#     children={"A1": pool},
# )
# plate = client.add_resource(plate)
# print(plate.children)

# # Increase and decrease quantity in a specific well of the plate
# client.increase_plate_well(plate, "A1", 30)
# print(f"A1 Quantity after increase: {plate.children}")

# client.decrease_plate_well(plate, "A1", 20)
# print(f"A1 Quantity after decrease: {plate.children}")

# # Update or add a new well to the plate
# client.update_plate_well(plate, "A2", pool1)
# print(f"A2 Pool Name: {plate.children}")
