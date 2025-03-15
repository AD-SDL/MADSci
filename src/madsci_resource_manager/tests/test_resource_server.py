"""Automated pytest unit tests for the madsci resource manager's REST server."""

import pytest
from madsci.common.types.resource_types import (
    Consumable,
    Container,
    Grid,
    Queue,
    Resource,
    Row,
    Stack,
    VoxelGrid,
)
from madsci.common.types.resource_types.definitions import ResourceManagerDefinition
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.resource_manager.resource_server import (
    ResourceGetQuery,
    ResourceHistoryGetQuery,
    create_resource_server,
)
from madsci.resource_manager.resource_tables import (
    ResourceTable,
    create_session,
)
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import Engine
from sqlmodel import Session as SQLModelSession
from starlette.testclient import TestClient


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


@pytest.fixture
def test_client(interface: ResourceInterface) -> TestClient:
    """Resource ServerTest Client Fixture"""
    resource_manager_definition = ResourceManagerDefinition(
        name="Test Resource Manager"
    )
    app = create_resource_server(
        resource_manager_definition=resource_manager_definition,
        resource_interface=interface,
    )
    return TestClient(app)


def test_info(test_client: TestClient) -> None:
    """Test the root endpoint for the Resource Manager's server."""
    result = test_client.get("/info").json()
    ResourceManagerDefinition.model_validate(result)


def test_add_valid_resource(test_client: TestClient) -> None:
    """Test adding a valid resource"""
    resource1 = Resource()
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))

    response.raise_for_status()

    response = test_client.get(f"/resource/{resource1.resource_id}")

    response.raise_for_status()

    resource_result = Resource.model_validate(response.json())
    assert resource_result.resource_id == resource1.resource_id
    assert resource_result.resource_name == resource1.resource_name
    assert resource_result.base_type == resource1.base_type
    assert resource_result.created_at is not None
    assert resource_result.updated_at is not None
    assert resource_result.removed is False

    stack = Stack()
    resource2 = Resource()
    stack.children.append(resource2)
    Stack.model_validate(stack.model_dump(mode="json"))

    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()
    stack_result = Stack.model_validate(response.json())
    assert stack_result.resource_id == stack.resource_id
    assert stack_result.resource_name == stack.resource_name
    assert stack_result.base_type == stack.base_type
    assert stack_result.created_at is not None
    assert stack_result.updated_at is not None
    assert stack_result.removed is False
    assert len(stack_result.children) == 1
    assert stack_result.children[0].resource_id == resource2.resource_id


def test_add_invalid_resource(test_client: TestClient) -> None:
    """Test adding an invalid resource"""
    resource1 = Resource()
    json_dump = resource1.model_dump(mode="json")
    json_dump["base_type"] = "blah"
    response = test_client.post("/resource/add", json=json_dump)

    assert response.status_code == 422  # Unprocessable Entity

    response = test_client.post("/resource/add", json={})

    assert response.status_code == 422  # Unprocessable Entity


def test_update_resource(test_client: TestClient) -> None:
    """Test updating a resource"""
    # First add a resource
    resource1 = Resource()
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))
    response.raise_for_status()

    # Update the resource
    resource1.resource_name = "Updated Name"
    response = test_client.post(
        "/resource/update", json=resource1.model_dump(mode="json")
    )
    response.raise_for_status()

    # Verify the update
    response = test_client.get(f"/resource/{resource1.resource_id}")
    response.raise_for_status()
    updated_resource = Resource.model_validate(response.json())

    assert updated_resource.resource_id == resource1.resource_id
    assert updated_resource.resource_name == "Updated Name"
    assert updated_resource.base_type == resource1.base_type
    assert updated_resource.updated_at is not None
    assert updated_resource.removed is False


def test_update_nonexistent_resource(test_client: TestClient) -> None:
    """Test updating a resource that doesn't exist"""
    resource1 = Resource()
    response = test_client.post(
        "/resource/update", json=resource1.model_dump(mode="json")
    )
    assert response.status_code == 500


def test_remove_resource(test_client: TestClient) -> None:
    """Test removing a resource"""
    # First add a resource
    resource1 = Resource()
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))
    response.raise_for_status()

    # Remove the resource
    response = test_client.delete(f"/resource/{resource1.resource_id}")
    response.raise_for_status()

    # Verify resource is marked as removed
    removed_resource = Resource.model_validate(response.json())
    assert removed_resource.resource_id == resource1.resource_id
    assert removed_resource.removed is True

    # Verify resource is not found in main table
    response = test_client.get(f"/resource/{resource1.resource_id}")
    assert response.status_code == 404


def test_remove_nonexistent_resource(test_client: TestClient) -> None:
    """Test removing a resource that doesn't exist"""
    response = test_client.delete("/resource/nonexistent-id")
    assert response.status_code == 404


def test_query_resource(test_client: TestClient) -> None:
    """Test querying for a resource"""
    # First add a resource
    resource1 = Resource(resource_name="Test Resource")
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))
    response.raise_for_status()

    # Query for the resource by name
    query = ResourceGetQuery(resource_name="Test Resource").model_dump(mode="json")
    response = test_client.post("/resource/query", json=query)
    response.raise_for_status()

    # Verify the queried resource matches
    queried_resource = Resource.model_validate(response.json())
    assert queried_resource.resource_id == resource1.resource_id
    assert queried_resource.resource_name == resource1.resource_name


def test_query_nonexistent_resource(test_client: TestClient) -> None:
    """Test querying for a resource that doesn't exist"""
    query = ResourceGetQuery(resource_name="Nonexistent Resource").model_dump(
        mode="json"
    )
    response = test_client.post("/resource/query", json=query)
    assert response.status_code == 404


def test_query_resource_invalid_params(test_client: TestClient) -> None:
    """Test querying with invalid parameters"""
    query = {"invalid_param": "value"}
    response = test_client.post("/resource/query", json=query)
    assert response.status_code == 422  # Unprocessable Entity


def test_query_history(test_client: TestClient) -> None:
    """Test querying resource history"""
    # First add a resource
    resource1 = Resource(resource_name="History Test Resource")
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))
    response.raise_for_status()

    # Remove the resource to create history entry
    response = test_client.delete(f"/resource/{resource1.resource_id}")
    response.raise_for_status()

    # Query history
    query = ResourceHistoryGetQuery(resource_id=resource1.resource_id).model_dump(
        mode="json"
    )
    response = test_client.post("/history/query", json=query)
    response.raise_for_status()

    # Verify the history entries
    history_entries = response.json()
    assert len(history_entries) > 0
    assert history_entries[0]["resource_id"] == resource1.resource_id
    assert history_entries[0]["resource_name"] == resource1.resource_name


def test_query_history_nonexistent_resource(test_client: TestClient) -> None:
    """Test querying history for nonexistent resource"""
    query = ResourceHistoryGetQuery(resource_id="nonexistent-id").model_dump(
        mode="json"
    )
    response = test_client.post("/history/query", json=query)
    response.raise_for_status()
    assert len(response.json()) == 0


def test_query_history_invalid_params(test_client: TestClient) -> None:
    """Test querying history with invalid parameters"""
    query = {"invalid_param": "value"}
    response = test_client.post("/history/query", json=query)
    assert response.status_code == 422  # Unprocessable Entity


def test_restore_deleted_resource(test_client: TestClient) -> None:
    """Test restoring a previously deleted resource"""
    # First add a resource
    resource1 = Resource(resource_name="Resource to Restore")
    response = test_client.post("/resource/add", json=resource1.model_dump(mode="json"))
    response.raise_for_status()

    # Remove the resource
    response = test_client.delete(f"/resource/{resource1.resource_id}")
    response.raise_for_status()

    # Restore the resource
    response = test_client.post(f"/history/{resource1.resource_id}/restore")
    response.raise_for_status()

    # Verify the restored resource
    restored_resource = Resource.model_validate(response.json())
    assert restored_resource.resource_id == resource1.resource_id
    assert restored_resource.resource_name == resource1.resource_name
    assert restored_resource.removed is False

    # Verify resource is accessible again
    response = test_client.get(f"/resource/{resource1.resource_id}")
    response.raise_for_status()
    assert response.status_code == 200


def test_restore_nonexistent_resource(test_client: TestClient) -> None:
    """Test restoring a resource that doesn't exist in history"""
    response = test_client.post("/history/nonexistent-id/restore")
    assert response.status_code == 404


def test_push_to_stack(test_client: TestClient) -> None:
    """Test pushing a resource onto a stack"""
    # Create a stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()
    stack_id = stack.resource_id

    # Create a resource to push
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(f"/resource/{stack_id}/push", json=push_body)
    response.raise_for_status()

    # Verify the resource was pushed
    stack_result = Stack.model_validate(response.json())
    assert len(stack_result.children) == 1
    assert stack_result.children[0].resource_id == resource.resource_id


def test_push_to_queue(test_client: TestClient) -> None:
    """Test pushing a resource onto a queue"""
    # Create a queue
    queue = Queue()
    response = test_client.post("/resource/add", json=queue.model_dump(mode="json"))
    response.raise_for_status()
    queue_id = queue.resource_id

    # Create a resource to push
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(f"/resource/{queue_id}/push", json=push_body)
    response.raise_for_status()

    # Verify the resource was pushed
    queue_result = Queue.model_validate(response.json())
    assert len(queue_result.children) == 1
    assert queue_result.children[0].resource_id == resource.resource_id


def test_push_to_non_container(test_client: TestClient) -> None:
    """Test pushing a resource onto a non-container resource"""
    resource_parent = Resource()

    response = test_client.post(
        "/resource/add", json=resource_parent.model_dump(mode="json")
    )
    response.raise_for_status()

    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{resource_parent.resource_id}/push", json=push_body
    )
    assert response.status_code == 500


def test_push_to_wrong_container(test_client: TestClient) -> None:
    """Test pushing a resource onto a container that isn't a stack or queue"""
    # Create a non-stack, non-queue container
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Create a resource to push
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{container.resource_id}/push", json=push_body
    )
    assert response.status_code == 500


def test_push_existing_resource(test_client: TestClient) -> None:
    """Test pushing an existing resource onto a stack"""
    # Create a stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()
    stack_id = stack.resource_id

    # Create and add a resource
    resource = Resource()
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Push the existing resource using its ID
    push_body = {"child_id": resource.resource_id}
    response = test_client.post(f"/resource/{stack_id}/push", json=push_body)
    response.raise_for_status()

    # Verify the resource was pushed
    stack_result = Stack.model_validate(response.json())
    assert len(stack_result.children) == 1
    assert stack_result.children[0].resource_id == resource.resource_id


def test_push_to_nonexistent_container(test_client: TestClient) -> None:
    """Test pushing to a nonexistent container"""
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post("/resource/nonexistent-id/push", json=push_body)
    assert response.status_code == 500


def test_push_invalid_body(test_client: TestClient) -> None:
    """Test pushing with invalid body"""
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()
    stack_id = stack.resource_id

    # Try pushing with invalid body
    push_body = {"invalid_field": "value"}
    response = test_client.post(f"/resource/{stack_id}/push", json=push_body)
    assert response.status_code == 422  # Unprocessable Entity


def test_pop_from_stack(test_client: TestClient) -> None:
    """Test popping a resource from a stack"""
    # Create a stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()
    stack_id = stack.resource_id

    # Create and push a resource
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(f"/resource/{stack_id}/push", json=push_body)
    response.raise_for_status()

    # Pop the resource
    response = test_client.post(f"/resource/{stack_id}/pop")
    response.raise_for_status()

    # Verify the popped resource and updated stack
    popped_resource, updated_stack = response.json()
    assert Resource.model_validate(popped_resource).resource_id == resource.resource_id
    assert len(Stack.model_validate(updated_stack).children) == 0


def test_pop_from_queue(test_client: TestClient) -> None:
    """Test popping a resource from a queue"""
    # Create a queue
    queue = Queue()
    response = test_client.post("/resource/add", json=queue.model_dump(mode="json"))
    response.raise_for_status()
    queue_id = queue.resource_id

    # Create and push a resource
    resource = Resource()
    push_body = {"child": resource.model_dump(mode="json")}
    response = test_client.post(f"/resource/{queue_id}/push", json=push_body)
    response.raise_for_status()

    # Pop the resource
    response = test_client.post(f"/resource/{queue_id}/pop")
    response.raise_for_status()

    # Verify the popped resource and updated queue
    popped_resource, updated_queue = response.json()
    assert Resource.model_validate(popped_resource).resource_id == resource.resource_id
    assert len(Queue.model_validate(updated_queue).children) == 0


def test_pop_from_empty_container(test_client: TestClient) -> None:
    """Test popping from an empty container"""
    # Create an empty stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()

    # Try to pop from empty stack
    response = test_client.post(f"/resource/{stack.resource_id}/pop")
    assert response.status_code == 500


def test_pop_from_nonexistent_container(test_client: TestClient) -> None:
    """Test popping from a nonexistent container"""
    response = test_client.post("/resource/nonexistent-id/pop")
    assert response.status_code == 500


def test_pop_from_non_container(test_client: TestClient) -> None:
    """Test popping from a non-container resource"""
    # Create a regular resource
    resource = Resource()
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try to pop from non-container resource
    response = test_client.post(f"/resource/{resource.resource_id}/pop")
    assert response.status_code == 500


def test_pop_from_wrong_container(test_client: TestClient) -> None:
    """Test popping from a container that isn't a stack or queue"""
    # Create a non-stack, non-queue container
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Try to pop from non-stack, non-queue container
    response = test_client.post(f"/resource/{container.resource_id}/pop")
    assert response.status_code == 500


def test_set_child(test_client: TestClient) -> None:
    """Test setting a child resource in a container"""
    # Create a container
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Create child resource and set it
    resource = Resource()
    set_body = {"key": "test_key", "child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/set", json=set_body
    )
    response.raise_for_status()

    # Verify the child was set
    result = Container.model_validate(response.json())
    assert "test_key" in result.children
    assert result.children["test_key"].resource_id == resource.resource_id


def test_set_child_nonexistent_container(test_client: TestClient) -> None:
    """Test setting a child in a nonexistent container"""
    resource = Resource()
    set_body = {"key": "test_key", "child": resource.model_dump(mode="json")}
    response = test_client.post("/resource/nonexistent-id/child/set", json=set_body)
    assert response.status_code == 500


def test_set_child_invalid_container(test_client: TestClient) -> None:
    """Test setting a child in a non-container resource"""
    # Create a regular resource
    parent = Resource()
    response = test_client.post("/resource/add", json=parent.model_dump(mode="json"))
    response.raise_for_status()

    # Try to set child on non-container
    child = Resource()
    set_body = {"key": "test_key", "child": child.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{parent.resource_id}/child/set", json=set_body
    )
    assert response.status_code == 500


def test_set_child_invalid_body(test_client: TestClient) -> None:
    """Test setting a child with invalid request body"""
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting with invalid body
    invalid_body = {"invalid_field": "value"}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/set", json=invalid_body
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_set_child_row(test_client: TestClient) -> None:
    """Test setting a child resource of a grid"""

    row = Row(row_dimension=2)
    response = test_client.post("/resource/add", json=row.model_dump(mode="json"))
    response.raise_for_status()

    resource = Resource()
    set_body = {"key": 0, "child": resource.model_dump(mode="json")}
    response = test_client.post(f"/resource/{row.resource_id}/child/set", json=set_body)
    response.raise_for_status()

    result = Row.model_validate(response.json())
    assert result.children[0].resource_id == resource.resource_id


def test_set_child_grid(test_client: TestClient) -> None:
    """Test setting a child resource in a grid"""
    # Create a grid
    grid = Grid(row_dimension=2, column_dimension=2)
    response = test_client.post("/resource/add", json=grid.model_dump(mode="json"))
    response.raise_for_status()

    # Create child resource and set it
    resource = Resource()
    set_body = {"key": (0, 0), "child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{grid.resource_id}/child/set", json=set_body
    )
    response.raise_for_status()

    # Verify the child was set
    result = Grid.model_validate(response.json())
    assert result.children[0][0].resource_id == resource.resource_id


def test_set_child_voxel_grid(test_client: TestClient) -> None:
    """Test setting a child resource in a voxel grid"""
    # Create a voxel grid
    voxel_grid = VoxelGrid(row_dimension=2, column_dimension=2, layer_dimension=2)
    response = test_client.post(
        "/resource/add", json=voxel_grid.model_dump(mode="json")
    )
    response.raise_for_status()

    # Create child resource and set it
    resource = Resource()
    set_body = {"key": (0, 0, 0), "child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{voxel_grid.resource_id}/child/set", json=set_body
    )
    response.raise_for_status()

    # Verify the child was set
    result = VoxelGrid.model_validate(response.json())
    assert result.children[0][0][0].resource_id == resource.resource_id


def test_remove_child(test_client: TestClient) -> None:
    """Test removing a child resource from a container"""
    # Create a container
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Create and set child resource
    resource = Resource()
    set_body = {"key": "test_key", "child": resource.model_dump(mode="json")}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/set", json=set_body
    )
    response.raise_for_status()

    # Remove the child
    remove_body = {"key": "test_key"}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/remove", json=remove_body
    )
    response.raise_for_status()

    # Verify the child was removed
    result = Container.model_validate(response.json())
    assert "test_key" not in result.children


def test_remove_child_nonexistent_container(test_client: TestClient) -> None:
    """Test removing a child from a nonexistent container"""
    remove_body = {"key": "test_key"}
    response = test_client.post(
        "/resource/nonexistent-id/child/remove", json=remove_body
    )
    assert response.status_code == 500


def test_remove_child_invalid_container(test_client: TestClient) -> None:
    """Test removing a child from a non-container resource"""
    # Create a regular resource
    parent = Resource()
    response = test_client.post("/resource/add", json=parent.model_dump(mode="json"))
    response.raise_for_status()

    # Try to remove child from non-container
    remove_body = {"key": "test_key"}
    response = test_client.post(
        f"/resource/{parent.resource_id}/child/remove", json=remove_body
    )
    assert response.status_code == 500


def test_remove_child_invalid_body(test_client: TestClient) -> None:
    """Test removing a child with invalid request body"""
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Try removing with invalid body
    invalid_body = {"invalid_field": "value"}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/remove", json=invalid_body
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_remove_child_nonexistent_key(test_client: TestClient) -> None:
    """Test removing a child with a key that doesn't exist"""
    # Create a container
    container = Container()
    response = test_client.post("/resource/add", json=container.model_dump(mode="json"))
    response.raise_for_status()

    # Try to remove nonexistent child
    remove_body = {"key": "nonexistent_key"}
    response = test_client.post(
        f"/resource/{container.resource_id}/child/remove", json=remove_body
    )
    assert response.status_code == 500


def test_set_quantity(test_client: TestClient) -> None:
    """Test setting the quantity of a resource"""
    # Create a resource
    resource = Consumable(quantity=0)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Set quantity to integer value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity", params={"quantity": 42}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 42

    # Set quantity to float value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity", params={"quantity": 3.14}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 3.14


def test_set_quantity_nonexistent_resource(test_client: TestClient) -> None:
    """Test setting quantity for a nonexistent resource"""
    response = test_client.post(
        "/resource/nonexistent-id/quantity", params={"quantity": 42}
    )
    assert response.status_code == 500


def test_set_quantity_invalid_value(test_client: TestClient) -> None:
    """Test setting quantity with invalid value type"""
    # Create a resource
    resource = Consumable(quantity=0)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting invalid quantity value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity", params={"quantity": "invalid"}
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_set_quantity_stack_fails(test_client: TestClient) -> None:
    """Test setting quantity for a stack resource"""
    # Create a stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting quantity for stack
    response = test_client.post(
        f"/resource/{stack.resource_id}/quantity", params={"quantity": 42}
    )
    assert response.status_code == 500


def test_set_quantity_above_capacity(test_client: TestClient) -> None:
    """Test setting quantity above capacity"""
    # Create a consumable resource with capacity
    resource = Consumable(quantity=0, capacity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting quantity above capacity
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity", params={"quantity": 42}
    )
    assert response.status_code == 500


def test_set_capacity(test_client: TestClient) -> None:
    """Test setting the capacity of a resource"""
    # Create a resource
    resource = Consumable(quantity=0)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Set capacity to integer value
    response = test_client.post(
        f"/resource/{resource.resource_id}/capacity", params={"capacity": 42}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.capacity == 42

    # Set capacity to float value
    response = test_client.post(
        f"/resource/{resource.resource_id}/capacity", params={"capacity": 3.14}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.capacity == 3.14


def test_set_capacity_nonexistent_resource(test_client: TestClient) -> None:
    """Test setting capacity for a nonexistent resource"""
    response = test_client.post(
        "/resource/nonexistent-id/capacity", params={"capacity": 42}
    )
    assert response.status_code == 500


def test_set_capacity_invalid_value(test_client: TestClient) -> None:
    """Test setting capacity with invalid value type"""
    # Create a resource
    resource = Consumable(quantity=0)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting invalid capacity value
    response = test_client.post(
        f"/resource/{resource.resource_id}/capacity", params={"capacity": "invalid"}
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_set_capacity_stack(test_client: TestClient) -> None:
    """Test setting capacity for a stack resource"""
    # Create a stack
    stack = Stack()
    response = test_client.post("/resource/add", json=stack.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting capacity for stack
    response = test_client.post(
        f"/resource/{stack.resource_id}/capacity", params={"capacity": 42}
    )
    response.raise_for_status()
    result = Stack.model_validate(response.json())
    assert result.capacity == 42


def test_set_capacity_below_quantity(test_client: TestClient) -> None:
    """Test setting capacity below current quantity"""
    # Create a consumable resource with quantity
    resource = Consumable(quantity=5)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try setting capacity below quantity
    response = test_client.post(
        f"/resource/{resource.resource_id}/capacity", params={"capacity": 3}
    )
    assert response.status_code == 500


def test_remove_capacity_limit(test_client: TestClient) -> None:
    """Test removing the capacity limit of a resource"""
    # Create a resource with capacity
    resource = Consumable(quantity=5, capacity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Remove capacity limit
    response = test_client.delete(f"/resource/{resource.resource_id}/capacity")
    response.raise_for_status()

    # Verify capacity was removed
    result = Consumable.model_validate(response.json())
    assert result.capacity is None


def test_remove_capacity_limit_nonexistent_resource(test_client: TestClient) -> None:
    """Test removing capacity limit for a nonexistent resource"""
    response = test_client.delete("/resource/nonexistent-id/capacity")
    assert response.status_code == 500


def test_remove_capacity_limit_no_capacity(test_client: TestClient) -> None:
    """Test removing capacity limit from resource that has no capacity set"""
    # Create a resource without capacity
    resource = Consumable(quantity=5)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try removing non-existent capacity limit
    response = test_client.delete(f"/resource/{resource.resource_id}/capacity")
    response.raise_for_status()

    # Verify resource is unchanged
    result = Consumable.model_validate(response.json())
    assert result.capacity is None


def test_increase_quantity(test_client: TestClient) -> None:
    """Test increasing the quantity of a resource"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Increase quantity
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/increase", params={"amount": 5}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 15


def test_increase_quantity_nonexistent_resource(test_client: TestClient) -> None:
    """Test increasing quantity for a nonexistent resource"""
    response = test_client.post(
        "/resource/nonexistent-id/quantity/increase", params={"amount": 5}
    )
    assert response.status_code == 500


def test_increase_quantity_invalid_value(test_client: TestClient) -> None:
    """Test increasing quantity with invalid value type"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try increasing with invalid value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/increase",
        params={"amount": "invalid"},
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_decrease_quantity(test_client: TestClient) -> None:
    """Test decreasing the quantity of a resource"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Decrease quantity
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/decrease", params={"amount": 5}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 5


def test_decrease_quantity_nonexistent_resource(test_client: TestClient) -> None:
    """Test decreasing quantity for a nonexistent resource"""
    response = test_client.post(
        "/resource/nonexistent-id/quantity/decrease", params={"amount": 5}
    )
    assert response.status_code == 500


def test_decrease_quantity_invalid_value(test_client: TestClient) -> None:
    """Test decreasing quantity with invalid value type"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try decreasing with invalid value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/decrease",
        params={"amount": "invalid"},
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_change_quantity_by(test_client: TestClient) -> None:
    """Test changing the quantity of a resource by a given amount"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Change quantity by a positive amount
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/change_by", params={"amount": 5}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 15

    # Change quantity by a negative amount
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/change_by", params={"amount": -3}
    )
    response.raise_for_status()
    result = Consumable.model_validate(response.json())
    assert result.quantity == 12


def test_change_quantity_by_nonexistent_resource(test_client: TestClient) -> None:
    """Test changing quantity by a given amount for a nonexistent resource"""
    response = test_client.post(
        "/resource/nonexistent-id/quantity/change_by", params={"amount": 5}
    )
    assert response.status_code == 500


def test_change_quantity_by_invalid_value(test_client: TestClient) -> None:
    """Test changing quantity by a given amount with invalid value type"""
    # Create a resource
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Try changing quantity by invalid value
    response = test_client.post(
        f"/resource/{resource.resource_id}/quantity/change_by",
        params={"amount": "invalid"},
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_empty_resource(test_client: TestClient) -> None:
    """Test emptying the contents of a container or consumable resource"""
    # Create a consumable resource with quantity
    resource = Consumable(quantity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Empty the resource
    response = test_client.post(f"/resource/{resource.resource_id}/empty")
    response.raise_for_status()

    # Verify the resource is empty
    result = Consumable.model_validate(response.json())
    assert result.quantity == 0


def test_fill_resource(test_client: TestClient) -> None:
    """Test filling a consumable resource to capacity"""
    # Create a consumable resource with capacity
    resource = Consumable(quantity=5, capacity=10)
    response = test_client.post("/resource/add", json=resource.model_dump(mode="json"))
    response.raise_for_status()

    # Fill the resource
    response = test_client.post(f"/resource/{resource.resource_id}/fill")
    response.raise_for_status()

    # Verify the resource is filled to capacity
    result = Consumable.model_validate(response.json())
    assert result.quantity == 10
