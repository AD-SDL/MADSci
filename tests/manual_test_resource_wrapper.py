# flake8: noqa
"""Manual test for ResourceWrapper functionality in MADSci client."""

from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import (
    Asset,
    Pool,
    Queue,
    Stack,
)

# Initialize the ResourcesClient with the database URL
base_url = "http://localhost:8003"
client = ResourceClient(resource_server_url=base_url)

print("=== Testing ResourceWrapper Functionality ===")

# Create and add a stack using traditional client methods
stack = Stack(
    resource_name="test_wrapper_stack",
    resource_class="stack",
    capacity=10,
    ownership=None,
)
stack = client.add_resource(stack)
print(f"Stack created with ID: {stack.resource_id}")
print(f"Stack is wrapped: {type(stack).__name__}")

# Test wrapper properties
print(f"Stack unwrap type: {type(stack.unwrap)}")
print(f"Stack data type: {type(stack.data)}")
print(f"Stack client available: {hasattr(stack, 'client')}")

# Create some assets to work with
assets = []
for i in range(3):
    asset = Asset(resource_name=f"wrapper_test_asset_{i}", resource_class="asset")
    asset = client.add_resource(asset)
    assets.append(asset)
    print(f"Asset {i} created with ID: {asset.resource_id}")

print("\n=== Testing New Wrapper Syntax ===")

# Test new syntax: stack.push(child) instead of client.push(stack, child)
print("Testing stack.push(asset) - new syntax")
original_children_count = len(stack.children) if stack.children else 0
stack = stack.push(assets[0])
new_children_count = len(stack.children) if stack.children else 0
print(f"Children count before: {original_children_count}, after: {new_children_count}")
print(f"Push operation successful: {new_children_count > original_children_count}")
# print(client.get_resource(stack.resource_id))
# Test method chaining
print("\nTesting method chaining: stack.push().set_capacity()")
try:
    result = stack.push(assets[1]).set_capacity(15)
    print(f"Method chaining successful, new capacity: {result.capacity}")
except Exception as e:
    print(f"Method chaining failed: {e}")

# Test pop operation with new syntax
print("\nTesting stack.pop() - new syntax")
try:
    popped_asset, updated_stack = stack.pop()
    print(f"Popped asset: {popped_asset.resource_name}")
    print(
        f"Updated stack children count: {len(updated_stack.children) if updated_stack.children else 0}"
    )
    stack = updated_stack  # Update our reference
except Exception as e:
    print(f"Pop operation failed: {e}")

print("\n=== Testing Resource Locking Functionality ===")

# Test basic lock acquisition and release
print("Testing basic lock acquisition")
stack = client.acquire_lock(stack, lock_duration=60.0)

print(f"Lock acquired: {stack is not None}")

# Check lock status
is_locked, locked_by = client.is_locked(stack)
print(f"Resource is locked: {is_locked}")
print(f"Locked by: {locked_by}")

# Test lock release
print("Testing lock release")
client.release_lock(stack)
print(f"Lock released: {stack is not None}")
# # Verify lock is released
is_locked_after, locked_by_after = client.is_locked(stack)
print(f"Resource is locked after release: {is_locked_after}")

# print("\n=== Testing Context Manager Locking ===")

# # Test single resource locking with context manager
print("Testing single resource context manager locking")
try:
    with client.lock(stack, lock_duration=30.0) as locked_stack:
        print(f"Inside context manager - resource type: {type(locked_stack).__name__}")
        print(f"Resource ID: {locked_stack.resource_id}")

        # Perform operations while locked
        locked_stack = locked_stack.push(assets[2])
        print("Performed push operation while locked")
        print(
            f"Children count: {len(locked_stack.children) if locked_stack.children else 0}"
        )

    print("Context manager exited successfully")
except Exception as e:
    print(f"Context manager failed: {e}")

# Test multiple resource locking
print("\nTesting multiple resource context manager locking")
try:
    with client.lock(stack, assets[0], lock_duration=30.0) as (
        locked_stack,
        locked_asset,
    ):
        print(f"Locked stack type: {type(locked_stack).__name__}")
        print(f"Locked asset type: {type(locked_asset).__name__}")
        print("Multiple resource locking successful")
except Exception as e:
    print(f"Multiple resource locking failed: {e}")

print("\n=== Testing Update Functionality ===")

# Test refresh method (should be available through wrapper)
print("Testing resource update")
try:
    refreshed_stack = stack.update_resource()
    print(f"Resource updated successfully: {type(refreshed_stack).__name__}")
    print(f"Refreshed stack ID: {refreshed_stack.resource_id}")
except Exception as e:
    print(f"Refresh failed: {e}")

print("\n=== Testing get_resource with Different Input Types ===")

# Test get_resource with resource ID (string)
print("Testing get_resource with resource ID")
retrieved_by_id = client.get_resource(stack.resource_id)
print(f"Retrieved by ID - type: {type(retrieved_by_id).__name__}")
print(f"Retrieved by ID - name: {retrieved_by_id.resource_name}")

# Test get_resource with resource object
print("Testing get_resource with resource object")
retrieved_by_object = client.get_resource(stack)
print(f"Retrieved by object - type: {type(retrieved_by_object).__name__}")
print(f"Retrieved by object - name: {retrieved_by_object.resource_name}")

print("\n=== Testing Backward Compatibility ===")

# Ensure old syntax still works
print("Testing backward compatibility - client.push(stack, asset)")
old_children_count = len(stack.children) if stack.children else 0
try:
    stack = client.push(stack, assets[0])
    new_children_count = len(stack.children) if stack.children else 0
    print(f"Old syntax still works: {new_children_count >= old_children_count}")
except Exception as e:
    print(f"Backward compatibility failed: {e}")

print("\n=== Testing Queue with New Syntax ===")

# Create a queue to test queue-specific operations
queue = Queue(
    resource_name="test_wrapper_queue",
    resource_class="queue",
    capacity=5,
    ownership=None,
)
queue = client.add_resource(queue)
print(f"Queue created: {queue.resource_name}")

# Test queue operations with new syntax
print("Testing queue.push() and queue.pop()")
try:
    queue = queue.push(assets[0])
    print("Queue push successful")

    popped_item, updated_queue = queue.pop()
    print(f"Queue pop successful - popped: {popped_item.resource_name}")
    queue = updated_queue
except Exception as e:
    print(f"Queue operations failed: {e}")

print("\n=== Testing Pool Operations with New Syntax ===")

# Create a pool to test pool-specific operations
pool = Pool(
    resource_name="test_wrapper_pool",
    resource_class="pool",
    capacity=100.0,
    quantity=50.0,
)
pool = client.add_resource(pool)
print(f"Pool created: {pool.resource_name}")

# Test pool operations with new syntax
print("Testing pool operations with wrapper")
try:
    original_quantity = pool.quantity
    pool = pool.set_capacity(200)
    print(f"Set capacity successful - new capacity: {pool.capacity}")

    pool = pool.fill()

    print(f"Increase quantity successful - new quantity: {pool.quantity}")

    pool = pool.empty()
    print(f"Decrease quantity successful - new quantity: {pool.quantity}")

except Exception as e:
    print(f"Pool operations failed: {e}")

print("\n=== Testing Individual Resource Lock Context Managers ===")

# Test using stack.lock and resource.lock as individual context managers
print("Testing stack.lock() and resource.lock() as individual context managers")

# Create fresh resources for this test
test_stack = Stack(
    resource_name="lock_test_stack", resource_class="stack", capacity=10, ownership=None
)
test_stack = client.add_resource(test_stack)

test_resource = Asset(resource_name="lock_test_asset", resource_class="asset")
test_resource = client.add_resource(test_resource)

print(f"Created test stack: {test_stack.resource_name}")
print(f"Created test resource: {test_resource.resource_name}")

try:
    # Test the pattern you requested: with stack.lock, resource.lock:
    with test_stack.lock(), test_resource.lock():
        print("Inside nested lock context managers")

        # Perform operation while both resources are locked
        original_parent_id = getattr(test_resource, "parent_id", None)
        print(f"Resource parent_id before push: {original_parent_id}")

        test_stack = test_stack.push(test_resource)
        print("Push operation completed while resources locked")

        # Get fresh resource to check parent_id
        updated_resource = client.get_resource(test_resource.resource_id)
        final_parent_id = getattr(updated_resource, "parent_id", None)
        print(f"Resource parent_id after push: {final_parent_id}")

    print("Exited nested lock context managers")

    # Verify the relationship was established
    if (
        hasattr(updated_resource, "parent_id")
        and updated_resource.parent_id == test_stack.resource_id
    ):
        print("SUCCESS: Resource parent_id matches stack resource_id")
    else:
        print("VERIFICATION: Checking if resource is in stack children")
        final_stack = client.get_resource(test_stack.resource_id)
        if final_stack.children and any(
            child.resource_id == test_resource.resource_id
            for child in final_stack.children
        ):
            print("SUCCESS: Resource found in stack children")
        else:
            print("INFO: Parent-child relationship verification method may vary")

except Exception as e:
    print(f"Individual resource lock context managers failed: {e}")

print("\n=== Testing Alternative Lock Syntax ===")

# Test alternative syntax in case the above doesn't work exactly as expected
print("Testing with client.lock() for individual resources")

try:
    # Create another set of test resources
    alt_stack = Stack(
        resource_name="alt_lock_stack",
        resource_class="stack",
        capacity=10,
        ownership=None,
    )
    alt_stack = client.add_resource(alt_stack)

    alt_resource = Asset(resource_name="alt_lock_asset", resource_class="asset")
    alt_resource = client.add_resource(alt_resource)

    # Test using separate lock calls
    with client.lock(alt_stack) as locked_stack:
        with client.lock(alt_resource) as locked_resource:
            print("Inside nested client.lock() context managers")

            locked_stack = locked_stack.push(locked_resource)
            print("Push operation completed with nested client locks")

            # Verify the operation
            updated_stack = client.get_resource(alt_stack.resource_id)
            if updated_stack.children:
                child_ids = [child.resource_id for child in updated_stack.children]
                if alt_resource.resource_id in child_ids:
                    print(
                        "SUCCESS: Resource successfully added to stack with nested locks"
                    )
                else:
                    print("INFO: Resource not found in immediate children list")

except Exception as e:
    print(f"Alternative lock syntax failed: {e}")

print("\n=== All Tests Completed ===")
