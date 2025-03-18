"""Pytest unit tests for the Resource Manager's internal db interfacing logic."""

import pytest
from madsci.common.types.resource_types import (
    Consumable,
    Container,
    ContinuousConsumable,
    Grid,
    Queue,
    Resource,
    Row,
    Slot,
    Stack,
    VoxelGrid,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_tables import (
    ResourceTable,
    create_session,
)
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import Engine
from sqlmodel import Session as SQLModelSession


@pytest.fixture(scope="session")
def pmr_postgres_config() -> PostgresConfig:
    """Configure the Postgres fixture"""
    return PostgresConfig(image="postgres:17")


# Create a Postgres fixture
postgres_engine = create_postgres_fixture(ResourceTable)


@pytest.fixture
def interface(postgres_engine: Engine) -> ResourceInterface:
    """Resource Table Interface Fixture"""

    def sessionmaker() -> SQLModelSession:
        return create_session(postgres_engine)

    return ResourceInterface(engine=postgres_engine, sessionmaker=sessionmaker)


def test_create_interface(interface: ResourceInterface) -> None:
    """Test creating a resource interface"""
    assert interface


def test_add_resource(interface: ResourceInterface) -> None:
    """Test adding a resource"""
    resource1 = Resource()
    resource = interface.add_resource(resource=resource1)
    assert resource.resource_id == resource1.resource_id
    assert resource.resource_name == resource1.resource_name
    assert resource.removed is False

    resource2 = interface.get_resource(resource_id=resource1.resource_id)
    assert resource2.resource_id == resource1.resource_id
    assert resource2.resource_name == resource1.resource_name
    assert resource2.removed is False

    resource3 = interface.get_resource(
        resource_id=resource1.resource_id,
        resource_name=resource1.resource_name,
        parent_id=resource1.parent_id,
        resource_type=resource1.resource_type,
        resource_base_type=resource1.base_type,
        unique=True,
    )
    assert resource3.resource_id == resource1.resource_id
    assert resource3.resource_name == resource1.resource_name
    assert resource3.removed is False


def test_add_with_children(interface: ResourceInterface) -> None:
    """Test adding a resource with children"""
    # Create test resources
    stack1 = Stack()
    resource1 = Resource()
    stack1.children.append(resource1)

    # Test initial stack creation with one child
    stack2 = interface.add_resource(resource=stack1)
    assert stack1.base_type == "stack"
    assert stack2.resource_id == stack1.resource_id
    assert stack2.base_type == "stack"
    assert stack2.resource_name == stack1.resource_name
    assert isinstance(stack2, Stack)
    assert len(stack2.children) == 1
    assert stack2.quantity == 1

    # Verify first child properties
    child1 = stack2.children[0]
    assert child1.resource_id == resource1.resource_id
    assert child1.resource_name == resource1.resource_name

    # Test updating stack with additional child
    resource2 = Resource()
    stack2.children.append(resource2)
    stack3 = interface.update_resource(resource=stack2)

    # Verify updated stack properties
    assert stack3.resource_id == stack2.resource_id
    assert stack3.base_type == "stack"
    assert stack3.resource_name == stack2.resource_name
    assert isinstance(stack3, Stack)
    assert len(stack3.children) == 2
    assert stack3.quantity == 2

    # Verify both children properties
    assert stack3.children[0].resource_id == resource1.resource_id
    assert stack3.children[0].resource_name == resource1.resource_name
    assert stack3.children[1].resource_id == resource2.resource_id
    assert stack3.children[1].resource_name == resource2.resource_name


def test_push_to_stack(interface: ResourceInterface) -> None:
    """Test pushing a resource to a stack"""
    # Create test resources
    stack1 = Stack()
    resource1 = Resource()
    stack1.children.append(resource1)

    # Test initial stack creation with one child
    stack2 = interface.add_resource(resource=stack1)
    assert len(stack2.children) == 1
    assert stack2.quantity == 1
    assert stack2.base_type == "stack"

    # Verify first child properties
    child1 = stack2.children[0]
    assert child1.resource_id == resource1.resource_id
    assert child1.resource_name == resource1.resource_name
    assert stack2.children[0].resource_id == resource1.resource_id
    assert stack2.children[0].resource_name == resource1.resource_name
    assert stack2.children[0].parent_id == stack2.resource_id

    # Test pushing a new resource to the stack
    resource2 = Resource()
    stack3 = interface.push(parent_id=stack2.resource_id, child=resource2)

    # Verify updated stack properties
    assert len(stack3.children) == 2
    assert stack3.quantity == 2
    assert stack3.children[1].resource_id == resource2.resource_id
    assert stack3.children[1].resource_name == resource2.resource_name
    assert stack3.children[1].parent_id == stack3.resource_id
    assert stack2.children[0].resource_id == resource1.resource_id
    assert stack2.children[0].resource_name == resource1.resource_name
    assert stack2.children[0].parent_id == stack2.resource_id

    # Test pushing a resource to the stack by id
    resource3 = Resource()
    interface.add_resource(resource=resource3)
    stack4 = interface.push(parent_id=stack3.resource_id, child=resource3.resource_id)

    # Verify updated stack properties
    assert len(stack4.children) == 3
    assert stack4.quantity == 3
    assert stack4.children[2].resource_id == resource3.resource_id
    assert stack4.children[2].resource_name == resource3.resource_name
    assert stack4.children[2].parent_id == stack4.resource_id


def test_pop_from_stack(interface: ResourceInterface) -> None:
    """Test popping a resource from a stack"""
    # Create test resources
    stack1 = Stack()
    resource1 = Resource()
    stack1.children.append(resource1)
    resource2 = Resource()
    stack1.children.append(resource2)

    # Test initial stack creation with two children
    stack2 = interface.add_resource(resource=stack1)
    assert len(stack2.children) == 2
    assert stack2.quantity == 2

    # Verify first child properties
    child1 = stack2.children[0]
    assert child1.resource_id == resource1.resource_id
    assert child1.resource_name == resource1.resource_name
    assert stack2.children[0].resource_id == resource1.resource_id
    assert stack2.children[0].resource_name == resource1.resource_name
    assert stack2.children[0].parent_id == stack2.resource_id

    # Verify second child properties
    child2 = stack2.children[1]
    assert child2.resource_id == resource2.resource_id
    assert child2.resource_name == resource2.resource_name
    assert stack2.children[1].resource_id == resource2.resource_id
    assert stack2.children[1].resource_name == resource2.resource_name
    assert stack2.children[1].parent_id == stack2.resource_id

    # Test popping a resource from the stack
    child2_new, stack3 = interface.pop(parent_id=stack2.resource_id)

    # Verify updated stack properties
    assert child2_new.resource_id == resource2.resource_id
    assert len(stack3.children) == 1
    assert stack3.quantity == 1
    assert stack3.children[0].resource_id == resource1.resource_id
    assert stack3.children[0].resource_name == resource1.resource_name
    assert stack3.children[0].parent_id == stack3.resource_id


def test_push_to_queue(interface: ResourceInterface) -> None:
    """Test pushing a resource to a queue"""
    # Create test resources
    queue1 = Queue()
    resource1 = Resource()
    queue1.children.append(resource1)

    # Test initial queue creation with one child
    queue2 = interface.add_resource(resource=queue1)
    assert len(queue2.children) == 1
    assert queue2.quantity == 1
    assert queue2.base_type == "queue"

    # Verify first child properties
    child1 = queue2.children[0]
    assert child1.resource_id == resource1.resource_id
    assert child1.resource_name == resource1.resource_name
    assert queue2.children[0].resource_id == resource1.resource_id
    assert queue2.children[0].resource_name == resource1.resource_name
    assert queue2.children[0].parent_id == queue2.resource_id

    # Test pushing a new resource to the queue
    resource2 = Resource()
    queue3 = interface.push(parent_id=queue2.resource_id, child=resource2)

    # Verify updated queue properties
    assert len(queue3.children) == 2
    assert queue3.quantity == 2
    assert queue3.children[1].resource_id == resource2.resource_id
    assert queue3.children[1].resource_name == resource2.resource_name
    assert queue3.children[1].parent_id == queue3.resource_id
    assert queue2.children[0].resource_id == resource1.resource_id
    assert queue2.children[0].resource_name == resource1.resource_name
    assert queue2.children[0].parent_id == queue2.resource_id

    # Test pushing a resource to the queue by id
    resource3 = Resource()
    interface.add_resource(resource=resource3)
    queue4 = interface.push(parent_id=queue3.resource_id, child=resource3.resource_id)

    # Verify updated queue properties
    assert len(queue4.children) == 3
    assert queue4.quantity == 3
    assert queue4.children[2].resource_id == resource3.resource_id
    assert queue4.children[2].resource_name == resource3.resource_name
    assert queue4.children[2].parent_id == queue4.resource_id


def test_pop_from_queue(interface: ResourceInterface) -> None:
    """Test popping a resource from a queue"""
    # Create test resources
    queue1 = Queue()
    resource1 = Resource()
    queue1.children.append(resource1)
    resource2 = Resource()
    queue1.children.append(resource2)

    # Test initial queue creation with two children
    queue2 = interface.add_resource(resource=queue1)
    assert len(queue2.children) == 2
    assert queue2.quantity == 2

    # Verify first child properties
    child1 = queue2.children[0]
    assert child1.resource_id == resource1.resource_id
    assert child1.resource_name == resource1.resource_name
    assert queue2.children[0].resource_id == resource1.resource_id
    assert queue2.children[0].resource_name == resource1.resource_name
    assert queue2.children[0].parent_id == queue2.resource_id

    # Verify second child properties
    child2 = queue2.children[1]
    assert child2.resource_id == resource2.resource_id
    assert child2.resource_name == resource2.resource_name
    assert queue2.children[1].resource_id == resource2.resource_id
    assert queue2.children[1].resource_name == resource2.resource_name
    assert queue2.children[1].parent_id == queue2.resource_id

    # Test popping a resource from the queue
    child1_new, queue3 = interface.pop(parent_id=queue2.resource_id)

    # Verify updated queue properties
    assert child1_new.resource_id == resource1.resource_id
    assert len(queue3.children) == 1
    assert queue3.quantity == 1
    assert queue3.children[0].resource_id == resource2.resource_id
    assert queue3.children[0].resource_name == resource2.resource_name
    assert queue3.children[0].parent_id == queue3.resource_id


def test_set_child(interface: ResourceInterface) -> None:
    """Test setting a child in a container"""
    # Create test resources
    container = Container()
    resource1 = Resource()

    # Add container to database first
    container = interface.add_resource(resource=container)

    # Test setting initial child
    container2 = interface.set_child(
        container_id=container.resource_id, key="slot1", child=resource1
    )

    # Verify container properties
    assert len(container2.children) == 1
    assert container2.quantity == 1
    assert "slot1" in container2.children
    assert container2.children["slot1"].resource_id == resource1.resource_id

    # Test setting child using existing resource id
    resource2 = Resource()
    resource2 = interface.add_resource(resource=resource2)
    container3 = interface.set_child(
        container_id=container2.resource_id, key="slot2", child=resource2.resource_id
    )

    # Verify updated container properties
    assert len(container3.children) == 2
    assert container3.quantity == 2
    assert "slot2" in container3.children
    assert container3.children["slot2"].resource_id == resource2.resource_id

    # Test updating existing slot
    resource3 = Resource()
    container4 = interface.set_child(
        container_id=container3.resource_id, key="slot1", child=resource3
    )

    # Verify slot was updated
    assert len(container4.children) == 2
    assert container4.quantity == 2
    assert container4.children["slot1"].resource_id == resource3.resource_id


def test_set_child_invalid_container(interface: ResourceInterface) -> None:
    """Test setting a child in an invalid container type"""
    # Create test resources using a Stack instead of Container
    stack = Stack()
    resource = Resource()

    # Add stack to database
    stack = interface.add_resource(resource=stack)

    # Attempt to set child on invalid container type
    with pytest.raises(ValueError):
        interface.set_child(container_id=stack.resource_id, key="slot1", child=resource)


def test_set_child_capacity_limit(interface: ResourceInterface) -> None:
    """Test setting a child when container is at capacity"""
    # Create container with capacity=1
    container = Container(capacity=1)
    resource1 = Resource()
    resource2 = Resource()

    # Add container and fill its only slot
    container = interface.add_resource(resource=container)
    container = interface.set_child(
        container_id=container.resource_id, key="slot1", child=resource1
    )

    # Attempt to add another child when at capacity
    with pytest.raises(ValueError) as exc_info:
        interface.set_child(
            container_id=container.resource_id, key="slot2", child=resource2
        )

    assert "because it is full" in str(exc_info.value)


def test_remove_child(interface: ResourceInterface) -> None:
    """Test removing a child from a container"""
    # Create test resources
    container = Container()
    resource1 = Resource()
    resource2 = Resource()

    # Add container and children
    container = interface.add_resource(resource=container)
    container = interface.set_child(
        container_id=container.resource_id, key="slot1", child=resource1
    )
    container = interface.set_child(
        container_id=container.resource_id, key="slot2", child=resource2
    )

    # Verify initial state
    assert len(container.children) == 2
    assert container.quantity == 2
    assert "slot1" in container.children
    assert "slot2" in container.children

    # Remove first child
    container = interface.remove_child(container_id=container.resource_id, key="slot1")

    # Verify child was removed
    assert len(container.children) == 1
    assert container.quantity == 1
    assert "slot1" not in container.children
    assert "slot2" in container.children
    assert container.children["slot2"].resource_id == resource2.resource_id


def test_remove_child_invalid_container(interface: ResourceInterface) -> None:
    """Test removing a child from an invalid container type"""
    # Create test resources using a Stack instead of Container
    stack = Stack()
    resource = Resource()

    # Add stack and push resource
    stack = interface.add_resource(resource=stack)
    stack = interface.push(parent_id=stack.resource_id, child=resource)

    # Attempt to remove child from invalid container type
    with pytest.raises(ValueError):
        interface.remove_child(container_id=stack.resource_id, key="0")


def test_remove_child_invalid_key(interface: ResourceInterface) -> None:
    """Test removing a child with invalid key"""
    # Create and add container
    container = Container()
    container = interface.add_resource(resource=container)

    # Attempt to remove non-existent child
    with pytest.raises(KeyError):
        interface.remove_child(
            container_id=container.resource_id, key="non_existent_slot"
        )


def test_set_capacity(interface: ResourceInterface) -> None:
    """Test setting capacity of a container"""
    # Create container with initial capacity
    container = Container(capacity=5)
    container = interface.add_resource(resource=container)

    # Test changing capacity
    interface.set_capacity(resource_id=container.resource_id, capacity=10)

    # Get updated container
    updated_container = interface.get_resource(resource_id=container.resource_id)
    assert updated_container.capacity == 10


def test_set_capacity_with_existing_children(interface: ResourceInterface) -> None:
    """Test setting capacity with existing children"""
    # Create container and add children
    container = Container(capacity=5)
    container = interface.add_resource(resource=container)

    # Add 3 children
    for i in range(3):
        resource = Resource()
        container = interface.set_child(
            container_id=container.resource_id, key=f"slot{i}", child=resource
        )

    # Test setting valid capacity above current quantity
    interface.set_capacity(resource_id=container.resource_id, capacity=4)
    updated_container = interface.get_resource(resource_id=container.resource_id)
    assert updated_container.capacity == 4

    # Test setting capacity below current quantity
    with pytest.raises(ValueError) as exc_info:
        interface.set_capacity(resource_id=container.resource_id, capacity=2)
    assert "because it currently contains" in str(exc_info.value)


def test_set_capacity_invalid_resource(interface: ResourceInterface) -> None:
    """Test setting capacity on resource without capacity attribute"""
    # Create regular resource without capacity
    resource = Resource()
    resource = interface.add_resource(resource=resource)

    # Attempt to set capacity on invalid resource
    with pytest.raises(ValueError) as exc_info:
        interface.set_capacity(resource_id=resource.resource_id, capacity=5)
    assert "has no capacity attribute" in str(exc_info.value)


def test_set_capacity_no_change(interface: ResourceInterface) -> None:
    """Test setting capacity to current value"""
    # Create container with initial capacity
    container = Container(capacity=5)
    container = interface.add_resource(resource=container)

    # Set capacity to same value
    interface.set_capacity(resource_id=container.resource_id, capacity=5)

    # Verify capacity remains unchanged
    updated_container = interface.get_resource(resource_id=container.resource_id)
    assert updated_container.capacity == 5


def test_remove_capacity_limit(interface: ResourceInterface) -> None:
    """Test removing capacity limit from a container"""
    # Create container with initial capacity
    container = Container(capacity=5)
    container = interface.add_resource(resource=container)

    # Remove capacity limit
    interface.remove_capacity_limit(resource_id=container.resource_id)

    # Get updated container
    updated_container = interface.get_resource(resource_id=container.resource_id)
    assert updated_container.capacity is None


def test_remove_capacity_limit_no_capacity_set(interface: ResourceInterface) -> None:
    """Test removing capacity limit when none is set"""
    # Create container with no capacity
    container = Container()
    container = interface.add_resource(resource=container)

    # Attempt to remove non-existent capacity limit
    interface.remove_capacity_limit(resource_id=container.resource_id)

    # Get container and verify still None
    updated_container = interface.get_resource(resource_id=container.resource_id)
    assert updated_container.capacity is None


def test_remove_capacity_limit_invalid_resource(interface: ResourceInterface) -> None:
    """Test removing capacity limit from resource without capacity attribute"""
    # Create regular resource without capacity
    resource = Resource()
    resource = interface.add_resource(resource=resource)

    # Attempt to remove capacity limit from invalid resource
    with pytest.raises(ValueError) as exc_info:
        interface.remove_capacity_limit(resource_id=resource.resource_id)
    assert "has no capacity attribute" in str(exc_info.value)


def test_set_quantity(interface: ResourceInterface) -> None:
    """Test setting quantity of a container"""
    # Create container with initial quantity
    consumable = Consumable(quantity=0)
    consumable = interface.add_resource(resource=consumable)

    # Test changing quantity
    updated_resource = interface.set_quantity(
        resource_id=consumable.resource_id, quantity=5
    )
    assert updated_resource.quantity == 5


def test_set_quantity_with_capacity(interface: ResourceInterface) -> None:
    """Test setting quantity with capacity constraint"""
    # Create container with capacity limit
    consumable = Consumable(quantity=0, capacity=10)
    consumable = interface.add_resource(resource=consumable)

    # Test setting valid quantity within capacity
    updated_resource = interface.set_quantity(
        resource_id=consumable.resource_id, quantity=8
    )
    assert updated_resource.quantity == 8

    # Test setting quantity exceeding capacity
    with pytest.raises(ValueError) as exc_info:
        interface.set_quantity(resource_id=consumable.resource_id, quantity=15)
    assert "because it exceeds the capacity" in str(exc_info.value)


def test_set_quantity_invalid_resource(interface: ResourceInterface) -> None:
    """Test setting quantity on resource without quantity attribute"""
    # Create a resource type that doesn't have quantity attribute
    resource = Resource()
    resource = interface.add_resource(resource=resource)

    # Attempt to set quantity on invalid resource
    with pytest.raises(ValueError) as exc_info:
        interface.set_quantity(resource_id=resource.resource_id, quantity=5)
    assert "has no quantity attribute" in str(exc_info.value)


def test_set_quantity_read_only(interface: ResourceInterface) -> None:
    """Test setting quantity on resource with read-only quantity property"""
    # Note: This test requires a resource type with a read-only quantity property
    # Create a stack (which typically has a read-only quantity based on children)
    stack = Stack()
    stack = interface.add_resource(resource=stack)

    # Attempt to set quantity on resource with read-only quantity
    with pytest.raises(ValueError) as exc_info:
        interface.set_quantity(resource_id=stack.resource_id, quantity=5)
    assert "read-only quantity" in str(exc_info.value)


def test_set_quantity_float_value(interface: ResourceInterface) -> None:
    """Test setting quantity with float value"""
    # Create container
    consumable = ContinuousConsumable(quantity=0.0)
    consumable = interface.add_resource(resource=consumable)

    # Test setting float quantity
    updated_consumable = interface.set_quantity(
        resource_id=consumable.resource_id, quantity=3.5
    )
    assert updated_consumable.quantity == 3.5


def test_set_child_row(interface: ResourceInterface) -> None:
    """Test setting a child in a row container"""

    row = Row(row_dimension=1)
    row = interface.add_resource(resource=row)

    resource = Resource()
    row_result = interface.set_child(
        container_id=row.resource_id, key=0, child=resource
    )

    assert row_result.children[0].resource_id == resource.resource_id

    with pytest.raises(KeyError):
        interface.set_child(container_id=row.resource_id, key=1, child=resource)


def test_set_child_grid(interface: ResourceInterface) -> None:
    """Test setting a child in a grid container"""
    # Create grid container
    grid = Grid(row_dimension=1, column_dimension=1)
    grid = interface.add_resource(resource=grid)

    # Create child resource
    resource = Resource()
    resource = interface.add_resource(resource=resource)

    # Set child in grid container
    grid = interface.set_child(
        container_id=grid.resource_id, key=(0, 0), child=resource
    )

    # Verify child was set
    assert grid.children[0][0].resource_id == resource.resource_id

    with pytest.raises(KeyError):
        interface.set_child(container_id=grid.resource_id, key=(0, 1), child=resource)


def test_set_child_voxel_grid(interface: ResourceInterface) -> None:
    """Test setting a child in a voxel grid container"""
    # Create voxel grid container
    voxel_grid = VoxelGrid(row_dimension=1, column_dimension=1, layer_dimension=1)
    voxel_grid = interface.add_resource(resource=voxel_grid)

    # Create child resource
    resource = Resource()
    resource = interface.add_resource(resource=resource)

    # Set child in voxel grid container
    voxel_grid = interface.set_child(
        container_id=voxel_grid.resource_id, key=(0, 0, 0), child=resource
    )

    # Verify child was set
    assert voxel_grid.children[0][0][0].resource_id == resource.resource_id

    with pytest.raises(KeyError):
        interface.set_child(
            container_id=voxel_grid.resource_id, key=(0, 0, 1), child=resource
        )


def test_remove_resource(interface: ResourceInterface) -> None:
    """Test removing a resource"""
    resource = Resource()
    resource = interface.add_resource(resource=resource)
    removed_resource = interface.remove_resource(resource_id=resource.resource_id)
    assert removed_resource.resource_id == resource.resource_id
    assert removed_resource.removed is True

    fetched_resource = interface.get_resource(resource_id=resource.resource_id)
    assert fetched_resource is None


def test_remove_resource_with_children(interface: ResourceInterface) -> None:
    """Test removing a resource with children"""
    stack = Stack()
    resource1 = Resource()
    stack.children.append(resource1)
    stack = interface.add_resource(resource=stack)

    removed_stack = interface.remove_resource(resource_id=stack.resource_id)
    assert removed_stack.resource_id == stack.resource_id
    assert removed_stack.removed is True

    fetched_stack = interface.get_resource(resource_id=stack.resource_id)
    assert fetched_stack is None

    fetched_child = interface.get_resource(resource_id=resource1.resource_id)
    assert fetched_child is None


def test_restore_resource(interface: ResourceInterface) -> None:
    """Test restoring a removed resource"""
    resource = Resource()
    resource = interface.add_resource(resource=resource)
    interface.remove_resource(resource_id=resource.resource_id)

    restored_resource = interface.restore_resource(resource_id=resource.resource_id)
    assert restored_resource.resource_id == resource.resource_id
    assert restored_resource.removed is False

    fetched_resource = interface.get_resource(resource_id=resource.resource_id)
    assert fetched_resource.resource_id == resource.resource_id
    assert fetched_resource.removed is False


def test_restore_resource_with_children(interface: ResourceInterface) -> None:
    """Test restoring a removed resource with children"""
    stack = Stack()
    resource1 = Resource()
    stack.children.append(resource1)
    stack = interface.add_resource(resource=stack)
    interface.remove_resource(resource_id=stack.resource_id)

    restored_stack = interface.restore_resource(resource_id=stack.resource_id)
    assert restored_stack.resource_id == stack.resource_id
    assert restored_stack.removed is False

    fetched_stack = interface.get_resource(resource_id=stack.resource_id)
    assert fetched_stack.resource_id == stack.resource_id
    assert fetched_stack.removed is False

    fetched_child = interface.get_resource(resource_id=resource1.resource_id)
    assert fetched_child.resource_id == resource1.resource_id
    assert fetched_child.removed is False


def test_empty_container(interface: ResourceInterface) -> None:
    """Test emptying a container"""
    container = Container()
    resource1 = Resource()
    resource2 = Resource()
    container = interface.add_resource(resource=container)
    container = interface.set_child(
        container_id=container.resource_id, key="slot1", child=resource1
    )
    container = interface.set_child(
        container_id=container.resource_id, key="slot2", child=resource2
    )

    # Verify initial state
    assert len(container.children) == 2
    assert container.quantity == 2

    # Empty the container
    emptied_container = interface.empty(resource_id=container.resource_id)

    # Verify container is empty
    assert len(emptied_container.children) == 0
    assert emptied_container.quantity == 0


def test_empty_consumable(interface: ResourceInterface) -> None:
    """Test emptying a consumable"""
    consumable = Consumable(quantity=10)
    consumable = interface.add_resource(resource=consumable)

    # Verify initial state
    assert consumable.quantity == 10

    # Empty the consumable
    emptied_consumable = interface.empty(resource_id=consumable.resource_id)

    # Verify consumable is empty
    assert emptied_consumable.quantity == 0


def test_fill_consumable(interface: ResourceInterface) -> None:
    """Test filling a consumable"""
    consumable = Consumable(quantity=5, capacity=10)
    consumable = interface.add_resource(resource=consumable)

    # Verify initial state
    assert consumable.quantity == 5

    # Fill the consumable
    filled_consumable = interface.fill(resource_id=consumable.resource_id)

    # Verify consumable is filled to capacity
    assert filled_consumable.quantity == 10


def test_fill_consumable_no_capacity(interface: ResourceInterface) -> None:
    """Test filling a consumable with no capacity set"""
    consumable = Consumable(quantity=5)
    consumable = interface.add_resource(resource=consumable)

    # Verify initial state
    assert consumable.quantity == 5

    # Attempt to fill the consumable without capacity
    with pytest.raises(ValueError) as exc_info:
        interface.fill(resource_id=consumable.resource_id)
    assert "has no capacity limit set" in str(exc_info.value)


def test_push_pop_slot(interface: ResourceInterface) -> None:
    """Test pushing to and popping from a slot with capacity of 1"""
    # Create a slot with capacity 1
    slot = Slot()
    slot = interface.add_resource(resource=slot)

    # Create a resource and push it to the slot
    resource1 = Resource()
    slot = interface.push(parent_id=slot.resource_id, child=resource1)

    # Verify slot properties after push
    assert len(slot.children) == 1
    assert slot.quantity == 1
    assert slot.children[0].resource_id == resource1.resource_id

    # Attempt to push another resource to the full slot
    resource2 = Resource()
    with pytest.raises(ValueError) as exc_info:
        interface.push(parent_id=slot.resource_id, child=resource2)
    assert "because it is full" in str(exc_info.value)

    # Pop the resource from the slot
    popped_resource, slot = interface.pop(parent_id=slot.resource_id)

    # Verify slot properties after pop
    assert popped_resource.resource_id == resource1.resource_id
    assert len(slot.children) == 0
    assert slot.quantity == 0
